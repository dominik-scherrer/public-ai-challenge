# Gemeinde MCP Pipeline — Specification  {#SP_GMP}

> **Code:** SP_GMP
> **Status:** draft
> **Created:** 2026-09-24
> **Updated:** 2026-09-24
>
> **Concept:** [C_GMP](./gemeinde_mcp.concept.md)
> **Depends on:** none
> **Used by:** —
> **Plan:** [PL_GMP](./gemeinde_mcp.plan.md)
>
> Specification for the Gemeinde Model Context Protocol (MCP) Pipeline, defining data structures, contracts, validation rules, state transitions, verification criteria, and design decisions.

## 01. Data Structures  {#SP_GMP_01}
### 01_01. ScoutedService  {#SP_GMP_01_01}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| name | string | Yes | — | Unique from ENUM master list | The service identifier. |
| description | string | Yes | — | — | The service description. |
| urls | list[string] | Conditional | — | Required if available is true | URLs associated with the service. |
| available | boolean | Yes | — | — | Indicates if the service is available. |

Invariants:
- If `available` is true, `urls` must contain at least one valid URL.

### 01_02. Service Inventory  {#SP_GMP_01_02}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| file_path | string | Yes | — | Matches `output/{name}_inventory.json` | Path to the generated JSON inventory. |
| data | dict | Yes | — | Conforms to `mmp-service-inventory/v0` | Contains structured service attributes, contacts, procedures, and evidence. |

Invariants:
- `data` must pass JSON schema validation for `mmp-service-inventory/v0`.

### 01_03. ServiceProcessingDeps  {#SP_GMP_01_03}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| http_client | httpx.AsyncClient | Yes | — | Shared instance | Client for fetching URLs. |
| model_name | string | Yes | — | e.g., "openai:gpt-4o" | LLM model identifier. |

Invariants:
- The `http_client` is instantiated once and shared across all runs.

### 01_04. SynthesizedContent  {#SP_GMP_01_04}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| service_name | string | Yes | — | Matches ScoutedService | Name of the service. |
| markdown | string | Yes | — | — | Unified Markdown document. |
| source_urls | list[string] | Yes | — | — | URLs used for synthesis. |

### 01_05. ExtractedData  {#SP_GMP_01_05}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| service_name | string | Yes | — | Matches ScoutedService | Name of the service. |
| json_data | dict | Yes | — | Valid against schema | The extracted Service Inventory data. |

Invariants:
- `json_data` must be structurally valid.

### 01_06. ServiceResource  {#SP_GMP_01_06}

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| name | string | Yes | — | — | The service identifier. |
| markdown_content | string | Yes | — | Content of `output/{name}.md` | The Markdown content. |
| tools_module | string | No | — | Path to Python module | Path to generated tools module. |

## 02. Contracts  {#SP_GMP_02}
### 02_01. Content Synthesis  {#SP_GMP_02_01}
Purpose: Fetches service URLs and synthesizes HTML/PDF content into a single Markdown file.

Input:

| Parameter | Type | Required | Description |
|---|---|---|---|
| service | ScoutedService | Yes | The scouted service data. |
| deps | ServiceProcessingDeps | Yes | Dependencies for fetching and LLM calls. |

Output:

| Return | Type | Description |
|---|---|---|
| result | SynthesizedContent | The synthesized Markdown and source URLs. |

Errors:

| Error | Condition | Result |
|---|---|---|
| Network Error | URL fetch fails | Log warning, skip URL. If all URLs fail, fallback to unavailable behavior. |

Processing logic pseudocode:
```python
if not service.available:
    write_unavailable_markdown(service.name)
    write_empty_tools(service.name)
    return

fragments = []
for url in service.urls:
    try:
        content = deps.http_client.get(url)
        fragments.append(convert_to_markdown(content))
    except FetchError:
        log_warning()
        continue

if not fragments:
    write_unavailable_markdown(service.name)
    write_empty_tools(service.name)
    return

synthesized = synthesis_agent.run(fragments, deps)
write_file(f"output/{service.name}.md", synthesized.markdown)
```

