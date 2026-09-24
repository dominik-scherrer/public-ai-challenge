---
status: accepted
---

# Sovereignty is offered by the reference client, not enforced by the protocol

MMP servers are vendor-neutral MCP servers: any MCP client — including Claude and ChatGPT — may connect. Consequently the protocol cannot guarantee that a Citizen's question stays in Switzerland; the *client* decides where the conversation (and the tool-call arguments the server receives) goes. We do not pretend otherwise.

The sovereignty offer lives in the **reference client**: a chat embedded on the Municipality website, running on Swiss public AI, which is the default path for Citizens. MMP servers and the reference client are public infrastructure; the protocol is open. Interoperability with Claude/ChatGPT is the *reach* argument (Citizens meet their Gemeinde where they already are, knowingly), not the sovereignty argument.

## Considered options

- **Enforce** — accept calls only from the public AI client. Technically weak (any client can present as anything), and it kills the reach story. Rejected.
- **Claim "your data never leaves Switzerland" anyway.** Untrue for the ChatGPT path. Rejected — this ADR exists so nobody puts it on a slide.

## Consequences

- Pitch wording: "Via the Gemeinde chat your question stays in Switzerland; via ChatGPT it doesn't. MMP gives Citizens the choice and gives every Gemeinde a sovereign default without building anything."
- The Build may use any capable open-source model (its input is public web content); only the reference client must run on Swiss public AI.
- The reference client is a first-class deliverable, not a demo shim — it is where the sovereignty offer is real.
