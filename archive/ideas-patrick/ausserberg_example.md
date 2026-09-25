Ausserberg is a good example because it already has a mix of **true online forms, static PDFs, structured municipal information, and links into cantonal systems**. That is close to the heterogeneity an MCP abstraction layer would have to normalize.

| Service / information                    | Current shape on Ausserberg                                                                                                                                                                      | Possible MCP shape                                                                                      | Fit                                                   |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Register move-in**                     | Native web form: name, previous municipality, new Ausserberg address, contact details, message. ([Ausserberg][1])                                                                                | `register_move_in(...)` or initially `get_move_in_requirements()` + `prepare_move_in_submission()`      | **Excellent**                                         |
| **Register move-out**                    | Native web form with old/new address and contact details. ([Ausserberg][2])                                                                                                                      | `register_move_out(...)`                                                                                | **Excellent**                                         |
| **Rent municipal facilities**            | Rich transactional web form covering dates, facilities, equipment, acceptance of conditions and file upload; municipal office reviews and approves the request. ([Ausserberg][3])                | `list_facilities()`, `get_facility_options()`, `request_facility_booking(...)`                          | **Excellent**; very agent-friendly                    |
| **Building applications**                | Not handled by the municipality website itself. Ausserberg requires applications through the cantonal **eConstruction** platform; it is/was a pilot municipality. ([Ausserberg][4])              | `get_building_application_requirements()`, then adapter/deep-link to cantonal service                   | **Excellent example of federation**                   |
| **Forms / applications**                 | Collection of downloadable PDFs: drinking-water connection, wastewater connection, solar installation, canteen request, foreign-resident forms, municipal-work reporting, etc. ([Ausserberg][5]) | `list_forms(topic)`, `get_form_schema(form_id)`, `prefill_form(...)`                                    | **Very high**                                         |
| **Report municipal work/problem**        | PDF form for an unresolved municipal work item: description, exact location, urgency, contact details. ([Ausserberg][6])                                                                         | `report_issue(description, location, urgency)`                                                          | **Excellent candidate for upgrading PDF → API**       |
| **ID card / passport guidance**          | Information page explaining required documents, signatures by age, prices, validity, and where passports are handled. ([Ausserberg][7])                                                          | `get_id_requirements(age, case)`, `get_passport_process()`                                              | **High**, mainly informational                        |
| **Regulations**                          | Collection of municipal regulatory PDFs: police, building/zoning, cemetery, water/sewer, waste, driving fees, fire brigade, etc. ([Ausserberg][8])                                               | `search_regulations(query)`, `get_rule(topic)`, `cite_regulation(...)`                                  | **Very high** for trustworthy civic agents            |
| **Official publications**                | Dated HTML notices, currently including public planning procedures with deadlines and objection instructions. ([Ausserberg][9])                                                                  | `list_official_notices()`, `search_notices()`, `get_active_deadlines()`                                 | **Excellent**                                         |
| **Municipal noticeboard / news**         | “Weibil-Totz”: local notices such as waste collection and infrastructure works. ([Ausserberg][10])                                                                                               | `get_local_notices()`, `get_disruptions()`                                                              | **High**                                              |
| **Waste / recycling**                    | Waste and recycling information largely published through a calendar/document; includes recycling-centre opening hours and disposal guidance. ([Ausserberg][11])                                 | `next_waste_collection(type)`, `where_dispose(item)`, `recycling_point_hours()`                         | **Excellent**, but requires structuring document data |
| **Driving permits for rural roads**      | Concrete rules and prices published online; permits can be bought through municipality, local shop, machine, Parkingpay or TWINT. ([Ausserberg][12])                                             | `get_road_permit_requirement()`, `calculate_road_permit_price(days)`, possibly `purchase_road_permit()` | **Very high**                                         |
| **Municipal offices / responsibilities** | Detailed directory tying people to functions, departments, phone numbers and emails. ([Ausserberg][13])                                                                                          | `find_responsible_office(topic)` / `who_handles(issue)`                                                 | **Excellent foundational tool**                       |
| **Council responsibilities**             | Portfolios explicitly assigned: planning, building, water, education, social affairs, transport, etc. ([Ausserberg][14])                                                                         | Same routing tool, with structured authority metadata                                                   | **High**                                              |
| **Opening hours / contact**              | Structured contact information and counter opening hours. ([Ausserberg][15])                                                                                                                     | `get_office_hours()` / `get_contact(service)`                                                           | **Easy / foundational**                               |
| **Local events**                         | HTML calendar aggregating municipality, parish and local association events. ([Ausserberg][16])                                                                                                  | `list_events(date_range, category)`                                                                     | **High**, trivial to expose                           |
| **Municipal facilities directory**       | Facilities described individually—school house, Burgerstube, sports field, multi-purpose hall, Bielhüs, etc.—with intended uses. ([Ausserberg][17])                                              | `search_facilities(capacity/use)` combined with booking                                                 | **High**                                              |
| **Municipal finance / assemblies**       | Budgets, annual accounts, assembly invitations and supporting documents published online. ([Ausserberg][18])                                                                                     | `get_budget(year)`, `get_accounts(year)`, `list_assembly_agenda()`                                      | **High for PublicAI**                                 |
| **Planning / participation procedures**  | Formal public planning publications and supporting documents, including deadlines and objection procedures. Current land-use-plan revision is an example. ([Ausserberg][9])                      | `get_planning_procedures()`, `get_objection_deadline()`, `get_planning_documents()`                     | **Very high / differentiated**                        |
| **Foreign-resident procedures**          | Cantonal PDFs exposed via the municipal forms section, e.g. residence permits and mutation notifications. ([Ausserberg][5])                                                                      | `get_foreigner_procedure(change_type)` + canton routing                                                 | **High**, good cross-level-government example         |

