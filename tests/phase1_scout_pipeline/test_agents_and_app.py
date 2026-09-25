from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from public_ai_challenge.phase1_scout_pipeline.agents import (
    choose_strategy,
    heuristic_interpret,
    heuristic_strategy,
    inspect_service,
)
from public_ai_challenge.phase1_scout_pipeline.app import (
    _is_government,
    _parent_domain,
    compile_source_bundle,
    linked_source_role,
    run_scout,
)
from public_ai_challenge.phase1_scout_pipeline.catalog import all_terms, load_service_index
from public_ai_challenge.phase1_scout_pipeline.contracts import (
    HandlingType,
    IndexRelation,
    InteractionType,
    ReconResult,
    ScoutFinding,
    SourceRole,
    StrategyMode,
)
from public_ai_challenge.phase1_scout_pipeline.runtime import PageIR


class AgentsAndAppTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_heuristic_strategy_branches(self):
        index = load_service_index()
        # Small site branch
        recon_small = ReconResult(
            entrypoint="https://example.ch/",
            internal_links=50,
            service_directory_candidates=[],
        )
        strat_small = heuristic_strategy(recon_small, index)
        self.assertEqual(strat_small.mode, StrategyMode.BROAD_SMALL_SITE)
        self.assertEqual(strat_small.max_depth, 2)
        self.assertEqual(strat_small.max_pages, 25)

        # Larger site branch
        recon_large = ReconResult(
            entrypoint="https://example.ch/",
            internal_links=120,
            service_directory_candidates=[],
        )
        strat_large = heuristic_strategy(recon_large, index)
        self.assertEqual(strat_large.mode, StrategyMode.TARGETED)

        # Site with directory candidate
        recon_dir = ReconResult(
            entrypoint="https://example.ch/",
            internal_links=30,
            service_directory_candidates=["https://example.ch/services"],
        )
        strat_dir = heuristic_strategy(recon_dir, index)
        self.assertEqual(strat_dir.mode, StrategyMode.TARGETED)

    async def test_choose_strategy_fallbacks(self):
        index = load_service_index()
        recon = ReconResult(entrypoint="https://example.ch/", internal_links=10)

        # When use_agent is False -> uses heuristic
        strat1 = await choose_strategy(recon, index, use_agent=False)
        self.assertEqual(strat1.mode, StrategyMode.BROAD_SMALL_SITE)

        # When use_agent is True but no SCOUT_MODEL set -> uses heuristic
        with patch.dict("os.environ", {}, clear=True):
            strat2 = await choose_strategy(recon, index, use_agent=True)
            self.assertEqual(strat2.mode, StrategyMode.BROAD_SMALL_SITE)

    async def test_inspect_service_fallbacks(self):
        finding = ScoutFinding(
            service_id="move_in",
            local_name="Anmeldung",
            index_relation=IndexRelation.INDEXED,
            confidence=0.9,
            source_ids=["src_1"],
        )
        now = datetime.now(UTC)
        page = PageIR(
            source_id="src_1",
            url="https://example.ch/anmeldung",
            retrieved_at=now,
            title="Anmeldung",
            language="de",
            headings=[],
            text="Info",
            links=[],
            forms=[],
            documents=[],
        )

        # When use_agent is False
        res1 = await inspect_service(finding, page, use_agent=False)
        self.assertEqual(res1.service_id, "move_in")
        self.assertEqual(res1.handling.type, HandlingType.STATIC_PAGE)

        # When use_agent is True but no SCOUT_MODEL set
        with patch.dict("os.environ", {}, clear=True):
            res2 = await inspect_service(finding, page, use_agent=True)
            self.assertEqual(res2.service_id, "move_in")

    def test_heuristic_interpret_handling_types(self):
        finding = ScoutFinding(
            service_id="move_in",
            local_name="Anmeldung",
            index_relation=IndexRelation.INDEXED,
            confidence=0.9,
            source_ids=["src_1"],
        )

        now = datetime.now(UTC)

        # HTML Form handling
        page_form = PageIR(
            source_id="src_1",
            url="https://example.ch/umzug",
            retrieved_at=now,
            title="Umzug",
            language="de",
            headings=[],
            text="Formular ausfüllen",
            links=[],
            forms=["https://example.ch/submit"],
            documents=[],
        )
        interp_form = heuristic_interpret(finding, page_form)
        self.assertEqual(interp_form.handling.type, HandlingType.HTML_FORM)
        self.assertEqual(interp_form.handling.interaction, InteractionType.REQUEST)

        # PDF handling
        page_pdf = PageIR(
            source_id="src_2",
            url="https://example.ch/abfall",
            retrieved_at=now,
            title="Abfall",
            language="de",
            headings=[],
            text="Entsorgungskalender herunterladen",
            links=[],
            forms=[],
            documents=["https://example.ch/plan.pdf"],
        )
        interp_pdf = heuristic_interpret(finding, page_pdf)
        self.assertEqual(interp_pdf.handling.type, HandlingType.PDF)
        self.assertEqual(interp_pdf.handling.interaction, InteractionType.INFORMATION)

        # External handoff
        page_handoff = PageIR(
            source_id="src_3",
            url="https://example.ch/umzug",
            retrieved_at=now,
            title="Wohnsitzwechsel",
            language="de",
            headings=[],
            text="Bitte nutzen Sie das offizielle Portal eumzug.swiss für die Meldung.",
            links=[{"url": "https://www.eumzug.swiss", "text": "eUmzug", "internal": False}],
            forms=[],
            documents=[],
        )
        interp_handoff = heuristic_interpret(finding, page_handoff)
        self.assertEqual(interp_handoff.handling.type, HandlingType.EXTERNAL_HANDOFF)
        self.assertEqual(interp_handoff.handling.interaction, InteractionType.WAYFINDING)

        # Static Page fallback
        page_static = PageIR(
            source_id="src_4",
            url="https://example.ch/zeiten",
            retrieved_at=now,
            title="Öffnungszeiten",
            language="de",
            headings=[],
            text="Die Kanzlei ist montags von 8 bis 11 Uhr geöffnet.",
            links=[],
            forms=[],
            documents=[],
        )
        interp_static = heuristic_interpret(finding, page_static)
        self.assertEqual(interp_static.handling.type, HandlingType.STATIC_PAGE)
        self.assertEqual(interp_static.handling.interaction, InteractionType.INFORMATION)

    def test_catalog_and_all_terms(self):
        index = load_service_index()
        self.assertTrue(len(index.services) >= 5)
        terms = all_terms(index)
        self.assertIn("waste_collection", terms)
        self.assertIn("abfall", terms["waste_collection"])

    def test_domain_and_role_helpers(self):
        self.assertEqual(_parent_domain("https://sub.binn.ch/path"), "binn.ch")
        self.assertEqual(_parent_domain("https://binn.ch"), "binn.ch")

        self.assertTrue(_is_government("https://www.vs.ch/dienststelle"))
        self.assertTrue(_is_government("https://ch.ch/umzug"))
        self.assertTrue(_is_government("https://admin.ch/portal"))
        self.assertFalse(_is_government("https://google.com"))

        # Role categorization
        self.assertEqual(linked_source_role("https://example.ch/action", "form"), SourceRole.FORM)
        self.assertEqual(
            linked_source_role("https://example.ch/abfuhrplan-2026.pdf", "document"),
            SourceRole.CALENDAR_PDF,
        )
        self.assertEqual(
            linked_source_role("https://example.ch/bauantrag.pdf", "document"),
            SourceRole.APPLICATION_PDF,
        )
        self.assertEqual(
            linked_source_role("https://example.ch/abfallreglement.pdf", "document"),
            SourceRole.REGULATION_PDF,
        )
        self.assertEqual(
            linked_source_role("https://example.ch/info.pdf", "document"),
            SourceRole.INFORMATION_PDF,
        )
        self.assertEqual(
            linked_source_role("https://www.vs.ch/portal", "link"),
            SourceRole.OFFICIAL_HANDOFF,
        )

    def test_compile_source_bundle(self):
        now = datetime.now(UTC)
        page = PageIR(
            source_id="src_permits",
            url="https://example.ch/bau",
            retrieved_at=now,
            title="Bauwesen",
            language="de",
            headings=[],
            text="Baugesuche und Formulare",
            links=[
                {"url": "https://www.vs.ch/portal/bau", "text": "Kantonales Portal", "internal": False},
                {"url": "https://partner.example.ch/info", "text": "Partner Subdomain", "internal": False},
                {"url": "https://commercial-third-party.com/news", "text": "News", "internal": False},
            ],
            forms=["https://example.ch/bau/form"],
            documents=["https://example.ch/bau/reglement.pdf"],
        )

        sources = compile_source_bundle(page)
        # root + form + doc + cantonal handoff + sibling official subdomain (commercial third-party excluded)
        self.assertEqual(len(sources), 5)
        roles = {s.role for s in sources}
        self.assertIn(SourceRole.MUNICIPAL_SERVICE_PAGE, roles)
        self.assertIn(SourceRole.FORM, roles)
        self.assertIn(SourceRole.REGULATION_PDF, roles)
        self.assertIn(SourceRole.OFFICIAL_HANDOFF, roles)
        urls = {str(s.url) for s in sources}
        self.assertIn("https://partner.example.ch/info", urls)
        self.assertNotIn("https://commercial-third-party.com/news", urls)

    @patch("public_ai_challenge.phase1_scout_pipeline.app.recon")
    @patch("public_ai_challenge.phase1_scout_pipeline.app.execute_strategy")
    async def test_run_scout_generates_valid_discovery_and_artifacts(self, mock_exec, mock_recon):
        now = datetime.now(UTC)
        root_page = PageIR(
            source_id="src_root",
            url="https://example.ch/",
            retrieved_at=now,
            title="Gemeinde Muster",
            language="de",
            headings=["Willkommen"],
            text="Offizielle Website",
            links=[
                {"url": "https://example.ch/verwaltung/abfall", "text": "Abfallentsorgung", "internal": True}
            ],
            forms=[],
            documents=[],
        )
        abfall_page = PageIR(
            source_id="src_abfall",
            url="https://example.ch/verwaltung/abfall",
            retrieved_at=now,
            title="Abfallwesen und Kehricht",
            language="de",
            headings=["Abfall"],
            text="Hier finden Sie alle Angaben zur Kehrichtabfuhr und Entsorgung.",
            links=[],
            forms=[],
            documents=["https://example.ch/docs/abfallkalender.pdf"],
        )

        recon_res = ReconResult(
            entrypoint="https://example.ch/",
            title="Gemeinde Muster",
            language="de",
            internal_links=1,
            service_directory_candidates=[],
            sampled_links=["Abfallentsorgung"],
        )
        mock_recon.return_value = (recon_res, root_page)
        mock_exec.return_value = [root_page, abfall_page]

        out_path = self.tmp_dir / "muster_run"
        discovery = await run_scout(
            url="https://example.ch/",
            municipality="Muster",
            canton="BE",
            out_dir=out_path,
            use_agent=False,
        )

        # Check in-memory object
        self.assertEqual(discovery.municipality.name, "Muster")
        self.assertEqual(discovery.municipality.canton, "BE")
        self.assertTrue(len(discovery.services) >= 5)

        # Check persisted artifacts
        discovery_file = out_path / "discovery.json"
        sources_file = out_path / "sources.jsonl"
        report_file = out_path / "crawl-report.json"

        self.assertTrue(discovery_file.exists())
        self.assertTrue(sources_file.exists())
        self.assertTrue(report_file.exists())

        loaded_disc = json.loads(discovery_file.read_text(encoding="utf-8"))
        self.assertEqual(loaded_disc["municipality"]["name"], "Muster")

        # Verify sources.jsonl has 2 lines (root + abfall)
        lines = sources_file.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)

    def test_crawl_records_network_failures(self):
        import urllib.error

        from public_ai_challenge.phase1_scout_pipeline.contracts import DiscoveryFailure, ScoutStrategy
        from public_ai_challenge.phase1_scout_pipeline.runtime import broad_crawl, targeted_crawl

        now = datetime.now(UTC)
        root = PageIR(
            source_id="src_root",
            url="https://example.ch/",
            retrieved_at=now,
            title="Root",
            language="de",
            headings=[],
            text="hello",
            links=[
                {"url": "https://example.ch/broken1", "text": "Broken 1", "internal": True},
                {"url": "https://example.ch/broken2", "text": "abfall Broken 2", "internal": True},
            ],
            forms=[],
            documents=[],
        )

        strategy_broad = ScoutStrategy(
            mode=StrategyMode.BROAD_SMALL_SITE,
            reason="test",
            roots=["https://example.ch/"],
            max_pages=5,
            max_depth=2,
        )
        strategy_targeted = ScoutStrategy(
            mode=StrategyMode.TARGETED,
            reason="test",
            roots=["https://example.ch/"],
            max_pages=5,
            max_depth=1,
            target_services=["waste_collection"],
        )

        failures_broad: list[DiscoveryFailure] = []
        with patch("public_ai_challenge.phase1_scout_pipeline.runtime.fetch_page", side_effect=urllib.error.URLError("Connection refused")):
            with self.assertLogs("public_ai_challenge.phase1_scout_pipeline.runtime", level="WARNING") as cm:
                pages = broad_crawl(root, strategy_broad, failures=failures_broad)
                self.assertEqual(len(pages), 1)  # only root kept
                self.assertEqual(len(failures_broad), 2)
                self.assertEqual(failures_broad[0].stage, "crawl")
                self.assertIn("Connection refused", failures_broad[0].error)
                self.assertTrue(any("Failed to fetch" in msg for msg in cm.output))

        failures_targeted: list[DiscoveryFailure] = []
        with patch("public_ai_challenge.phase1_scout_pipeline.runtime.fetch_page", side_effect=TimeoutError("Timed out")):
            with self.assertLogs("public_ai_challenge.phase1_scout_pipeline.runtime", level="WARNING") as cm:
                pages = targeted_crawl(
                    root,
                    strategy_targeted,
                    {"waste_collection": ["abfall"]},
                    failures=failures_targeted,
                )
                self.assertEqual(len(pages), 1)
                self.assertEqual(len(failures_targeted), 1)
                self.assertEqual(failures_targeted[0].stage, "crawl")
                self.assertIn("TimeoutError", failures_targeted[0].error)

    async def test_agent_call_exceptions_fall_back_to_heuristics(self):
        from public_ai_challenge.phase1_scout_pipeline.catalog import load_service_index
        from public_ai_challenge.phase1_scout_pipeline.contracts import IndexRelation, ScoutFinding

        index = load_service_index()
        recon_res = ReconResult(entrypoint="https://example.ch/", internal_links=10)

        # Mock pydantic_ai.Agent to raise an error during run()
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=RuntimeError("OpenAI API rate limit"))

        with patch.dict("os.environ", {"SCOUT_MODEL": "test-model"}):
            with patch("pydantic_ai.Agent", return_value=mock_agent_instance):
                with self.assertLogs("public_ai_challenge.phase1_scout_pipeline.agents", level="WARNING") as cm:
                    # Strategy selection fallback
                    strat = await choose_strategy(recon_res, index, use_agent=True)
                    self.assertEqual(strat.mode, StrategyMode.BROAD_SMALL_SITE)
                    self.assertTrue(any("Agent strategy selection failed" in msg for msg in cm.output))

                with self.assertLogs("public_ai_challenge.phase1_scout_pipeline.agents", level="WARNING") as cm:
                    # Service inspection fallback
                    finding = ScoutFinding(
                        service_id="waste_collection",
                        local_name="Abfall",
                        index_relation=IndexRelation.INDEXED,
                        confidence=0.8,
                        source_ids=["src_1"],
                    )
                    page = PageIR(
                        source_id="src_1",
                        url="https://example.ch/abfall",
                        retrieved_at=datetime.now(UTC),
                        title="Abfall",
                        language="de",
                        headings=["Abfall"],
                        text="Abfallentsorgung",
                        links=[],
                        forms=[],
                        documents=[],
                    )
                    interp = await inspect_service(finding, page, use_agent=True)
                    self.assertEqual(interp.service_id, "waste_collection")
                    self.assertTrue(any("Agent service inspection failed" in msg for msg in cm.output))


if __name__ == "__main__":
    unittest.main()
