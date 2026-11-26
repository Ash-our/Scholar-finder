# University location coverage

The26 November2026 review attempted named host institutions across all359 stored source listings. ROR v2 supplied real institution identities and city coordinates. Country-wide awards, online study, portals and ambiguous campus choices stay separate from physical study-host points.

| Measure | Before | Reviewed result |
| --- | ---: | ---: |
| Listings with institution locations |103|221|
| Institution placements across listings |103|355|
| Unique institution locations |76|239|
| Distinct city coordinate pairs |66|191|

These totals include closed listings. The default discovery map excludes14 closed calls and applies the user's other filters. Multiple institutions can have the same city coordinate; clusters and spiderfying keep their individual markers available. Coordinates identify institution cities, not verified campus buildings.

The previous collector queried an entire provider string as one organization, stopped when a country marker existed, and rejected empty-country records. The new resolver handles explicit partner lists, reviewed acronym/title aliases and existing placements. It requires an exact unique ROR name/alias with compatible known destination and optional reviewed city/identity constraints.42 previously empty destination lists were filled from explicitly named, uniquely resolved hosts. No nationality, GPA, deadline, funding or official-verification fields were inferred from geography.

`data/institution-locations.json` retains source-title/provider guards and evidence URLs. `data/unresolved-institution-locations.json` lists35 named-host cases involving source identity/destination conflicts, ambiguous names, missing exact ROR matches or campus delivery questions. Some programmes are already partially mapped through their other partners;35 issues do not mean35 entirely unmapped awards.

Independent review corrected NIAS's outdated Wassenaar ROR point (its programme/contact address is Amsterdam), rejected Birzeit's external scholarship portal as a study host, and prevented inferred partner countries from disambiguating an otherwise ambiguous INSTN identity on a second pass. A real subsequent source refresh exposed an incomplete broad search for American University; a guarded direct ROR identity plus exact name/US/Washington checks now preserves its verified location.

Reproduce a read-only enrichment pass:

```powershell
.\.venv\Scripts\python.exe scripts/enrich-universities.py --input .runtime/university-locations/input-before.jsonl --cache-only --output .runtime/university-locations-check
```

The original input, cached ROR lookups,118-record reviewed proposal, repeat comparison and full decision audit remain in ignored runtime storage. Two original-input runs produced byte-identical proposals; enrichment of all359 already enriched records produced0 further changes and0 API requests. Proposal file SHA-256: `535d09c7f50795aeb204b1d58021b8e74e56890b2e110c720c9e14023742fc25` (physical file bytes).

The parent applied **only placements/destination fields** to current Mongo source identities, preserving newer scholarship content.118 acknowledged live Kafka events were processed by real Spark, followed by acknowledged American University and Tokyo recovery events. Stored addition times and all unrelated source fields were verified unchanged. Later genuine source observations continue to update the live catalogue.

Actual recollection exposed the same incomplete name-search issue for Tokyo. The resolver now completes ROR pagination within its request budget and resumes partial cached searches using their original literal query. It never accepts an identity from incomplete results. Tokyo's106 results required5 additional requests to complete6 pages. Fresh replay of all103 baseline mapped records with placements removed recovered all103 with zero coordinate mismatches; a separate independent cache-only replay also passed. Partial cache/network/budget/page-limit conditions are explicit, and the dry-run command returns nonzero for incomplete runs.28 focused enrichment tests pass; the full project suite passes83 tests with1 opt-in wrapper skipped. The managed collector was reloaded with this final implementation.

Primary references: [ROR API](https://ror.readme.io/docs/rest-api), [NIAS contact](https://nias.knaw.nl/contact/), [American University award](https://www.american.edu/admissions/international/egls.cfm), [American University ROR identity](https://ror.org/052w4zt36).