### The interesting part for your MCP idea

Ausserberg exposes roughly **four different service shapes**, and I think these are more important than the individual services:

1. **Structured information**
   - offices
   - responsibilities
   - prices
   - opening hours
   - requirements
   - facilities

   These are straightforward read-only MCP resources/tools.

2. **HTML transactions**
   - move-in
   - move-out
   - facility reservation
   - general contact

   These can potentially become actual **write/action MCP tools**, assuming the municipality authorizes automated submissions. ([Ausserberg][1])

3. **PDF-as-a-service**
   - water connection
   - sewage connection
   - foreign-resident forms
   - solar installations
   - unresolved public works
   - regulations

   This is where your abstraction layer adds substantial value. The citizen currently needs to **discover a PDF → understand it → fill it → determine submission channel**. MCP could expose the underlying semantic operation instead:
   `apply_for_water_connection(...)`
   rather than
   `download("2022 Trinkwasseranschlussgesuch.pdf")`. ([Ausserberg][5])

4. **Federated external services**
   - construction → cantonal eConstruction
   - passport → cantonal passport centre
   - road permit/payment → Parkingpay / TWINT / physical outlets

   The municipality is effectively already a **service router**, not necessarily the service provider. ([Ausserberg][4])

That last observation is important.

### I would not build an “Ausserberg MCP server”

I would define something more like:

```text
municipality.get_service(service_type, municipality)

municipality.get_requirements(
    service="identity_card",
    municipality="Ausserberg",
    citizen_context={...}
)

municipality.find_authority(
    municipality="Ausserberg",
    topic="wastewater connection"
)

municipality.list_forms(
    municipality="Ausserberg",
    topic="water"
)

municipality.get_official_notices(
    municipality="Ausserberg",
    active_only=true
)

municipality.get_deadlines(
    municipality="Ausserberg",
    topic="spatial_planning"
)

municipality.report_issue(
    municipality="Ausserberg",
    location=...,
    category=...,
    description=...
)

municipality.reserve_facility(
    municipality="Ausserberg",
    facility="Burgerstube",
    start=...,
    end=...
)
```

The **Ausserberg adapter** then knows that one operation means scraping/querying HTML, another means transforming a PDF, another means submitting a website form, and another redirects to a cantonal service.

### Most promising prototype

For a hackathon I would make the first Ausserberg adapter support **6 generic capabilities**:

**`service_search` → `service_requirements` → `authority_lookup` → `official_notices` → `forms` → `submit_request`**

Then demonstrate questions/actions such as:

> “I’m moving to Ausserberg next month. What do I need to do?”

The agent discovers the move-in service and applicable municipal contact/form. ([Ausserberg][1])

> “I want to install solar panels. What do I have to submit?”

It discovers the solar-installation form plus the relevant building/planning framework rather than merely doing a website keyword search. ([Ausserberg][5])

> “Can I rent somewhere in Ausserberg for a 50-person birthday and get a projector?”

