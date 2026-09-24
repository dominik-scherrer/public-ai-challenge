---
status: draft
version: 4.0.0
---

# Specification: Gemeinde MCP Pipeline [SP_GMP]

## 01. Data Structures

### 1.1 ServiceMention (Input from Stage 2)
```json
{
  "service_name": "string (required, unique)",
  "category": "string (required, e.g. 'Forms and registration', 'Permits and planning')",
  "source_urls": ["string (required, HTTP/HTTPS URL, at least one)"]
}
```
The set of `category` values is defined by Stage 2. The same category string must be used consistently across all `ServiceMention` objects belonging to the same area.

### 1.2 Generated Tool File (Output of Stage 3)
A Python module (`output/{service_name}_tools.py`) containing one or more functions. Each function:
- Has a descriptive name reflecting the semantic action (e.g., `register_move_in`, `get_office_hours`). Generic names (e.g., `submit_form_1`) are used only when the LLM cannot determine the purpose.
- Has typed parameters with descriptive names matching the domain (e.g., `previous_municipality: str`, not `field_3: str`).
- Has a docstring explaining what the tool does, what parameters it expects, and what it returns.
- Is decorated with `@tool_meta(category="...", kind="action"|"informational")` to carry the category and tool kind.
- Contains executable Python code:
    - **Action tools**: submit a form via HTTP POST, download a file, compose an email, fetch calendar data, etc.
    - **Informational tools**: extract a specific fact from the service's Markdown content and return it (e.g., office hours, ID requirements, fees).
- Returns a string or dict describing the result.

### 1.3 ServiceResource (Internal to Stage 4)
```json
{
  "service_name": "string",
  "category": "string",
  "markdown_content": "string (content of the .md file)",
  "tools_module": "string (Python module path for the generated tools)"
}
```

## 02. Contracts

### 2.1 Stage 3: Service Processing

**Input**:
- `ServiceMention` list (JSON file from Stage 2).
- Access to the crawled files directory from Stage 1.

**Output directory**: `output/`
- `output/fragments/` — intermediate per-URL Markdown fragments.
- `output/{service_name}.md` — final Markdown file per service.
- `output/{service_name}_tools.py` — generated Python tool module per service.

**Content synthesis contract**:
- For each `source_url` in the `ServiceMention`:
    - Determine the file type (HTML or PDF).
    - If HTML: extract the `<main>` element (fall back to `<body>`), convert to Markdown using `markdownify`.
    - If PDF: extract text content, convert to Markdown.
    - Write the result to `output/fragments/{service_name}__{url_hash}.md`.
- After all `source_urls` are processed: send all fragments to an LLM to synthesize a single, cohesive, well-structured Markdown document. Write the result to `output/{service_name}.md`.

