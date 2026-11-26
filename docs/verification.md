# Verification record — 26 November 2026

This file records executed checks. It is not a claim that every environment or every source is supported.

## Map exploration UX and university locations — current verification

- Actual Chrome loaded the supplied Liveuamap reference at1440×1000; reference and final screenshots were inspected. Text-only fetch returned403. Browser plugin skill is unavailable, so installed Playwright Chrome was the fallback. Existing Arabic/purple components were adapted to a map-led layout with compact filters and a right results rail.
- Closing the university chip keeps country and viewport; closing the country chip keeps pan/zoom. Background inside a country clears university only; another country switches/focuses; sea/noninteractive page background clears filters and personalization. Controls/cards/markers do not reset filters. Only the explicit world button resets the view. Known sibling university markers remain visible while one university filters the list.
- Public production Chrome QA at1440×1000 and390×844 passed those transitions after genuine location ingestion. It independently calculates geographic center/zoom from Web Mercator tiles, chooses uncovered actual GB land, switches France/Germany, then resets in the North Sea. It waits for Leaflet's actual zoom transition. No console/pageerrors or horizontal/page-height overflow. Independent checks also passed770/820px, mobile university selection, profile/storage reset and toolbar retention.
- The requested provenance section is removed from ScholarshipDetail; original/official links and useful card addition times remain. Six frontend tests pass, including real polygon semantics for another/current country, ocean, holes, islands and shared borders. TypeScript/Vite build passes. A Windows file lock caused one dist-clean failure; `npm run build -- --emptyOutDir false` successfully rebuilt without deleting files still being served.
- Independent review found a mobile explanatory overlay trapping cluster taps. Noninteractive note/heading/toolbar gaps now pass pointer events through; buttons stay interactive. The failing flow was rechecked. Mobile controls use labeled icons and chip-close tap targets are larger.
- University coverage/provenance and unresolved cases are in `university-locations.md`.118 acknowledged location-update Kafka events were processed by real Spark; immutable addition times and all unrelated current source fields were verified unchanged. A later real source refresh exposed broad-name recollection; final resolver tests/evidence are recorded below.

### Visual fidelity ledger

Final backend evidence: **83 tests passed,1 opt-in wrapper skipped** with real Mongo enabled;28 enrichment tests cover exact multi-host resolution, country/city constraints, raw-record recollection, pinned identities, ambiguity and partial pagination. All359 enriched records are idempotent; all103 baseline records remap from empty placements with zero coordinate mismatches. Tokyo's complete106-result search used5 additional real page requests; incomplete CLI results return exit1 in a direct offline contract check. Both American University and Tokyo recovery events were acknowledged and processed; final221 mapped listings/239 institution locations restored. Current snapshot/physical SHA and changing live counters are in `data/catalogue-manifest.json`. Collector-only reload retained Kafka/Spark/Mongo/API and existing checkpoints. No new hosting account or fixed-domain setup was created after the user canceled that request; existing Pinggy preview remains in use.

| Comparison | Reference/render evidence and result |
| --- | --- |
| Layout | Reference map~1044px/results~396px; implementation1050px map/390px right rail at1440. Map is full bleed, result list scrolls independently, controls compact. |
| Copy/task | Former visible intro is a screen-reader heading. Existing Arabic navigation/filter meanings remain; provenance removal was explicitly requested. No extra promotional sections. |
| Typography | IBM Plex Sans Arabic retained; deliberate compact control sizes,15px result titles and secondary metadata inspected on desktop/mobile. |
| Palette/assets | White/purple identity and actual OSM tiles retained. Reference conflict imagery/red symbols are intentionally excluded; country tags stay geographically anchored. |
| Selection | Selected-only purple border, real city locations, independent chips and actual list filtering verified. |
| Responsive | Available-viewport map, collapsible mobile filters, one-row labeled icon controls, no body overflow at390/770/820/1440 widths; noninteractive overlays do not block markers. |

External artifacts: `liveuamap-reference.png`, `ux-desktop.png`, `ux-mobile-country.png`, `ux-qa.json` in the visualization directory below. Visual and functional validation were separate. This is a scholarship adaptation of the reference structure, with its own content and identity.

## Earlier country tags, streaming visibility and public preview (historical)

