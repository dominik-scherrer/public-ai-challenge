# Original MVP design context

This file records the decisions that shaped the implementation. For current
commands, permissions, package contents, and tool behavior, use
[README.md](../README.md). For unfinished validation, use [PLAN.md](../PLAN.md).

The original goal was a CLI-first pipeline: inspect a municipal website, produce
an evidence-backed inventory of six services, and package a read-only MCP server
from a maintained template. Discovery and evidence review use separate agents;
the builder is deterministic. Every package exposes the same six tools even when
a service has only a handoff or no discovered information.

The design required field-level excerpts, retained source snapshots, explicit
coverage and query outcomes, conditional requirements, and visible limitations.
The runtime answers from its packaged snapshot; it does not update itself. Forms
and external portals are handoffs, while PDF/calendar content is uninspected.
These constraints are implemented in the contracts, prompts, crawler, builder,
and runtime; their precise current behavior is documented in the README.

The original acceptance plan also called for a second German-speaking
municipality and a Docker demonstration. Neither is established by the current
repository. The crawler is hard restricted to `www.ausserberg.ch`, and the
recorded review did not launch Docker. The broader municipality catalogue and
transactional tools discussed during ideation were not implemented.
