---
status: accepted
---

# The MMP server is stateless and keeps no Citizen queries

Tool-call arguments from any MCP host (including ChatGPT) reach the MMP server, so it could become a central register of Citizens' life situations. It therefore stores no query text: only technical metrics (latency, errors, which Service ID was retrieved). Anything beyond that leaves the Citizen only through an explicit, consented action.

Two consented channels exist:
- **Gap Report** (`report_gap`): only a topic abstracted by the client before sending, never raw text.
- **Feedback**: a "send feedback" button; further information is sent only if the Citizen agrees.

Gap Reports and Feedback go to the **MMP operator**, not the Municipality, and feed the next Build (targeted re-check by the Judge, targeted crawl by the builder). The Municipality receives only a periodic aggregate ("top questions your site doesn't answer"). Assumed defaults, not yet confirmed by the team: the Citizen sees and can edit the exact text before sending; retention 90 days.

## Considered options

- **Normal query logging** for debugging and analytics. Rejected: indefensible under nDSG and turns the sovereignty argument against us.

## Consequences

- Pitch line: "The server knows which Services are in demand, never who asked or why."
- Debugging relies on synthetic test queries only.
- `find_service` ranking cannot learn from query history.