- Latest user correction implemented: country count tags remain at the attributed country coordinates; no country polygon overlays appear before selection. Nearby labels are revealed with zoom rather than moved away from their countries. Selecting a tag zooms to the real geometry, draws only that country's purple outline, and displays known university/city placements. Returning to all countries removes the overlay and restores tags.
- Frozen snapshot at16:15 UTC: **359 real source listings** (Finder224, IEFA80, ScholarPal28, official4, Scholars4dev19, Amideast4). Default discovery: **345 across73 mapped countries**,12 verified open,1 upcoming,332 unverified;14 closed excluded. Source listings are not all distinct verified awards. Snapshot SHA-256 is recorded and calculated from the actual JSONL file bytes.
- New-source real collection published19 Scholars4dev and4 Amideast records through Kafka. Nine additional real ROR location updates were processed. Amideast host-country/residence separation, explicit Hope Fund2026 closure, scholarship-vs-admission deadlines and SGFP upcoming partial funding have regression coverage. A later official CURE fetch returned500; its old evidence was not refreshed and the current count conservatively shows12 open.
- `added_at` is server-owned and immutable on updates/retries. Legacy values come from actual ingestion audit times, with missing audit history left unknown. Tests cover null first-stream timestamps, ordering and metadata exclusion from content hashes. Recent-event API exposes bounded live/replay history with actual observed/processed times and Kafka transport offsets. Real Spark and collector heartbeat checks distinguish active processing/scheduling from stale saved state.
- At the final browser observation,484 unique live events were stored,52 imported events were separate, and invalid live records were0. The collection started16:07 UTC and finished16:14 UTC; the next persisted run was22:07 UTC (00:07 Palestine on27 November), dependent on the computer/services remaining running. These are observations, not UI constants.
- Fresh executed checks: **55 Python tests passed,1 opt-in wrapper skipped** with real Mongo enabled; **4 frontend tests passed**; TypeScript/Vite production build passed after the final tag-position correction. PowerShell syntax checks and `pip check` passed. The original full streaming scenario evidence below remains valid; it was not rerun for this UI change.
- Real Chrome desktop1440×1050 and mobile390×844 QA passed on the production app and through the public Pinggy HTTPS URL. The test clicked the provider's first-visit Enter site button normally. It covered tags/no initial overlays, mouse tag selection, selected-only purple boundary and zoom, UK university clustering/selection, list filtering, actual addition/detail timestamps, return to all countries, real Kafka offsets and processor heartbeat, with0 captured console/page errors and no horizontal overflow. Final desktop, selected-mobile and live-feed screenshots were visually inspected. The QA JSON and screenshots remain outside product source in the visualization directory listed below.
- Pinggy public health matched `application=scholarship-map`; the full public browser flow passed. Free sessions expire after60 minutes. The actual session started16:22 UTC; the command can create a new URL after expiry. Cloudflare provisioning failed with timeout/503/429; localhost.run health worked but bandwidth throttling prevented reliable full-page loading and its domain rotated. These alternatives are not presented as stable deployments. Start/stop/provider-switch scripts were independently reviewed; localhost.run stop/restart was exercised before switching to Pinggy.
- Independent final read-only review found no remaining material issues in the country-tag correction or preview start/stop handling. Earlier findings about stale collector schedules, Amideast destinations and tracked tunnel shutdown were corrected and rechecked. Docker's frontend stage now copies the country-reference JSON at the import's expected path; Docker remains unexecuted on this host.

## Earlier catalogue expansion (historical)

The first delivered catalogue was too limited for useful discovery. Default discovery and real collection were expanded; the original implementation evidence below is retained as historical evidence.

- Current frozen snapshot: **336 real listings** (Finder224, IEFA80, ScholarPal28, official programmes4). Default API/UI: **325 listings across72 mapped countries**, with13 verified-open and312 unverified;11 known closed calls excluded.
- Real Finder collection traversed12 current pages. Real IEFA pagination used the observed `pager-next` markup and collected80 records with0 errors. Repeated unchanged observations did not duplicate the catalogue.
- Direct official verification published13 successfully rechecked records with0 errors in the final verification run. Title/cycle/deadline guards and official proof patterns are documented in `docs/official-verification.md`.
- Frozen snapshot and SHA-256: `data/catalogue-manifest.json`. At its observation time the live event counter was406; imported events were separate, invalid live records0. These counts can change during further scheduled collection.
- Fresh Python suite: **46 passed,1 opt-in scenario wrapper skipped** (real Mongo tests enabled). Frontend: **4 tests passed**; TypeScript/Vite production build passed. PowerShell scripts parsed successfully.
- Expanded production Chrome QA passed at1440×1000 and390×844:30 cards per page, next/previous pagination, official detail link, country/status/empty filters, profile submission/reset, global preference and custom GPA basis,13 source rows, current-filter Spark insights, low-zoom regional cluster expansion, marker selection, no horizontal overflow and0 captured console/page errors.
- Spark SQL batch completed on336 stored records and materialized the full snapshot;5 near-duplicate candidates were recorded without automatic merging. The original MinHash benchmark remains the original frozen50-record experiment.
- Independent read-only review reported no material findings in the expansion;14 focused tests passed. A follow-up verified regional-cluster deduplication/selection and the real IEFA pager selector (2 map and3 source tests passed).

## Initial implementation evidence (historical)

## Environment and dependency evidence

