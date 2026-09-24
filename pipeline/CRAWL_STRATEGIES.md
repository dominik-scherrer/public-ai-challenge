# Crawl Strategies

## 1. One orchestrator, multiple bounded strategies

There is no universal scraper.

Reconnaissance produces a typed plan selecting one of four main strategies plus a fetch tier.

## 2. Fetch tiers

```text
HTTP
  ↓ insufficient
HEADLESS_BROWSER
  ↓ interaction required
AGENT_BROWSER
```

Default to HTTP. Escalation must record a reason.

We are crawling public-information sources at low volume, so optimization should focus on **avoiding unnecessary requests**, not bypassing anti-bot protections.

Operational defaults:

- clear and stable user agent
- conservative concurrency
- per-host rate limits
- cache aggressively
- reuse snapshots
- respect robots and obvious site constraints
- prefer sitemap/directory traversal over brute-force crawling
- stop when coverage converges

## 3. FULL_CRAWL

Best for tiny municipalities, low page counts and weak information architecture.

```text
official domain
→ bounded breadth-first crawl
→ classify every page
→ retain service evidence
→ discard unrelated content
```

Primary risk: tourism, news, associations and local-business noise.

## 4. SECTION_CRAWL

Best for small/medium municipalities with identifiable administration sections.

```text
homepage
→ discover service-bearing departments
→ crawl selected subtrees
```

Examples: Einwohnerkontrolle, Kanzlei, Soziales, Bauverwaltung, Steueramt, Online-Schalter.

## 5. DIRECTORY_CRAWL

Best for large cities and mature portals.

```text
service directory
→ service links
→ detail pages
→ transaction endpoints
→ official supporting documents
```

Avoid news archives, political archives, media pages, broad tourism content and unrelated departmental history.

## 6. DISCOVERY_CRAWL

Best for unclear structures, portal ecosystems and unusual CMSs.

```text
shallow reconnaissance
→ discover structure
→ compile CrawlPlan
→ switch to FULL / SECTION / DIRECTORY
```

Discovery must remain shallow; it should not become the long-running scraper.

## 7. Targeted follow-up

After initial extraction, fetch only evidence likely to close real gaps.

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

The planner/small model can rank candidate links, but deterministic policy caps follow-ups.

## 8. Language-aware planning

Keep distinct:

```text
administrative language
population language
website language
```

Language context influences which site variants to inspect, expected coverage and multilingual service pairing.

Population-language data is a planning signal, not proof that a municipality publishes services in that language.

## 9. Multilingual equivalence

Two pages do not automatically mean two services.

```text
Wohnsitzbestätigung
        \
         → canonical service
        /
attestation de domicile
```

Merge only with sufficient evidence and preserve every official label and source.

## 10. Stop rules

Stop because of explicit conditions, never because a model "feels done".

Possible conditions:

- page budget reached
- discovered service directory exhausted
- no new services in the last N retained pages
- remaining links classified low relevance
- language coverage target met
- repeated-content threshold reached
- external-domain boundary reached
- coverage objective reached

Every crawl records the stop reason.

## 11. Site adapters

A successful discovery crawl may compile a reusable adapter containing:

- allowed roots
- service-link selectors
- exclusion patterns
- language routing
- field selectors
- portal transition rules

Adapters are cached and versioned. They are hints/programs, never authority: provenance still points to the current source snapshot.
