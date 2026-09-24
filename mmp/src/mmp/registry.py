"""Operator configuration: known Municipalities and the Handoff allow-list."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # .../mmp
DATA_DIR = PACKAGE_ROOT / "data"
INVENTORY_DIR = DATA_DIR / "inventories"
CAPTURE_DIR = DATA_DIR / "captures"
EXTRACTION_DIR = DATA_DIR / "extractions"
OPERATOR_DIR = DATA_DIR / "operator"  # Gap Reports + Feedback (ADR-0005), not in git


@dataclass(frozen=True)
class MunicipalityEntry:
    slug: str
    name: str
    canton: str
    bfs: int | None
    website: str
    official_domains: tuple[str, ...]
    languages: tuple[str, ...] = ("de",)
    robots_blocked: bool = False
    extra: dict = field(default_factory=dict, compare=False, hash=False)


@lru_cache
def municipalities(path: Path = DATA_DIR / "municipalities.yml") -> tuple[MunicipalityEntry, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = []
    for item in raw.get("municipalities", []):
        entries.append(
            MunicipalityEntry(
                slug=item["slug"],
                name=item["name"],
                canton=item["canton"],
                bfs=item.get("bfs"),
                website=item["website"],
                official_domains=tuple(item["official_domains"]),
                languages=tuple(item.get("languages", ["de"])),
                robots_blocked=bool(item.get("robots_blocked", False)),
            )
        )
    return tuple(entries)


def find_municipality(key: str | int) -> MunicipalityEntry | None:
    text = str(key).strip().lower()
    for entry in municipalities():
        if text in {entry.slug, entry.name.lower(), str(entry.bfs)}:
            return entry
    return None


@lru_cache
def handoff_allowlist(path: Path = DATA_DIR / "handoff_allowlist.yml") -> tuple[str, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return tuple(item["domain"] for item in raw.get("domains", []))
