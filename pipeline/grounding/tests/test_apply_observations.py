from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apply_observations import apply_observations, summarize


BASE = {
    "schema": "tool-grounding-matrix/v1",
    "tools": [
        {
            "tool_id": "garbage_collection",
            "capability": "waste_collection",
            "maturity": "dummy",
            "supported_municipalities": [],
            "observations": [],
            "contract_version": 1,
            "contract_changes": [],
            "decision_notes": [],
        }
    ],
}


def batch(municipality: str, run_id: str, result: str = "supported"):
    return {
        "schema": "agent-scrap-tool-observations/v1",
        "run_id": run_id,
        "municipality": municipality,
        "canton": "VS",
        "observations": [
            {
                "tool_id": "garbage_collection",
                "service_lead_id": f"lead_{municipality.lower()}_waste",
                "result": result,
                "source_refs": ["src_1"],
                "notes": None,
                "proposed_change": None,
            }
        ],
    }


class GroundingTests(unittest.TestCase):
    def test_first_supported_municipality_advances_grounded_1(self):
        matrix = apply_observations(copy.deepcopy(BASE), batch("Binn", "run-1"))
        row = matrix["tools"][0]
        self.assertEqual(row["maturity"], "grounded_1")
        self.assertEqual(row["supported_municipalities"], ["Binn"])

    def test_second_supported_municipality_advances_grounded_n(self):
        matrix = apply_observations(copy.deepcopy(BASE), batch("Binn", "run-1"))
        matrix = apply_observations(matrix, batch("Ausserberg", "run-2"))
        row = matrix["tools"][0]
        self.assertEqual(row["maturity"], "grounded_n")
        self.assertEqual(row["supported_municipalities"], ["Ausserberg", "Binn"])

    def test_not_observed_does_not_ground_tool(self):
        matrix = apply_observations(
            copy.deepcopy(BASE),
            batch("Binn", "run-1", result="not_observed"),
        )
        self.assertEqual(matrix["tools"][0]["maturity"], "dummy")

    def test_duplicate_observation_is_idempotent(self):
        matrix = apply_observations(copy.deepcopy(BASE), batch("Binn", "run-1"))
        matrix = apply_observations(matrix, batch("Binn", "run-1"))
        self.assertEqual(len(matrix["tools"][0]["observations"]), 1)

    def test_manual_terminal_state_is_preserved(self):
        base = copy.deepcopy(BASE)
        base["tools"][0]["maturity"] = "local_only"
        matrix = apply_observations(base, batch("Binn", "run-1"))
        self.assertEqual(matrix["tools"][0]["maturity"], "local_only")

    def test_summary_counts(self):
        matrix = apply_observations(copy.deepcopy(BASE), batch("Binn", "run-1"))
        self.assertEqual(summarize(matrix), {"grounded_1": 1, "total": 1})


if __name__ == "__main__":
    unittest.main()
