# Reference Client  {#C_CLIENT}

> **Code:** C_CLIENT
> **Status:** active
> **Created:** 2026-09-25
> **Updated:** 2026-09-25
>
> **Depends on:** C_SERVER
>
> The Citizen-facing chat embedded on a Municipality website, running on Swiss public AI.

## 1. Philosophy  {#C_CLIENT_01}
Provides the sovereign default path for citizens to interact with municipality services.

## 2. Domain Model  {#C_CLIENT_02}
- **Reference Client**: A fork of the Open WebUI deployment used by Swiss public AI.

## 5. Design Decisions  {#C_CLIENT_DEC}

### DEC_01 — Sovereignty is offered by the reference client, not enforced by the protocol  {#C_CLIENT_DEC_01}
> **Status:** resolved (ADR-0002)
> **Date:** 2026-09-25
**Decision:** The sovereignty offer lives in the reference client running on Swiss public AI. The protocol remains open to other clients (Claude, ChatGPT) for reach, but only the reference client guarantees data stays in Switzerland.

### DEC_02 — Fork of Open WebUI with self-built MCP Apps host  {#C_CLIENT_DEC_02}
> **Status:** resolved (ADR-0006)
> **Date:** 2026-09-25
**Decision:** Fork Open WebUI and build a minimal MCP Apps host (sandboxed iframe + postMessage) into it so the Service Card renders identically across all clients.

### DEC_03 — Does the public model call MMP tools reliably?  {#C_CLIENT_DEC_03}
> **Status:** open (OQ-2)
**Question:** Reliable tool calling of the public model behind the fork is unverified. If it fails, the reference client fails. Needs testing with a dummy MMP server before building the host.
