"""Read-only access to published Service Inventories, keyed by BFS number."""

from __future__ import annotations

import json
import re
from pathlib import Path

from mmp.registry import INVENTORY_DIR
from mmp.schema import Inventory, Service


class InventoryStore:
    def __init__(self, directory: Path = INVENTORY_DIR):
        self.directory = directory
        self._cache: dict[int, tuple[float, Inventory]] = {}

    def bfs_numbers(self) -> list[int]:
        return sorted(int(p.stem) for p in self.directory.glob("*.json") if p.stem.isdigit())

    def get(self, bfs: int) -> Inventory | None:
        path = self.directory / f"{int(bfs)}.json"
        if not path.exists():
            return None
        mtime = path.stat().st_mtime
        cached = self._cache.get(int(bfs))
        if cached and cached[0] == mtime:
            return cached[1]
        inventory = Inventory.model_validate(json.loads(path.read_text(encoding="utf-8")))
        self._cache[int(bfs)] = (mtime, inventory)
        return inventory

    def all(self) -> list[Inventory]:
        return [inv for bfs in self.bfs_numbers() if (inv := self.get(bfs))]


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) > 2}


def rank_services(inventory: Inventory, query: str, limit: int = 5) -> list[tuple[int, Service]]:
    """Keyword fallback only (OQ-2): no semantic search, no learning from queries (ADR-0005)."""
    words = _tokens(query)
    scored = []
    for service in inventory.services:
        haystack = _tokens(" ".join([service.title, service.summary or "", *service.keywords, *service.categories]))
        # prefix match so "Kehrichtsäcke" finds "Kehricht", "Schulwechsel" finds "Schule"
        score = sum(1 for w in words if any(h.startswith(w[:6]) or w.startswith(h[:6]) for h in haystack if len(h) > 3))
        if score:
            scored.append((score, service))
    scored.sort(key=lambda pair: -pair[0])
    return scored[:limit]
