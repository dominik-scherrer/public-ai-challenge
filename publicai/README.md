# Municipality MCP server factory

A CLI-first factory that turns municipal HTML into an evidence-backed, read-only
MCP server. Discovery is currently restricted to **`www.ausserberg.ch`**. The
restriction is enforced in code, including DNS resolution and redirects; it
cannot be widened by a prompt, URL parameter or configuration file.

## Run

Requires Python 3.14 and `uv`:

```sh
uv sync
cp .env.example .env  # only when .env does not already exist
```

Set `OPENAI_API_KEY` in `.env`. Both Pydantic AI agents use the OpenAI API directly:
`gpt-6-sol` for discovery and `gpt-6-luna` for evidence review, with low reasoning
effort. Model IDs and reasoning effort are configurable in `config.yaml`. Discovery
uses Sol because live Luna runs failed the schema and evidence checks.

```sh
uv run factory discover https://www.ausserberg.ch/ --out artifacts
uv run factory build artifacts/discovery-<id>/discovery.json --out artifacts
uv run factory run https://www.ausserberg.ch/ --out artifacts
```

`publicai` is an alias for the same CLI. Set each step's default in `config.yaml`:

```yaml
model:
  discovery_model: gpt-6-sol
  review_model: gpt-6-luna
```

Both `discover` and `run` accept independent overrides:

```sh
uv run factory discover https://www.ausserberg.ch/ --out artifacts \
  --discovery-model gpt-6-sol --review-model gpt-6-luna
```

Use `--model MODEL` to override both steps. A step-specific option takes precedence
over `--model`; otherwise, the configured value is used. Use `--config PATH` to load
another configuration file. The `build` step is deterministic and uses no model.

Model API traffic goes only to OpenAI's fixed API endpoint; this is separate
from website retrieval. Discovery uses Pydantic AI's native `WebSearch` capability
with indexed results filtered to `www.ausserberg.ch`. Set `web_search_enabled: false`
in `config.yaml` to disable it (the default when no configuration file is loaded).
Search can incur provider tool charges; hosted searches are separate from the
crawler request budget. Neither agent gets a browser, shell, filesystem access,
form submission or external URL fetching. No secrets are passed to their prompts or tools.

Each run writes a new directory; existing discoveries and packages are never
overwritten. Failed discovery/review/build attempts produce diagnostic artifacts
and a nonzero exit code. Local artifacts are ignored by Git.
Successful discoveries include `metrics.json` with duration, website requests and
per-agent token/tool usage. Diagnostics retain safe validation details, not API payloads.
For semantic review rejections, inspect `review.json` beside `diagnostic.json` for
the rejected claim paths and reasons; no discovery is published until review passes.

## The two agents and their boundaries

1. **Discovery agent** inspects public municipal HTML or explicitly linked
   public JSON through Pydantic AI's `WebFetch` capability (`web_fetch`) and searches
   known navigation using `list_sources`. Because OpenAI Responses has no native
   WebFetch support in the installed SDK, this capability uses the restricted
   crawler as its local implementation. Native `WebSearch` finds additional page
   candidates; snippets cannot become evidence until a page is fetched and retained.
   It returns a
   typed inventory with literal excerpts for every fact. Trusted acquisition code
   owns source IDs, hashes, timestamps and website permissions.
2. **Evidence-review agent** checks every claim and municipality identity. Its
   only tool, `read_source`, reads retained text by source ID. Missing checks,
   unsupported claims, conflicts in definitive answers or identity disagreement
   block publication. Review is best-effort semantic checking, not proof.

The deterministic builder packages a maintained template; neither agent writes
or executes code. The runtime has no model dependency or credentials and makes
no outbound requests. Both agents' instructions live in `src/publicai/prompts/`.
The small tool sets are loaded eagerly because they are needed throughout each
agent's task; there is no general tool discovery or sub-agent spawning.

The crawler allows GET only, respects robots rules and pins public IP addresses
at connection time. Defaults are 100 requests including robots/sitemaps and
redirects, two concurrent requests, a ten-minute run, ten-second requests, five
redirects and 5 MiB response bodies. Cookies, credentials, proxies from the
environment, query strings, non-default ports and private-network destinations
are blocked for fetching. Observed public download-query links are retained only
as handoffs. PDF/iCalendar titles and links are retained as uninspected document
metadata; external portals also remain handoffs. JavaScript
execution, PDF/calendar parsing and form submission are outside this MVP. Public
JSON must be explicitly linked from inspected municipal HTML on the permitted host;
its size, nesting and values are bounded, and links within JSON are never auto-followed.
Observed form labels, required markers and authentication interfaces are retained
as acquisition metadata. They are never treated as complete procedural requirements.
HTML nesting is limited to 128 elements. Empty or excessively nested optional pages
become recorded acquisition gaps; identity and useful-evidence checks still apply.
Published email and telephone link destinations remain citable even when their
visible labels contain no address or number.

## Six stable tools

