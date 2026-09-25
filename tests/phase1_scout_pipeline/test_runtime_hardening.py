from __future__ import annotations

import socket
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from public_ai_challenge.phase1_scout_pipeline.contracts import ScoutStrategy, StrategyMode
from public_ai_challenge.phase1_scout_pipeline.runtime import (
    PageIR,
    Parser,
    clean,
    execute_strategy,
    fetch_page,
    is_asset_url,
    is_news_item,
    link_priority,
    normalize_url,
    recon,
    validate_public_url,
)


class RuntimeHardeningTests(unittest.TestCase):
    def test_validate_public_url_rejects_invalid_schemes_and_hosts(self):
        with self.assertRaises(ValueError) as ctx:
            validate_public_url("ftp://example.com/file.txt")
        self.assertIn("public http(s) URL required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_public_url("file:///etc/passwd")
        self.assertIn("public http(s) URL required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_public_url("http://localhost/admin")
        self.assertIn("local hostname rejected", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_public_url("http://printer.local/status")
        self.assertIn("local hostname rejected", str(ctx.exception))

    @patch("socket.getaddrinfo")
    def test_validate_public_url_ssrf_prevention(self, mock_getaddrinfo):
        # Loopback IPv4
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        with self.assertRaises(ValueError) as ctx:
            validate_public_url("http://safe-looking.com/")
        self.assertIn("non-public destination rejected", str(ctx.exception))

        # Private RFC1918 10.x.x.x
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 80))]
        with self.assertRaises(ValueError):
            validate_public_url("http://internal.company.com/")

        # Cloud metadata service (169.254.169.254)
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]
        with self.assertRaises(ValueError):
            validate_public_url("http://metadata.aws.internal/")

        # Public global IP should succeed without error
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        validate_public_url("https://example.ch/")

    def test_normalize_url_edge_cases(self):
        # Trailing slash handling
        self.assertEqual(normalize_url("https://example.ch/path/"), "https://example.ch/path")
        self.assertEqual(normalize_url("https://example.ch/"), "https://example.ch/")
        # Redundant slashes
        self.assertEqual(normalize_url("https://example.ch///a//b"), "https://example.ch/a/b")
        # Non-standard ports
        self.assertEqual(normalize_url("https://example.ch:8443/test"), "https://example.ch:8443/test")
        self.assertEqual(normalize_url("http://example.ch:8080/test"), "http://example.ch:8080/test")
        # Tracking parameter removal
        self.assertEqual(
            normalize_url("https://example.ch/page?fbclid=xyz&pk_campaign=123&keep=true&mc_cid=999"),
            "https://example.ch/page?keep=true",
        )

    def test_parser_filters_scripts_and_extracts_structure(self):
        html = """
        <!DOCTYPE html>
        <html lang="de-CH">
        <head>
            <title>   Gemeinde Muster   </title>
            <style>body { color: red; }</style>
            <script>alert("evil");</script>
        </head>
        <body>
            <noscript>JavaScript required</noscript>
            <svg><text>Ignored</text></svg>
            <h1>Willkommen in Muster</h1>
            <p>Offizielle Seite der Gemeindeverwaltung.</p>
            <a href="/dienstleistungen">Dienstleistungen</a>
            <a href="/docs/abfallkalender.pdf">Abfallkalender (PDF)</a>
            <form action="/kontakt/submit" method="post">
                <input name="email">
            </form>
        </body>
        </html>
        """
        parser = Parser("https://example.ch/")
        parser.feed(html)

        self.assertEqual(parser.language, "de-CH")
        self.assertEqual(clean(" ".join(parser.title)), "Gemeinde Muster")
        self.assertIn("Willkommen in Muster", parser.headings)
        # Verify script/style/svg/noscript were excluded from text
        full_text = clean(" ".join(parser.text))
        self.assertNotIn("color: red", full_text)
        self.assertNotIn("alert", full_text)
        self.assertNotIn("JavaScript required", full_text)
        self.assertNotIn("Ignored", full_text)
        self.assertIn("Offizielle Seite der Gemeindeverwaltung", full_text)

        # Verify links, documents, and forms
        self.assertEqual(len(parser.links), 2)
        self.assertEqual(parser.documents, ["https://example.ch/docs/abfallkalender.pdf"])
        self.assertEqual(parser.forms, ["https://example.ch/kontakt/submit"])

    @patch("public_ai_challenge.phase1_scout_pipeline.runtime.validate_public_url")
    @patch("urllib.request.urlopen")
    def test_fetch_page_rejects_unsupported_content_type(self, mock_urlopen, mock_val):
        mock_response = MagicMock()
        mock_response.geturl.return_value = "https://example.ch/file.pdf"
        mock_response.headers.get_content_type.return_value = "application/pdf"
        mock_response.read.return_value = b"%PDF-1.5..."
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            fetch_page("https://example.ch/file.pdf")
        self.assertIn("unsupported content type: application/pdf", str(ctx.exception))

    def test_asset_and_news_classification(self):
        self.assertTrue(is_asset_url("https://example.ch/logo.PNG"))
        self.assertTrue(is_asset_url("https://example.ch/style.css"))
        self.assertTrue(is_asset_url("https://example.ch/bundle.js"))
        self.assertFalse(is_asset_url("https://example.ch/verwaltung"))

        # News patterns
        self.assertTrue(is_news_item("https://example.ch/aktuelles/20260924-baugesuch-123"))
        self.assertTrue(is_news_item("https://example.ch/news/einzelsitzung-4921"))
        self.assertFalse(is_news_item("https://example.ch/verwaltung/bauwesen"))

    def test_link_priority_scoring(self):
        admin_link = {"text": "Kanzlei und Öffnungszeiten", "url": "https://example.ch/kanzlei"}
        noise_link = {"text": "Tourismus und Skiclub Galerie", "url": "https://example.ch/skiclub"}
        news_link = {"text": "Baugesuch", "url": "https://example.ch/news/28092026-baugesuch-913"}

        terms = ["baugesuch", "öffnungszeiten"]
        p_admin = link_priority(admin_link, terms)
        p_noise = link_priority(noise_link, terms)
        p_news = link_priority(news_link, terms)

        self.assertGreater(p_admin, p_noise)
        self.assertGreater(p_admin, p_news)

    @patch("public_ai_challenge.phase1_scout_pipeline.runtime.fetch_page")
    def test_recon_extracts_directory_candidates(self, mock_fetch):
        mock_fetch.return_value = PageIR(
            source_id="src_home",
            url="https://example.ch/",
            retrieved_at=datetime.now(UTC),
            title="Gemeinde Test",
            language="de",
            headings=["Willkommen"],
            text="Startseite",
            links=[
                {"url": "https://example.ch/online-schalter", "text": "Online-Schalter", "internal": True},
                {"url": "https://example.ch/dienstleistungen/alle", "text": "Dienstleistungen", "internal": True},
                {"url": "https://external.ch/info", "text": "Extern", "internal": False},
            ],
            forms=[],
            documents=[],
        )

        result, _page = recon("https://example.ch/")
        self.assertEqual(result.internal_links, 2)
        self.assertEqual(len(result.service_directory_candidates), 2)
        self.assertIn("https://example.ch/online-schalter", [str(u) for u in result.service_directory_candidates])

    def test_targeted_crawl_and_execute_strategy(self):
        root = PageIR(
            source_id="src_root",
            url="https://example.ch/",
            retrieved_at=datetime.now(UTC),
            title="Home",
            language="de",
            headings=[],
            text="",
            links=[
                {"url": "https://example.ch/abfall", "text": "Abfall und Entsorgung", "internal": True},
                {"url": "https://example.ch/sport", "text": "Sportplatz", "internal": True},
            ],
            forms=[],
            documents=[],
        )

        strategy = ScoutStrategy(
            mode=StrategyMode.TARGETED,
            reason="Structured site",
            roots=["https://example.ch/"],
            max_pages=2,
            max_depth=1,
            target_services=["waste_collection"],
        )

        with patch("public_ai_challenge.phase1_scout_pipeline.runtime.fetch_page") as mock_fetch:
            mock_fetch.return_value = PageIR(
                source_id="src_abfall",
                url="https://example.ch/abfall",
                retrieved_at=datetime.now(UTC),
                title="Abfall",
                language="de",
                headings=[],
                text="Informationen zur Abfallentsorgung",
                links=[],
                forms=[],
                documents=[],
            )

            terms = {"waste_collection": ["abfall", "kehricht"]}
            pages = execute_strategy(root, strategy, terms)
            self.assertEqual(len(pages), 2)
            self.assertEqual(pages[1].url, "https://example.ch/abfall")


if __name__ == "__main__":
    unittest.main()
