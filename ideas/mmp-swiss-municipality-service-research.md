# Model Municipality Protocol (MMP): What Swiss Gemeinden Actually Offer Online, and What Is Worth Exposing via MCP

Across the 19 Swiss municipality websites sampled in 6 languages/regions and 11 cantons, the same roughly 12 service categories recur regardless of size. What changes with size is **how** a service is offered, not **whether** it is offered. Big cities run authenticated transaction portals and some open APIs. Small Gemeinden mostly publish semi-structured "product" pages, PDF downloads and links out to cantonal portals. That makes an MMP-style scraper-plus-structurer feasible and most valuable exactly where the project wants to focus: small municipalities.

## TL;DR

- **One taxonomy fits all sizes.** Resident services (Einwohnerdienste), certificates, construction permits, taxes, debt enforcement, civil status, waste, facility booking, social services/AHV, schools, events/associations, politics/regulations, and contact/opening hours appear on sites from Saint-George VD (about 700 inhabitants) up to Stadt Zürich. Winterthur alone lists 169 services in 8 categories.
- **The chat interface pays off most in navigation and jurisdiction, not transactions.** In the Nationale E-Government-Studie 2025 (DVS/SECO with DemoSCOPE, March 2025), 53% of the population name hard-to-find services as the biggest obstacle, up 6 points from 2021, and most respondents first look for information through common search engines such as Google. Fees and competent offices vary locally: a Wohnsitzbestätigung costs CHF 10 in Schwyz, CHF 12 in Pfaffnau, CHF 20 in Grindelwald and CHF 30 in Oberglatt. Answering "what, where, how much, which office, which portal" is the killer feature. Actual transactions should be deep-linked to eUmzugCH, eBau, AGOV-authenticated portals and the like, not re-implemented.
- **Feasibility is good because the long tail is templated.** i-web says over 650 municipalities and cities have built their sites with its GemWeb/CityWeb modules (the vendor's own figure), with a repeating "Online-Schalter/Dienstleistungen" URL and data structure; OneGov Cloud and WordPress cover much of the rest. Target 3–4 CMS adapters plus a generic LLM extractor, and map everything onto the eCH-0070 Leistungsinventar as a canonical schema.

## Key Findings

1. **Service catalogs are strongly homogeneous.** Seantis/OneGov put it bluntly: all Swiss Gemeinden are very similar in their service offering and processes. The sample confirms this. The long tail is local (firewood orders in Scuol, market stall rental in Trogen, parking vignettes, the Oberglatt local-history book).
2. **Small Gemeinden: "Online-Schalter" often means a download library.** Scuol's Online-Schalter is described as laws, regulations, forms and documents to download. Saint-George VD offers PDF forms only. Trogen AR's items are mostly PDF/XLSX files marked "gratis". Real web forms exist mainly for high-volume certificates (Wohnsitzbestätigung in Pfaffnau, Oberglatt, Grindelwald; certificates in Novazzano and Airolo).
3. **Large cities: mature portals, identity-gated.** According to Stadt Zürich, «Mein Konto» gives access to over 100 services and has about 250,000 users, who have been able to log in with AGOV since 3 June 2026; it will also receive formal requests digitally. From 1 January 2027, new digital-communication rules apply there to authorities and professional representatives. Winterthur has a filterable catalog of 169 services. Lugano issues electronically sealed certificates 24/7.
4. **The transactional core is being centralized above the Gemeinde.** eUmzugCH (moving) is available in 24 cantons according to the eOperations Schweiz service page, and has been mandatory for Bernese municipalities since 1 February 2026. eBau (building permits) has been mandatory in Bern since 1 March 2022. The Thurgau digital counter issues a signed Wohnsitzbestätigung PDF, usually within 15 minutes. For MMP this means small-Gemeinde transactions are often *already* someone else's API or portal, so MMP should route to them.
5. **An MCP precedent already exists in Zürich.** The city's OGD pages list MCP servers for OpenERZ, its waste collection API covering Zürich, Basel, St. Gallen, Uster, Thalwil, Adliswil and Horgen, and for the CKAN open-data catalog. MMP's differentiation is therefore the **small-municipality long tail**, not Zürich.

## Sampled Municipalities

Population figures are approximate unless marked. Novazzano (2,346, end of 2024) and Trogen (1,877, 31.12.2024, via Wikidata citing BFS) were confirmed. Figures for Pfaffnau (~2,674) and Grindelwald (~3,800) are from 2020. Disentis (~2,200), Scuol (~4,600–4,700) and Saint-George (~700) are the municipalities' own rounded figures. Verify all of them against BFS STATPOP before publication.

| # | Municipality (Canton) | Size class | Language | URL(s) sampled | Delivery pattern observed | Platform |
|---|---|---|---|---|---|---|
| 1 | Zürich (ZH) | Large city | DE | https://www.stadt-zuerich.ch/de/service/mein-konto.html ; …/mein-konto/gesuche-antraege.html | Authenticated portal (AGOV), 100+ services, open data + MCP | Custom |
| 2 | Winterthur (ZH) | Large city | DE | https://eservices.winterthur.ch/alle-services/ (→ stadt.winterthur.ch/services) | Filterable catalog of 169 services, 8 categories | Custom (Nuxt) |
| 3 | Bern (BE) | Large city | DE | https://www.bern.ch/themen/planen-und-bauen/baubewilligung/ebau | Links to cantonal eBau (mandatory) | Custom |
| 4 | Lausanne (VD) | Large city | FR | https://www.lausanne.ch/prestations/controle-des-habitants/attestation-domicile-declaration-residence.html | "Prestations" pages + Guichet virtuel | Custom |
| 5 | Lugano (TI) | Large city | IT | egov.lugano.ch (per press coverage) | Sportello online, e-sealed certificates 24/7 | Custom |
| 6 | Emmen (LU) | Mid/large | DE | https://www.emmen.ch/online-schalter/32351/detail | i-web Online-Schalter, order + payment | i-web |
| 7 | Dübendorf (ZH) | Mid/large | DE | https://www.duebendorf.ch/dienstleistungen/24826 | Dienstleistungen pages + online ordering | i-web |
| 8 | Wettingen (AG) | Mid | DE | https://www.wettingen.ch/dienstleistungen/6060 | Dienstleistungen + Online-Schalter | i-web |
| 9 | Schwyz (SZ) | Mid | DE | https://www.gemeindeschwyz.ch/dienstleistungen/60800 | Dienstleistungen + Online-Schalter (CHF 10 certificate) | i-web |
| 10 | Stans (NW) | Small/mid | DE | https://www.stans.ch/dienstleistungen/13764 | Dienstleistungen + Online-Schalter; **robots.txt blocks automated access** | i-web |
| 11 | Oberglatt (ZH) | Small/mid | DE | https://www.oberglatt.ch/politik-verwaltung/verwaltung/online-schalter.html/46 | Web forms with basket/prepayment + eUmzug, eFristerstreckung, eGov Box links | i-web (inferred) |
| 12 | Grindelwald (BE) | Small | DE | https://www.gemeinde-grindelwald.ch/dienstleistung/wohnsitzbestaetigung-wohnsitzbescheinigung/ ; /online-schalter/ | Service pages + many links to AHV/akbern portals | WordPress |
| 13 | Pfaffnau (LU) | Small | DE | https://www.pfaffnau.ch/verwaltung/dienstleistungen.html/31/egov_service/383 ; /online-schalter.html/32 | Mostly PDF/DOTX + one paid order + links to my.lu.ch, rawi.lu.ch | i-web (inferred) |
| 14 | Trogen (AR) | Small | DE | https://www.trogen.ch/verwaltung/online-schalter.html/182 | PDF/XLSX downloads + links to bgs.ar.ch, mein.ar.ch | i-web (inferred) |
| 15 | Scuol (GR) | Small | RM/DE | https://www.scuol.net/de/online-schalter.html/13 | Legal-text library + orderable products (vignettes, firewood) | i-web (inferred) |
| 16 | Disentis/Mustér (GR) | Small | RM/DE | https://www.disentis.ch/de/onlineschalter/downloads/ | Download hub per department | WordPress (Bricks/WPML) |
| 17 | Saint-George (VD) | Very small | FR | https://www.saint-george.ch/f/administration-communale/guichet-virtuel/formulaire-divers.asp | PDF forms only; ID cards in person | Custom ASP |
| 18 | Airolo (TI) | Small | IT | https://www.comuneairolo.ch/richiesta_documenti.jsp ; /sportello_online.jsp | Document-request form, room booking, formulari | Custom JSP |
| 19 | Novazzano (TI) | Small | IT | https://www.novazzano.ch/sportello/ | One web form for 7 certificates (Fr. 10 each), no online payment | WordPress |

Supplementary pages consulted: Ecublens VD, Cheseaux-sur-Lausanne VD, Savigny VD, Chiasso TI, Arbedo-Castione TI, Meggen LU (eUmzug page), Kallnach BE (eUmzug page), Thusis GR and Churwalden GR (assembly minutes).

## Service Taxonomy and MCP Value Assessment

Value rating: **High** means a clear, frequent citizen pain that chat solves. **Medium** means useful but lower frequency, or mainly deep-linking. **Low** means a nice-to-have.

### 1. Einwohnerdienste / Meldewesen (resident registration and moving) — High
Zuzug/Wegzug/Umzug via eUmzugCH, Wochenaufenthalt, Drittmeldepflicht for landlords, arrival/departure forms and fees. Moving is a legally time-boxed event (14-day reporting duty) that touches two municipalities with possibly different processes, and eUmzug still isn't universal everywhere. A chat agent answering "I'm moving from X to Y — can I do it online, what does it cost, what do I need?" removes the most common cross-site friction. Keep the transaction in eUmzugCH and deep-link to it.

### 2. Bescheinigungen & Auszüge (certificates and registry extracts) — High
Wohnsitzbestätigung/-bescheinigung (CHF 10–30 depending on municipality), SBB GA Familia/Duo residence confirmation, Heimatausweis, Aufenthaltsausweis, Strafregisterauszug, and French/Italian equivalents. The most frequent formal online transaction on small-Gemeinde sites, with the most local variance in fee and delivery. A clear, actionable MMP tool: return the exact order-form URL, price and turnaround.

### 3. Ausweise & Identität (ID documents) — Medium
Identitätskarte, passports. Mostly a routing question (Gemeinde vs. cantonal passport office), which varies by canton; chat disambiguation helps, transaction stays offline/cantonal.

### 4. Bauen & Planung (building and planning) — High for information, Low for transaction
Baugesuch via cantonal eBau (mandatory in Bern since March 2022), zoning/building regulations, use-of-public-ground permits. Construction rules are the most jurisdiction-specific content on any site. RAG over regulation PDFs saves real time but needs strong "confirm with Bauverwaltung" guardrails — Scuol explicitly notes only the printed version is legally binding.

### 5. Steuern & Finanzen (taxes and finance) — Medium
Fristerstreckung Steuererklärung, E-Steuerkonto, Hundesteuer, Handänderungssteuer. Per the Nationale E-Government-Studie 2025, the tax return remains the most-often-online government task (76%), but runs on cantonal software. MMP's value is deadlines, extension links and clarifying cantonal vs. communal.

### 6. Betreibung & Konkurs (debt enforcement) — High
Betreibungsauskunft, often via a regional office rather than the Gemeinde itself. A Betreibungsregisterauszug is needed for almost every apartment application; in OneGov's 2016 data for one mid-size municipality it was 61% of all form transactions. "Which office is responsible for my address?" is exactly the kind of question chat solves well.

### 7. Zivilstand, Bestattung & Einbürgerung (civil status, burial, naturalisation) — Medium
Trautermin, Bestattungsamt/Friedhofreglement, naturalisation pages. Sensitive, often emotional life-event questions handled by regional civil-status offices — patient 24/7 explanation plus correct routing adds real value.

### 8. Entsorgung, Versorgung & Umwelt (waste, utilities, environment) — High frequency, moderate depth
Abfallkalender, regional waste responsibility, collection-point hours, meter reading. Probably the most frequent recurring citizen question ("when is paper collected on my street?") and a good demo, but small-Gemeinde calendars are usually PDFs/images with street-dependent zones — budget for PDF/table extraction and address-to-zone mapping. Reuse OpenERZ where it already covers a municipality.

### 9. Reservationen & Vermietungen (facility booking and passes) — High (under-rated)
Room/hall rental, Spartageskarte Gemeinde, parking vignettes. In OneGov's usage data, reservations were 56% of online transactions for one mid-size Gemeinde. Availability queries ("Is the gym free Saturday?") are ideal for chat and Generative UI, though the data is often locked in booking systems rather than scrapeable HTML.

### 10. Soziales, Gesundheit, Alter & AHV (social services, health, old age) — High for accessibility
AHV-Zweigstelle forms, Sozialamt, senior services, childcare subsidies. The target users (elderly, disabled, recent migrants) are the least served by fragmented websites. Plain-language, multilingual routing to the right benefit is high-impact — do not handle personal case data.

### 11. Bildung, Familie & Freizeit (schools, family, leisure, events, associations) — Medium
School sites (often separate domains), Sportpass, event calendars, Vereinsverzeichnis, event permits. Good for community engagement; event data is usually the most structured content on i-web/OneGov sites, so cheap to include, but lower in civic urgency.

### 12. Politik, Publikationen & Rechtssammlung (politics, notices, regulations) — Medium–High for transparency
Gemeindeversammlung minutes, amtliche Publikationsorgane, systematic law collections. Searching across years of assembly minutes ("What did the Gemeinde decide about the new gym?") is unsupported today on small-municipality sites. Content is almost entirely PDF — treat as document retrieval, not structured tools.

### 13. Kontakt, Öffnungszeiten & Organisation (contact, opening hours; cross-cutting) — High and foundational
Opening hours, staff directories, contact forms, appointment booking. Small administrations have limited hours (e.g. Pfaffnau closed Monday/Wednesday/Friday afternoons). "Is the Gemeindekanzlei open now, and who handles X?" plus hand-off to the right contact form is the baseline tool every MMP instance should ship.

## Small vs. Large Municipalities: Patterns That Matter for Feasibility

| Dimension | Small Gemeinden (<10k) | Large cities |
|---|---|---|
| Service breadth | Same core categories, plus idiosyncratic local items | Same core, plus many more specialised services (Zürich 100+, Winterthur 169) |
| Delivery mode | PDF/DOTX/XLSX downloads, simple web forms, links to cantonal portals | Authenticated end-to-end transactions (AGOV, «Mein Konto»), e-sealed documents |
| Structure | Surprisingly structured if on i-web/OneGov (product pages with price, department, links); unstructured if custom ASP/JSP or WordPress | Structured catalogs with categories and filters; some open data and APIs |
| Machine access | Usually crawlable; some block bots (Stans robots.txt) | Crawlable catalogs; APIs for selected domains (OpenERZ, CKAN); MCP already exists |
| Language | Multilingual edge cases: Romansh-authoritative texts (Scuol), Italian/French forms | Mostly primary language, some English |
| Main risk for MMP | Stale PDFs, fee/rule drift, content spread over school/regional/cantonal domains | Little added value versus existing portals; auth-walled content |

**Interpretation.** The digital gap is real: in Myni Gmeind's 2022 municipal survey (with SGV and TransferPlus), 58% of participating municipalities saw themselves as digitalisation laggards and only 2% as pioneers. Switzerland is also behind the EU: in the European Commission's eGovernment Benchmark 2024, 79% of the Swiss services examined were online versus 88% in the EU, with an overall score of 60 points against an EU average of 76. But for MMP, "less digitized" mostly means *less transactional*, not *less described*. Small Gemeinden still publish what, how much, where and when, just in inconsistent formats — a structuring problem an LLM-based pipeline handles well. The hard part is not extraction but **freshness and liability**: fees, calendars and regulations change yearly, and small offices won't notify you.

## Recommendations for MMP

1. **Adopt eCH-0070 (Leistungsinventar CH) as the canonical service ID schema,** with the 13 categories above as a user-facing layer. Gives cross-municipality comparability and a credible "standards-based" story for the public-sector jury.
2. **Build CMS-specific adapters first.** In order: i-web (`/dienstleistungen/NNN`, `/online-schalter.html/NN/product/NN`, `egov_service/NNN`), OneGov Cloud/admin.digital, then WordPress. Generic LLM extractor for custom sites (Saint-George, Airolo). i-web's scale (650+ municipalities per the vendor) means one good adapter covers a large share of German-speaking Switzerland.
3. **Define a small, uniform MCP tool surface:** `find_service(query, municipality)`, `get_service_details(id)` (fee, documents, responsible office, channel, source URL, last-crawled date), `get_opening_hours`, `get_waste_dates(address)`, `search_documents(query)` for minutes/regulations, and `route_to_portal(service)` for eUmzugCH, eBau, AGOV and cantonal portals. Always return the source URL for Generative UI "open official page" buttons.
4. **Route, don't re-implement, transactions.** Auth, e-ID/AGOV and legal submission already live in eUmzugCH, eBau, «Mein Konto» and cantonal counters. MMP should hand off with prefilled context where allowed.
5. **Demo with a contrast pair.** Same question ("I'm moving to Trogen — what do I need, and when is waste collection?") answered for Trogen AR vs. Zürich. Makes the small-municipality value obvious.
6. **Engineer for trust:** respect robots.txt (Stans), show "last verified" timestamps, add a legal-disclaimer layer for building/tax content, and offer an opt-in path for municipal staff to correct extracted data — this path doubles as the adoption channel.

## Caveats

- This is a qualitative survey of 19 sites plus supplementary pages, not a census. For several small sites (Pfaffnau, Trogen, Oberglatt, Grindelwald) only partial service lists were read. Absence of a service here does not prove it is missing online.
- Population figures are approximate or dated for most small municipalities; confirm against BFS STATPOP (table px-x-0102010000_101).
- CMS attribution for Pfaffnau, Trogen, Oberglatt and Scuol is inferred from URL patterns. WordPress attributions (Grindelwald, Disentis, Novazzano) were confirmed from page source.
- Conflicting eUmzugCH coverage figures: eOperations states both "21 Kantone" (older text) and "24 Kantone" (current service page). The higher, more recent figure is used here but should be treated as a moving target.
- OneGov transaction-mix figures are from a 2016 vendor blog about one unnamed mid-size municipality — indicative only, not representative statistics.
- Rapid change: fees, calendars and portal integrations (e.g. Zürich's 1 January 2027 digital-communication rules, Bern's eUmzug obligation) change frequently. Re-crawl before any demo.

---
*Research compiled 2026-09-24 for the AI Weeks Zurich hackathon submission. Full artifact with inline sources: see project record.*
