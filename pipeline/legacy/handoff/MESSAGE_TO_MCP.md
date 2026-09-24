# Message to MCP person

**Scraping calling MCP 👋**

Saw the live `minigmeind` tool surface — this actually makes the boundary cleaner.

I adapted the ingestion handoff so I am **not** generating data tied to individual MCP tool names. Instead, the municipality inventories now expose canonical data + provenance + semantic capability tags.

So:

```text
scraping / ingestion
→ canonical Service Inventory + capabilities
→ your MCP adapters/tools
```

For example:

```text
residence_registration
→ get_move_in_requirements / register_move_in

office_hours
→ get_office_hours

building_application
→ get_building_application_requirements

facilities
→ list_facilities / get_facility_options
```

This means your tool surface can evolve without forcing the crawler schema to change.

I also mapped the tool surface from your latest screenshot to the fields/evidence the ingestion pipeline needs to provide:

`pipeline/handoff/MCP_CAPABILITY_MATRIX.md`

The first data batch is still here:

`pipeline/handoff/delivery-2026-09-24/`

I would start with **Ausserberg** and replace a small useful slice of dummy tools with grounded data first:

- `list_services`
- `get_move_in_requirements`
- `find_responsible_office`
- `get_office_hours`
- `list_forms`
- `get_building_application_requirements`
- `list_facilities` / `get_facility_options`

For action tools like `register_move_in` or `request_facility_booking`, my suggestion is that the first real version prepares/routes to the official endpoint rather than claiming the municipality accepted a transaction.

If this boundary works for you, I'll treat the capability matrix as the ingestion backlog and keep feeding richer inventories into the same contract.
