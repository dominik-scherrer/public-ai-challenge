# Legacy pipeline material

> **LEGACY / SUPERSEDED**
>
> Nothing in this directory defines the current Scout architecture or the current Scout → MCP Factory contract.

The active architecture is:

```text
Municipality URL + Service Index
→ Scout Step 1: Discover
→ Scout Step 2: Understand / Compile
→ municipality-discovery/v1
→ MCP Factory
```

Current implementation: `pipeline/scout/`  
Current architecture docs: `pipeline/*.md`  
Current downstream contract: `municipality-discovery/v1`

## Why these files remain

These directories contain useful hackathon history, real seed data, earlier schemas and implementation experiments. They are retained for evidence and archaeology, not for new development.

| Directory | What it was | Why superseded |
|---|---|---|
| `handoff/` | `mmp-service-inventory/v0` handoff and seed deliveries | Replaced by Scout's `MunicipalityDiscovery` contract |
| `prototype/` | early bounded crawler + PageIR prototype | Replaced by `pipeline/scout/runtime.py` and Scout orchestration |
| `scrapping/` | early browser/baseline schemas, tools and duplicated architecture docs | Replaced by root Scout docs and `pipeline/scout/` |

Historical commands and relative paths inside these folders may no longer run after the move. Do not repair them unless deliberately extracting a useful technique into Scout.
