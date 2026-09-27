# First MCP inventory batch — 2026-09-24

Partial source-backed seed delivery for MCP integration.

Contains Ausserberg plus the seven pipeline benchmark municipalities: Binn, Biel/Bienne, Zürich, Lausanne, Lugano, Ilanz/Glion and Bosco/Gurin.

Each folder contains `inventory.json`, `documents.jsonl` and `build-report.json`.

This batch was assembled from retrievable official public sources in the current environment. It is **not represented as a native crawler HTTP execution**. Its purpose is to unblock the MCP/runtime workstream against the agreed `mmp-service-inventory/v0` contract. Native crawler runs can replace these seed inventories without changing the MCP integration.

Biel/Bienne is intentionally delivered as an empty partial inventory because the official city website could not be reliably retrieved in this run; the gap is explicit rather than backfilled from non-authoritative material.
