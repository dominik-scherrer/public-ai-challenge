# Crawl Strategies

## 1. One orchestrator, multiple bounded strategies

There should not be one universal scraper.

The orchestrator chooses a known strategy after reconnaissance.

## 2. FULL_CRAWL

Best for:

- tiny municipalities
- low page counts
- simple CMS
- weak information architecture
- municipal services embedded in general administration pages

Behavior:

```text
official domain
→ bounded breadth-first crawl
→ classify every page
→ retain municipal-service evidence
→ discard unrelated content
```

Typical budget:

- 100–1,000 pages depending on observed scale
- strict same-domain rules
- file-type allowlist
- depth limit

Primary risk:

- tourism / news / associations / local business noise

## 3. SECTION_CRAWL

Best for:

- small and medium municipalities
- identifiable administration sections
- service content grouped by department

Behavior:

```text
homepage
→ discover administration sections
→ rank likely service-bearing sections
→ crawl only selected subtrees
```

Examples:

- Einwohnerkontrolle
- Kanzlei
- Soziales
- Bauverwaltung
- Steueramt
- Online-Schalter

## 4. DIRECTORY_CRAWL

Best for:

- large cities
- mature service portals
- clear A–Z service indexes
- structured eGovernment portals

Behavior:

```text
service directory
→ service links
→ service detail pages
→ transaction endpoints
→ linked official documents
```

Avoid crawling:

- news archives
- political archives
- media pages
- unrelated department history
- broad tourism content

## 5. DISCOVERY_CRAWL

Best for:

- unknown structures
- portal ecosystems
- several linked official domains
- unusual CMS
- unclear service boundaries

Behavior:

```text
shallow reconnaissance
→ discover structure
→ choose FULL / SECTION / DIRECTORY
```

The discovery crawler should not become the long-running scraper.

## 6. Targeted follow-up

After initial extraction:

```text
known:
✓ service name
✓ authority
✓ description

missing:
✗ eligibility
✗ fee
✗ required documents
✗ transaction endpoint
```

The orchestrator ranks linked evidence candidates and may fetch a small number of them.

Example:

```json
{
  "follow": [
    {
      "url": "/online-schalter/umzug",
      "reason": "likely transaction endpoint"
    },
    {
      "url": "/downloads/merkblatt-umzug.pdf",
      "reason": "likely requirements and documents"
    }
  ]
}
```

This is preferred over unbounded browsing.

## 7. Language-aware crawl planning

Keep three concepts separate:

```text
administrative language
population language
website language
```

They are related but not equivalent.

Municipality context may contain:

```json
{
  "administrative_languages": ["de", "fr"],
  "population_languages": {
    "de": 0.55,
    "fr": 0.40,
    "other": 0.05
  },
  "website_languages": ["de", "fr"],
  "crawl_languages": ["de", "fr"]
}
```

Language affects:

- which site variants should be inspected
- expected coverage
- multilingual service pairing
- labels retained in the canonical record
- gap detection

## 8. Multilingual equivalence

Two pages do not automatically mean two services.

```text
Wohnsitzbestätigung
                 → canonical service
        /
attestation de domicile
```

Store:

```json
{
  "service_id": "...",
  "labels": {
    "de": "...",
    "fr": "..."
  },
  "source_refs": [
    "src_de",
    "src_fr"
  ]
}
```

## 9. Stop rules

Stop because of explicit conditions, not because the model "feels done".

Possible conditions:

- page budget reached
- all discovered service-directory entries processed
- no new services found in last N pages
- all required service fields above coverage threshold
- remaining links classified as low relevance
- language parity reached
- repeated content detected
- external domain boundary reached

Every crawl stores the stop reason.
