# Municipality URL → runnable MCP package: 24-hour MVP

Status: implementation plan based on Patrick's confirmed scope, 2026-09-24.
Inputs: `ideas-patrick/servicelist_patrick.md`, `ideas-patrick/ausserberg_example.md`, and `ideas/mmp-swiss-municipality-service-research.md`. Dominik's documents are excluded from the design.

## Outcome and scope

A team member supplies an official Swiss municipality URL. The builder discovers public German-language information, extracts supported services, produces a review report, and exports a runnable MCP package. The same data and runtime power a hosted demo endpoint. Ausserberg is the reference municipality; a second German-speaking municipality tests generalization without bespoke code.

Information and official handoffs only. Unknown attributes are omitted; records with insufficient evidence are skipped and reported. Partial builds are permitted and visibly identified. No submission, authentication to citizen portals, payments, live availability claims, or guaranteed universal coverage.

Commercial LLMs handle build-time extraction. Use a small provider interface so Apertus on Swisscom infrastructure can be evaluated later. Runtime retrieval does not require an LLM or provider key. Citizen conversations use the host's chosen model independently.

## UI recommendation

Use an unmodified Open WebUI deployment for citizen conversations. Its native MCP integration supports Streamable HTTP; an administrator configures the endpoint and enables the tools. Pin a tested release. Do not build or fork a chat client or implement rich MCP Apps cards during the hackathon.

Build a separate minimal team page: URL input → progress → extracted services and review report → download package and copy hosted endpoint. Implement with server-rendered HTML alongside the Python backend. A CLI exposes the same build operation and is the fallback if the UI is cut for time.

Use Open WebUI as the primary narrated demo, then demonstrate the same inventory through ChatGPT and Claude. Validate access to custom MCP connections in the actual demo accounts immediately. If a host cannot connect, record the limitation; a protocol smoke test is not proof of compatibility with that host.

Reference: https://docs.openwebui.com/features/extensibility/mcp/

## Architecture

```text
Team page / CLI
      |
Bounded crawl → HTML/PDF text + source snapshots
      |
LLM extraction → typed inventory → validation → review report
      |
Immutable build directory
      +-- downloadable package + shared runtime
      +-- hosted shared runtime → /municipalities/<id>/mcp
                                      |
                              Open WebUI / ChatGPT / Claude
```

The LLM produces data, never executable server code. Every package uses the same maintained runtime. Each endpoint is bound to one inventory; tool calls cannot select arbitrary local files or URLs.

Use Python and uv, the official MCP Python SDK, typed schema validation, ordinary HTTP fetching and HTML parsing, and PDF text extraction. Pin compatible dependencies after an initial smoke test; verify the repository's Python 3.14 baseline against them. Use JSON plus SQLite full-text search for local retrieval. No vector database, task queue, Kubernetes, or runtime agent loop is needed.

## Initial tool contract

Keep four tools for the mandatory delivery:

| Tool | Input | Result |
| --- | --- | --- |
| `list_services` | optional category, pagination | Compact supported-service catalog |
| `find_service` | query, bounded result limit | Matching services and snippets |
| `get_service` | stable service ID | Requirements, office, fees, documents, official handoffs, evidence |
| `search_documents` | query, optional service ID, bounded result limit | Relevant excerpts with URL and page/section references |

Contacts and office hours are fields in service records; notices are typed records retrievable through these tools. Separate authority, notices, or waste-date tools can follow when extraction warrants them. Use German synonyms for search; return an explicit no-match result instead of fabricated answers.

Responses contain structured data and a readable text representation for host interoperability. Each response identifies municipality and build timestamp. Unknown fields remain absent; a separate completeness field states omissions. Fixed tool descriptions tell the host to use source links and distinguish information, requests, and confirmed outcomes.

## Ausserberg reference set

Must cover: arrival/departure, residence certificates where discovered, municipal contacts/hours, facility rental requests, and building/solar application routing. Include at least one text-based PDF to demonstrate document retrieval. Regulations and official notices are included if the crawl discovers usable sources, but legal interpretation and computed objection deadlines are excluded.

Reference scenarios:

1. “Ich ziehe nach Ausserberg. Wo melde ich mich an und welche Unterlagen brauche ich?”
2. “Wie kann ich einen Gemeinderaum für eine Geburtstagsfeier anfragen?”
3. “Wo finde ich das Formular für eine Solaranlage und welche Stelle ist zuständig?”
4. “Wann ist die Gemeindekanzlei offen?”
5. “Ist der Saal nächsten Samstag frei?” → explain that availability is not available in the inventory and provide the official request channel.

Answers may contain only supported details. Discovery of a form does not prove that all procedural requirements have been found. Facility requests are subject to municipal review, not confirmed reservations.

## Data and evidence

Inventory envelope: schema version, municipality identity, official URL, source language, build ID, fetched timestamps, runtime compatibility, and partial/complete build status. Only include a BFS identifier if established from evidence; otherwise use a stable local identity.

Service: stable ID, title, category, summary, delivery mode, optional requirements/fees/office/hours, form/document references, and official handoff URLs. Use internal categories initially; eCH mapping is a later enrichment, not a hackathon dependency.

