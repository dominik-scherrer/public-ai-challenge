from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scout.agents import heuristic_strategy
from scout.catalog import load_service_index
from scout.contracts import ReconResult, ScoutStrategy, StrategyMode
from scout.runtime import PageIR, broad_crawl, normalize_url


class RuntimeTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_and_fragment(self):
        self.assertEqual(
            normalize_url(
                "HTTPS://Example.CH:443//a//b/?utm_source=x&q=1#frag"
            ),
            "https://example.ch/a/b?q=1",
        )

    def test_small_site_gets_broad_strategy(self):
        index = load_service_index()
        recon = ReconResult(
            entrypoint="https://example.ch/",
            internal_links=20,
            sampled_links=["Verwaltung", "Abfall"],
        )
        strategy = heuristic_strategy(recon, index)
        self.assertEqual(
            strategy.mode,
            StrategyMode.BROAD_SMALL_SITE,
        )

    def test_larger_site_gets_targeted_strategy(self):
        index = load_service_index()
        recon = ReconResult(
            entrypoint="https://example.ch/",
            internal_links=300,
            service_directory_candidates=[
                "https://example.ch/dienstleistungen"
            ],
        )
        strategy = heuristic_strategy(recon, index)
        self.assertEqual(
            strategy.mode,
            StrategyMode.TARGETED,
        )

    def test_broad_crawl_skips_redirect_duplicates_and_prioritises_admin(self):
        # Mirrors Binn: several links redirect to the same home page, and the
        # admin pages sit behind history/news pages in navigation order.
        def page(url, links=(), body=None):
            return PageIR(
                source_id="src_" + (body or url),
                url=url,
                retrieved_at=datetime.now(timezone.utc),
                title=url,
                language="de",
                headings=[],
                text="",
                links=[{"url": link, "text": "", "internal": True} for link in links],
                forms=[],
                documents=[],
            )

        base = "https://example.ch"
        site = {
            f"{base}/home": page(f"{base}/home", [
                f"{base}/gemeinde/geschichte",
                f"{base}/gemeinde/news/28082026-baugesuch-muster-913",
                f"{base}/gemeinde/bild.webp",
                f"{base}/gemeinde/verwaltung/abfallbewirtschaftung",
                f"{base}/gemeinde/verwaltung",
            ]),
        }
        aliases = {f"{base}/": f"{base}/home", f"{base}/index": f"{base}/home"}

        def fake_fetch(url):
            final = aliases.get(url, url)
            return site.get(final) or page(final)

        root = page(f"{base}/start", [f"{base}/", f"{base}/index"])
        strategy = ScoutStrategy(
            mode=StrategyMode.BROAD_SMALL_SITE,
            reason="test",
            roots=[root.url],
            max_pages=4,
            max_depth=2,
        )
        with patch("scout.runtime.fetch_page", side_effect=fake_fetch):
            pages = broad_crawl(root, strategy, {"waste_collection": ["abfall"]})

        urls = [p.url for p in pages]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(urls.count(f"{base}/home"), 1)
        self.assertNotIn(f"{base}/gemeinde/bild.webp", urls)
        self.assertEqual(urls[2:], [
            f"{base}/gemeinde/verwaltung/abfallbewirtschaftung",
            f"{base}/gemeinde/verwaltung",
        ])


if __name__ == "__main__":
    unittest.main()
