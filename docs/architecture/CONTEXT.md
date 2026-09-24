# Model Municipality Protocol (MMP)

Public infrastructure that makes the information and services of Swiss municipalities reachable through a chat interface, running on Swiss public AI so that citizens' questions never leave the country.

## Language

**Citizen**:
A person interacting with a Municipality through the chat interface. The primary user and the demo persona.
_Avoid_: End user, resident, Einwohner (in code/docs — fine in German UI copy)

**Municipality**:
A Swiss Gemeinde whose website is the source of truth for its services. Not the primary user; the entity being made reachable.
_Avoid_: Gemeinde (in code/docs), commune, client, tenant

**MMP Operator**:
Swiss AI, running MMP as a service public: it operates the builder, the shared MMP server and the Reference Client, and is the only party that maintains anything.
_Avoid_: Provider, vendor, platform owner

**Service**:
One thing a Municipality offers a Citizen, as published on its website. Every Service belongs to exactly one tier below.
_Avoid_: Offering, Leistung (in code/docs), feature, endpoint

**Leistung**:
An entry in the eCH-0070 inventory, identified by its numeric Leistungs-ID. A Service maps to at most one Leistung; a Service with no match is *unmapped*, never invented.
_Avoid_: Using "Leistung" for a Service, category, service type

**Build**:
One run of the builder over one Municipality website, producing that Municipality's Service Inventory. Builds are repeatable; freshness is achieved by rerunning, not by patching.

**Service Inventory**:
The data a Build produces for one Municipality: all its Services, each attribute with its source. Served by the one shared MMP server under the Municipality's BFS number.
_Avoid_: Generated server, MCP per Gemeinde, dataset

**Judge**:
The automated LLM check that decides whether a Build goes live, by verifying each attribute against its source quote and measuring eCH-0070 coverage. The only quality gate.
_Avoid_: Reviewer, validator, QA bot

**Withheld Attribute**:
An attribute of a Service that failed the Judge and is therefore not shown; the Service goes live without it and the Citizen is told to ask the Municipality. Principle: say less rather than say something wrong.
_Avoid_: Missing, null, error

**Build Floor**:
The threshold below which a whole Build is blocked and the previous Build stays live (e.g. coverage drops sharply), because it signals a site relaunch rather than content change. A configurable parameter.
_Avoid_: Quality threshold, cutoff
_Avoid_: Scrape, crawl (those are steps inside a Build), sync, import, ingestion

**Scheduled Build**:
A Build started by the routine rerun schedule, without anyone at the Municipality.

**Requested Build**:
A Build a Municipality starts itself (e.g. after updating its website). Optional; requires no expertise and no review. Unauthenticated but rate-limited (one per Municipality per day); domain verification is the target.

**Reference Client**:
The Citizen-facing chat embedded on a Municipality website, running on Swiss public AI, and itself a host that renders Service Cards. The default and sovereign way to use MMP; other MCP clients (Claude, ChatGPT) may connect but offer no such guarantee.
_Avoid_: Chatbot, widget, frontend, the app

**Gap Report**:
A Citizen-consented signal that a question found no Service; carries only an abstracted topic, never the Citizen's words or situation.
_Avoid_: Log, missing-service ticket

**Feedback**:
A Citizen-consented message about an answer or Service, sent only when the Citizen presses "send feedback" and agrees to what is included.
_Avoid_: Rating, telemetry, log

### Service tiers

**Information**:
A Service whose value is knowing something — opening hours, responsible office, required documents, fees, deadlines.

**Wayfinding**:
A Service whose value is being pointed to the right form, online counter or contact, with a checklist. The Citizen performs the action themselves.

**Transaction**:
A Service executed on the Citizen's behalf (register a move, order a certificate). Out of scope for MMP v1; envisioned long-term via a real API with eID/AGOV identity, never by submitting scraped forms.
_Avoid_: Action, write, submission, proxy

### Interaction

**Service Card**:
The single standardized view of a Service, shipped by every MMP server and rendered identically in any MCP host (Reference Client, Claude, ChatGPT).
_Avoid_: Widget, form, page, Gen UI component

**Handoff**:
What a Service Card produces when the Citizen acts: the Municipality's original online counter, form or contact, opened with the Citizen's inputs pre-filled. The Citizen submits in the original system.
_Avoid_: Submission, redirect, deep link
