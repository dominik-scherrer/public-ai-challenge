# Glossary

| Term | Definition |
|------|------------|
| Gemeinde | A Swiss municipality. |
| ScoutedService | A JSON record containing a service name, description, availability status, and URLs where the service was found on the Gemeinde website. Produced by Stage 2 (Service Detection). Input to Stage 3. |
| Predefined Service | An item from the master list of services that Stage 2 matches against website content (e.g., `Anmeldung Wohnsitz`). |
| Markdown content file | A synthesized text document at `output/{name}.md` containing unified information about a specific service. Produced by Stage 3. |
| Generated tool file | A Python module at `output/{name}_tools.py` containing LLM-generated functions for a specific service. Produced by Stage 3. |
| Action tool | A generated MCP tool function that performs an action: submit a form, download a file, compose an email. |
| Informational tool | A generated MCP tool function that extracts a specific fact from the Markdown content and returns the fact to the caller (e.g., office hours, ID requirements). |
| Cross-service tool | A built-in MCP tool that operates across loaded services (e.g., `list_services`, `search_services`). Written in the server code, not LLM-generated. |
| MCP | Model Context Protocol — a standard protocol for exposing data and tools to LLM clients. |
| MCP Resource | A read-only data item exposed by an MCP server. In this project: the Markdown content of a service. |
| MCP Tool | An executable action exposed by an MCP server. In this project: a Python function that performs an action or extracts a fact related to a service. |
| Service Processing | Stage 3 of the pipeline. Fetches HTML/PDF content for a service, produces a Markdown content file, and generates a tool file using PydanticAI agents. |
| Content Synthesis Agent | A PydanticAI agent that takes Markdown fragments as input and returns a `SynthesizedContent` model containing a unified Markdown document. |
| Tool Generation Agent | A PydanticAI agent that takes synthesized Markdown, raw source content, and service metadata as input and returns a `GeneratedTools` model containing Python code. Validates output syntax via `ast.parse` and self-corrects using `ModelRetry`. |
| SynthesizedContent | A Pydantic model returned by the Content Synthesis Agent. Fields: `service_name`, `markdown`, `source_urls`. |
| GeneratedTools | A Pydantic model returned by the Tool Generation Agent. Fields: `service_name`, `python_code`, `tool_names`. |
| ServiceProcessingDeps | A dataclass injected into PydanticAI agents via `RunContext`. Contains a shared `httpx.AsyncClient` and the LLM model identifier. |
| PydanticAI | A Python framework for building type-safe LLM agents with structured Pydantic model outputs, dependency injection via `RunContext`, and self-healing validation via `ModelRetry`. |
| ModelRetry | A PydanticAI exception raised inside an `@output_validator` or tool function. Feeds the error message back to the LLM and prompts the LLM to self-correct the output. |
