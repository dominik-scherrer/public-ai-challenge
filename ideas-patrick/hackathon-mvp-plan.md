# Municipality MCP server factory

## Outcome

A CLI-first, two-stage agentic pipeline:

**Municipality URL → discovery and normalization agent → validated service inventory → server-building agent → tested MCP server package.**

The first version covers six service categories through seven standardized tools. It provides information and official handoffs, with live refresh for news and collection schedules. Form submissions, PDF extraction, builder UI, and hosted chat demos are deferred.

## 1. Standard service catalogue

Every server exposes the same tools and schemas. Missing information produces an explicit coverage status rather than a missing tool or an invented answer.

| Service | Tool and optional inputs | Normalized result |
|---|---|---|
| Office hours | `get_office_hours(office)` | Office names, weekly hours, published exceptions, contact details |
| Garbage collection | `get_garbage_collection(waste_type, zone, date_from, date_to)` | Published collection dates, waste types, zones, instructions and calendar links |
| Waste recycling | `get_recycling_info(material)` | Accepted materials, disposal guidance, collection points, addresses and hours |
| Move in | `get_move_in_requirements()` | Published requirements, documents, deadlines, responsible office and official registration link |
| Move out | `get_move_out_requirements()` | Published requirements, documents, deadlines, responsible office and official deregistration link |
| Report a problem | `get_problem_reporting_info(category)` | Reporting channels, supported categories, observed form fields and official reporting link |
| Municipal news | `get_latest_municipality_news(limit)` | Headlines, published dates when available, article URLs and publisher |

Use English tool identifiers and preserve source-language content. Start with German-speaking municipalities and German discovery synonyms.

Collection queries default to the next 30 days in `Europe/Zurich`, with a maximum 90-day range. News defaults to five results, capped at twenty. Return available zone choices when a schedule requires a zone; do not infer address-to-zone mappings.

## 2. Stage 1: discover, inspect and normalize

The discovery agent receives the municipality URL and the versioned service catalogue.

- Search navigation, sitemaps, municipal service pages, contact pages, waste sections and news sections specifically for the catalogue.
- Prefer HTML and public structured sources: RSS/Atom, iCalendar and JSON endpoints discovered through official pages.
- Inspect service shape: information page, HTML form, document link, external portal or structured feed. Record visible form fields, required markers, authentication barriers and handoff destinations without submitting anything.
- Record PDF titles and official links only. Mark their contents as uninspected; discover a service from its referring page without claiming knowledge of the PDF.
- Keep external portals as handoffs. Fetch external public feeds only when the municipality explicitly links them as a service source, using the same network protections.

Produce a versioned `discovery.json` with:

- Municipality identity, official URL, language, timestamps and build ID.
- One entry for each of the seven capabilities.
- Normalized service data, delivery shape, official handoffs and coverage: `supported`, `partial`, `handoff_only`, or `unavailable`.
- Field-level evidence: source URL, supporting excerpt and retrieval timestamp.
- Missing information, conflicts and discovery failures.
- Live-source specifications for news and schedules, including format, URL and captured fixtures.

Keep absence of evidence distinct from evidence that a service does not exist. Do not equate observed form fields with complete procedural requirements.

Default crawl limits: 100 HTML/feed requests, two concurrent requests per domain and ten minutes per discovery run. Respect robots rules, block private-network destinations and validate redirects. Report truncation explicitly.

Reuse suitable crawler and provenance components from the repository. Introduce an explicit adapter to the new factory contract; existing seed inventories remain candidates until validated.

## 3. Stage 2: generate within a fixed server standard

A separate builder agent consumes the validated discovery artifact. It generates service modules, source adapters and tests within a maintained Python server template.

The shared template owns MCP transport, schemas, response formatting, safe HTTP access, caching, logging and startup. Generated code cannot change these contracts or add dependencies outside the pinned allowlist.

Each package contains:

