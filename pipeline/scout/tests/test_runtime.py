from __future__ import annotations

import unittest

from scout.agents import heuristic_strategy
from scout.catalog import load_service_index
from scout.contracts import ReconResult, StrategyMode
from scout.runtime import normalize_url


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


if __name__ == "__main__":
    unittest.main()
