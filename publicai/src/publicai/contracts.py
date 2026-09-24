"""Versioned municipal snapshot contracts and deterministic evidence checks."""

import hashlib
import ipaddress
import re
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import parse_qsl, unquote, urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

CONTRACT_VERSION = "1.0"
ALLOWED_HOST = "www.ausserberg.ch"
type CapabilityId = Literal[
    "office_hours", "garbage_collection", "recycling", "move_in", "move_out", "problem_reporting"
]
CAPABILITY_IDS: tuple[CapabilityId, ...] = (
    "office_hours",
    "garbage_collection",
    "recycling",
    "move_in",
    "move_out",
    "problem_reporting",
)
type Coverage = Literal["supported", "partial", "handoff_only", "unavailable"]
type MissingReason = Literal[
    "not_found",
    "blocked",
    "crawl_limit",
    "pdf_uninspected",
    "conflicting_evidence",
    "explicitly_not_offered",
    "inaccessible",
    "ical_uninspected",
    "javascript_required",
]
type Nonempty = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)
]
type Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,120}$")]


class StrictModel(BaseModel):
    """Reject unknown fields at every artifact boundary."""

    model_config = ConfigDict(extra="forbid")


class EvidenceRef(StrictModel):
    """An exact, whitespace-normalized excerpt from one retained source."""

    source_id: Identifier
    excerpt: Nonempty


class Fact(StrictModel):
    """A source-language claim with one or more retained supporting excerpts."""

    value: Nonempty
    evidence: list[EvidenceRef] = Field(min_length=1)


class DateFact(StrictModel):
    """An explicitly published date, never expanded from recurring prose."""

    value: date
    evidence: list[EvidenceRef] = Field(min_length=1)


class LinkedDocument(StrictModel):
    """Observed document metadata; its contents have never been retrieved or interpreted."""

    title: Fact | None = None
    url: Fact
    kind: Literal["pdf", "calendar"]
    status: Literal["uninspected"] = "uninspected"


class ObservedFormField(StrictModel):
    """Visible label and observed HTML required marker, never a procedural requirement."""

    label: Fact
    required_marker: bool = False


class SourceSnapshot(StrictModel):
    """Relevant public text retained by the trusted fetcher, with its digest."""

    id: Identifier
    url: Nonempty
    title: str = Field(max_length=1000)
    text: str = Field(min_length=1, max_length=5 * 1024 * 1024)
    retrieved_at: AwareDatetime
    sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    kind: Literal["homepage", "contact", "service"] = "service"
    links: list[str] = Field(default_factory=list)
    documents: list[LinkedDocument] = Field(default_factory=list)
    form_fields: list[ObservedFormField] = Field(default_factory=list)
    authentication_observed: bool = False

    @model_validator(mode="after")
    def verify_snapshot(self) -> Self:
        """Check the exact retained bytes and the deployment's host restriction."""
        validate_url(self.url, municipality_only=True)
        if self.kind == "homepage" and urlsplit(self.url).path not in {"", "/"}:
            raise ValueError("A homepage source must be the municipality's root homepage URL.")
        if hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("Source content hash does not match retained text.")
        for link in self.links:
            validate_url(link)
        for document in self.documents:
            if document.url.value not in self.links:
                raise ValueError("Document destinations must occur in the source's observed links.")
            if any(ref.source_id != self.id for ref in evidence_refs(document)):
                raise ValueError("Document metadata must cite its referring source.")
        return self


class Requirement(StrictModel):
    """One published requirement together with all its known conditions."""

    text: Fact
    conditions: list[Fact] = Field(default_factory=list)


class ServiceEntry(StrictModel):
    """An evidence-backed office, waste stream, procedure or reporting category."""

    id: Identifier
    label: Fact
    hours: list[Fact] = Field(default_factory=list)
    contacts: list[Fact] = Field(default_factory=list)
    instructions: list[Fact] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    locations: list[Fact] = Field(default_factory=list)
    materials: list[Fact] = Field(default_factory=list)
    purpose: Fact | None = None
    zone: Fact | None = None
    dates: list[DateFact] = Field(default_factory=list)
    form_fields: list[Fact] = Field(default_factory=list)


class Conflict(StrictModel):
    """Unresolved alternative claims excluded from definitive answers."""

    field: Nonempty
    claims: list[Fact] = Field(min_length=2)


class Capability(StrictModel):
    """One fixed catalogue capability, including coverage and known gaps."""

    coverage: Coverage
    entries: list[ServiceEntry] = Field(default_factory=list)
    handoffs: list[Fact] = Field(
        default_factory=list,
        description="Official service destination URLs only, with evidence from the linking page. "
        "The fact value must be an exact URL without labels or explanatory prose.",
    )
    missing_reasons: list[MissingReason] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    valid_from: DateFact | None = None
    valid_to: DateFact | None = None
    delivery_shapes: list[
        Literal[
            "information_page", "html_form", "document_link", "external_portal", "structured_source"
        ]
    ] = Field(default_factory=list)
    zone_required: bool = False
    not_offered_evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        """Reject contradictory dates, duplicate identifiers and uncited denials."""
        if self.valid_from and self.valid_to and self.valid_from.value > self.valid_to.value:
            raise ValueError("Published validity boundaries are reversed.")
        if len({entry.id for entry in self.entries}) != len(self.entries):
            raise ValueError("Service entry ids must be unique within a capability.")
        if "explicitly_not_offered" in self.missing_reasons and not self.not_offered_evidence:
            raise ValueError("explicitly_not_offered requires direct evidence.")
        return self