| Tool | Optional filters |
| --- | --- |
| `get_office_hours` | `office` |
| `get_garbage_collection` | `waste_type`, `zone`, `date_from`, `date_to` |
| `get_recycling_info` | `material` |
| `get_move_in_requirements` | — |
| `get_move_out_requirements` | — |
| `get_problem_reporting_info` | `category` |

All tools are read-only and return structured results and readable text. Results
include coverage (`supported`, `partial`, `handoff_only`, `unavailable`), query
outcome, citations, source retrieval timestamps and an explicit build-time
snapshot label. `supported` means minimum structured guidance, not completeness.
Requirements retain their conditions; form fields do not imply an exhaustive
procedure. Conflicting claims are reported separately from definitive answers.
A package can have partial coverage when identity and review checks pass and at
least one capability has evidence-backed data or an official handoff.

Filters match exact identifiers or labels, ignoring case and surrounding spaces.
Unknown filters return available choices. Zone-dependent waste guidance requires
a zone; no address mapping is inferred. Collection date windows are inclusive,
use Europe/Zurich, default to today through 29 days later, and cannot exceed 90
calendar days. General instructions survive missing dates. Absence of dates is
only `no_matching_dates` when an explicit published interval covers the whole
query. Undated and expired snapshots are labeled accordingly. Rebuild to update.

## Generated package

A successful `build-<id>/` contains its own `pyproject.toml`, maintained `uv.lock`,
`Dockerfile`, `compose.yaml`, `README.md`, manifest with file hashes,
`discovery.json`, evidence report, `llms.txt`, `municipality.md`, runtime source,
conformance tests and independently authored fictional fixtures.

From a generated directory:

```sh
uv sync --frozen --no-dev
uv run --frozen --no-dev municipality-mcp --discovery discovery.json --transport stdio
uv run --frozen --no-dev municipality-mcp --discovery discovery.json --transport streamable-http
# Streamable HTTP endpoint: http://127.0.0.1:8000/mcp

docker compose up --build
```

### Connect from ChatGPT desktop or Codex

Keep the Streamable HTTP server above running, then in the **ChatGPT desktop app**
open **Settings → MCP servers → Add server**. Name it `municipality`, choose
**Streamable HTTP**, and enter `http://127.0.0.1:8000/mcp`. Save and select
**Restart**. In the composer, type `/mcp` to confirm the server and its tools appear.
The Codex CLI and IDE extension share this MCP configuration with the desktop app.

Alternatively, configure it from a terminal on the same computer:

```sh
codex mcp add municipality --url http://127.0.0.1:8000/mcp
codex mcp list
```

These steps are for the local desktop/CLI/IDE clients. ChatGPT **web** cannot
reach your computer's loopback address through this configuration; a private
server needs a [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
or another reachable HTTPS endpoint and a developer-mode connection.
See OpenAI's [MCP setup guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
for the current client steps.

The HTTP launch defaults to loopback. Container port mapping also uses loopback;
production authentication and public hosting are deferred. The generated
container runs as a dedicated non-root user with a read-only filesystem,
capability drops, resource limits and a private runtime network. Docker itself
should run rootlessly. Consult the generated README for runtime commands and
the exact isolation limits of conformance checks.
Compose derives image names from each release's project directory, avoiding a
shared mutable image tag. Container health checks probe the running loopback MCP
server; `--check` remains an offline snapshot validation command.

The repository's factory container can also run the CLI. Model credentials belong
only to the factory process; generated runtime containers do not inherit them.

## Validate

```sh
uv run ruff format .
uv run ruff check .
uv run pytest
# Build a clearly fictional fixture without contacting a model or website:
uv run factory build src/publicai/fixtures/representative.json --out artifacts
```

Tests use deterministic Pydantic AI `FunctionModel` agents, fake HTTP boundaries,
and independently authored source excerpts. They exercise the normal workflow,
identity/evidence checks, filters, zones, date boundaries, malicious source text,
network limits and immutable publication. Every package runs offline conformance
in a subprocess with cleared credentials, denied sockets/process spawning and
resource limits. This local check is defense in depth, not an OS sandbox.
Generated Docker configuration supports a separate container runtime; the
builder's automatic checks do not launch Docker.

The fixture municipality is fictional. Its URLs use the authorized host only to
exercise network policy; its contents are **not facts about Ausserberg**.

Telemetry is off by default. `config.yaml` can opt into Logfire instrumentation
with model/tool content and binary payloads disabled. `send_to_logfire: true`
requires `LOGFIRE_TOKEN`; standard `OTEL_EXPORTER_OTLP_*` settings can target an
Aspire collector. No telemetry service is contacted unless enabled. Application
logs contain event names and exception types on stderr, never SDK payloads.

The original plan also requests a second municipality. That trial is deferred
because the crawler currently permits only `www.ausserberg.ch`. The shared
contracts and fictional fixtures exercise service variants without contacting
another site. See [PLAN.md](PLAN.md) for outstanding validation.

The existing standalone OpenAI connectivity script remains available:
`uv run python scripts/test_openai.py`.
