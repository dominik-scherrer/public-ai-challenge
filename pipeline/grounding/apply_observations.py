from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUTO_LEVELS = {"dummy", "grounded_1", "grounded_n"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def observation_key(run_id: str, municipality: str, observation: dict[str, Any]) -> tuple:
    return (
        run_id,
        municipality,
        observation.get("tool_id"),
        observation.get("service_lead_id"),
        observation.get("result"),
        tuple(sorted(observation.get("source_refs", []))),
    )


def apply_observations(matrix: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    if batch.get("schema") != "agent-scrap-tool-observations/v1":
        raise ValueError("unsupported observation schema")

    run_id = batch.get("run_id")
    municipality = batch.get("municipality")
    if not run_id or not municipality:
        raise ValueError("run_id and municipality are required")

    tools = {row["tool_id"]: row for row in matrix.get("tools", [])}

    for observation in batch.get("observations", []):
        tool_id = observation.get("tool_id")
        if tool_id not in tools:
            raise ValueError(f"unknown tool_id: {tool_id}")

        row = tools[tool_id]
        event = {
            "run_id": run_id,
            "municipality": municipality,
            "canton": batch.get("canton"),
            "service_lead_id": observation.get("service_lead_id"),
            "result": observation.get("result"),
            "source_refs": observation.get("source_refs", []),
            "notes": observation.get("notes"),
            "proposed_change": observation.get("proposed_change"),
        }

        existing = {
            observation_key(
                item.get("run_id", ""),
                item.get("municipality", ""),
                item,
            )
            for item in row.get("observations", [])
        }
        key = observation_key(run_id, municipality, observation)
        if key not in existing:
            row.setdefault("observations", []).append(event)

        supported = sorted(
            {
                item["municipality"]
                for item in row.get("observations", [])
                if item.get("result") == "supported"
            }
        )
        row["supported_municipalities"] = supported

        if row.get("maturity") in AUTO_LEVELS:
            if len(supported) == 0:
                row["maturity"] = "dummy"
            elif len(supported) == 1:
                row["maturity"] = "grounded_1"
            else:
                row["maturity"] = "grounded_n"

    return matrix


def summarize(matrix: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in matrix.get("tools", []):
        maturity = row.get("maturity", "unknown")
        result[maturity] = result.get(maturity, 0) + 1
    result["total"] = len(matrix.get("tools", []))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Agent Scrap observations to the tool grounding matrix")
    parser.add_argument("observations", type=Path)
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path(__file__).with_name("tool-grounding-matrix.json"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    matrix = load_json(args.matrix)
    batch = load_json(args.observations)
    updated = apply_observations(matrix, batch)

    target = args.out or args.matrix
    target.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summarize(updated), indent=2))


if __name__ == "__main__":
    main()
