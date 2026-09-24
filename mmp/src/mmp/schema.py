"""The MMP Service Inventory, version 1: typed data, never generated code.

Implements, in one place:

- ADR-0001: every Service carries an eCH-0070 mapping slot (``ech0070``); a
  Service with no verified match is ``unmapped``, never given an invented ID.
- ADR-0003: a Build produces *this* JSON document. One shared MMP server serves
  every Municipality's inventory, addressed by BFS-Gemeindenummer.
- ADR-0007: attributes are typed (fees are amount + currency, deadlines are a
  number of days, documents are items with an audience and an optional
  condition), free text is short, and every attribute points at the literal
  source quote that supports it (``Evidence``), so the Judge can check it
  attribute by attribute (ADR-0004).

Vocabulary follows ``docs/architecture/CONTEXT.md`` (Service, Build, Judge,
Withheld Attribute, Handoff, Service Card, ...).
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_ID = "mmp-inventory/v1"

MAX_FREE_TEXT = 400  # ADR-0007: free text is short


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def normalize_ws(text: str) -> str:
    """Whitespace-insensitive form used for literal quote matching."""
    return re.sub(r"\s+", " ", text).strip()


class Evidence(StrictModel):
    """A literal quote from one retained Source. The Build drops any attribute
    whose quote does not occur (whitespace-normalized) in that source's text."""

    source_id: str
    quote: str = Field(min_length=3, max_length=1200)


class Attribute(StrictModel):
    evidence: list[Evidence] = Field(min_length=1)


class Source(StrictModel):
    id: str
    url: str
    title: str = ""
    retrieved_at: datetime
    sha256: str
    capture_method: Literal["crawler", "browser_capture"]
    text: str = Field(description="Retained public text; the ground truth quotes are checked against.")


class Contact(Attribute):
    """An office, never a named person (data minimization)."""

    office: str = Field(max_length=160)
    phone: str | None = None
    email: str | None = None
    address: str | None = Field(default=None, max_length=200)
    url: str | None = None


class OpeningHoursEntry(StrictModel):
    days: str = Field(max_length=60, description="As written on the site, e.g. 'Dienstag - Freitag'")
    times: list[str] = Field(description="e.g. ['08.30 - 12.00', '13.30 - 16.00']")


class OpeningHours(Attribute):
    office: str = Field(max_length=160)
    entries: list[OpeningHoursEntry] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=MAX_FREE_TEXT)


class Deadline(Attribute):
    days: int = Field(ge=0, le=365)
    relative_to: Literal["move_in", "move_out", "event"]
    label: str = Field(max_length=160)


class Fee(Attribute):
    label: str = Field(max_length=160)
    amount: Decimal = Field(ge=0, description="0 means explicitly free of charge")
    currency: Literal["CHF"] = "CHF"
    unit: str | None = Field(default=None, max_length=80)


ConditionKey = Literal["if_available", "separated_parents", "divorced", "married", "from_abroad", "other"]


class RequiredDocument(Attribute):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str = Field(max_length=200)
    applies_to: Literal["each_person", "adult", "child", "household"] = "each_person"
    audience: Literal["all", "swiss", "foreign"] = "all"
    condition: str | None = Field(
        default=None,
        max_length=200,
        description="Only needed if this condition holds, verbatim from the site, e.g. "
        "'für Kinder von getrennt lebenden Eltern'. Matched against the Citizen's "
        "situation in the client, never on the server (ADR-0005).",
    )
    condition_key: ConditionKey | None = Field(
        default=None,
        description="The condition, typed (ADR-0007: controlled list), so the client can match it "
        "deterministically against what the Citizen stated instead of asking a model.",
    )


PrefillKey = Literal["move_date", "household_size", "adults", "children", "previous_municipality"]


class HandoffField(StrictModel):
    key: PrefillKey
    label: str = Field(max_length=120)


class Handoff(Attribute):
    """Where the Citizen acts themselves (CONTEXT.md: Handoff). Never a submission."""

    kind: Literal["online_form", "eumzug", "counter", "email", "phone", "download"]
    label: str = Field(max_length=160)
    url: str | None = None
    fields: list[HandoffField] = Field(
        default_factory=list, description="Facts the client may pre-fill, only from what the Citizen said."
    )


class Ech0070(StrictModel):
    status: Literal["mapped", "unmapped"] = "unmapped"
    id: str | None = Field(default=None, pattern=r"^\d{5}$")
    name: str | None = None

    @model_validator(mode="after")
    def _mapped_needs_id(self) -> "Ech0070":
        if (self.status == "mapped") != (self.id is not None):
            raise ValueError("A mapped Service needs a Leistungs-ID; an unmapped one must not have one")
        return self


class WithheldAttribute(StrictModel):
    field: str
    reason: str


class Service(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(max_length=120)
    tier: Literal["information", "wayfinding"]
    summary: str | None = Field(default=None, max_length=MAX_FREE_TEXT)
    summary_evidence: list[Evidence] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list, description="Coverage tags for the Judge")
    keywords: list[str] = Field(default_factory=list, description="Synonyms for find_service")
    ech0070: Ech0070 = Field(default_factory=Ech0070)
    responsible: Contact | None = None
    deadline: Deadline | None = None
    fees: list[Fee] = Field(default_factory=list)
    documents: list[RequiredDocument] = Field(default_factory=list)
    opening_hours: OpeningHours | None = None
    handoffs: list[Handoff] = Field(default_factory=list)
    source_ids: list[str] = Field(min_length=1)
    withheld: list[WithheldAttribute] = Field(default_factory=list)


class Municipality(StrictModel):
    bfs: int = Field(ge=1, le=9999)
    name: str
    canton: str = Field(pattern=r"^[A-Z]{2}$")
    website: str
    official_domains: list[str] = Field(min_length=1)
    languages: list[str] = Field(default_factory=lambda: ["de"])
    general_contact: Contact | None = None


class JudgeStatus(StrictModel):
    status: Literal["passed", "not_run", "dry_run"]
    models: list[str] = Field(default_factory=list)
    report: str | None = None
    coverage: float | None = None


class BuildInfo(StrictModel):
    id: str
    built_at: datetime
    method: Literal["crawler", "browser_capture"]
    extraction: str = Field(description="Which model (or 'manual') extracted the typed data")
    judge: JudgeStatus
    verified_by_municipality: bool = False  # OQ-1: no sign-off gate; label stays visible


class Inventory(StrictModel):
    schema_: Literal["mmp-inventory/v1"] = Field(default=SCHEMA_ID, alias="schema")
    municipality: Municipality
    build: BuildInfo
    sources: list[Source]
    services: list[Service]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def source(self, source_id: str) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)

    def service(self, service_id: str) -> Service | None:
        return next((s for s in self.services if s.id == service_id), None)

    def dump(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def domain_allowed(url: str, domains: list[str]) -> bool:
    """True if ``url`` is https(s) on one of ``domains`` or a subdomain of one."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in {"https", "http"} or parts.username or parts.password:
        return False
    host = (parts.hostname or "").lower()
    for domain in domains:
        d = domain.lower().removeprefix("www.")
        if host == d or host.endswith("." + d):
            return True
    return False
