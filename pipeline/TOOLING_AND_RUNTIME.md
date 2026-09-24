# Scout Tooling and Runtime

## 1. Architectural split

Scout combines:

- **PydanticAI reasoning**
- typed graph/state orchestration
- deterministic acquisition/runtime tools

The agent should reason about the municipality.

It should not own raw networking or unrestricted browsing.

## 2. Planned framework

### Pydantic models

Use Pydantic models as contracts for:

- Service Index
- Recon result
- Scout strategy
- Scout finding
- service handling
- municipality service
- MunicipalityDiscovery

### PydanticAI

Use PydanticAI agents for semantic decisions:

- interpret reconnaissance
- choose scouting strategy
- match local pages/services to indexed services
- classify possible new/variant services
- understand local service handling
- produce concise grounded summaries

### Typed graph orchestration

Represent Scout as explicit state transitions rather than one open-ended autonomous loop.

Conceptual nodes:

```text
Recon
→ Strategy
→ Discover
→ CoverageCheck
→ FollowUp?
→ InspectServices
→ Compile
→ Validate
```

## 3. Deterministic tool layer

Keep narrow replaceable interfaces.

Examples:

```text
fetch(url) -> SourceSnapshot
parse(snapshot) -> PageIR
discover_links(page) -> Link[]
inspect_sitemap(url) -> SitemapResult
normalize_url(url) -> URL
snapshot(response) -> SourceSnapshot
```

The agent may choose which legal tool to use.

The tool implementation enforces:

- HTTP safety
- domain policy
- redirect validation
- rate limits
- cache
- request budgets
- provenance

## 4. Browser tooling

Do not make browser automation the architecture.

Escalation order:

```text
HTTP
  ↓ insufficient
headless browser
  ↓ genuine interaction required
interactive browser
```

Possible implementations remain replaceable:

- Crawl4AI
- Crawlee / Playwright
- Stagehand-like interaction patterns
- Browser Use for difficult research cases

## 5. Scout strategies

A strategy defines *how to search*, not what is true.

Initial strategy families:

### broad_small_site
Broad bounded exploration for small municipal sites.

### service_directory
Enumerate a structured service catalogue and related resources.

### targeted_large_city
Search specifically for indexed services and high-value roots; avoid full-site crawling.

### mixed_content
Broad enough for small sites but with aggressive municipal-vs-tourism/community filtering.

### custom
Typed escape hatch for unusual structures.

## 6. Tool-use principle

The model should operate inside a legal action space.

Good:

```text
"service directory found; inspect it next"
```

Bad:

```text
"browse anywhere on the internet until satisfied"
```

Scout is agentic because it adapts its plan, not because it has unlimited autonomy.

## 7. Semantic inspection principle

The semantic layer should receive bounded evidence.

Prefer:

```text
Service Index entry
+ relevant PageIRs
+ source/resource metadata
```

over:

```text
entire raw website
```

This reduces tokens and keeps reasoning inspectable.

## 8. Provider independence

The agent architecture should not depend on one commercial model.

Provider/model adapters can change while:

- Pydantic contracts
- graph state
- deterministic tools
- provenance
- MunicipalityDiscovery

remain stable.

## 9. Current repo transition

Existing crawler/prototype/baseline utilities should be treated as reusable acquisition components.

They are not the final Scout abstraction.

The implementation should migrate useful code behind Scout tools rather than preserving old `crawler → normalized service inventory` boundaries for architectural reasons.
