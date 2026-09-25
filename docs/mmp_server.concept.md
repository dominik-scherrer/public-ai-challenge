# MMP Server  {#C_SERVER}

> **Code:** C_SERVER
> **Status:** active
> **Created:** 2026-09-25
> **Updated:** 2026-09-25
>
> **Depends on:** C_GMP
>
> A single generic, multi-tenant MCP server that serves Service Inventories for all Municipalities.

## 1. Philosophy  {#C_SERVER_01}
A stateless, secure server that reads generated JSON data and serves standard Service Cards over MCP.

## 5. Design Decisions  {#C_SERVER_DEC}

### DEC_01 — Stateless server, no citizen query logs  {#C_SERVER_DEC_01}
> **Status:** resolved (ADR-0005)
> **Date:** 2026-09-25
**Decision:** The MMP server stores no query text, only technical metrics. Feedback and Gap Reports are explicitly consented by the citizen.
**Rationale:** Indefensible under nDSG and turns the sovereignty argument against us.

### DEC_02 — One generic MMP server  {#C_SERVER_DEC_02}
> **Status:** resolved (ADR-0003)
> **Date:** 2026-09-25
**Decision:** A single generic MMP server serves every Municipality, addressed by BFS number. No LLM-generated code runs on public infrastructure.
