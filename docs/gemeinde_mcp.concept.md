# Gemeinde MCP Pipeline  {#C_GMP}

> **Code:** C_GMP
> **Status:** draft
> **Created:** 2026-09-24
> **Updated:** 2026-09-24
> **Author:** Pipeline Team
> **Owner:** Service Processing Team
> **Complexity:** medium
>
> **Depends on:** none
> **Used by:** —
> **Spike:** —
> **Specification:** [SP_GMP](./gemeinde_mcp.sp.md)
> **Plan:** [gemeinde_mcp.plan.md](./gemeinde_mcp.plan.md)
>
> Converts a Gemeinde (Swiss municipality) website into a running Model Context Protocol (MCP) server. A 4-stage pipeline extracts website content, synthesizes information, generates Python tool functions via Large Language Models (LLMs), and serves the resulting resources and tools to LLM clients.

## 1. Philosophy  {#C_GMP_01}
### 1.1. Core Principle  {#C_GMP_01_01}
The pipeline exists to convert unstructured municipality website content into standardized MCP resources and executable MCP tools. This enables external LLM clients to query municipal information and perform actions programmatically.

### 1.2. Design Constraints  {#C_GMP_01_02}
The pipeline consists of four stages. This team owns and builds Stage 3 (Service Processing) and Stage 4 (MCP Server). Another team owns Stage 1 (Website Crawl) and Stage 2 (Service Detection). Stage 1 and Stage 2 act as external dependencies.

## 2. Domain Model  {#C_GMP_02}
### 2.1. Key Entities  {#C_GMP_02_01}
- **ScoutedService**: A JSON record containing a service name, description, availability status, and source URLs.
- **Markdown content file**: A synthesized text document containing the unified information about a specific service.
- **Generated tool file**: A Python file containing LLM-generated functions for a specific service.
- **MCP Resource**: A read-only data item exposed by the MCP server, mapped to the Markdown content file.
- **MCP Tool**: An executable action exposed by the MCP server, mapped to the functions in the generated tool file. Tools are categorized as action tools (perform actions) or informational tools (extract facts).
- **Cross-service tools**: Built-in MCP tools written in the server code that operate across multiple services.

### 2.2. Data Flows  {#C_GMP_02_02}
The pipeline executes in two phases and four stages:

```text
Phase 1: Scouting (External)
Stage 1: Website Crawl (crawls HTML and PDFs) -> Stage 2: Service Detection (matches content to predefined services)

Phase 2: Building (Internal)
Stage 2 -> Stage 3: Service Processing (fetches URLs, extracts text, generates tools) -> Stage 4: MCP Server (loads resources and tools, runs server)
```

- **Stage 1**: Crawls the provided website URL.
- **Stage 2**: Analyzes crawled data to produce a list of ScoutedService records.
- **Stage 3**: Processes each ScoutedService record to output one Markdown content file and one generated tool file.
- **Stage 4**: Starts the MCP server using the output files from Stage 3.

## 3. Mechanisms  {#C_GMP_03}
### 3.1. Core Algorithm  {#C_GMP_03_01}
Stage 3 executes the following steps sequentially for each ScoutedService:

1. **Availability Check**: If the ScoutedService indicates the service is unavailable, write a Markdown content file stating the service is absent and write an empty generated tool file. Proceed to the next ScoutedService.
2. **Fetch**: Execute HTTP GET requests for each URL in the ScoutedService concurrently. Extract text from HTML or PDF content. Write the text to temporary Markdown fragment files. Save the raw source content.
3. **Extract and Synthesize**: Execute the Content Synthesis Agent (a PydanticAI agent) providing the temporary Markdown fragment files as input. The agent returns a `SynthesizedContent` Pydantic model. Write the model data to the Markdown content file.
4. **Generate Tools**: Execute the Tool Generation Agent (a PydanticAI agent) providing the synthesized Markdown, raw source content, and ScoutedService metadata as input. The agent returns a `GeneratedTools` Pydantic model. Write the model data to the generated tool file.

