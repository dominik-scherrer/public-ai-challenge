from __future__ import annotations

from pathlib import Path

from .contracts import ServiceIndex


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "catalog" / "services.json"


def load_service_index(path: Path | None = None) -> ServiceIndex:
    source = path or default_catalog_path()
    return ServiceIndex.model_validate_json(source.read_text(encoding="utf-8"))


def all_terms(index: ServiceIndex) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for service in index.services:
        terms = []
        for values in service.labels.values():
            terms.extend(values)
        terms.extend(service.hints)
        out[service.id] = [term.lower() for term in terms]
    return out
