# Collection Rulebook — Swiss Municipal Service Baseline (v0.1, 2026-09-24)

Binding for every municipality collection. Schemas: `../schemas/`. Helper: `capture-helpers.js`. Validator: `../tools/finalize.py`.

## 1. Capture discipline (route b)

| Step | Tool | May back an evidence quote? |
|---|---|---|
| Discovery / navigation | WebFetch, or `__cap()` link lists | WebFetch: **never** |
| Evidence capture | Browser pane: `__cap(url)` (same-origin re-fetch, DOMParser text) or `get_page_text` on the rendered tab | yes |
| Quote check | `__verify(url, quotes)` in the browser | — sets `quote_check` |

- A WebFetch summary is never quoted. If a source was only seen via WebFetch, its record gets `capture_method: webfetch_discovery_only`, `snapshot_quality: discovery_summary_only`, and no service field may cite it as evidence.
- `content_hash`, `last_modified`, `etag`, `canonical_url`, `hreflang` are recorded **only when directly observed** by `__cap`. Otherwise `null` / `[]`. Never guess.
- `snapshot_quality: raw_hash_text` means raw bytes were hashed and verbatim text extracted, but the raw bytes are **not archived**. Say so; don't imply a stored snapshot.
- JS-rendered pages (text missing from `__cap`): navigate the tab, use `get_page_text`; record `capture_method: browser_rendered_page_text`, `snapshot_quality: rendered_text_only`.
- Cross-origin pages (cantonal/portal domains) cannot be `__cap`-ed from another origin: open them in their own tab. If the browser has no access to a domain, record the portal link as observed on the municipal page and do not capture it.
- PDFs: `__cap` returns hash + headers only. Only quote PDF content if you actually read it in the browser (rendered viewer text); otherwise cite the PDF as a `documents[]` entry backed by the link text on the HTML page.

## 2. Is it a service? (inclusion test)

Include when an identifiable actor can **obtain / request / register / report / apply / pay / change / cancel / fulfil** something with a public administrative responsibility, AND the page identifies that capability (not just a topic).

Exclude (log in `crawl-report.rejected_candidates` with reason): news, politics, council bios, tourism, hotels, restaurants, associations/clubs, events, businesses, generic municipality descriptions, pure topic pages with no capability, departments as such.

Borderline rules:
- **Delegated/intermunicipal provider** (e.g. regional waste association, cantonal office acting for the municipality): include if the municipal site presents it as the way residents fulfil that municipal obligation; set `provider.authority_level` accordingly (`intermunicipal`/`canton`) and add a judgement_note.
- **Cantonal/federal services merely linked** (e.g. passports): include only if the municipality itself performs a step (counter, application intake). Otherwise reject with reason `not municipal responsibility`.
- **Facility booking / rentals** by the municipality (hall, sports field): service.
- **Regulations only** (Reglement PDF with no action): not a service by itself; may be a `documents[]` entry.
- **Information-only public duty** (e.g. "Hunde müssen angemeldet werden" with no channel): include as `status: partial` with `actions:[{type:information_only}]` if the obligation + responsible office are stated.

## 3. Identity & multilingual merge

- One canonical service per administrative capability, not per page.
- Merge language pages only with evidence: hreflang pair, explicit language switcher mapping, identical URL slug structure/ID, or same office + same procedure + same fee. Record the basis in `judgement_notes` (INFERENCE unless hreflang/switcher = FACT).
- `labels.<lang>` holds the **verbatim official label** (page H1 or directory entry) — never a translation. Extra variants go to `labels.alt`. Languages without an official label stay `null`.
- `concept` is a normalized English snake_case name (machine-facing, not official). Prefer the shared vocabulary in §7.

## 4. Provenance classifications (accepted)

| Class | Use for |
|---|---|
| `official` | Verbatim statement from the responsible authority's own publication (labels, raw fee text, stated documents, stated channels with explicit wording). |
| `observed` | Directly observed in a non-responsible but identifiable source (e.g. a third-party portal page, cantonal page describing a municipal service). |
| `derived` | Deterministic transform of an official/observed value (`"CHF 30.–"` → amount 30, currency CHF). Set `derived_from`. |
| `inferred` | Semantic interpretation by the collector (paragraph → eligibility; `channels.postal=true` from "per Post einreichen"; English description; merge decisions). |
| `dynamic` | Computed at analysis/query time (not expected in this baseline). |

Every populated field path gets a `field_provenance` entry. Paths: `labels.de`, `description`, `provider.name`, `provider.department`, `eligibility[0]`, `requirements[0]`, `documents[0]`, `fees[0].raw_text`, `fees[0].amount`, `processing_time`, `channels.online`, `actions[0]`, `contacts[0]`.

Evidence quotes: short (≤ 400 chars, ideally one sentence), verbatim, checked with `__verify` → `quote_check: exact` (`__verify` compares after collapsing whitespace only; no other normalization). Unchecked → `not_checked` and it does not count toward coverage.

## 5. Status & trust

- `status: verified` — label, provider and ≥1 action/channel all backed by checked official evidence.
- `status: partial` — real service but key facts (channel, provider, or action) not evidenced.
- `status: candidate` — plausible service, evidence thin or authority unclear. Keep few.

Trust dimensions (never collapsed into one score):
- `authority`: high = responsible authority published the evidence itself; medium = official but different level/delegated body or third-party platform operated for the authority; low = non-official source.
- `directness`: primary = service page of the provider; secondary = directory/overview/department page; indirect = only linked from elsewhere.
- `freshness`: known = a source-stated date exists (`source_modified_at` with basis); stale_indicated = visible evidence of outdated content (old year, expired form); unknown = otherwise. Being online now ≠ fresh.
- `evidence_coverage`: **computed by `tools/finalize.py`** = share of populated field paths having ≥1 checked evidence quote (derived fields count if their `derived_from` path is covered). Coverage metric, not trust.
- `conflicts`: copy of service `conflicts[]`; never silently resolved.

## 6. Crawl conduct & stopping

- Recon first (homepage nav, A–Z, sitemap.xml, search, eGov links, languages/hreflang). Write `recon_plan` into crawl-report.
- Stay on official domains; follow external links only with evidence the target is an official part of the service; record the transition in `actions[].transition`.
- Service counts are soft budgets, not quotas. Stop per CRAWL_STRATEGIES §9 and record `stop_reason`. Never pad.
- Be polite: sequential requests, no parallel hammering.

## 7. Shared concept vocabulary (extend if needed, note additions)

residence_registration, residence_deregistration, move_within_municipality, residence_certificate, identity_card_application, civil_status_documents, marriage_preparation, birth_registration, death_registration, naturalisation, dog_registration, dog_tax, building_permit, building_permit_minor, building_file_inspection, parking_permit_resident, parking_permit_visitor, public_space_use_permit, event_permit, tax_return, tax_payment, waste_collection, bulky_waste_collection, green_waste, waste_vignette_or_bag_fee, water_connection, meter_reading_report, childcare_subsidy, childcare_place, school_enrolment, social_assistance, supplementary_benefits, facility_booking, grave_and_burial, lost_and_found, debt_enforcement_extract, business_permit, noise_complaint_or_damage_report, voting_register, fishing_or_hunting_or_crystal_permit, energy_advice, housing_support.

## 8. FACT / INFERENCE / HYPOTHESIS / IDEA

Use `judgement_notes` on services and the four headings in `notes.md`. Never promote an INFERENCE/HYPOTHESIS/IDEA to FACT.
