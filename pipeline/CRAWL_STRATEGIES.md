# Scout Strategies

## 1. One Scout, multiple bounded strategies

Scout is agentic because it adapts how it searches to the municipality it encounters.

There is no universal crawl plan.

Reconnaissance produces a typed `ScoutStrategy` that selects one bounded acquisition mode.

## 2. Strategy families

### broad_small_site

Best for:

- tiny municipalities
- low page counts
- weak information architecture
- services embedded across general administration pages

Behavior:

```text
official domain
→ bounded broad exploration
→ classify service-bearing pages
→ retain official resources
→ stop when queue/budget exhausted
```

Primary question:

> Is broad discovery cheaper and more complete than complex planning?

### service_directory

Best for:

- structured service catalogues
- i-web-like `/dienstleistungen/` patterns
- mature municipal online counters
- predictable repeated service templates

Behavior:

```text
service directory
→ enumerate service links
→ inspect representative/detail pages
→ retain forms/PDFs/handoffs
→ compile reusable structural hints
```

Primary question:

> Can one discovered structure cheaply cover many services?

### targeted_large_city

Best for:

- very large city websites
- many departments
- mature portals
- high branching factor

Behavior:

```text
Service Index
→ search/discover high-value roots
→ inspect only relevant sections
→ avoid whole-site crawl
```

Primary question:

> Can Scout find indexed services without crawling the city?

### mixed_content

Best for:

- small sites mixing municipality and tourism/community content
- associations, hotels, events and local commerce living near official pages

Behavior:

```text
bounded broad discovery
+ aggressive authority/service classification
+ municipal source filtering
```

Primary question:

> Can Scout retain municipal capabilities without turning into a generic local-content crawler?

### custom

Typed escape hatch for unusual structures.

A custom strategy still requires:

- explicit reason
- roots
- budgets
- allowed domains
- stop conditions

It is not permission for unconstrained browsing.

## 3. Fetch tiers

The scouting strategy is separate from the fetch mechanism.

```text
HTTP
  ↓ insufficient
HEADLESS_BROWSER
  ↓ genuine interaction required
INTERACTIVE_BROWSER
```

Default to HTTP.

Every escalation records a reason.

## 4. Targeted follow-up

Scout does not stop after the first candidate page when the source bundle is clearly incomplete.

Example:

```text
found:
✓ waste service page

linked:
? calendar PDF
? recycling point page
? regional operator

Scout may issue a bounded follow-up
because those sources change how the service is handled.
```

Follow-ups should answer a specific unresolved question.

Examples:

- missing primary source
- unclear handling type
- external handoff boundary
- possible live feed/API
- service/index match ambiguity

## 5. Service Index-aware planning

The Service Index is part of the scouting plan.

For a large municipality:

```text
indexed services
→ targeted discovery queries/roots
→ unresolved-service queue
```

For a tiny municipality:

```text
broad crawl
→ classify discovered capabilities
→ compare against Service Index
```

The same index supports different strategies.

## 6. Language-aware planning

Keep distinct:

- administrative language
- population language
- website language
- source language

Language metadata guides scouting but does not prove a service exists in that language.

Perfect multilingual equivalence is not a prerequisite for Scout MVP; preserve original labels and source URLs.

## 7. Stop rules

Scout stops because deterministic conditions are met, not because the model “feels done.”

Possible conditions:

- request/page budget reached
- queue exhausted
- service directory exhausted
- unresolved indexed-service budget exhausted
- repeated-content threshold reached
- remaining candidate links scored below threshold
- target roots exhausted
- external-domain boundary reached
- time budget reached

Every run records its stop reason.

## 8. Site knowledge

Successful runs may preserve reusable structural hints:

- known service-directory root
- useful selectors
- exclusion patterns
- language routes
- CMS signature
- portal transition patterns

These hints can improve future reconnaissance.

They never replace current-source provenance.

## 9. Example strategy expectations

```text
Binn
→ broad_small_site

Dübendorf
→ service_directory

Zürich
→ targeted_large_city

Bosco/Gurin
→ mixed_content
```

The benchmark is successful when Scout actually behaves differently, not merely when four strategy labels are emitted.
