from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class StrategyMode(StrEnum):
    BROAD_SMALL_SITE = "broad_small_site"
    TARGETED = "targeted"


class IndexRelation(StrEnum):
    INDEXED = "indexed"
    VARIANT = "variant"
    POSSIBLE_NEW = "possible_new"


class Availability(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    HANDOFF_ONLY = "handoff_only"
    UNAVAILABLE = "unavailable"
    NOT_OBSERVED = "not_observed"


class HandlingType(StrEnum):
    STATIC_PAGE = "static_page"
    STRUCTURED_PAGE = "structured_page"
    PDF = "pdf"
    HTML_FORM = "html_form"
    EXTERNAL_HANDOFF = "external_handoff"
    LIVE_FEED = "live_feed"
    STRUCTURED_API = "structured_api"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class InteractionType(StrEnum):
    INFORMATION = "information"
    WAYFINDING = "wayfinding"
    REQUEST = "request"
    TRANSACTION = "transaction"


class SourceRole(StrEnum):
    MUNICIPAL_SERVICE_PAGE = "municipal_service_page"
    SERVICE_DIRECTORY = "service_directory"
    DEPARTMENT_PAGE = "department_page"
    CONTACT_PAGE = "contact_page"
    FORM = "form"
    APPLICATION_PDF = "application_pdf"
    INFORMATION_PDF = "information_pdf"
    CALENDAR_PDF = "calendar_pdf"
    REGULATION_PDF = "regulation_pdf"
    OFFICIAL_HANDOFF = "official_handoff"
    LIVE_FEED = "live_feed"
    STRUCTURED_API = "structured_api"


class Municipality(BaseModel):
    name: str
    canton: str = Field(min_length=2, max_length=2)
    official_url: str


class BuildInfo(BaseModel):
    run_id: str
    scouted_at: datetime
    service_index_version: str


class ServiceIndexEntry(BaseModel):
    id: str
    labels: dict[str, list[str]]
    hints: list[str] = []


class ServiceIndex(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_version: Literal["service-index/v1"] = Field(
        default="service-index/v1", alias="schema"
    )
    version: str
    services: list[ServiceIndexEntry]

    @property
    def schema(self) -> str:  # type: ignore[override]
        return self.schema_version


class ReconResult(BaseModel):
    entrypoint: str
    title: str | None = None
    language: str | None = None
    internal_links: int = 0
    service_directory_candidates: list[str] = []
    sampled_links: list[str] = []
    notes: list[str] = []


class ScoutStrategy(BaseModel):
    mode: StrategyMode
    reason: str
    roots: list[str]
    max_pages: int = Field(ge=1, le=100)
    max_depth: int = Field(ge=0, le=5)
    target_services: list[str] = []


class SourceRef(BaseModel):
    source_id: str
    url: str
    role: SourceRole
    retrieved_at: datetime | None = None
    discovered_from: str | None = None


class ScoutFinding(BaseModel):
    service_id: str | None = None
    local_name: str
    index_relation: IndexRelation
    source_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    evidence_excerpt: str | None = None


class Handling(BaseModel):
    type: HandlingType
    interaction: InteractionType
    summary: str
    live: bool = False
    external_system: str | None = None


class InformationCoverage(BaseModel):
    available: bool
    structured: bool = False


class ServiceInterpretation(BaseModel):
    service_id: str | None = None
    local_name: str
    index_relation: IndexRelation
    availability: Availability
    handling: Handling
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = []


class MunicipalityService(BaseModel):
    service_id: str | None = None
    local_name: str
    index_relation: IndexRelation
    availability: Availability
    handling: Handling
    sources: list[SourceRef] = []
    information: InformationCoverage
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = []


class CatalogSuggestion(BaseModel):
    local_name: str
    proposal: Literal["possible_new_service", "possible_variant"]
    reason: str
    source_ids: list[str]
    confidence: float = Field(ge=0, le=1)


class CoverageSummary(BaseModel):
    indexed_services_checked: int
    supported: int = 0
    partial: int = 0
    handoff_only: int = 0
    unavailable: int = 0
    not_observed: int = 0
    new_candidates: int = 0


class DiscoveryFailure(BaseModel):
    url: AnyHttpUrl | None = None
    stage: str
    error: str


class MunicipalityDiscovery(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_version: Literal["municipality-discovery/v1"] = Field(
        default="municipality-discovery/v1", alias="schema"
    )
    municipality: Municipality
    build: BuildInfo
    strategy: ScoutStrategy
    services: list[MunicipalityService]
    catalog_suggestions: list[CatalogSuggestion] = []
    coverage: CoverageSummary
    failures: list[DiscoveryFailure] = []

    @property
    def schema(self) -> str:  # type: ignore[override]
        return self.schema_version
