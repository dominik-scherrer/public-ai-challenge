# Durable implementation notes

- A live recycling review rejected `partial` because a collection-point label
  looked sufficient, but deterministic coverage requires `locations` or
  `instructions`. Both agents share explicit field guidance in the catalogue;
  labels alone must not be treated as structured disposal guidance. Review
  rejections use trusted error messages; arbitrary SDK exception text stays hidden.
- The authorized website hostname is exactly `www.ausserberg.ch`. External
  portal URLs can be retained as handoffs but are never fetched. The OpenAI API
  connection is separate from website retrieval. `config.yaml` does not widen
  the website boundary.
- Discovery uses Pydantic AI `WebSearch` with OpenAI indexed-only search and a
  municipal domain filter, enabled by the checked-in config. `WebFetch` uses
  the existing crawler via its custom local implementation: the installed SDK
  does not support native WebFetch on OpenAI Responses. Search citations cannot
  substitute for retained sources. Hosted searches are outside the crawler budget.
- The two Pydantic AI agents perform discovery and evidence review. Package
  generation is deterministic; there is no code-generating builder agent.
  Current defaults use `gpt-6-sol` for discovery and `gpt-6-luna` for review.
  Earlier live Luna discovery attempts failed schema/evidence checks; this is
  historical test evidence, not a guarantee about future model behavior.
- Full-context review precedes snapshot minimization. Source hashes identify
  retained excerpts and relevant observed links, not original HTML responses.
  They support reproducible checks but do not prove source authenticity.
- Form labels and required markers are acquisition observations, not complete
  procedural requirements. An empty or over-nested optional page is recorded
  as an acquisition gap; final identity and useful-evidence checks still apply.
- The crawler permits only a narrow observed Ausserberg PDF handoff query shape
  (`action=get_file`, numeric `id`, alphanumeric `resource_link_id`). Such URLs
  are retained as uninspected document links and never fetched.
- Generated Compose releases use project-scoped image names. Keep distinct
  project names when deploying or rolling back snapshot releases.
- Runtime `--check` validates the offline snapshot. `--health-check` negotiates
  MCP and lists the six tools on the running loopback HTTP server; its port must
  match the server's port.
- The locked MCP 2.x SDK uses `MCPServer` as its high-level Python server.
