from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scout.app import compile_source_bundle, run_scout
from scout.contracts import (
    Availability,
    HandlingType,
    IndexRelation,
    ReconResult,
)
from scout.runtime import PageIR


class ScoutIntegrationTests(unittest.TestCase):
    def test_sibling_subdomain_is_retained_as_official_handoff(self):
        now = datetime.now(timezone.utc)
        page = PageIR(
            source_id="src_patent",
            url="https://www.binn.ch/gemeinde/allgemein/strahlerpatente",
            retrieved_at=now,
            title="Strahlerpatente",
            language="de",
            headings=["Strahlerpatente"],
            text="Strahlerpatente können online gekauft werden.",
            links=[
                {
                    "url": "https://strahlerpatente.binn.ch/",
                    "text": "Kauf eines Strahlerpatents",
                    "internal": False,
                }
            ],
            forms=[],
            documents=[],
        )
        bundle = compile_source_bundle(page)
        self.assertTrue(
            any(
                source.role.value == "official_handoff"
                and str(source.url).startswith("https://strahlerpatente.binn.ch/")
                for source in bundle
            )
        )

    def test_fixture_run_compiles_discovery_json(self):
        now = datetime.now(timezone.utc)
        root = PageIR(
            source_id="src_root",
            url="https://example.ch/",
            retrieved_at=now,
            title="Gemeinde Beispiel",
            language="de",
            headings=["Gemeinde Beispiel"],
            text="Willkommen bei der Gemeinde Beispiel.",
            links=[],
            forms=[],
            documents=[],
        )
        waste = PageIR(
            source_id="src_waste",
            url="https://example.ch/verwaltung/abfall",
            retrieved_at=now,
            title="Abfallentsorgung",
            language="de",
            headings=["Abfallentsorgung"],
            text="Informationen zu Kehricht, Recycling und Sammelstellen.",
            links=[],
            forms=[],
            documents=["https://example.ch/docs/abfallkalender.pdf"],
        )
        patent = PageIR(
            source_id="src_patent",
            url="https://example.ch/verwaltung/strahlerpatente",
            retrieved_at=now,
            title="Strahlerpatente",
            language="de",
            headings=["Strahlerpatente"],
            text="Für Strahlerpatente ist ein Gesuch bei der Gemeinde einzureichen.",
            links=[],
            forms=["https://example.ch/formulare/strahlerpatent"],
            documents=[],
        )

        recon_result = ReconResult(
            entrypoint=root.url,
            title=root.title,
            language="de",
            internal_links=12,
            sampled_links=["Abfall", "Verwaltung"],
        )

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("scout.app.recon", return_value=(recon_result, root)),
            patch("scout.app.execute_strategy", return_value=[root, waste, patent]),
        ):
            discovery = asyncio.run(
                run_scout(
                    "https://example.ch/",
                    "Beispiel",
                    "VS",
                    Path(tmp),
                    use_agent=False,
                )
            )

            parsed = json.loads(
                (Path(tmp) / "discovery.json").read_text(encoding="utf-8")
            )

        self.assertEqual(parsed["schema"], "municipality-discovery/v1")

        waste_service = next(
            service
            for service in discovery.services
            if service.service_id == "waste_collection"
        )
        self.assertEqual(waste_service.availability, Availability.SUPPORTED)
        self.assertIn(
            waste_service.handling.type,
            {HandlingType.PDF, HandlingType.MIXED},
        )
        self.assertTrue(
            any(source.role.value == "calendar_pdf" for source in waste_service.sources)
        )

        self.assertTrue(
            any(
                suggestion.local_name == "Strahlerpatente"
                for suggestion in discovery.catalog_suggestions
            )
        )

        indexed_missing = [
            service
            for service in discovery.services
            if service.index_relation == IndexRelation.INDEXED
            and service.availability == Availability.NOT_OBSERVED
        ]
        self.assertGreaterEqual(len(indexed_missing), 1)


if __name__ == "__main__":
    unittest.main()