Every substantive extracted claim has a source ID, URL, exact supporting text, and page/section when available. Preserve effective dates separately from fetch times. Do not describe a recent fetch as municipal verification. Dates and fees retain their conditions; conflicts are reported and affected attributes withheld. Distinguish unknown, not applicable, inaccessible, and conflicting information in the review report.

## Build pipeline and boundaries

1. Validate HTTP(S) input and identify the official site. Refuse private/local network destinations; revalidate redirects and resolved destinations.
2. Discover links from the homepage, navigation, sitemap, and service/form sections. Respect robots rules. Initial configurable bounds: 100 HTML pages, 20 PDFs, 10 MB per document, two concurrent requests per domain, and a ten-minute build deadline. Report when a bound truncates discovery.
3. Fetch and cache source snapshots; strip navigation and extract readable text with stable source identifiers. Skip scanned PDFs with an explicit report entry for the MVP. Browser rendering is a fallback only if essential reference pages require it.
4. Follow the official domain by default. Retain external handoff links with evidence from the referring municipal page. Do not crawl external sites automatically; any enabled external domain gets the same URL validation. External links are not an authorization to submit data.
5. Extract schema-constrained records with commercial LLMs. Treat website text as untrusted content. No tools, shell execution, credentials, or executable templates are available to extraction. Validate structured outputs and evidence references. Unsupported claims are withheld.
6. Deduplicate services and validate records, dates, URL schemes, and references. Use targeted model review of ambiguous results only within a build budget; deterministic checks remain mandatory.
7. Produce the package and report. A minimum usable build needs verified municipality identity and one source-backed service with an official next step or contact. Below that, return a failed build report rather than a nominally useful server.

The hosted builder is team-restricted to bound cost. The public demo MCP endpoint serves only the public, read-only snapshot over HTTPS with rate limits. Do not log citizen tool arguments or ship extraction credentials in packages. This is an independent hosting choice, not a requirement inherited from other idea folders.

## Package and refresh

Export a ZIP containing pinned runtime source/dependencies, Dockerfile, Compose configuration, inventory JSON, SQLite retrieval index, referenced text excerpts, build manifest, review report, and launch/host-connection instructions. Build an equivalent hosted instance from the same artifact. Retain full crawl snapshots as team build artifacts; package only the source material needed for retrieval and evidence.

Primary launch: `docker compose up --build`. First launch requires dependency/image downloads; serving the built snapshot then requires no commercial model key. Label this distinction in the README. Offer stdio if it is needed for a tested host path; Streamable HTTP is the primary transport.

Manual rebuild command creates a new immutable build and report. Compare added/removed services and failed sources. A failed rebuild leaves the prior hosted build active. Team explicitly promotes a successful partial build when coverage regresses. Scheduled refresh, public publishing workflows, and automatic deployment are outside the MVP.

## 24-hour delivery schedule

| Hours | Engineer A: extraction | Engineer B: runtime and integration | Engineer C, if available |
| --- | --- | --- | --- |
| 0–2 | Agree schema; curate 10–15 reference records | Fixture MCP server; verify actual host accounts and HTTP connection | Bring up HTTPS hosting and Open WebUI |
| 2–7 | Bounded crawler and HTML/PDF text | Four tools over fixture; search and response format | Builder page, job status, download flow |
| 7–12 | LLM extraction, evidence, omissions report | Export package; wire automatic inventory into runtime | Package documentation; host integration checks |
| 12–17 | Run Ausserberg; fix extraction failures | End-to-end build/download/launch/host test | Evaluate reference scenarios and second municipality |
| 17–21 | Second-site fixes; rebuild comparison | Negative tests; freeze dependencies and deploy demo | Demo flow, report presentation, setup documentation |
| 21–24 | Joint buffer, fixes, rehearsal, and reproducible release | Joint buffer, fixes, rehearsal, and reproducible release | Joint buffer, fixes, rehearsal, and reproducible release |

With two engineers, B owns the minimal builder page after CLI export works. Cut visual polish, dedicated notices tooling, browser rendering, and optional stdio before sacrificing evidence, clean package startup, or host tests. Stop adding features at hour 17. Reserve the last three hours for failures and rehearsal. Apertus evaluation happens after the commercial-model baseline passes.

## Acceptance checks

- Ausserberg builds from its URL through the normal pipeline, without manually patching generated records.
- Each exposed substantive claim has retrievable supporting evidence. Manually inspect the reference set for omissions and incorrect extraction; record results rather than asserting universal accuracy.
- Package launches from a clean environment using documented commands and contains no model credentials.
- Hosted and downloaded versions return equivalent records for the same build.
- Actual ChatGPT, Claude, and Open WebUI accounts discover tools and complete at least one successful multi-tool scenario each. Record versions, setup, and any limitations.
- Unknown fees, unavailable calendars, contradictory dates, blocked pages, scanned PDFs, and empty searches produce omissions or clear unavailable results.
- Malicious page instructions remain inert data; crawl inputs and redirects cannot target internal network addresses.
- A second German-speaking municipality produces useful source-backed services without site-specific code; report coverage instead of promising parity.
- A failed rebuild preserves the last good hosted snapshot.

## Setup inputs needed when implementation starts

Available commercial model credentials and spending ceiling; a hosting environment with public HTTPS; access to the three demo host accounts; and ownership of the workstreams. These do not block the schema, fixture, and local pipeline work. Confirm them in the first hour rather than discovering access issues near the demo.
