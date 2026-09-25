"""Adapter exposing alternative_pipeline_publicai discovery through ScoutProtocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from public_ai_challenge.core.interfaces import ScoutProtocol
from public_ai_challenge.core.models import ScoutedServiceRecord, ScoutResult

from .contracts import Discovery


class PublicAIScoutAdapter(ScoutProtocol):
    """Adapter for Patrick's PublicAI discovery pipeline implementing ScoutProtocol."""

    def __init__(self, discovery_file: Path | str | None = None) -> None:
        self.discovery_file = Path(discovery_file) if discovery_file else None

    async def scout(
        self,
        url: str,
        municipality: str,
        canton: str,
        output_dir: Path | str | None = None,
    ) -> ScoutResult:
        if self.discovery_file and self.discovery_file.exists():
            data = json.loads(self.discovery_file.read_text(encoding="utf-8"))
            discovery = Discovery.model_validate(data)
            return self.to_scout_result(discovery)

        raise NotImplementedError(
            "Live PublicAI discovery execution requires explicit crawler settings; "
            "provide a discovery_file or use ScoutPipelineAdapter for live crawling."
        )

    @staticmethod
    def to_scout_result(discovery: Discovery) -> ScoutResult:
        records: list[ScoutedServiceRecord] = []
        sources_map = {s.id: s.url for s in discovery.sources}

        for cap_id, cap in discovery.capabilities.items():
            source_urls = [
                sources_map[ref.source_id]
                for ref in cap.evidence
                if ref.source_id in sources_map
            ]
            records.append(
                ScoutedServiceRecord(
                    name=cap_id.value,
                    description=cap.summary.value if hasattr(cap, "summary") else "",
                    urls=list(set(source_urls)),
                    available=cap.status.value in ("available", "partial"),
                    metadata={"status": cap.status.value},
                )
            )

        return ScoutResult(
            municipality_name=discovery.identity.name.value,
            canton="VS",  # Default or extracted
            official_url=discovery.official_url,
            services=records,
            raw_discovery=discovery,
        )
