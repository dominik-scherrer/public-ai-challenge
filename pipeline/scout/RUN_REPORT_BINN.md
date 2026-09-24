# Scout run report — Binn VS

First end-to-end run of Scout MVP-1 against a real municipality: `https://www.binn.ch/`.

**Result:** the success path works. From the Binn URL, Scout picked a sensible bounded strategy. It found the waste, building and office-hours services, kept two official handoffs (`strahlerpatente.binn.ch` and the canton's building portal) and proposed **Strahlerpatente** as a new service. It reported `move_in` and `forms` as `not_observed`, not `unavailable`, and wrote valid `municipality-discovery/v1` JSON.

That result needed five small fixes. The first real run (`runs/binn-off`) produced valid JSON with mostly wrong content. `runs/binn-off-v2` is the run after the fixes. Agent mode was not tested: no model is configured.

---

## 1. Environment

| | |
|---|---|
| Branch | `feat/scout-mvp-1` (PR #13), based on `a91a265` |
| OS | macOS (Darwin 25.6, arm64) |
| Python | 3.14.7 |
| uv | 0.12.18 |
| pydantic | 2.13.5 |
| pydantic-ai | 2.49.0 |
| Model | none (`SCOUT_MODEL` unset) |
| Run date | 2026-09-24 |

## 2. Test results

| Stage | Result |
|---|---|
| `uv sync` as checked out | **failed**: `Expected a Python module at: src/municipality_scout/__init__.py` |
| After build fix | 6 / 7 pass: `test_fixture_run_compiles_discovery_json` errors with `TypeError: 'tuple' object does not support the context manager protocol` |
| After test fix | 7 / 7 pass |
| Final (with 3 new regression tests) | **10 / 10 pass** |

Remaining warning (harmless, not fixed): `Field name "schema" in "ServiceIndex" / "MunicipalityDiscovery" shadows an attribute in parent "BaseModel"`.

## 3. Deterministic run summary

| | `runs/binn-off` (before) | `runs/binn-off-v2` (after) |
|---|---|---|
| Strategy | `broad_small_site`, 25 pages, depth 2 | same |
| Strategy reason | "Small/shallow site without a clear service directory." | same |
| Pages fetched | 25 | 25 |
| Distinct URLs | **21** (home ×3, gemeindeinfos ×2, steckbrief ×2) | **25** |
| Admin pages reached | Kontakt only | Verwaltung, Bauwesen, Abfallbewirtschaftung, Belegung Gemeindesaal, Reglemente, Kontakt, Auswärtige Ämter, Mitteilungsblätter |
| Obvious noise fetched | Wetter, Luftaufnahmen, Immobilien, Anschlagbrett, Die Siedlungen + 6 hamlet pages, Geschichte | Steckbrief, Das Binntal, Ortsplan, Schule (budget filler after admin pages) |
| Off-site pages stored | 0 (not reached) | 0 (two redirect to vs.ch / energieregiongoms.ch and are now dropped) |
| Stop reason | page budget (25/25) — **not recorded** in `crawl-report.json` | same |
| Failures recorded | 0 — fetch errors are silently skipped | same |
| `discovery.json` validates | yes | yes |

**Is the strategy plausible for Binn?** Yes. `www.binn.ch/` is a portal page with one internal link. Behind it, `/gemeinde` has about 146 internal links, most of them club photo galleries. A bounded broad crawl is right for a site this size. With the priority fix, 25 pages are enough to reach every administration page.

## 4. Services discovered (`runs/binn-off-v2`)

| service_id | availability | local_name | handling.type / interaction | confidence | sources |
|---|---|---|---|---|---|
| `waste_collection` | supported | Abfallbewirtschaftung | static_page / information | 0.65 | `/gemeinde/verwaltung/abfallbewirtschaftung` |
| `move_in` | not_observed | Zuzug | unknown / information | 0.00 | — |
| `office_hours` | supported | Kontakt | html_form / request | 0.85 | `/gemeinde/allgemein/kontakt` + mail form |
| `forms` | not_observed | Formulare | unknown / information | 0.00 | — |
| `building_application` | supported | Bauwesen | static_page / information | 0.65 | `/gemeinde/verwaltung/bauwesen` + `vs.ch/.../portail-utilisateurs` (official_handoff) |

Every supported service uses the same generic deterministic summary, for example *"The municipality provides this service primarily as information on an official web page."* Better summaries are what agent mode is for.

The office hours match is correct. The Kontakt page states *"Öffnungszeiten Montag, Dienstag & Freitag: 10.00 Uhr - 11.00 Uhr und 13.30 Uhr - 15.30 …"*.

For comparison, the before run (`runs/binn-off`) matched `waste_collection` **and** `building_application` to the home page, with local name "Webcam". It also proposed "Gemeindeinfos" (twice) and "Geschichte" as new services.

## 5. New-service candidates

| Run | catalog_suggestions |
|---|---|
| before | "Gemeinde Binn \| Binntal …" (Gemeindeinfos) ×2, "Geschichte" — all false positives |
| after | **Strahlerpatente** (confidence 0.58) — correct |

**Strahlerpatente:** Scout discovered it on its own. It is not in the Service Index, and nothing was added by hand. The link to `http://strahlerpatente.binn.ch/` is an image link with no text, and it is kept as an `official_handoff` on a sibling municipal subdomain, not dropped as an unrelated external page.

## 6. Source-bundle examples (`runs/binn-off-v2`)

```text
Strahlerpatente (possible_new)
  municipal_service_page  https://www.binn.ch/gemeinde/allgemein/strahlerpatente
  official_handoff        http://strahlerpatente.binn.ch/

building_application
  municipal_service_page  https://www.binn.ch/gemeinde/verwaltung/bauwesen
  official_handoff        https://www.vs.ch/de/web/sajmte/portail-utilisateurs

office_hours
  municipal_service_page  https://www.binn.ch/gemeinde/allgemein/kontakt
  form                    https://www.binn.ch/gemeinde/allgemein/kontakt?id=38&mod_action=check_mailform&data=session&language=de
```

## 7. Problems found

### Quality assessment (after fixes)

| Service / candidate | Result | Good? | Problem |
|---|---|---|---|
| waste_collection | Abfallbewirtschaftung page | ✅ | Bundle misses the regional waste authority links (`revo.ch` guide, recycling map, container chips). REVO is not recognisable as official by domain. |
| building_application | Bauwesen + canton portal | ✅ | Handling says `static_page`; really a cantonal handoff (`external_handoff` / `mixed`). |
| office_hours | Kontakt page | ✅ | Handling says `html_form / request` only because the page has a contact mail form. |
| move_in | not_observed | ✅ | Kept distinct from `unavailable`. Not found in 25 pages; Binn may not publish it. |
| forms | not_observed | ✅ | Binn has no forms page. |
| Strahlerpatente | possible_new + sibling handoff | ✅ | Handling says `static_page`; really an `external_handoff` to the permit shop. |
| Belegung Gemeindesaal | fetched, not proposed | ❌ | A real facility-booking service; missed because no generic service word appears in its title or slug. |
| Energieberatung / Baudossiers links | not in any bundle | ⚠️ | Internal links that redirect to other official sites are now dropped instead of being recorded as handoffs. |

### Answers to the review questions

1. **Real services, not generic pages?** After the fixes, yes. Before, no: the home page and news pages matched.
2. **Missed obvious services?** Belegung Gemeindesaal (facility booking) and the REVO waste resources.
3. **One page satisfying several index entries?** Yes before (home page → waste + building). Fixed: at most one entry per page.
4. **`not_observed` vs `unavailable` distinct?** Yes, in both runs.
5. **PDFs/forms/handoffs retained?** Forms and handoffs yes. Binn's service pages link no PDFs.
6. **Authoritative sources?** Yes. All sources are on `www.binn.ch`, `strahlerpatente.binn.ch` or `vs.ch`.
7. **Handling useful to the Factory?** Only partly. Types are coarse and the summaries are generic templates. The bundle carries the useful signal, the handoffs, but `handling.type` does not reflect it.
8. **False-positive `possible_new`?** Three before, none after.

### Root causes of the before-run failures

- **Navigation text in every page body.** Binn's CMS renders the full site navigation first. `page.text[:5000]` contained "Abfall", "Bauwesen", "Formulare" … on every page, so matching and new-service signals fired everywhere, and the home page won the ties.
- **Site-wide heading.** Every page's first heading is the "Webcam" widget, which became `local_name`.
- **Parent path segments.** `/verwaltung/…` matched the `office_hours` term "Verwaltung" for every page below it.
- **Redirect duplicates.** Dedupe used the requested URL, not the final URL after redirects.
- **Plain breadth-first order.** The budget ran out on hamlet and history pages before reaching Verwaltung.

## 8. Fixes made

All fixes are inside `pipeline/scout/`, and each commit is test-covered.

| Commit | Fix | Category |
|---|---|---|
| `d2977cb` | `pyproject.toml`: `[tool.uv.build-backend] module-name = "scout"`; add `uv.lock` | broken package |
| `3dc82e7` | `tests/test_scout.py`: parenthesised `with` statement | broken test |
| `6382ae6` | `runtime.py`: skip pages already seen by final URL or body hash; skip image assets; order each depth by priority (index terms and admin wording up; tourism, clubs, galleries and dated news items down) | redirect duplicate, crawl prioritisation, news noise |
| `cf5a7d3` | `discovery.py`: match only the title's first segment, headings that aren't site-wide, and the page's own URL slug; one page per index entry; never treat dated news items as services; dedupe candidates | Service Index matching, false-positive discovery |
| `93f4914` | `runtime.py`: drop pages whose final host is not the scouted site | redirect / crawl boundary |
| `8fc48b9` | `app.py`: cantonal (`vs.ch` …), `admin.ch` and `ch.ch` links count as official handoffs; recognise `portail` / `portale` | source bundle loss |

New regression tests (fixtures modelled on Binn): redirect duplicates + priority + off-site redirect, navigation text not matching every service, cantonal portal kept in the bundle.

## 9. Agent mode

```text
AGENT_MODE_BLOCKED_NO_MODEL
```

`SCOUT_MODEL` is not set, and there is no `OPENAI_API_KEY` or `.env`. No credentials were invented. The deterministic fallback path is what ran above. Agent mode is expected to help most on generic handling summaries and on handling types, not on matching, which is now deterministic.

## 10. Next three highest-value changes

1. **Derive `handling` from the source bundle.** When a bundle holds an `official_handoff` (Strahlerpatente, Bauwesen), set `external_handoff` / `wayfinding` or `mixed`. Ignore generic contact mail forms when deciding `html_form`. This is the smallest change that makes the output directly useful to the Factory, and it needs no model.
2. **Record crawl evidence.** Add `stop_reason`, fetch failures and off-site redirects to `crawl-report.json` / `failures[]`. Keep off-site redirects of internal links as `official_handoff` sources for the linking page (Baudossiers → vs.ch). Store raw snapshots.
3. **Run agent mode on Binn** with a configured `SCOUT_MODEL`, and compare handling types and summaries against the table above. Then extend the Service Index or generic signals for facility booking (Belegung Gemeindesaal), which is also in the MVP reference scenarios.

---

## Reproduce

```bash
git fetch origin
git switch feat/scout-mvp-1
cd pipeline/scout

# uv: https://docs.astral.sh/uv/  (or: pip install uv)
uv sync
uv run python -m unittest discover -s tests -v

# deterministic run
uv run scout https://www.binn.ch/ \
  --municipality Binn \
  --canton VS \
  --out runs/binn-off-v2 \
  --model-mode off

# validate the output
uv run python -c "from scout.contracts import MunicipalityDiscovery; import pathlib; \
print(MunicipalityDiscovery.model_validate_json(pathlib.Path('runs/binn-off-v2/discovery.json').read_text()).schema)"

# agent mode (needs a model)
export SCOUT_MODEL='openai:<model>'
export OPENAI_API_KEY='…'
uv run scout https://www.binn.ch/ --municipality Binn --canton VS --out runs/binn-agent --model-mode agent
```

Results depend on the live site, so later runs can differ.
