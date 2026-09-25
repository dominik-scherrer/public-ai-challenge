"""Injection / safety check — ADR-0007.

"The Judge additionally runs an injection check that flags — never passes
through — instructions to a model, foreign-domain links and payment
details."

Deterministic checks run first and always (cheap, reliable, no model
needed — consistent with the small-model/deterministic-runtime split in
pipeline/PROVENANCE_AND_TRUST.md and pipeline/ARCHITECTURE.md: "use the
cheapest sufficient tool"). The LLM check in llm.py's injection_judge
rubric is a second pass over free-text fields only, for the case a
deterministic pattern can't catch: text written to manipulate a model
reading it, not a human.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from public_ai_challenge.phase3_judge.schemas import Claim, InjectionFinding

# Conservative IBAN pattern (CH + 19 digits, or general IBAN shape) and a
# generic long-digit-run check for card-like numbers. False positives here
# are cheap (they just get flagged for review); false negatives aren't.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_CARD_LIKE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

_INJECTION_KEYWORDS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "system prompt",
    "as an ai",
    "act as",
    "new instructions:",
)


def _own_domain(url: str, municipality_domain: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    domain = municipality_domain.lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain) or host == "www." + domain


def check_foreign_links(text: str, municipality_domain: str) -> list[str]:
    """Returns any http(s) URLs in `text` that are not on the municipality's own domain."""
    urls = re.findall(r"https?://[^\s)\]\"']+", text)
    return [u for u in urls if not _own_domain(u, municipality_domain)]


def check_payment_details(text: str) -> bool:
    return bool(_IBAN_RE.search(text) or _CARD_LIKE_RE.search(text))


def check_injection_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in _INJECTION_KEYWORDS)


def deterministic_check(claim: Claim, municipality_domain: str) -> InjectionFinding | None:
    """Runs the cheap checks. Returns a flagged finding, or None if clean.

    Only inspects text; run this on every claim regardless of `is_free_text`
    — a foreign link or payment detail is dangerous in a structured field
    too (e.g. a "fee payment link"), not only in prose.
    """
    text = str(claim.value)

    foreign_links = check_foreign_links(text, municipality_domain)
    if foreign_links:
        return InjectionFinding(
            claim=claim,
            flagged=True,
            category="foreign_domain_link",
            reason=f"Links to non-municipality domain(s): {', '.join(foreign_links)}",
            detector="deterministic",
        )

    if check_payment_details(text):
        return InjectionFinding(
            claim=claim,
            flagged=True,
            category="payment_details",
            reason="Text matches an IBAN- or card-number-like pattern.",
            detector="deterministic",
        )

    if check_injection_keywords(text):
        return InjectionFinding(
            claim=claim,
            flagged=True,
            category="instruction_injection",
            reason="Text matches a known prompt-injection phrase.",
            detector="deterministic",
        )

    return None
