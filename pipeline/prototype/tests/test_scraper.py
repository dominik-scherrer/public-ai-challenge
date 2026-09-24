from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scraper
from model_adapter import _parse_json_object
from scraper import (
    MunicipalHTMLParser,
    SourceSnapshot,
    _link_priority,
    build_service,
    crawl,
    heuristic_extract,
    model_extract,
    normalize_url,
)


class ParserTests(unittest.TestCase):
    def fixture_page(self, name: str, url: str):
        html = (ROOT / "fixtures" / name).read_text(encoding="utf-8")
        parser = MunicipalHTMLParser(url)
        parser.feed(html)
        return parser.page_ir(url, "src_fixture")

    def test_page_ir_extracts_structure(self):
        page = self.fixture_page(
            "binn_sample.html",
            "https://example.ch/gemeinde/wohnsitzbescheinigung",
        )
        self.assertEqual(page["language"], "de")
        self.assertIn("Wohnsitzbescheinigung", page["headings"])
        self.assertTrue(
            any(
                link["url"].endswith("/formular/wohnsitz")
                for link in page["links"]
            )
        )
        self.assertIn("CHF 20", page["main_text"])

    def test_heuristic_marks_service_candidate(self):
        page = self.fixture_page(
            "binn_sample.html",
            "https://example.ch/gemeinde/wohnsitzbescheinigung",
        )
        result = heuristic_extract(page, "Binn", "VS")
        self.assertTrue(result["is_service"])
        self.assertGreaterEqual(result["confidence"], 0.48)

    def test_patent_page_is_service_candidate(self):
        page = self.fixture_page(
            "binn_patent.html",
            "https://www.binn.ch/gemeinde/allgemein/strahlerpatente",
        )
        result = heuristic_extract(page, "Binn", "VS")
        self.assertTrue(result["is_service"])
        self.assertEqual(result["page_role"], "service")

    def test_tourism_news_is_negative(self):
        page = self.fixture_page(
            "tourism_news.html",
            "https://www.binn.ch/aktuelles/wetter-webcam",
        )
        result = heuristic_extract(page, "Binn", "VS")
        self.assertFalse(result["is_service"])

    def test_service_keeps_source_and_jurisdiction(self):
        page = self.fixture_page(
            "binn_sample.html",
            "https://example.ch/gemeinde/wohnsitzbescheinigung",
        )
        result = heuristic_extract(page, "Binn", "VS")
        snapshot = SourceSnapshot(
            source_id="src_fixture",
            url=page["url"],
            canonical_url=None,
            retrieved_at="2026-09-24T12:00:00+00:00",
            status=200,
            content_type="text/html",
            language="de",
            last_modified=None,
            etag=None,
            sha256="sha256:fixture",
        )
        service = build_service(
            result, page, snapshot, "Binn", "VS"
        )
        self.assertIsNotNone(service)
        self.assertEqual(service["source_refs"], ["src_fixture"])
        self.assertEqual(
            service["jurisdiction"]["municipality"], "Binn"
        )
        self.assertEqual(service["status"], "partial")


class UrlAndPriorityTests(unittest.TestCase):
    def test_url_normalization_removes_fragment_tracking_and_default_port(self):
        value = normalize_url(
            "HTTPS://Example.CH:443//a//b/?utm_source=x&q=1#frag"
        )
        self.assertEqual(value, "https://example.ch/a/b?q=1")

    def test_admin_link_outscores_news(self):
        service = {
            "text": "Bewilligung beantragen",
            "url": "https://example.ch/verwaltung/bewilligung",
        }
        news = {
            "text": "Aktuelles Wetter",
            "url": "https://example.ch/aktuelles/wetter",
        }
        self.assertGreater(
            _link_priority(service), _link_priority(news)
        )


class ModelTests(unittest.TestCase):
    def test_fenced_json_is_parsed(self):
        fence = chr(96) * 3
        value = _parse_json_object(
            fence + 'json\n{"is_service": true}\n' + fence
        )
        self.assertTrue(value["is_service"])

    def test_model_failure_falls_back(self):
        class BrokenModel:
            def extract_service(self, *args, **kwargs):
                raise RuntimeError("boom")

        page = {
            "url": "https://example.ch/verwaltung/bewilligung",
            "title": "Bewilligung",
            "headings": ["Bewilligung"],
            "main_text": "Ein Gesuch kann eingereicht werden.",
            "forms": [],
            "documents": [],
        }
        result = model_extract(
            page, "Binn", "VS", BrokenModel(), "candidate"
        )
        self.assertEqual(result["extractor"], "heuristic-v1")
        self.assertTrue(result["model_fallback"])
        self.assertIn("boom", result["model_error"])

    def test_invalid_model_output_falls_back(self):
        class InvalidModel:
            def extract_service(self, *args, **kwargs):
                return {
                    "page_role": "service",
                    "is_service": "yes",
                    "confidence": 1,
                }

        page = {
            "url": "https://example.ch/verwaltung/bewilligung",
            "title": "Bewilligung",
            "headings": ["Bewilligung"],
            "main_text": "Ein Gesuch kann eingereicht werden.",
            "forms": [],
            "documents": [],
        }
        result = model_extract(
            page, "Binn", "VS", InvalidModel(), "always"
        )
        self.assertTrue(result["model_fallback"])


class CrawlTests(unittest.TestCase):
    def test_redirect_final_url_processed_once(self):
        root_html = (
            b'<html><body><a href="/alias-a">A</a>'
            b'<a href="/alias-b">B</a></body></html>'
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
            if url.endswith("/alias-a") or url.endswith("/alias-b"):
                return (
                    snapshot(
                        "https://example.ch/final", target_html
                    ),
                    target_html,
                )
            return snapshot(
                "https://example.ch/", root_html
            ), root_html

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                scraper, "validate_public_http_url", return_value=None
            ),
            patch.object(
                scraper, "fetch", side_effect=fake_fetch
            ),
        ):
            report = crawl(
                "https://example.ch/",
                "Example",
                "ZH",
                Path(tmp),
                max_pages=5,
                max_depth=2,
                delay_seconds=0,
                model_mode="off",
            )
            rows = [
                json.loads(line)
                for line in (
                    Path(tmp) / "sources.jsonl"
                ).read_text().splitlines()
            ]
            final_urls = [row["url"] for row in rows]
            self.assertEqual(
                final_urls.count("https://example.ch/final"), 1
            )
            self.assertEqual(report.pages_fetched, 2)


if __name__ == "__main__":
    unittest.main()
