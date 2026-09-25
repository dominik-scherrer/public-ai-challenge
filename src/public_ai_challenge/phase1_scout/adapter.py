"""Phase 1 Final Adapter: Scout discovery combined with SafeCrawler."""

import logging
from typing import Any

from public_ai_challenge.core.interfaces import ScoutProtocol
from public_ai_challenge.core.models import ScoutResult, ScoutedServiceRecord
from public_ai_challenge.phase1_scout.config import Settings
from public_ai_challenge.phase1_scout.crawler import SafeCrawler
from public_ai_challenge.phase1_scout.discovery import discover_findings
from public_ai_challenge.phase1_scout.agents import inspect_service
from public_ai_challenge.phase1_scout.runtime import PageIR

logger = logging.getLogger(__name__)

class FinalScoutAdapter(ScoutProtocol):
    def __init__(self, use_agent: bool = False):
        self.use_agent = use_agent

    async def scout(
        self,
        url: str,
        municipality: str,
        canton: str,
        output_dir: str | None = None,
    ) -> ScoutResult:
        logger.info("FinalScoutAdapter: Starting discovery on %s", url)
        settings = Settings()
        pages_ir = []
        try:
            async with SafeCrawler(settings.crawl) as crawler:
                fetched_pages = await crawler.seed(url)
                from datetime import datetime, UTC
                for i, page in enumerate(fetched_pages):
                    pages_ir.append(
                        PageIR(
                            source_id=f"page_{i}",
                            url=page.url,
                            title=page.title,
                            headings=[],
                            text=page.text,
                            forms=[field.label for field in page.form_fields],
                            documents=[link.url for link in page.links if link.kind == "pdf"],
                            links=[{"url": link.url, "internal": link.kind == "html"} for link in page.links],
                            retrieved_at=datetime.now(UTC),
                            language="de",
                        )
                    )
        except Exception as e:
            logger.error("SafeCrawler encountered an error: %s", e)
            return ScoutResult(municipality_name=municipality, canton=canton, official_url=url, services=[])

        from public_ai_challenge.phase1_scout.catalog import load_service_index
        index = load_service_index()
        findings = discover_findings(pages_ir, index)

        scouted_services = []
        for finding in findings:
            page = next((p for p in pages_ir if finding.source_ids and p.source_id == finding.source_ids[0]), None)
            if not page:
                continue
                
            interpretation = await inspect_service(finding, page, self.use_agent)
            
            scouted_services.append(
                ScoutedServiceRecord(
                    name=finding.local_name,
                    description=interpretation.handling.summary if interpretation.handling else "",
                    urls=[page.url],
                    available=interpretation.availability == "supported",
                    metadata={"service_id": finding.service_id or "unknown"}
                )
            )

        return ScoutResult(municipality_name=municipality, canton=canton, official_url=url, services=scouted_services)
