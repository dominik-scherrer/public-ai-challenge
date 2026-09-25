"""Adapter exposing phase1_scout_pipeline through ScoutProtocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from public_ai_challenge.core.interfaces import ScoutProtocol
from public_ai_challenge.core.models import ScoutedServiceRecord, ScoutResult

from .app import run_scout
from .contracts import Availability, MunicipalityDiscovery


class ScoutPipelineAdapter(ScoutProtocol):
    """Adapter that executes the Phase 1 Scout pipeline and returns a normalized ScoutResult."""

    def __init__(self, use_agent: bool = False) -> None:
        self.use_agent = use_agent

    async def scout(
        self,
        url: str,
        municipality: str,
        canton: str,
        output_dir: Path | str | None = None,
    ) -> ScoutResult:
        out_path = Path(output_dir) if output_dir else Path("output/scout")
        out_path.mkdir(parents=True, exist_ok=True)

        discovery: MunicipalityDiscovery = await run_scout(
            url=url,
            municipality=municipality,
            canton=canton,
            out_dir=out_path,
            use_agent=self.use_agent,
        )

        return self.to_scout_result(discovery)

    @staticmethod
    def to_scout_result(discovery: MunicipalityDiscovery) -> ScoutResult:
        records: list[ScoutedServiceRecord] = []
        for s in discovery.services:
            urls = [source.url for source in s.sources if source.url]
            is_available = s.availability in (
                Availability.SUPPORTED,
                Availability.PARTIAL,
                Availability.HANDOFF_ONLY,
            )
            records.append(
                ScoutedServiceRecord(
                    name=s.local_name,
                    description=s.handling.summary or "",
                    urls=urls,
                    available=is_available,
                    metadata={
                        "service_id": s.service_id,
                        "availability": s.availability.value,
                        "handling_type": s.handling.type.value,
                        "interaction": s.handling.interaction.value,
                        "confidence": s.confidence,
                    },
                )
            )

        return ScoutResult(
            municipality_name=discovery.municipality.name,
            canton=discovery.municipality.canton,
            official_url=discovery.municipality.official_url,
            services=records,
            raw_discovery=discovery,
        )


class FileScoutAdapter(ScoutProtocol):
    """Adapter that loads scouted services from a static JSON file (for offline/demo runs)."""

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path)

    async def scout(
        self,
        url: str,
        municipality: str,
        canton: str,
        output_dir: Path | str | None = None,
    ) -> ScoutResult:
        import json

        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        records: list[ScoutedServiceRecord] = []

        # Check if format is raw list of services or MunicipalityDiscovery
        if isinstance(data, list):
            for item in data:
                records.append(
                    ScoutedServiceRecord(
                        name=item.get("name", "Unknown"),
                        description=item.get("description", ""),
                        urls=item.get("urls", []),
                        available=item.get("available", True),
                    )
                )
        elif isinstance(data, dict) and "services" in data:
            discovery = MunicipalityDiscovery.model_validate(data)
            return ScoutPipelineAdapter.to_scout_result(discovery)

        return ScoutResult(
            municipality_name=municipality,
            canton=canton,
            official_url=url,
            services=records,
            raw_discovery=data,
        )

