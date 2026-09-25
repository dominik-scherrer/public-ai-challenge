# Glossary

| Term | Definition |
|------|------------|
| Citizen | A person interacting with a Municipality through the chat interface. |
| Municipality | A Swiss Gemeinde whose website is the source of truth for its services. |
| MMP Operator | Swiss AI, running MMP as a service public: operates builder, server, and client. |
| Service | One thing a Municipality offers a Citizen, published on its website. |
| Leistung | An entry in the eCH-0070 inventory, identified by its numeric Leistungs-ID. |
| Build | One run of the builder over one Municipality website, producing its Service Inventory. |
| Service Inventory | The data a Build produces for one Municipality: all its Services, each attribute with its source. |
| Judge | The automated LLM check that decides whether a Build goes live (quality gate). |
| Withheld Attribute | An attribute of a Service that failed the Judge and is therefore not shown. |
| Build Floor | The threshold below which a whole Build is blocked and the previous Build stays live. |
| Scheduled Build | A Build started by the routine rerun schedule. |
| Requested Build | A Build a Municipality starts itself. |
| Reference Client | The Citizen-facing chat embedded on a Municipality website, running on Swiss public AI. |
| Gap Report | A Citizen-consented signal that a question found no Service. |
| Feedback | A Citizen-consented message about an answer or Service. |
| Information | A Service whose value is knowing something (hours, fees, etc). |
| Wayfinding | A Service whose value is being pointed to the right form/contact. |
| Transaction | A Service executed on the Citizen's behalf. Out of scope for MMP v1. |
| Service Card | The single standardized view of a Service, rendered identically in any MCP host. |
| Handoff | The Municipality's original online counter opened with Citizen's inputs pre-filled. |
| MCP | Model Context Protocol — a standard protocol for exposing data and tools to LLM clients. |
| ScoutedService | A JSON record containing a service name, description, availability, and URLs. |
| PydanticAI | Framework for building type-safe LLM agents with structured Pydantic outputs. |