### 3.2. Edge Cases  {#C_GMP_03_02}
- **URL Fetch Failures**: Network errors or HTTP error responses during the fetch step halt processing for the specific URL.
- **LLM Failures**: Timeout or connection errors from the LLM provider raise exceptions.
- **Syntax Errors**: The Tool Generation Agent validates generated code using `ast.parse`. Syntax errors raise a `ModelRetry` exception, which prompts the LLM to self-correct the code.

## 4. Integration Points  {#C_GMP_04}
### 4.1. Dependencies  {#C_GMP_04_01}
- **Stage 1 and Stage 2**: External systems providing the ScoutedService records.
- **PydanticAI**: Library for orchestrating LLM agents and validating outputs.
- **httpx**: Library for asynchronous HTTP requests.
- **markdownify**: Library for converting HTML to Markdown.
- **pymupdf**: Library for extracting text from PDF files.

### 4.2. API Surface  {#C_GMP_04_02}
- **Contract A (Scouted Services List)**: The input from Stage 2 to Stage 3. A JSON array of ScoutedService objects. Each object contains `name` (string), `description` (string), `urls` (array of strings), and `available` (boolean).
- **Contract B (Stage 3 Output)**: The output from Stage 3 to Stage 4. Two files per service: `output/{name}.md` (Markdown content file) and `output/{name}_tools.py` (generated tool file).

## 5. Design Decisions  {#C_GMP_DEC}

### DEC_01 — Declarative tool definitions with generic executor  {#C_GMP_DEC_01}
**Status:** resolved
**Question:** Should the system use declarative JSON tool definitions parsed by a generic executor instead of generating Python code?
**Options:**

| Option | Description |
|--------|-------------|
| Generate Python code | Selected |
| Declarative JSON + generic executor | Rejected |

**Decision:** Generate Python code.
**Rationale:** Generated Python code provides flexibility for handling custom interaction flows in the initial version.
**Rejected because:** A generic executor must anticipate and handle specific interaction types. Interaction schemas do not accommodate custom flows efficiently.

### DEC_02 — Declarative tool definitions with runtime LLM interpreter  {#C_GMP_DEC_02}
**Status:** resolved
**Question:** Should the system use a runtime LLM to interpret declarative tool definitions during execution?
**Options:**

| Option | Description |
|--------|-------------|
| Generate Python code | Selected |
| Declarative JSON + runtime LLM | Rejected |

**Decision:** Generate Python code.
**Rationale:** Eliminates runtime LLM dependency for tool execution.
**Rejected because:** A runtime LLM adds 2 to 10 seconds of latency per tool call and incurs ongoing token usage costs.

### DEC_03 — LLM-generated cross-service tools  {#C_GMP_DEC_03}
**Status:** resolved
**Question:** Should an LLM generate the cross-service tools (e.g., listing loaded services)?
**Options:**

| Option | Description |
|--------|-------------|
| Built-in server code | Selected |
| LLM-generated tools | Rejected |

**Decision:** Write cross-service tools directly in the server codebase.
**Rationale:** Cross-service operations read the deterministic state of the server.
**Rejected because:** LLM generation provides no benefit for deterministic operations.

### DEC_04 — Markdown resources without informational tools  {#C_GMP_DEC_04}
**Status:** resolved
**Question:** Should the MCP server omit informational tools and require clients to read the full Markdown resources?
**Options:**

| Option | Description |
|--------|-------------|
| Generate resources and informational tools | Selected |
| Expose only resources | Rejected |

**Decision:** Generate both Markdown resources and informational tools.
**Rationale:** Informational tools extract targeted facts and return the specific facts to the client, which uses fewer tokens.
**Rejected because:** Reading full Markdown documents for specific factual questions increases token consumption and latency for the client.

## Changelog

| Date | Change |
|------|--------|
| 2026-09-24 | Initial version (v6.0.0) |