**Tool generation contract**:
- After `output/{service_name}.md` is written, send the following to an LLM:
    - The synthesized Markdown content (to understand the service's purpose).
    - The original source files (HTML/PDF) for the service (to extract mechanical details).
    - The `category` from the `ServiceMention`.
    - A system prompt instructing the LLM to:
        1. Identify actions a user or LLM might want to perform related to this service. Generate an **action tool** for each.
        2. Identify specific facts that a user or LLM might want to query (e.g., office hours, requirements, fees). Generate an **informational tool** for each.
        3. For web forms, analyze the raw HTML to determine the correct `action` URL, HTTP method, and exact `name` attributes for all inputs to ensure the generated Python code submits the correct payload.
        4. Use semantically meaningful function names and parameter names.
        5. Decorate each function with `@tool_meta(category="...", kind="action"|"informational")`.
        6. Include `httpx` calls for HTTP interactions in action tools.
        7. Include error handling (timeouts, non-200 responses).
- The LLM writes the generated code to `output/{service_name}_tools.py`.

**Error handling**:
- If a crawled file does not exist for a `source_url`, log a warning and skip that URL.
- If all `source_urls` for a `ServiceMention` fail, write an empty Markdown file with the header `# {service_name}\n\nNo content available.` and an empty tools file.
- If the LLM fails to generate tool code, write an empty tools file (the service is still exposed as an MCP Resource without tools).

### 2.2 Stage 4: MCP Server

**Server name**: `gemeinde-mcp-server`

**Resources**:
- URI pattern: `gemeinde://services/{service_name}`
- MIME type: `text/markdown`
- Content: The contents of `output/{service_name}.md`.

**Generated tools**:
- At startup, the server scans `output/` for `*_tools.py` files.
- For each file, the server dynamically imports the module and registers each public function as an MCP Tool.
- The tool name, parameters, docstring, category, and kind are read from the function's signature, `__doc__`, and `@tool_meta` decorator.

**Built-in cross-service tools** (written in the server code, not LLM-generated):

| Tool | Parameters | Behavior |
|------|------------|----------|
| `list_services` | `category` (optional) | Return the list of loaded services. If `category` is provided, filter by category. |
| `list_tools` | `category` (optional) | Return the list of available tools with their names, docstrings, and categories. If `category` is provided, filter by category. |
| `search_services` | `query` (required) | Search across all service Markdown files for the query string. Return matching service names and relevant excerpts. |

**Security constraint**: Generated Python code executes in the server process. The generated code is auditable in `output/{service_name}_tools.py` before the server starts. The server does not generate or modify tool code at runtime.

## 03. Verification Criteria

### SP_GMP_03_01: Content Extraction
Given a `ServiceMention` with `source_urls` pointing to crawled HTML files, the output Markdown file contains readable text and no HTML tags.

### SP_GMP_03_02: Action Tool Generation
Given the Ausserberg move-in page (`anmeldung-wohnsitz`), the generated `anmeldung_wohnsitz_tools.py` contains a function named `register_move_in` (or similar) with `kind="action"` and parameters matching the form fields.

### SP_GMP_03_03: Informational Tool Generation
Given the Ausserberg office hours page, the generated tools file contains a function named `get_office_hours` (or similar) with `kind="informational"` that returns the office hours from the Markdown content.

### SP_GMP_03_04: MCP Resource Listing
When the MCP server starts with 5 services in the `output/` directory, `resources/list` returns 5 resources with URIs matching `gemeinde://services/{service_name}`.

### SP_GMP_03_05: MCP Resource Read
When reading `gemeinde://services/anmeldung_wohnsitz`, the server returns the Markdown content of `output/anmeldung_wohnsitz.md`.

### SP_GMP_03_06: MCP Tool Listing
When the MCP server starts with a service that has a `_tools.py` file containing 2 functions, `tools/list` includes 2 tools with names, parameters, and categories matching the function metadata.

### SP_GMP_03_07: Tool Execution
When calling the `register_move_in` tool with valid parameters, the tool executes the HTTP POST to the form action URL and returns a result describing the outcome.

### SP_GMP_03_08: Cross-Service Tool
When calling `list_services(category="Forms and registration")`, the server returns only the services whose `ServiceMention.category` is "Forms and registration".

## 04. Glossary
Same as `C_GMP` Section 05.

## 05. Alternatives Considered

### Alternative 1: Mechanical HTML scanning for interaction detection (Rejected)
**Description**: A rule-based script scans HTML for `<form>` elements, `mailto:` links, PDF links, calendar widgets, and generates a declarative `InteractionDefinition` JSON for each detected element.
**Pros**: No LLM cost. Deterministic output.
**Cons**: Cannot create informational tools. Produces generic tool names (`submit_form_1`) instead of semantic names (`register_move_in`). Cannot understand the purpose of a form.
**Decision**: Rejected.

### Alternative 2: Declarative tool definitions with a generic executor (Deferred)
**Description**: The LLM generates a declarative JSON definition for each tool instead of Python code. A generic executor interprets the definition at runtime.
**Pros**: No generated code to audit.
**Cons**: The executor must handle every possible interaction type. Complex interactions may not fit a declarative schema.
**Decision**: Deferred.

### Alternative 3: Runtime LLM interpreter (Deferred)
**Description**: The LLM generates a declarative tool definition. A second LLM call at runtime interprets the definition and executes the action.
**Pros**: No generated code. Handles complex, context-dependent interactions.
**Cons**: Adds LLM cost and 2–10 seconds latency per tool call at runtime.
**Decision**: Deferred.
