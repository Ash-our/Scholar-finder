# Data provenance

`countries.json` contains coarse country reference coordinates from the attributed Google DSPL country sample. These are explicitly country-level map placements, never university/campus locations. University enrichment uses exact ROR name/country matches and labels ROR coordinates as city-level.

Collectors record source URLs, fetch times, source-reported check dates, and uncertainty in each scholarship. `sample.jsonl`, when generated, is an attributed snapshot of actual collected listings, not a synthetic catalogue. Snapshot data is never automatically treated as currently open or as a freshly verified official call.

`curation.json` contains reviewed field corrections by source record ID. An entry that asserts official verification must include the actual official URL, application-cycle identity, timestamp, and verification note. Collector reads do not refresh that timestamp. Do not add invented awards, GPA requirements, dates, or university coordinates.

Each correction has an explicit `_match` guard for the reviewed source cycle, title and deadline. A later call or changed source deadline bypasses the old correction and requires fresh review; do not remove that guard just to preserve a green open-status label.

Research HTML is kept only in ignored `.runtime/research`; tracked parser fixtures are reduced structural examples under `tests/fixtures`.

Expanded snapshot: `catalogue-manifest.json` records its actual source/status counts, observation time and SHA-256. `official-programmes.json` supplies reviewed discovery seeds; `verification-rules.json` pins current-cycle proof patterns for direct official rechecks. A configured seed is not itself an open-status assertion. Raw expansion/proof assessments are retained only under ignored `.runtime/expansion`.

IEFA source: https://www.iefa.org/scholarships and https://www.iefa.org/terms. Its pages retain their provider's copyright; this educational project stores bounded factual metadata, source references and short eligibility context, not a mirrored website. Do not publish source content without checking the applicable reuse terms.

Scholarships for Ghazza Initiative: https://scholarship-finder.fly.dev/lite. Preserve official links and the difference between their last-check time and our fetch time.

Geographic reference: https://raw.githubusercontent.com/google/dspl/master/samples/google/canonical/countries.csv and https://ror.readme.io/docs/rest-api.

Country polygons: Natural Earth v5.1.2, 1:50m administrative countries, public domain: https://www.naturalearthdata.com/about/terms-of-use/. `country-boundaries-provenance.json` records source/output SHA-256 values. The bundled frontend asset simplifies rings at 0.025 degrees and rounds to four decimal places; boundaries are approximate reference shapes, not a legal assertion.

`host-institutions.json` contains reviewed source-record-to-host aliases, preserving each original provider name. Nine actual ROR enrichment updates added city-level placements for Oxford, Saarland, EPFL, ETH Zurich and Geneva Academy records. Unknown universities remain unknown.

The later university-location pass uses `institution-locations.json` for guarded host lists/aliases and exceptions, and exact ROR v2 identities/country/city checks. It expands76 to239 institution locations across221 listings, with191 distinct city coordinate pairs. Multiple institutions can share a city point; the map clusters/spiderfies them. `unresolved-institution-locations.json` records35 named-host issues separately from generic country-wide or online programmes. NIAS's old Wassenaar point is excluded because the actual programme is in Amsterdam; the Birzeit external-scholarship portal is not assigned as its awards' study host. American University's source refresh has a guarded direct ROR identity check to retain its Washington location. The frozen input, cache, proposals and publication audit remain under ignored `.runtime/university-locations`; the current snapshot/manifests contain actual stored data. See `docs/university-locations.md`.

The 26 November 18:15 Palestine snapshot contains359 actual source listings, including19 from Scholars4dev and4 from official Amideast pages. Scholars4dev is an aggregator, not official verification. Amideast residence/descent eligibility is kept distinct from study destination; SGFP is an upcoming partial-funding programme. Hope Fund Supplemental's explicit20 June2026 closure is preserved. `added_at` and `first_streamed_at` come from server processing/audit history, not the source's fetch or publication date.
