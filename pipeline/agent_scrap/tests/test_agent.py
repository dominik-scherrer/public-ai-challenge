from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent
from agent import (
    AgentScrap,
    MunicipalHTMLParser,
    SourceSnapshot,
    build_service_lead,
    build_tool_observations,
    normalize_url,
    service_score,
)


class AgentScrapTests(unittest.TestCase):
    def page(
        self,
        html: str,
        url: str = "https://example.ch/service",
    ):
        parser = MunicipalHTMLParser(url)
        parser.feed(html)
        return parser.page_ir(url, "src_fixture")

    def test_url_normalization(self):
        self.assertEqual(
            normalize_url(
                "HTTPS://Example.CH:443//a//b/?utm_source=x&q=1#frag"
            ),
            "https://example.ch/a/b?q=1",
        )

    def test_strahlerpatent_becomes_service_lead(self):
        page = self.page(
            (
                "<html lang='de'><body><h1>Strahlerpatente</h1>"
                "<p>Das Gesuch kann bei der Gemeinde eingereicht werden.</p>"
                "<a href='/formular-gesuch.pdf'>Gesuch</a></body></html>"
            ),
            "https://example.ch/gemeinde/strahlerpatente",
        )

        lead = build_service_lead(
            page,
            "Binn",
            "VS",
            service_score(page),
        )

        self.assertIsNotNone(lead)
        self.assertIn(
            lead["service_type_hint"],
            {"forms", "permit"},
        )
        self.assertTrue(
            any(
                source["role"] == "application_pdf"
                for source in lead["sources"]
            )
        )

    def test_tourism_weather_is_not_service(self):
        page = self.page(
            (
                "<html><body><h1>Wetter Webcam Tourismus</h1>"
                "<p>Hotels und Ferienwohnungen</p></body></html>"
            ),
            "https://example.ch/aktuelles/wetter-webcam",
        )

        self.assertLess(service_score(page), 0.48)

    def test_waste_calendar_generates_grounding_observations(self):
        page = self.page(
            (
                "<html><body><h1>Abfallentsorgung</h1>"
                "<a href='/abfallkalender.pdf'>Abfallkalender</a>"
                "</body></html>"
            ),
            "https://example.ch/verwaltung/abfall",
        )

        lead = build_service_lead(
            page,
            "Binn",
            "VS",
            service_score(page),
        )

        self.assertIsNotNone(lead)

        observations = build_tool_observations(
            "run-1",
            "Binn",
            "VS",
            [lead],
        )
        tool_ids = {
            observation["tool_id"]
            for observation in observations["observations"]
        }

        self.assertIn("list_services", tool_ids)
        self.assertIn("garbage_collection", tool_ids)
        self.assertIn("next_waste_collection", tool_ids)

    def test_model_failure_falls_back_to_heuristic(self):
        class BrokenModel:
            def classify(self, *args, **kwargs):
                raise RuntimeError("boom")

        page = self.page(
            "<html><body><h1>Abfallentsorgung</h1></body></html>",
            "https://example.ch/verwaltung/abfall",
        )

        score, hint, title = AgentScrap(
            model=BrokenModel()
        ).classify(
            page,
            "Binn",
            "VS",
            "always",
        )

        self.assertGreaterEqual(score, 0.48)
        self.assertIsNone(hint)
        self.assertIsNone(title)

    def test_redirect_final_url_processed_once(self):
        root_html = (
            b'<html><body><a href="/a">A</a>'
            b'<a href="/b">B</a></body></html>'
        )
        target_html = (
            b'<html><body><h1>Bewilligung</h1>'
            b'<p>Gesuch einreichen.</p></body></html>'
        )

        def snapshot(final_url, body):
            sha = __import__("hashlib").sha256(body).hexdigest()
            return SourceSnapshot(
                source_id="src_" + sha[:16],
                url=final_url,
                canonical_url=None,
                retrieved_at="2026-09-24T12:00:00+00:00",
                status=200,
                content_type="text/html",
                language=None,
                last_modified=None,
                etag=None,
                sha256="sha256:" + sha,
            )

        def fake_fetch(url):
            if url.endswith(("/a", "/b")):
                return (
                    snapshot(
                        "https://example.ch/final",
                        target_html,
                    ),
                    target_html,
                )

            return (
                snapshot(
                    "https://example.ch/",
                    root_html,
                ),
                root_html,
            )

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                agent,
                "validate_public_http_url",
                return_value=None,
            ),
            patch.object(
                agent,
                "fetch",
                side_effect=fake_fetch,
            ),
        ):
            report = AgentScrap(
                max_pages=5,
                max_depth=2,
                delay_seconds=0,
            ).run(
                "https://example.ch/",
                "Example",
                "ZH",
                Path(tmp),
            )

            sources = [
                json.loads(line)
                for line in (
                    Path(tmp) / "sources.jsonl"
                ).read_text().splitlines()
            ]

            self.assertEqual(
                sum(
                    1
                    for source in sources
                    if source["url"]
                    == "https://example.ch/final"
                ),
                1,
            )
            self.assertEqual(report.pages_fetched, 2)
            self.assertTrue(
                (Path(tmp) / "service-leads.jsonl").exists()
            )
            self.assertTrue(
                (Path(tmp) / "tool-observations.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
