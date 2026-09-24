from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scout.app import compile_source_bundle, run_scout
from scout.catalog import load_service_index
from scout.contracts import (
    Availability,
    HandlingType,
    IndexRelation,
    ReconResult,
)
from scout.discovery import discover_findings
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

    def test_cantonal_portal_is_retained_as_official_handoff(self):
        # Binn's Bauwesen page routes building permits to the canton's portal.
        page = PageIR(
            source_id="src_bau",
            url="https://www.binn.ch/gemeinde/verwaltung/bauwesen",
            retrieved_at=datetime.now(timezone.utc),
            title="Bauwesen",
            language="de",
            headings=["Bauwesen"],
            text="Baugesuche werden elektronisch eingereicht.",
            links=[
                {"url": "https://www.vs.ch/de/web/sajmte/portail-utilisateurs", "text": "", "internal": False},
                {"url": "http://www.indual.ch/", "text": "webdesign", "internal": False},
            ],
            forms=[],
            documents=[],
        )
        handoffs = [
            str(source.url)
            for source in compile_source_bundle(page)
            if source.role.value == "official_handoff"
        ]
        self.assertEqual(handoffs, ["https://www.vs.ch/de/web/sajmte/portail-utilisateurs"])

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

    def test_navigation_text_does_not_match_every_service(self):
        # Mirrors Binn: every page body starts with the full site navigation and
        # a 'Webcam' widget heading; a dated news item mentions 'Baugesuch'.
        now = datetime.now(timezone.utc)
        nav = "Home Strahlerpatente Verwaltung Bauwesen Abfallbewirtschaftung Formulare Kontakt"

        def page(slug, title, headings=()):
            return PageIR(
                source_id=f"src_{slug}",
                url=f"https://example.ch/gemeinde/{slug}",
                retrieved_at=now,
                title=f"{title} | Gemeinde Beispiel",
                language="de",
                headings=["Webcam", *headings],
                text=f"{nav} {title}",
                links=[],
                forms=[],
                documents=[],
            )

        pages = [
            page("home", "Gemeinde Beispiel"),
            page("geschichte", "Geschichte"),
            page("verwaltung", "Verwaltung", ["Öffnungszeiten"]),
            page("verwaltung/abfallbewirtschaftung", "Abfallbewirtschaftung"),
            page("allgemein/strahlerpatente", "Strahlerpatente"),
            page("aktuelles/28082026-baugesuch-muster-913", "Baugesuch Muster"),
        ]
        findings = discover_findings(pages, load_service_index())
        by_service = {f.service_id: f for f in findings if f.service_id}

        self.assertEqual(by_service["waste_collection"].source_ids, ["src_verwaltung/abfallbewirtschaftung"])
        self.assertEqual(by_service["waste_collection"].local_name, "Abfallbewirtschaftung")
        self.assertEqual(by_service["office_hours"].source_ids, ["src_verwaltung"])
        self.assertNotIn("building_application", by_service)
        self.assertNotIn("forms", by_service)

        pages_used = [source for f in findings for source in f.source_ids]
        self.assertEqual(len(pages_used), len(set(pages_used)))
        self.assertEqual(
            [f.local_name for f in findings if f.index_relation == IndexRelation.POSSIBLE_NEW],
            ["Strahlerpatente"],
        )


if __name__ == "__main__":
    unittest.main()
