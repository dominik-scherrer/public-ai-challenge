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
- **Service Inventory**: A typed JSON document (`mmp-service-inventory/v0`) describing the service attributes, contacts, procedures, and evidence references.
- **MCP Resource**: A read-only data item exposed by the MCP server, mapped to the Service Inventory or markdown.
- **Cross-service tools**: Built-in MCP tools written in the server code that read the deterministic JSON state of the server.

### 2.2. Data Flows  {#C_GMP_02_02}
The pipeline executes in two phases and four stages:

```text
Phase 1: Scouting (External)
Stage 1: Website Crawl (crawls HTML and PDFs) -> Stage 2: Service Detection (matches content to predefined services)

Phase 2: Building (Internal)
Stage 2 -> Stage 3: Service Processing (fetches URLs, extracts text, generates JSON Inventory) -> Stage 4: MCP Server (loads inventories and runs server)
```

- **Stage 1**: Crawls the provided website URL.
- **Stage 2**: Analyzes crawled data to produce a list of ScoutedService records.
- **Stage 3**: Processes each ScoutedService record to output a structured Service Inventory JSON file (per ADR-0003).
- **Stage 4**: Starts the MCP server using the generated inventory data.

## 3. Mechanisms  {#C_GMP_03}
### 3.1. Core Algorithm  {#C_GMP_03_01}
Stage 3 executes the following steps sequentially for each ScoutedService:

1. **Availability Check**: If the ScoutedService indicates the service is unavailable, write an inventory file stating `unavailable` status.
2. **Fetch**: Execute HTTP GET requests for each URL in the ScoutedService concurrently. Extract text from HTML or PDF content.
3. **Extract and Synthesize**: Execute the Content Synthesis Agent to generate a clean markdown representation.
4. **Generate Inventory Data**: Execute the Data Extraction Agent (a PydanticAI agent) providing the synthesized Markdown and source content as input. The agent returns a `ServiceInventory` Pydantic model (compliant with `mmp-service-inventory/v0`). Write the model to a JSON file.

### 3.2. Edge Cases  {#C_GMP_03_02}
- **URL Fetch Failures**: Network errors or HTTP error responses during the fetch step halt processing for the specific URL.
- **LLM Failures**: Timeout or connection errors from the LLM provider raise exceptions.
- **Schema Errors**: The Data Extraction Agent validates generated JSON against the schema. Validation errors trigger LLM self-correction.

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

### DEC_01 — Declarative tool definitions vs generated Python code {#C_GMP_DEC_01}
**Status:** resolved
**Question:** Should the system use declarative JSON definitions or generate Python code?
**Options:**

| Option | Description |
|--------|-------------|
| Declarative JSON (Service Inventory) | Selected |
| Generate Python code | Rejected |

**Decision:** Declarative JSON (Service Inventory).
**Rationale:** Conforms to ADR-0003 and ADR-0007. Generating Python code for public infrastructure is a security risk and creates maintenance overhead.
**Rejected because:** LLM-generated code cannot be safely verified by the Judge without a complex sandbox, and breaks the paradigm of a single generic MMP server.

### DEC_02 — Declarative tool definitions with runtime LLM interpreter  {#C_GMP_DEC_02}
**Status:** resolved
**Question:** Should the system use a runtime LLM to interpret declarative tool definitions during execution?
**Options:**

| Option | Description |
|--------|-------------|
| Deterministic parsing of JSON | Selected |
| Declarative JSON + runtime LLM | Rejected |

**Decision:** Deterministic parsing of JSON.
**Rationale:** The MMP server should read standard attributes and map them deterministicly to tools.
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
