from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import (
    MunicipalHTMLParser,
    SourceSnapshot,
    build_service,
    heuristic_extract,
)


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "fixtures" / "binn_sample.html").read_text(
            encoding="utf-8"
        )
        self.url = "https://example.ch/gemeinde/wohnsitzbescheinigung"

    def page(self):
        parser = MunicipalHTMLParser(self.url)
        parser.feed(self.html)
        return parser.page_ir(self.url, "src_fixture")

    def test_page_ir_extracts_structure(self):
        page = self.page()
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
        result = heuristic_extract(self.page(), "Binn", "VS")
        self.assertTrue(result["is_service"])
        self.assertGreaterEqual(result["confidence"], 0.55)

    def test_service_keeps_source_and_jurisdiction(self):
        page = self.page()
        result = heuristic_extract(page, "Binn", "VS")
        snapshot = SourceSnapshot(
            source_id="src_fixture",
            url=self.url,
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
            result,
            page,
            snapshot,
            "Binn",
            "VS",
        )

        self.assertIsNotNone(service)
        self.assertEqual(service["source_refs"], ["src_fixture"])
        self.assertEqual(service["jurisdiction"]["municipality"], "Binn")
        self.assertEqual(service["status"], "partial")


if __name__ == "__main__":
    unittest.main()