```text
municipality-mcp/
  pyproject.toml
  uv.lock
  Dockerfile
  compose.yaml
  README.md
  manifest.json
  discovery.json
  report.md
  llms.txt
  municipality.md
  src/
  tests/
  fixtures/
```

The manifest records municipality identity, build ID, contract version, template version, enabled live adapters and artifact hashes.

Standard runtime behavior:

- One municipality per server; no caller-supplied source URLs.
- Streamable HTTP at `/mcp` and a stdio launch command.
- Identical input/output schemas and read-only tool annotations across packages.
- Structured results plus readable text, following the [MCP tool specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
- A common response envelope containing municipality, capability, coverage, data, sources, timestamps, freshness and limitations.
- Missing service information is an ordinary typed result; execution failures are distinguished from missing coverage.
- No runtime model credentials or runtime LLM interpretation.

Validate generated code in isolation without factory credentials, then run the shared conformance suite. Allow two repair attempts; failed validation produces a diagnostic report rather than a release package.

### Live news and schedules

Prefer standard feed parsers; generate deterministic HTML adapters when needed. Test adapters against captured sources before packaging.

Refresh on demand after a 15-minute news cache or six-hour schedule cache expires. Use a ten-second refresh timeout and retain the last validated response on failure, clearly labelled stale. Without cached data, return an unavailable result and official source link.

Do not promise live coverage where only a PDF or inaccessible portal exists. Such services remain handoff-only. Source layout changes must produce a refresh failure rather than silently replacing valid data with an empty result.

## 4. Municipality knowledge sheet and factory workflow

Generate `municipality.md` from the same evidence-backed inventory: identity, official contacts, service responsibilities, official portals, languages, source links and known coverage gaps.

Generate `llms.txt` as a concise guide linking to that sheet and the service documentation, using the [llms.txt proposal](https://llmstxt.org/). Treat it as a packaged context artifact; automatic chatbot discovery is not guaranteed. Defer a separate installable skill.

Expose three CLI operations:

- `factory discover URL --out DIR`
- `factory build DISCOVERY_JSON --out DIR`
- `factory run URL --out DIR` — orchestrates both stages.

A usable package requires verified municipality identity and at least one evidence-backed capability or official service handoff. Report partial coverage prominently. Preserve immutable builds; rebuilding creates a new artifact and never overwrites the last successful package.

Retain the original 24-hour target as a planning assumption:

1. Hours 0–4: catalogue, schemas, template and fixtures.
2. Hours 4–10: targeted discovery and normalized handoff.
3. Hours 10–16: builder agent, generated adapters and packaging.
4. Hours 16–21: live refresh and end-to-end municipality runs.
5. Hours 21–24: conformance checks, documentation and rehearsal.

## 5. Acceptance checks

- Ausserberg builds through the normal URL-to-package workflow without manually editing generated data.
- A second German-speaking municipality builds without changes to factory code.
- Both packages expose the same seven tool contracts and launch using documented Docker and stdio commands.
- Every substantive answer is traceable to evidence; unsupported details remain absent.
- HTML forms produce guidance and handoffs without submissions.
- PDF-only services remain discoverable and explicitly link-only.
- News and schedule tests cover refresh, cache expiry, source failure, changed markup and stale fallback.
- Collection tests cover missing zones, absent future dates and date boundaries.
- Discovery tests cover crawl limits, blocked pages, conflicting evidence, redirects and malicious page instructions.
- Generated packages contain no secrets and pass the shared contract suite.
- The report distinguishes service discovery coverage from usable structured data and working live adapters.

Ausserberg already provides useful HTML fixtures for [office hours and news](https://www.ausserberg.ch/gemeinschaft/informationen/anschlagbrett-weibil-totz) and a [move-out form](https://www.ausserberg.ch/gemeinschaft/verwaltung/online-schalter/wegzug). Full coverage of the remaining services must be established by discovery.
