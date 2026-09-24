---
status: accepted
---

# The Reference Client is a fork of the Swiss public AI Open WebUI with a self-built MCP Apps host

The Reference Client is a fork of the Open WebUI deployment used by Swiss public AI. Open WebUI supports MCP natively (≥ v0.6.31) but only over Streamable HTTP, and does not render MCP Apps (`ui://`) views in core. We build a minimal MCP Apps host into the fork ourselves (sandboxed iframe + the spec's postMessage bridge) so the same Service Card renders identically in the Reference Client, Claude and ChatGPT.

## Considered options

- **Community plugin `mcp-app-bridge`.** Rejected: unverified, outside our control, and the Service Card is the demo's central moment.
- **Native Service Card components in the client.** Rejected: two Service Cards that drift apart, breaking the "one standardized UI" promise.

## Consequences

- The MMP server must speak Streamable HTTP.
- We own and maintain the host code in the fork (MMP operator, not the Municipality — ADR-0004).
- Open risk: reliable tool calling of the public model behind the fork is unverified (see OQ-2).
