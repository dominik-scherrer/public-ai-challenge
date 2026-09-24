#!/usr/bin/env python3
"""Compile crawler output into a municipality Service Inventory for the MCP runtime.

Input directory:
  sources.jsonl
  services.jsonl

Output directory:
  inventory.json
  documents.jsonl
  build-report.json

Dependency-free by design so any crawler workstream can produce the same handoff.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"missing required input: {path}")
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{i}: invalid JSON: {exc}") from exc
    return rows


def preferred_label(service: dict[str, Any], languages: list[str]) -> str:
    labels = service.get("labels") or {}
    for lang in languages + ["de", "fr", "it", "rm"]:
        value = labels.get(lang)
        if value:
            return value
    return service.get("title") or service.get("service_id") or "Untitled service"


def delivery_modes(service: dict[str, Any]) -> list[str]:
    channels = service.get("channels") or {}
    return [name for name, enabled in channels.items() if enabled is True]


def action_handoffs(service: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for action in service.get("actions") or []:
        if not isinstance(action, dict):
            continue
        url = action.get("url")
        if url:
            out.append({
                "type": action.get("type") or "official_handoff",
                "url": url,
                **({"label": action["label"]} if action.get("label") else {}),
            })
    return out


def source_projection(source: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "source_id", "url", "final_url", "canonical_url", "title", "publisher",
        "classification", "source_type", "language", "retrieved_at",
        "source_modified_at", "content_hash", "content_type", "page_role",
    )
    return {k: source.get(k) for k in keep if source.get(k) is not None}


def evidence_projection(service: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for field, prov in (service.get("field_provenance") or {}).items():
        for item in prov.get("evidence") or []:
            evidence.append({
                "field": field,
                "source_ref": item.get("source_ref"),
                "text": item.get("text"),
                "quote_check": item.get("quote_check", "not_checked"),
                "classification": prov.get("classification"),
            })
    return evidence


def completeness(service: dict[str, Any]) -> dict[str, str]:
    fields = (
        "description", "requirements", "fees", "documents",
        "processing_time", "actions", "contacts",
    )
    result = {}
    for field in fields:
        value = service.get(field)
        result[field] = "supported" if value not in (None, [], {}, "") else "unknown"
    return result


def service_projection(service: dict[str, Any], languages: list[str]) -> dict[str, Any]:
    projected = {
        "id": service.get("service_id"),
        "title": preferred_label(service, languages),
        "labels": service.get("labels") or {},
        "category": service.get("concept") or "unmapped",
        "summary": service.get("description"),
        "delivery_mode": delivery_modes(service),
        "requirements": service.get("requirements") or [],
        "fees": service.get("fees") or [],
        "documents": service.get("documents") or [],
        "processing_time": service.get("processing_time"),
        "contacts": service.get("contacts") or [],
        "handoffs": action_handoffs(service),
        "source_refs": service.get("source_refs") or [],
        "evidence": evidence_projection(service),
        "completeness": completeness(service),
        "status": service.get("status") or "candidate",
        "trust": service.get("trust") or {},
        "conflicts": service.get("conflicts") or [],
    }
    return {k: v for k, v in projected.items() if v is not None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--municipality", required=True)
    parser.add_argument("--canton", required=True)
    parser.add_argument("--official-url", required=True)
    parser.add_argument("--language", action="append", dest="languages", default=[])
    parser.add_argument("--bfs-id")
    parser.add_argument("--build-id")
    parser.add_argument("--status", choices=("partial", "complete"), default="partial")
    args = parser.parse_args()

    languages = args.languages or ["de"]
    sources = read_jsonl(args.input / "sources.jsonl")
    services = read_jsonl(args.input / "services.jsonl")
    source_by_id = {s.get("source_id"): s for s in sources if s.get("source_id")}

    missing_refs = []
    for svc in services:
        for ref in svc.get("source_refs") or []:
            if ref not in source_by_id:
                missing_refs.append({"service_id": svc.get("service_id"), "source_ref": ref})

    if missing_refs:
        raise SystemExit("cannot compile inventory: unresolved source_refs: " + json.dumps(missing_refs))

    projected_services = [service_projection(s, languages) for s in services]
    referenced_ids = {
        ref for svc in projected_services for ref in svc.get("source_refs", [])
    }
    projected_sources = [
        source_projection(source_by_id[sid])
        for sid in sorted(referenced_ids)
        if sid in source_by_id
    ]

    now = datetime.now(timezone.utc).isoformat()
    build_id = args.build_id or (
        f"{args.municipality.lower().replace(' ', '-')}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    municipality = {
        "name": args.municipality,
        "canton": args.canton,
        "official_url": args.official_url,
    }
    if args.bfs_id:
        municipality["bfs_id"] = args.bfs_id

    inventory = {
        "schema": "mmp-service-inventory/v0",
        "build_id": build_id,
        "built_at": now,
        "build_status": args.status,
        "runtime_compatibility": {
            "tools": ["list_services", "find_service", "get_service", "search_documents"]
        },
        "municipality": municipality,
        "source_languages": languages,
        "services": projected_services,
        "sources": projected_sources,
    }

    documents = []
    seen_docs = set()
    for svc in projected_services:
        for doc in svc.get("documents") or []:
            if not isinstance(doc, dict):
                continue
            key = (doc.get("url"), doc.get("title"), svc["id"])
            if key in seen_docs:
                continue
            seen_docs.add(key)
            documents.append({
                "service_id": svc["id"],
                **doc,
            })

    unchecked = sum(
        1
        for svc in projected_services
        for ev in svc.get("evidence") or []
        if ev.get("quote_check") != "exact"
    )
    conflicts = sum(len(svc.get("conflicts") or []) for svc in projected_services)

    report = {
        "schema": "mmp-build-report/v0",
        "build_id": build_id,
        "municipality": municipality,
        "counts": {
            "input_sources": len(sources),
            "referenced_sources": len(projected_sources),
            "services": len(projected_services),
            "documents": len(documents),
            "unchecked_evidence_quotes": unchecked,
            "conflicts": conflicts,
        },
        "warnings": [
            *(
                [f"{unchecked} evidence quote(s) are not exact-checked"]
                if unchecked else []
            ),
            *(
                [f"{conflicts} conflict(s) remain in service records"]
                if conflicts else []
            ),
        ],
        "handoff_ready": bool(projected_services) and not missing_refs,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.out / "documents.jsonl").open("w", encoding="utf-8") as fh:
        for document in documents:
            fh.write(json.dumps(document, ensure_ascii=False) + "\n")
    (args.out / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"compiled {len(projected_services)} services / "
        f"{len(projected_sources)} referenced sources -> {args.out}"
    )


if __name__ == "__main__":
    main()
