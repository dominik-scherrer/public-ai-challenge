# Architectural Framework

## Core Abstractions
- **Builder**: Crawls the municipality website, extracts services, and maps them to eCH-0070.
- **Judge**: Runs provenance, coverage, and injection checks. The only quality gate.
- **Service Inventory**: Typed JSON data containing the services of a municipality.
- **MMP Server**: Shared, stateless server that reads the Service Inventory and exposes Service Cards over MCP.
- **Reference Client**: Sovereign chat client running on Swiss public AI.

## Layers
- **Layer 0 (Core Tools)**: public_ai_challenge CLI, shared Pydantic models.
- **Layer 1 (Pipeline)**: Ingestion (Scout), Processing (Builder), and Quality Gate (Judge).
- **Layer 2 (Runtime)**: The stateless MMP Server hosting MCP tools.

## Conventions
- Structure: See .dev_flow/rules/structure.md.
