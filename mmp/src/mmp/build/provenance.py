"""Deterministic provenance gate — runs before the Judge, needs no model.

For every attribute a draft proposes:

1. each evidence quote must occur literally (whitespace-normalized) in the text
   of the Source it names — otherwise the quote is invented;
2. the attribute's *value* must be visible in its quotes (the fee amount, the
   deadline's number of days, the phone number, the e-mail, most words of a
   document label) — otherwise the value is invented;
3. every URL must be on the Municipality's official domains or the operator
   allow-list (ADR-0007) and must have been observed on a retained page.

An attribute that fails becomes a Withheld Attribute (CONTEXT.md): the Service
still goes live without it. "Say less rather than say something wrong."
The Judge (``pipeline/judge``) then checks the survivors semantically.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from mmp.build.pages import Page
from mmp.schema import (
    Contact,
    Deadline,
    Evidence,
    Fee,
    Handoff,
    OpeningHours,
    RequiredDocument,
    Service,
    WithheldAttribute,
    domain_allowed,
    normalize_ws,
)


def _norm(text: str) -> str:
    return normalize_ws(text).casefold()


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


class ProvenanceChecker:
    def __init__(self, pages: list[Page], official_domains: list[str], allowlist: list[str]):
        self.pages = {p.id: p for p in pages}
        self._norm_text = {p.id: _norm(p.text) for p in pages}
        self.official_domains = list(official_domains)
        self.link_domains = list(official_domains) + list(allowlist)
        observed: set[str] = set()
        for page in pages:
            observed.add(page.url.rstrip("/"))
            observed.update(link.url.rstrip("/") for link in page.links)
            observed.update(u.rstrip("/.") for u in re.findall(r"https?://[^\s)\]\"']+", page.text))
        self.observed_urls = observed

    # -- primitive checks -------------------------------------------------
    def quotes_ok(self, evidence: list[Evidence]) -> str | None:
        if not evidence:
            return "no source quote"
        for item in evidence:
            if item.source_id not in self.pages:
                return f"quote cites unknown source '{item.source_id}'"
            if _norm(item.quote) not in self._norm_text[item.source_id]:
                return "quote not found verbatim in the retained source text"
        return None

    @staticmethod
    def _joined(evidence: list[Evidence]) -> str:
        return " ".join(item.quote for item in evidence)

    def value_visible(self, value: str, evidence: list[Evidence], *, min_share: float = 0.6) -> bool:
        quotes = _norm(self._joined(evidence))
        words = [w for w in re.findall(r"\w+", _norm(value)) if len(w) > 2]
        if not words:
            return True
        hits = sum(1 for w in words if w in quotes)
        return hits / len(words) >= min_share

    def url_ok(self, url: str) -> str | None:
        if not domain_allowed(url, self.link_domains):
            return f"link to non-municipal domain withheld (ADR-0007): {url}"
        if url.rstrip("/") not in self.observed_urls:
            return "link was not observed on any retained page"
        return None

    # -- attribute checks -------------------------------------------------
    def check_contact(self, contact: Contact) -> str | None:
        if problem := self.quotes_ok(contact.evidence):
            return problem
        quotes = self._joined(contact.evidence)
        if contact.phone and _digits(contact.phone)[-9:] not in _digits(quotes):
            return "phone number not in quote"
        if contact.email and contact.email.lower() not in quotes.lower():
            return "e-mail not in quote"
        if contact.url and (problem := self.url_ok(contact.url)):
            return problem
        return None

    def check_deadline(self, deadline: Deadline) -> str | None:
        if problem := self.quotes_ok(deadline.evidence):
            return problem
        if not re.search(rf"\b{deadline.days}\b", self._joined(deadline.evidence)):
            return "number of days not in quote"
        return None

    def check_fee(self, fee: Fee) -> str | None:
        if problem := self.quotes_ok(fee.evidence):
            return problem
        quotes = _norm(self._joined(fee.evidence))
        if fee.amount == 0:
            if not re.search(r"gratis|kostenlos|gebührenfrei|keine gebühr|gratuit|gratuito", quotes):
                return "fee marked free but quote does not say so"
            return None
        amounts = set()
        for match in re.findall(r"\d[\d'’]*(?:[.,]\d{1,2})?", quotes):
            try:
                amounts.add(Decimal(match.replace("'", "").replace("’", "").replace(",", ".")))
            except InvalidOperation:
                continue
        if fee.amount not in amounts:
            return "fee amount not in quote"
        return None

    def check_document(self, doc: RequiredDocument) -> str | None:
        if problem := self.quotes_ok(doc.evidence):
            return problem
        if not self.value_visible(doc.label, doc.evidence):
            return "document label not supported by quote"
        if doc.condition and not self.value_visible(doc.condition, doc.evidence, min_share=0.8):
            return "document condition not supported by quote"
        return None

    def check_hours(self, hours: OpeningHours) -> str | None:
        if problem := self.quotes_ok(hours.evidence):
            return problem
        digits = _digits(self._joined(hours.evidence))
        for entry in hours.entries:
            for times in entry.times:
                if _digits(times) not in digits:
                    return f"opening time '{times}' not in quote"
        return None

    def check_handoff(self, handoff: Handoff) -> str | None:
        if problem := self.quotes_ok(handoff.evidence):
            return problem
        if handoff.url and (problem := self.url_ok(handoff.url)):
            return problem
        return None


def _try(model, data: Any):
    try:
        return model.model_validate(data), None
    except ValidationError as error:
        first = error.errors()[0]
        return None, f"invalid {model.__name__}: {first.get('loc')} {first.get('msg')}"


def check_service(draft: dict[str, Any], checker: ProvenanceChecker) -> tuple[Service | None, list[str]]:
    """Validate one draft. Returns (Service or None, notes)."""
    notes: list[str] = []
    withheld: list[WithheldAttribute] = []
    data = {k: v for k, v in draft.items() if k not in {"source_ids", "withheld", "ech0070"}}

    def keep_single(field: str, model, check) -> None:
        if data.get(field) is None:
            return
        obj, problem = _try(model, data[field])
        if obj is not None:
            problem = check(obj)
        if problem:
            withheld.append(WithheldAttribute(field=field, reason=problem))
            data[field] = None
        else:
            data[field] = obj.model_dump(mode="json")

    def keep_list(field: str, model, check, key=None) -> None:
        key = key or (lambda i, raw: f"{field}[{i}]")
        kept = []
        for i, raw in enumerate(data.get(field) or []):
            obj, problem = _try(model, raw)
            if obj is not None:
                problem = check(obj)
            if problem:
                withheld.append(WithheldAttribute(field=key(i, raw), reason=problem))
            else:
                kept.append(obj.model_dump(mode="json"))
        data[field] = kept

    keep_single("responsible", Contact, checker.check_contact)
    keep_single("deadline", Deadline, checker.check_deadline)
    keep_single("opening_hours", OpeningHours, checker.check_hours)
    keep_list("fees", Fee, checker.check_fee)
    keep_list(
        "documents",
        RequiredDocument,
        checker.check_document,
        key=lambda i, raw: f"documents[{raw.get('id', i) if isinstance(raw, dict) else i}]",
    )
    keep_list("handoffs", Handoff, checker.check_handoff)

    summary_ev = [Evidence.model_validate(e) for e in data.get("summary_evidence") or []]
    if data.get("summary"):
        problem = checker.quotes_ok(summary_ev)
        if problem:
            withheld.append(WithheldAttribute(field="summary", reason=problem))
            data["summary"] = None
            data["summary_evidence"] = []

    used = []
    for attr in ("responsible", "deadline", "opening_hours"):
        if data.get(attr):
            used += [e["source_id"] for e in data[attr]["evidence"]]
    for attr in ("fees", "documents", "handoffs"):
        for item in data.get(attr) or []:
            used += [e["source_id"] for e in item["evidence"]]
    used += [e["source_id"] for e in data.get("summary_evidence") or []]
    data["source_ids"] = list(dict.fromkeys(used))
    data["withheld"] = [w.model_dump() for w in withheld]

    if not data["source_ids"]:
        notes.append(f"{draft.get('id')}: dropped — no attribute survived the provenance check")
        return None, notes
    service, problem = _try(Service, {k: v for k, v in data.items() if v is not None})
    if service is None:
        notes.append(f"{draft.get('id')}: dropped — {problem}")
        return None, notes
    notes.extend(f"{service.id}: withheld {w.field} ({w.reason})" for w in withheld)
    return service, notes