- Windows, Python 3.13.5 for the final local launcher, Node 24.19, npm11.16.
- Java21.0.13, Kafka3.9.1, MongoDB8.0.38, PySpark4.0.3, MongoDB Spark Connector11.1.0.
- Portable services are under ignored `.runtime`; no Docker/WSL engine was installed on the host.
- `python -m pip check`: no broken requirements.
- PowerShell AST parsing: all `.ps1` scripts parsed successfully.
- PySpark4.0.3 Python3.13 worker probe: real parallelized Python map returned `[2,4,6]`, exit0. Initial Spark4.0.1 failed on Windows workers; upgrading addressed Apache SPARK-53759. `spark_runtime.py` selects the installed pinned Spark instead of an unrelated global `SPARK_HOME`.

## Automated tests and build

| Executed command | Observed result |
| --- | --- |
| `SM_TEST_SERVICES=1 .venv/Scripts/python.exe -m pytest -q` (PowerShell env equivalent) | **40 passed,1 skipped**; includes4 tests against real MongoDB |
| `npm test` in `frontend/` | **3 passed**,2 files |
| `npm run build` in `frontend/` | TypeScript and production Vite build passed |
| `.venv/Scripts/python.exe tests/streaming_scenario.py` | Exit0; report `benchmarks/results/streaming-scenario.json` |
| `.venv-spark/Scripts/python.exe -m scholarship_map.cli benchmark …` | Real Spark evaluation completed;30 measured result rows |
| `Start-Project.ps1`, then `Stop-Project.ps1`, then `Start-Project.ps1` | Launcher, scoped shutdown and restart executed; persisted data retained |

The skipped pytest wrapper is the opt-in full streaming scenario; that scenario was run separately and passed. One third-party Starlette TestClient deprecation warning remains, without failed assertions. Unit and integration tests cover eligibility uncertainty, GPA basis, opening/deadline instants, validation, catalogue/map identity, filters, pagination, source parsing, event identity, idempotency, ordering, cycle preservation and similarity features.

Independent review found three material issues and they were corrected: cycle-specific curation must not overwrite a later source cycle; opening timestamps must retain time and offset; the profile needs all-country preferences and a custom GPA basis. New regression tests failed before the fixes and passed afterward. A follow-up independent read-only review verified the fixes (20 relevant Python tests and2 profile tests passed).

## Real pipeline and data

Two collectors each fetched25 actual records and published acknowledged events to Kafka. Spark processed the initial50 and36 subsequent changed observations, totaling **86 live unique events** as observed before final restart. Normal catalogue: **50 records**; **2 open,44 unverified,4 closed** at that check. Separate explicitly labeled imports were used during development and are excluded from the live event counter.

An unchanged collection run then published0 and skipped25 records from each source. Spark wrote5 five-minute metric documents across sources/event types, with a ten-minute watermark. Normal data had0 invalid events. These are observed counts, not fixed UI constants.

Actual Spark SQL batch read MongoDB, wrote dimensional aggregates and a versioned50-record materialized snapshot, and found1 near-duplicate candidate without merging it. The final local-launcher Python3.13 batch completed successfully as well.

The separate scenario used topic `scholarships.scenario.226cca8644` and database `scholarshipmap_scenario_226cca8644_demo`. Observed result:

- 2 catalogue records, 3 unique events, 1 invalid record quarantined.
- A duplicate did not inflate the catalogue; a newer update was retained.
- A late record remained in the catalogue while 1 row was dropped by the watermark query.
- Real FastAPI reads confirmed stored data.
- Producer-to-storage-and-API latency: **12.846 seconds** for this scenario; not a browser latency guarantee.

The scenario and original benchmark ran using a Python3.12 environment, also pinned to Spark4.0.3. The stable launcher now uses the project `.venv` with Python3.13, validated by the worker probe and real batch run.

## Browser verification

The in-app browser failed to attach; isolated Playwright Chrome was used as the documented fallback. The production website on `http://127.0.0.1:8000/` was exercised at **1440×1000** and **390×844**.

Passed flows: Arabic/RTL, map-first mobile layout, list toggle, open listings, details/official links, country/status filters, empty results, optional profile, Japan preference, custom20-point GPA basis, profile reset,12 source rows, filter-aware materialized insights (44 unverified listings), marker selection, no horizontal page overflow, and no captured browser console/page errors. Screenshots were inspected for desktop, mobile, details and insights.

QA script, JSON and screenshots are outside product source at:

`C:/Users/pc/.codex/visualizations/2026/11/26/01a217db-c5d9-7203-bd36-760cd6cb09df/`

## Boundaries

Docker configuration exists but **image build and Compose startup were not executed**, because the engine is absent. Full-catalog crawling, accounts, notifications and automatic integration of all reference sources were not implemented. No claims of production scale, comprehensive scholarship coverage, isolated LSH memory savings or admission probability are made. Source verification and open status are time-sensitive; consult the actual official page before applying.