class MunicipalityIdentity(StrictModel):
    """Website consistency evidence; this does not prove independent authenticity."""

    name: Fact
    contact: Fact
    language: Literal["de"] = "de"


class DiscoveryFailure(StrictModel):
    """A sanitized acquisition failure without credentials or response bodies."""

    url: str
    reason: str
    detail: str = ""


class ReviewMetadata(StrictModel):
    """Best-effort semantic review status, separate from deterministic checks."""

    status: Literal["pending", "passed", "failed"] = "pending"
    agent: str = ""
    checked_at: AwareDatetime | None = None
    issues: list[str] = Field(default_factory=list)


class Discovery(StrictModel):
    """Complete versioned input to the offline deterministic package builder."""

    contract_version: Literal["1.0"]
    discovery_id: Identifier
    created_at: AwareDatetime
    official_url: Nonempty
    identity: MunicipalityIdentity
    capabilities: dict[CapabilityId, Capability]
    sources: list[SourceSnapshot] = Field(min_length=2, max_length=100)
    failures: list[DiscoveryFailure] = Field(default_factory=list)
    review: ReviewMetadata = Field(default_factory=ReviewMetadata)

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        """Validate identities, citations, boundaries and minimum service coverage."""
        validate_url(self.official_url, municipality_only=True)
        if set(self.capabilities) != set(CAPABILITY_IDS):
            raise ValueError("The discovery must include exactly all six capabilities.")
        sources = {source.id: source for source in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Source ids must be unique.")
        for ref in evidence_refs(self):
            source = sources.get(ref.source_id)
            if source is None:
                raise ValueError(f"Unknown evidence source: {ref.source_id}.")
            if normalize_whitespace(ref.excerpt) not in normalize_whitespace(source.text):
                raise ValueError(f"Evidence excerpt is absent from source {ref.source_id}.")
        name = normalize_whitespace(self.identity.name.value).casefold()
        identity_sources = {
            ref.source_id
            for ref in self.identity.name.evidence
            if name in normalize_whitespace(ref.excerpt).casefold()
        }
        home_sources = {sid for sid in identity_sources if sources[sid].kind == "homepage"}
        contact_sources = {sid for sid in identity_sources if sources[sid].kind == "contact"}
        distinct_identity_urls = {
            (
                urlsplit(sources[source_id].url).hostname,
                urlsplit(sources[source_id].url).path.rstrip("/"),
            )
            for source_id in identity_sources
        }
        if not home_sources or not contact_sources or len(distinct_identity_urls) < 2:
            raise ValueError(
                "Municipality identity must match distinct homepage and contact sources."
            )
        if not any(
            sources[ref.source_id].kind == "contact" for ref in self.identity.contact.evidence
        ):
            raise ValueError("Official contact must cite a contact or imprint source.")
        for capability_id, capability in self.capabilities.items():
            expected = classify_coverage(capability_id, capability)
            if capability.coverage != expected:
                raise ValueError(
                    f"{capability_id} coverage must be {expected} for its supplied facts."
                )
            disputed = {
                normalize_whitespace(claim.value).casefold()
                for conflict in capability.conflicts
                for claim in conflict.claims
            }
            definitive = [
                *facts(capability.entries),
                *capability.handoffs,
                *facts(capability.valid_from),
                *facts(capability.valid_to),
            ]
            if disputed.intersection(
                normalize_whitespace(str(fact.value)).casefold() for fact in definitive
            ):
                raise ValueError("A disputed claim must be absent from definitive service facts.")
            for handoff in capability.handoffs:
                try:
                    validate_url(handoff.value)
                except ValueError as error:
                    raise ValueError(f"Invalid {capability_id} handoff URL: {error}") from error
                if urlsplit(handoff.value).path in {"", "/"} and not urlsplit(handoff.value).query:
                    raise ValueError(
                        "Official handoffs must identify a service-specific destination."
                    )
                if not any(
                    handoff.value in sources[ref.source_id].links for ref in handoff.evidence
                ):
                    raise ValueError(
                        "Official handoffs must be linked by their cited retained source."
                    )
        return self


def normalize_whitespace(value: str) -> str:
    """Normalize whitespace only, retaining punctuation and factual content."""
    return re.sub(r"\s+", " ", value).strip()


def validate_url(value: str, *, municipality_only: bool = False) -> None:
    """Validate URL syntax; fetching additionally requires connection-time protection."""
    if re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValueError("URL contains whitespace or unsafe characters.")
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.port not in {None, 443 if url.scheme == "https" else 80}
    ):
        raise ValueError("Only credential-free public HTTP(S) URLs on standard ports are allowed.")
    unsafe_path = r"[\x00-\x20\x7f\\;]" if municipality_only else r"[\x00-\x1f\x7f\\;]"
    if (
        (url.query and (municipality_only or not is_public_document_link(value)))
        or url.fragment
        or re.search(unsafe_path, unquote(url.path))
    ):
        raise ValueError("Query strings, fragments and unsafe path parameters are forbidden.")
    hostname = url.hostname.lower().removesuffix(".")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        ascii_host = hostname.encode("idna").decode("ascii")
        labels = ascii_host.split(".")
        if (
            "." not in hostname
            or hostname.endswith((".localhost", ".local", ".internal"))
            or len(ascii_host) > 253
            or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
            )
            or all(re.fullmatch(r"(?:0x[a-f0-9]+|\d+)", label) for label in labels)
        ):
            raise ValueError("Local or ambiguous network destinations are forbidden.") from None
    else:
        if (
            not address.is_global
            or address.is_multicast
            or address.is_reserved
            or getattr(address, "ipv4_mapped", None)
        ):
            raise ValueError("Nonpublic IP destinations are forbidden.")
    if municipality_only and url.hostname.lower() != ALLOWED_HOST:
        raise ValueError(f"Source URLs must use the authorized host {ALLOWED_HOST}.")