It discovers suitable municipal facilities and the available equipment, then constructs the actual booking request. ([Ausserberg][17])

> “Are there any municipal procedures running right now that I can object to?”

It queries current official publications and returns the relevant procedure, legal basis, documents and deadline. The current land-use-plan revision is exactly such a case. ([Ausserberg][9])

That is considerably more compelling than a municipal chatbot: **the LLM handles intent and composition; the MCP layer supplies typed, attributable civic capabilities.**

[1]: https://www.ausserberg.ch/gemeinschaft/verwaltung/verwaltung/online-schalter/anmeldung-wohnsitz?utm_source=chatgpt.com "Anmeldung Wohnsitz | Gemeinde Ausserberg"
[2]: https://www.ausserberg.ch/gemeinschaft/verwaltung/online-schalter/wegzug?utm_source=chatgpt.com "Wegzug | Gemeinde Ausserberg"
[3]: https://www.ausserberg.ch/gemeinschaft/informationen/antraege-gesuche-reglemente/miete-gemeindeanlagen?utm_source=chatgpt.com "Miete Gemeindeanlagen | Gemeinde Ausserberg"
[4]: https://www.ausserberg.ch/gemeinschaft/informationen/bauwesen?utm_source=chatgpt.com "Bauwesen | Gemeinde Ausserberg"
[5]: https://www.ausserberg.ch/gemeinschaft/informationen/antraege-gesuche-reglemente/antraege%2C-gesuche-formulare?utm_source=chatgpt.com "Anträge, Gesuche, Formulare | Gemeinde Ausserberg"
[6]: https://www.ausserberg.ch/?action=get_file&id=105&resource_link_id=5ee&utm_source=chatgpt.com "Vom Antragsteller auszufüllen"
[7]: https://www.ausserberg.ch/gemeinschaft/informationen/antraege-gesuche-reglemente/beantragung-identitaetskarte-pass?utm_source=chatgpt.com "Beantragung Identitätskarte | Gemeinde Ausserberg"
[8]: https://www.ausserberg.ch/gemeinschaft/informationen/antraege-gesuche-reglemente/reglemente?utm_source=chatgpt.com "Reglemente | Gemeinde Ausserberg"
[9]: https://www.ausserberg.ch/gemeinschaft/informationen/amtliche-veroeffentlichungen?utm_source=chatgpt.com "Amtliche Veröffentlichungen | Gemeinde Ausserberg"
[10]: https://www.ausserberg.ch/gemeinschaft/informationen/anschlagbrett-weibil-totz?utm_source=chatgpt.com "Anschlagbrett (Weibil-Totz) | Gemeinde Ausserberg"
[11]: https://www.ausserberg.ch/?action=get_file&id=32&resource_link_id=5ef&utm_source=chatgpt.com "gemeinde@ausserberg.ch"
[12]: https://www.ausserberg.ch/erleben/tourismus/fahrgebuehren-ausserhalb-dorf?utm_source=chatgpt.com "Fahrgebühren ausserhalb Dorf | Gemeinde Ausserberg"
[13]: https://www.ausserberg.ch/gemeinschaft/verwaltung/aemter?utm_source=chatgpt.com "Ämter | Gemeinde Ausserberg"
[14]: https://www.ausserberg.ch/gemeinschaft/verwaltung/verwaltung/gemeinderat?utm_source=chatgpt.com "Gemeinderat von Ausserberg | Gemeinde Ausserberg"
[15]: https://www.ausserberg.ch/gemeinschaft/verwaltung/verwaltung/gemeindekanzlei?utm_source=chatgpt.com "Gemeindekanzlei | Gemeinde Ausserberg"
[16]: https://www.ausserberg.ch/zukunft/organisation/agenda-kalender-veranstaltungen?utm_source=chatgpt.com "Agenda / Kalender / Veranstaltungen | Gemeinde Ausserberg"
[17]: https://www.ausserberg.ch/gemeinschaft/verwaltung/verwaltung/gemeindelokalitaeten-infrastruktur?utm_source=chatgpt.com "Gemeindelokalitäten & Infrastruktur | Gemeinde Ausserberg"
[18]: https://www.ausserberg.ch/gemeinschaft/verwaltung/finanzen-politik/finanzen?utm_source=chatgpt.com "Finanzen | Gemeinde Ausserberg"
