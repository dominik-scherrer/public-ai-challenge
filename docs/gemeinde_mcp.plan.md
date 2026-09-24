# Implementation Plan: Gemeinde MCP Pipeline  {#PL_GMP}

> **Code:** PL_GMP
> **Status:** draft
> **Created:** 2026-09-24
> **Updated:** 2026-09-24
>
> **Concept:** [C_GMP](./gemeinde_mcp.concept.md)
> **Specification:** [SP_GMP](./gemeinde_mcp.sp.md)
> **Depends on:** none
> **Used by:** —
>
> Pipeline that extracts service content, synthesizes Markdown, generates Python tools, and serves them via an MCP server.

## Goal
Implement a pipeline that reads scouted services, extracts HTML and PDF content, creates a single Markdown document per service, generates executable Python tools, and provides the results via an MCP server.

## Technology Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM orchestration | PydanticAI | Provides structured outputs, dependency injection, and automatic self-healing. |
| HTTP client | `httpx.AsyncClient` | Shared across agents. Configurable timeouts. |
| Content extraction | BeautifulSoup, markdownify, pymupdf | Standard HTML and PDF processing libraries. Eliminates LLM extraction cost. |
| Output validation | `ast.parse` in `@output_validator` | Deterministic syntax check. Feeds errors back to LLM for self-correction. |
| LLM provider | OpenAI (`openai:gpt-4o`) | PydanticAI supports string identifiers for providers. |

## Required Knowledge
| Kind | Ref | Applies to | Note |
|------|-----|-----------|------|
| Structure | `.dev_flow/rules/` | All | Project-wide structural rules. |
| Skill | `python-cli` from `.dev_flow/skills/` | Phase 5 | CLI structure. |

## Progress
- [ ] Phase 1 — Project Setup & Scouting
- [ ] Phase 2 — Content Extraction & Synthesis
- [ ] Phase 3 — Tool Generation
- [ ] Phase 4 — MCP Server
- [ ] Phase 5 — End-to-End Pipeline

## Phases

### Phase 1 — Project Setup & Scouting [TODO]
**Depends on:** none
**Implements:** [SP_GMP_01](./gemeinde_mcp.sp.md#SP_GMP_01)
**Verify:** Module import succeeds. JSON parses into `ScoutedService`. Validate `SynthesizedContent` and `GeneratedTools` instances.

What to create:

| Entity | Module | Purpose |
|--------|--------|---------|
| Dependencies | `pyproject.toml` | Add `pydantic-ai[openai]`, `mcp`, `beautifulsoup4`, `markdownify`, `pymupdf`. |
| Models | `src/public_ai_challenge/gemeinde_mcp/models.py` | Define `ScoutedService`, `SynthesizedContent`, `GeneratedTools`. |
| Dataclass | `src/public_ai_challenge/gemeinde_mcp/models.py` | Define `ServiceProcessingDeps` with `http_client` and `model_name`. |
| Test data | `input/scouted_services.json` | 2-3 entries using Ausserberg URLs (mix of `available: true/false`). |

Notes:
- `ScoutedService` attributes: `name`, `description`, `urls`, `available`.
- `SynthesizedContent` attributes: `service_name`, `markdown`, `source_urls`.
- `GeneratedTools` attributes: `service_name`, `python_code`, `tool_names`.

### Phase 2 — Content Extraction & Synthesis [TODO]
**Depends on:** Phase 1
**Implements:** [SP_GMP_02](./gemeinde_mcp.sp.md#SP_GMP_02)
**Verify:** SP_GMP_05_01, SP_GMP_05_02

What to create:

| Entity | Module | Purpose |
|--------|--------|---------|
| `fetch_content` | `src/public_ai_challenge/gemeinde_mcp/extraction.py` | Fetches URL data and returns bytes and content type. |
| `extract_html_to_markdown` | `src/public_ai_challenge/gemeinde_mcp/extraction.py` | Parses `<main>` or `<body>` to Markdown. |
| `extract_pdf_to_markdown` | `src/public_ai_challenge/gemeinde_mcp/extraction.py` | Extracts text from PDF to Markdown. |
| `synthesis_agent` | `src/public_ai_challenge/gemeinde_mcp/agents.py` | Returns `SynthesizedContent` from Markdown fragments. |
| `process_service_content` | `src/public_ai_challenge/gemeinde_mcp/agents.py` | Extracts content and runs the synthesis agent per service. |

Notes:
- `process_service_content` writes unavailable messages for `available: false` services.
- Extracted fragments save to `output/fragments/{service.name}__{url_hash}.md`.
- Synthesized output saves to `output/{service.name}.md`.
- Returns raw fetched contents for Phase 3.

### Phase 3 — Tool Generation [TODO]
**Depends on:** Phase 1
**Implements:** [SP_GMP_03](./gemeinde_mcp.sp.md#SP_GMP_03)
**Verify:** SP_GMP_05_03, SP_GMP_05_04, SP_GMP_05_10

What to create:

| Entity | Module | Purpose |
|--------|--------|---------|
| `tool_gen_agent` | `src/public_ai_challenge/gemeinde_mcp/agents.py` | Generates `GeneratedTools` containing action and information tools. |
| `@tool_gen_agent.output_validator` | `src/public_ai_challenge/gemeinde_mcp/agents.py` | Strips code fences, parses syntax, raises `ModelRetry` on error. |
| `generate_tools` | `src/public_ai_challenge/gemeinde_mcp/tool_generator.py` | Runs agent using synthesized Markdown and raw content. |

Notes:
- Output saves to `output/{service.name}_tools.py`.
- Empty file writes when `service.available` is false or retries exhaust.

### Phase 4 — MCP Server [TODO]
**Depends on:** Phase 1
**Implements:** [SP_GMP_04](./gemeinde_mcp.sp.md#SP_GMP_04)
**Verify:** SP_GMP_05_05, SP_GMP_05_06, SP_GMP_05_07

What to create:

| Entity | Module | Purpose |
|--------|--------|---------|
| `FastMCP` | `src/public_ai_challenge/gemeinde_mcp/server.py` | Hosts the server. |
| CLI command | `src/public_ai_challenge/gemeinde_mcp/server.py` | Starts the server. |

Notes:
- Registers `output/{name}.md` files as MCP Resources with URI `gemeinde://services/{name}`.
- Registers public functions from `output/{name}_tools.py` as MCP Tools.
- Implements cross-service tools: `list_services`, `list_tools`, `search_services`.

### Phase 5 — End-to-End Pipeline [TODO]
**Depends on:** Phase 2, Phase 3, Phase 4
**Implements:** [SP_GMP_05](./gemeinde_mcp.sp.md#SP_GMP_05)
**Verify:** SP_GMP_05_08, SP_GMP_05_09

What to create:

| Entity | Module | Purpose |
|--------|--------|---------|
| `run_pipeline` | `src/public_ai_challenge/gemeinde_mcp/pipeline.py` | Manages async execution of extraction, tool generation, and server start. |
| CLI command | `src/public_ai_challenge/gemeinde_mcp/pipeline.py` | `gemeinde-mcp-pipeline --input ... --output ... [--model ...]`. |

Notes:
- Creates a single `httpx.AsyncClient` shared via `ServiceProcessingDeps`.

## Backlog
- Deferred concept alternatives.

## Changelog

| Date | Change |
|------|--------|
| 2026-09-24 | Initial version (v5.0.0) |
