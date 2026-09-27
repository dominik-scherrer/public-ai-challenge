# MCP Capability Matrix — ingestion ↔ Patrick's tool surface

Patrick's live `minigmeind` MCP is the application/capability layer. The ingestion pipeline remains the evidence and canonical-data layer.

> **Boundary:** ingestion answers *what do we know, from which official source, and how complete is it?*  
> MCP answers *which capability/tool should an agent expose and how should it behave?*

The 16:43 tool screenshot says **31 tools**, while 32 individual tool names are visible. Treat the exact count as a deployment detail; the semantic capabilities below are the stable requirement.

## Capability matrix

| MCP tool | Canonical capability | Data ingestion must provide | Evidence requirement | Ausserberg first-batch status |
|---|---|---|---|---|
| `list_services` | `service_catalog` | service id, title/labels, category, summary | official source per service | **seed supported** |
| `find_responsible_office` | `authority_routing` | service/topic → responsible office, contact | official authority/contact page | **needs enrichment** |
| `get_office_hours` | `office_hours` | office, weekday hours, exceptions | official office page | **needs enrichment** |
| `get_local_notices` | `local_notices` | notice title/date/topic/link | official notice source | not yet |
| `list_official_notices` | `official_notices` | notice/procedure metadata and dates | official publication | not yet |
| `search_regulations` | `regulations` | regulation/document title, text/excerpts, URL | official PDF/page + section/page | **source discovered; extraction pending** |
| `list_forms` | `forms` | form id/title/topic/document or URL | official forms page/document | **seed supported, needs itemization** |
| `get_form_schema` | `form_schema` | fields, types, required/optional, submission target | official form/HTML structure | needs extraction |
| `prefill_form` | `form_prefill` | schema + permitted prefillable fields | derived from supported form schema | later |
| `get_move_in_requirements` | `residence_registration` | requirements, documents, deadline, channel, authority | exact official evidence per substantive field | **priority enrichment** |
| `register_move_in` | `residence_registration_action` | official endpoint + input schema + action semantics | official form; do not infer successful submission | route/prepare first |
| `register_move_out` | `residence_deregistration_action` | official endpoint + input schema + action semantics | official form | route/prepare first |
| `get_foreigner_procedure` | `foreign_resident_procedure` | procedure type, forms, authority, routing | official municipal/cantonal source | later |
| `get_id_requirements` | `identity_document_guidance` | requirements, fee where supported, authority, channel | official service page | **good next target** |
| `get_passport_process` | `passport_routing` | responsible cantonal office/process, handoff URL | official routing source | good next target |
| `get_road_permit_requirement` | `road_permit` | eligibility/rules, channels, source | official rule/service page | later |
| `calculate_road_permit_price` | `road_permit_pricing` | typed tariff rules, conditions | exact tariff evidence | later; deterministic calculation only |
| `parking_permit` | `parking_permit` | permit type, eligibility, fee, application URL | official service/tariff source | not yet |
| `get_building_application_requirements` | `building_application` | requirements known locally, authority, external portal | official municipal/cantonal source | **seed routing supported; requirements need enrichment** |
| `get_planning_procedures` | `planning_procedures` | active procedure, dates, documents, authority | official publication | later |
| `garbage_collection` | `waste_collection` | collection type/date/zone | official calendar/data | not yet |
| `next_waste_collection` | `waste_collection` | typed schedule + address/zone relation | official calendar/data | not yet |
| `where_dispose` | `waste_disposal` | material → collection point/rule | official waste guidance | not yet |
| `recycling_point_hours` | `recycling_points` | location and opening hours | official source | not yet |
| `list_facilities` | `facilities` | facility id/name/use/capacity where supported | official facility page | **priority enrichment** |
| `get_facility_options` | `facility_options` | equipment/options/conditions | official facility/request page | **priority enrichment** |
| `request_facility_booking` | `facility_request_action` | request form schema, endpoint, review semantics | official request form | route/prepare first |
| `list_events` | `events` | event title/date/location/source | official calendar | later |
| `get_budget` | `municipal_budget` | year/document/structured values where reliable | official budget | later |
| `get_accounts` | `municipal_accounts` | year/document/structured values where reliable | official accounts | later |
| `list_assembly_agenda` | `assembly_agenda` | meeting date, agenda items, docs | official assembly publication | later |
| `report_issue` | `issue_reporting` | issue categories, location/contact fields, official target | official form/schema | later |

## What changes in the inventory

The Service Inventory no longer advertises concrete MCP tool names.

Instead it exposes semantic capability tags, for example:

```json
{
  "capabilities": [
    "service_catalog",
    "residence_registration",
    "forms",
    "municipal_contact",
    "building_application",
    "facility_rental"
  ]
}
```

Individual service records may also contain their own `capabilities`.

Patrick's MCP maps those capabilities onto whichever tool surface is currently deployed.

This keeps the ingestion contract stable even if:

- a tool is renamed
- two tools are merged
- a capability is exposed differently in ChatGPT and another host
- the dummy server changes its tool count
- additional tools are added

## First real-data replacement slice

For the first end-to-end replacement of dummy data, prioritize Ausserberg:

1. `list_services`
2. `get_move_in_requirements`
3. `find_responsible_office`
4. `get_office_hours`
5. `list_forms`
6. `get_building_application_requirements`
7. `list_facilities` / `get_facility_options`

Action tools such as `register_move_in` and `request_facility_booking` should initially **prepare or route to the official endpoint**, not claim a completed municipal transaction.
