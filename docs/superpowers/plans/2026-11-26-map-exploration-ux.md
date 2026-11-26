# Map exploration UX implementation plan

**Goal:** Deliver the user's direct interaction corrections and a more useful map-led scholarship explorer, inspired by the inspected Liveuamap screen while retaining the existing Arabic/purple design system.

**Architecture:** Keep filter selection independent from map viewport. Use real country-geometry hit testing for map background clicks, with only the selected boundary rendered. Preserve visible sibling universities when one university filters the list. Enrich explicitly named hosts with ROR evidence and publish genuine location updates through the existing Kafka/Spark path.

**Authorization/spec:** User explicitly requested continued UI/UX implementation, all named university locations, stable viewport on chip removal, country/background click navigation and removal of the provenance section. Empty page/sea means non-interactive background; normal controls/cards must not reset filters. Clear all filters also disables profile personalization, preserving no hidden active restrictions. Country-wide/online/ambiguous hosts must not acquire fabricated campus points.

## Independent deliverables

- [x] University coverage: backend enrichment + real ROR review + regression tests, agent owns enrichment/test/reference/dry-run files only. Parent reviews and publishes proposed updates; preserve immutable addition times.
- [x] Map interaction: geometry hit-test helper + independent point/country tests; map clicks inside current country clear university only, another country switches, sea clears filters. Chip removal preserves zoom/pan; only explicit country focus/world control changes the view. Markers and controls do not bubble into background reset.
- [x] UI: map-led viewport with compact existing header/filters, right results rail and mobile map/list view; independent country/university chips, clear action; remove requested provenance section from details. This is a targeted iteration of existing components/tokens with a supplied functional reference, so no new image-generation design gate is needed.
- [x] Verification: fresh frontend tests/build, backend tests including real Mongo, actual event ingestion of location updates, Chrome desktop/mobile and public preview checks. Verify empty/interactive click boundaries, holes/islands, all filtering levels, pan/zoom retention, sibling markers and metadata removal. Inspect final screenshots against reference structure; document intentional differences (scholarship purple/RTL, no war/feed imagery).

## Files

Frontend: App.tsx, components/ScholarshipMap.tsx, FiltersBar.tsx, ScholarshipDetail.tsx, styles.css, focused map geometry helper/tests. Backend/data enrichment files are exclusively owned by university_locations agent. Parent owns final snapshot/manifests/docs and runtime publishing. No Git repository/commits, no payments or permanent hosting.

## Evidence

Reference: actual Chrome1440×1000 screenshot `liveuamap-reference.png` outside the repository. Web text fetch returned403; normal Chrome loaded200. Browser plugin skill is unavailable, so use installed Playwright Chrome fallback for rendered validation. Existing native Kafka/Spark/Mongo/API services remain the implementation target; Docker is unexecuted on this host.

Final evidence26Nov19:59Palestine:83Pythonpassed/1opt-in skipped with realMongo;6frontendpassed;productionbuildpassed;realpublicChrome1440x1000and390x844fullUXflowpassed/0errors,extra770/820andmobileuni/profilechecks independentlypassed. Enrichment103→221records/76→239locations;118liveupdates+2recoveryeventsprocessed,nonlocationfieldsandaddedtimespreserved.25directidentitytestsbecame28withboundedpagination;all103baselinefreshrawreplay103mapped/0coordinatemismatches. Nativecollectorfinalcodereloaded,other servicesretained. CLIincompletepaginationexitcontractfixedandexercisedexit1. FrozenJSONLphysicalSHA30bb7832677c737e7ab1abced34117477a2d90b042c7d65254efbae5fb56d058. Usercanceledngrokaccount/staticURLrequest;retainexistingPinggypreview.NoGitpublicationorpaidresources.
