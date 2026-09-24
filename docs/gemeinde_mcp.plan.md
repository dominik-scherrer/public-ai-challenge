---
status: draft
version: 3.0.0
---

# Plan: Gemeinde MCP Pipeline [PL_GMP]

## 01. Phases

### Phase 1: Project Setup
**Goal**: Add dependencies and create the module structure.
**Tasks**:
- [ ] Add `mcp`, `httpx`, `beautifulsoup4`, `markdownify`, `pymupdf` (for PDF text extraction) to `pyproject.toml`.
- [ ] Add an LLM client library (e.g., `google-genai` or `openai`) to `pyproject.toml`.
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/` package with `__init__.py`.
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/models.py` — define `ServiceMention` as a dataclass or Pydantic model.
- [ ] Create a sample `input/service_mentions.json` with 2–3 entries from the Ausserberg website for manual testing.
- [ ] Download the corresponding Ausserberg HTML pages into a local `input/crawl/` directory as test data.
**Verify**: Import the models module without errors. Parse the sample JSON into `ServiceMention` objects.

### Phase 2: Content Synthesis
**Goal**: Read crawled HTML and PDF files and produce a synthesized Markdown document.
**Tasks**:
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/extraction.py`.
- [ ] Implement `extract_html_to_markdown(html: str) -> str`:
    - Parse HTML with BeautifulSoup.
    - Extract `<main>` element (fall back to `<body>`).
    - Convert to Markdown with `markdownify`.
- [ ] Implement `extract_pdf_to_markdown(pdf_path: str) -> str`:
    - Extract text using `pymupdf`.
    - Format as Markdown.
- [ ] Implement `synthesize_content(fragments: list[str]) -> str`:
    - Send the fragments to an LLM to synthesize into a single, clean Markdown document.
- [ ] Implement `process_service_content(mention: ServiceMention, crawl_dir: str, output_dir: str)`:
    - For each `source_url`, determine file type, call the appropriate extraction function, write the fragment to `output/fragments/{service_name}__{url_hash}.md`.
    - Pass all fragments to `synthesize_content`.
    - Write the final result to `output/{service_name}.md`.
**Verify**: `SP_GMP_03_01` — run `process_service_content` on an Ausserberg page. Confirm the output Markdown is a cohesive, readable document with no HTML tags.

### Phase 3: Tool Generation
**Goal**: Use an LLM to generate executable Python tool functions for each service.
**Tasks**:
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/tool_generator.py`.
- [ ] Implement `generate_tools(mention: ServiceMention, markdown_path: str, source_files: list[str], output_dir: str)`:
    - Read the synthesized Markdown file and the source files.
    - Send them to an LLM to generate Python functions.
    - Write the LLM's output to `output/{service_name}_tools.py`.
- [ ] Write the system prompt for the LLM. The prompt must instruct the LLM to:
    - Generate both action and informational tools.
    - Use the raw HTML to extract precise form actions, methods, and input names.
    - Decorate tools with `@tool_meta(category="...", kind="...")`.
    - Use semantically meaningful function and parameter names.
    - Include docstrings and error handling.
- [ ] Add validation: check that the generated Python file is syntactically valid (compile with `ast.parse`).
**Verify**: `SP_GMP_03_02` — run on the Ausserberg move-in page. Confirm the generated file contains a function with semantic name and parameters.

### Phase 4: MCP Server
**Goal**: Load the generated Markdown and tool files into a running MCP server.
**Tasks**:
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/server.py`.
- [ ] Initialize `FastMCP("gemeinde-mcp-server")`.
- [ ] Load all `output/{service_name}.md` files and register each as an MCP Resource with URI `gemeinde://services/{service_name}`.
- [ ] Load all `output/{service_name}_tools.py` files using `importlib`. Register each public function as an MCP Tool.
- [ ] Add a CLI entry point to start the server.
**Verify**: `SP_GMP_03_03`, `SP_GMP_03_04`, `SP_GMP_03_05` — start the server, list resources and tools, read one resource, call one tool.

### Phase 5: End-to-End Pipeline
**Goal**: Wire Phases 2–4 into a single command.
**Tasks**:
- [ ] Create `src/public_ai_challenge/gemeinde_mcp/pipeline.py`.
- [ ] Implement `run_pipeline(service_mentions_path: str, crawl_dir: str, output_dir: str)`:
    - Read the `ServiceMention` list.
    - For each mention, run content extraction (Phase 2), then tool generation (Phase 3).
    - Start the MCP server (Phase 4) over the output directory.
- [ ] Add a CLI entry point: `gemeinde-mcp-pipeline --input ... --crawl-dir ... --output ...`.
**Verify**: `SP_GMP_03_06` — run the full pipeline on the Ausserberg sample data. Start the MCP server. Call a generated tool and verify the action executes.

## 02. Phase Dependencies
- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 1.
- Phase 4 depends on Phase 1.
- Phase 5 depends on Phases 2, 3, and 4.

Phases 2, 3, and 4 can be developed in parallel after Phase 1 is complete.

## 03. Glossary
Same as `C_GMP` Section 05.