def is_public_document_link(value: str) -> bool:
    """Recognize Ausserberg's observed public download route for link-only handoffs.

    This exception never authorizes retrieval. Fetch URLs remain query-free.
    Duplicate keys, unknown parameters and arbitrary session values are rejected.
    """
    url = urlsplit(value)
    if url.hostname != ALLOWED_HOST or url.path not in {"", "/"} or len(url.query) > 256:
        return False
    try:
        pairs = parse_qsl(url.query, strict_parsing=True)
    except ValueError:
        return False
    params = dict(pairs)
    return (
        len(pairs) == 3
        and set(params) == {"action", "id", "resource_link_id"}
        and params["action"] == "get_file"
        and re.fullmatch(r"[0-9]{1,12}", params["id"]) is not None
        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", params["resource_link_id"]) is not None
    )


def evidence_refs(value: object) -> list[EvidenceRef]:
    """Collect citations from typed artifact data without inspecting arbitrary objects."""
    if isinstance(value, EvidenceRef):
        return [value]
    if isinstance(value, BaseModel):
        return [
            ref for name in type(value).model_fields for ref in evidence_refs(getattr(value, name))
        ]
    if isinstance(value, dict):
        return [ref for child in value.values() for ref in evidence_refs(child)]
    if isinstance(value, list):
        return [ref for child in value for ref in evidence_refs(child)]
    return []


def facts(value: object) -> list[Fact | DateFact]:
    """Collect typed claims for reports and conflict validation."""
    if isinstance(value, Fact | DateFact):
        return [value]
    if isinstance(value, BaseModel):
        return [fact for name in type(value).model_fields for fact in facts(getattr(value, name))]
    if isinstance(value, dict):
        return [fact for child in value.values() for fact in facts(child)]
    if isinstance(value, list):
        return [fact for child in value for fact in facts(child)]
    return []


def classify_coverage(capability_id: CapabilityId, capability: Capability) -> Coverage:
    """Derive coverage from the catalogue's independently defined minimums."""
    entries = capability.entries
    if capability_id == "office_hours":
        minimum = any(entry.hours and entry.contacts for entry in entries)
    elif capability_id == "garbage_collection":
        minimum = any(entry.instructions for entry in entries)
    elif capability_id == "recycling":
        minimum = any(entry.instructions or entry.locations for entry in entries)
    elif capability_id in {"move_in", "move_out"}:
        minimum = any(entry.instructions or entry.requirements for entry in entries) and (
            bool(capability.handoffs) or any(entry.contacts for entry in entries)
        )
    else:
        minimum = any(entry.contacts and entry.purpose for entry in entries)
    if minimum and not capability.conflicts:
        return "supported"
    substantive = any(
        entry.hours
        or entry.contacts
        or entry.instructions
        or entry.requirements
        or entry.locations
        or entry.materials
        or entry.purpose
        or entry.dates
        or entry.form_fields
        for entry in entries
    )
    if substantive or capability.conflicts:
        return "partial"
    if capability.handoffs:
        return "handoff_only"
    return "unavailable"


def load_discovery(path: Path) -> Discovery:
    """Load a discovery artifact with full deterministic validation."""
    return Discovery.model_validate_json(path.read_text(encoding="utf-8"))


def packaging_issues(discovery: Discovery) -> list[str]:
    """Return review and utility failures separate from schema validity."""
    issues = []
    if discovery.review.status != "passed" or discovery.review.issues:
        issues.append("Semantic review must pass before packaging.")
    if not any(
        item.handoffs
        or any(
            entry.hours
            or entry.contacts
            or entry.instructions
            or entry.requirements
            or entry.locations
            or entry.materials
            or entry.purpose
            or entry.dates
            or entry.form_fields
            for entry in item.entries
        )
        for item in discovery.capabilities.values()
    ):
        issues.append("At least one evidence-backed capability or official handoff is required.")
    return issues