Agent Definition:
```python
synthesis_agent = Agent[ServiceProcessingDeps, SynthesizedContent](
    model='openai:gpt-4o',
    deps_type=ServiceProcessingDeps,
    output_type=SynthesizedContent,
    system_prompt=(
        "You are a documentation specialist. Synthesize the provided Markdown "
        "fragments into a single, cohesive, well-structured Markdown document. "
        "Remove redundancies and organize the information logically. Preserve all "
        "factual details, URLs, contact information, and official references."
    ),
    retries=2,
)
```

### 02_02. Inventory Data Extraction  {#SP_GMP_02_02}
Purpose: Analyzes synthesized Markdown and source content to extract structured service inventory data.

Input:

| Parameter | Type | Required | Description |
|---|---|---|---|
| service | ScoutedService | Yes | The scouted service data. |
| markdown_content | string | Yes | Synthesized Markdown content. |
| source_contents | list[string] | Yes | Raw fetched content (HTML/PDF). |
| deps | ServiceProcessingDeps | Yes | Dependencies for LLM calls. |

Output:

| Return | Type | Description |
|---|---|---|
| result | ExtractedData | Extracted Service Inventory JSON and service name. |

Errors:

| Error | Condition | Result |
|---|---|---|
| Extraction Failure | LLM fails to generate valid inventory after 3 retries | Write minimal unavailable `_inventory.json` file. |

Processing logic pseudocode:
```python
if not service.available or not fragments_fetched:
    return write_unavailable_inventory(service.name)

inventory = data_extraction_agent.run(
    markdown_content,
    source_contents,
    service.name,
    service.description,
    deps
)
write_file(f"output/{service.name}_inventory.json", inventory.json_data)
```

Agent Definition:
```python
data_extraction_agent = Agent[ServiceProcessingDeps, ExtractedData](
    model='openai:gpt-4o',
    deps_type=ServiceProcessingDeps,
    output_type=ExtractedData,
    system_prompt=(
        "You are a municipal service data extractor. Extract structured attributes "
        "including description, requirements, fees, documents, contacts, and delivery mode "
        "into a valid mmp-service-inventory/v0 dictionary structure. Ensure factual accuracy."
    ),
    retries=3,
    defer_model_check=True,
)

@data_extraction_agent.output_validator
def validate_extracted_data(
    ctx: RunContext[ServiceProcessingDeps], output: ExtractedData
) -> ExtractedData:
    if not isinstance(output.json_data, dict):
        raise ModelRetry("json_data must be a valid dictionary structure.")
    if "schema" not in output.json_data:
        output.json_data["schema"] = "mmp-service-inventory/v0"
    return output
```

### 02_03. MCP Server Startup  {#SP_GMP_02_03}
Purpose: Exposes generated Markdown and tools via MCP protocol.

### 02_03. MCP Server Startup  {#SP_GMP_02_03}
Purpose: Exposes generated Markdown resources and inventory data via MCP protocol.

Input:

| Parameter | Type | Required | Description |
|---|---|---|---|
| output_dir | string | Yes | Path to `output/` directory containing `.md` and `_inventory.json` files. |

Output:

| Return | Type | Description |
|---|---|---|
| server | FastMCP | Running server instance exposing resources and tools. |

Errors:

| Error | Condition | Result |
|---|---|---|
| File Error | File fails to read | Skip file, log error. |

Processing logic pseudocode:
```python
server = FastMCP("Gemeinde-MCP")
for file in list_files("output/"):
    if file.endswith(".md"):
        register_resource(f"gemeinde://services/{file.stem}", file.read())
    elif file.endswith("_inventory.json"):
        register_inventory(file.stem, load_json(file))
register_tools(server)
```

## 03. Validation Rules  {#SP_GMP_03}
### 03_01. Input Validation  {#SP_GMP_03_01}
- `ScoutedService` data must pass JSON schema validation matching section 01_01.
- `urls` in `ScoutedService` must be valid URL formats.
- Extracted JSON data must conform to `mmp-service-inventory/v0`.

## 04. State Transitions  {#SP_GMP_04}
### 04_01. Lifecycle  {#SP_GMP_04_01}
Per-service processing lifecycle:
`pending` → `fetching` → `synthesizing` → `generating_inventory` → `complete` | `failed`

## 05. Verification Criteria  {#SP_GMP_05}
### 05_01. Functional Expectations  {#SP_GMP_05_01}

| ID | Description |
|---|---|
| SP_GMP_05_01 | Synthesized Markdown for available services contains cohesive text without HTML tags. |
| SP_GMP_05_02 | Synthesized Markdown for unavailable services states the service is unavailable, with a minimal inventory file. |
| SP_GMP_05_03 | Action handoffs match form fields, possess semantic names, and point to valid municipality links. |
| SP_GMP_05_04 | Informational facts extract correct attributes (e.g., office hours, fees, requirements). |
| SP_GMP_05_05 | MCP server with service files exposes resources with `gemeinde://services/{name}` URIs. |
| SP_GMP_05_06 | Reading `gemeinde://services/{name}` returns the correct Markdown content. |
| SP_GMP_05_07 | MCP server registers query tools reading non-empty `_inventory.json` files with correct metadata. |
| SP_GMP_05_09 | `list_services()` returns all loaded services. |

### 05_02. Invariant Checks  {#SP_GMP_05_02}

| ID | Description |
|---|---|
| SP_GMP_05_10 | PydanticAI output validator raises `ModelRetry` for invalid Python code, and the agent self-corrects within 3 retries, producing code that passes `ast.parse`. |

### 05_03. Integration Scenarios  {#SP_GMP_05_03}

| ID | Description |
|---|---|
| SP_GMP_05_08 | End-to-end pipeline processes scouted services list, produces synthesized markdown and structured inventories, and initializes a queryable MCP server. |

### 05_04. Edge Cases and Boundaries  {#SP_GMP_05_04}

| ID | Description |
|---|---|
| SP_GMP_EDGE_01 | URL fetch failure correctly falls back to unavailable behavior when all URLs fail. |
| SP_GMP_EDGE_02 | Inventory generation failure correctly yields a minimal fallback `_inventory.json` file. |

## 06. Reversibility  {#SP_GMP_06}
### 06_01. Rollback Strategy  {#SP_GMP_06_01}
Output files in the `output/` directory can be deleted. The pipeline can be re-run at any time. The pipeline maintains no persistent state outside the output directory.

## 07. Design Decisions  {#SP_GMP_DEC}
### DEC_01 — How to detect interactions in HTML?  {#SP_GMP_DEC_01}
**Context**: We need to identify actions a user can take on a service webpage.
**Considered Options**:
1. Mechanical HTML scanning: Rule-based script scans HTML for forms, links, widgets, generating JSON interactions.
2. LLM-based tool generation: PydanticAI agent analyzes HTML/PDF and synthesized content to generate Python tools.
**Decision**: Use LLM-based tool generation.
**Rationale**: Mechanical scanning cannot create informational tools, produces generic names, and cannot understand form purpose. LLM provides semantic names and identifies information needs.

### DEC_02 — How to execute tools?  {#SP_GMP_DEC_02}
**Context**: We need to execute the identified tools.
**Considered Options**:
1. Generated Python code: LLM generates Python code representing tools, executed by the server.
2. Declarative tool definitions with generic executor: LLM generates JSON, interpreted by generic executor.
**Decision**: Use generated Python code. (Declarative tool definitions are deferred.)
**Rationale**: A generic executor must handle all possible interaction types, which is complex. Python code allows flexible interactions.

### DEC_03 — Should tools be interpreted by LLM at runtime?  {#SP_GMP_DEC_03}
**Context**: We need a mechanism to execute declarative definitions if adopted.
**Considered Options**:
1. Runtime LLM interpreter: LLM interprets declarative definitions at runtime to execute actions.
2. Direct execution: Tools execute directly as Python code.
**Decision**: Direct execution. (Runtime interpreter is deferred.)
**Rationale**: Runtime LLM adds cost and latency (2–10 seconds) per tool call.

### DEC_04 — Which LLM client framework to use?  {#SP_GMP_DEC_04}
**Context**: We need a library to interact with LLMs.
**Considered Options**:
1. PydanticAI: Provides typed `BaseModel` outputs, `ModelRetry` self-healing, and dependency injection.
2. Raw LLM client calls (OpenAI/Anthropic SDK): Manual prompt construction, JSON parsing, no validation loop.
**Decision**: Use PydanticAI.
**Rationale**: Raw calls lack type-safe structured output, automatic validation retries, and dependency injection. PydanticAI reduces boilerplate and handles syntax error retries automatically.

## Changelog
- 2026-09-24 | Initial version (v6.0.0)
