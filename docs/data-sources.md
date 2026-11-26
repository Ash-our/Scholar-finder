# Scholarship data source register

Assessment date: 26 November 2026. Six active adapters: Finder (224 source listings across12 pages), ScholarPal (28), IEFA (80),4 official university programmes, Scholars4dev (19), and official Amideast (4). The frozen359-record snapshot shows12 verified open,1 upcoming,332 unverified and14 closed at16:15 UTC. Reviewed official-call rules recheck stored programmes directly; their state can change after a real page read. Other sources remain references or planned adapters. The assessment evidence below records the original investigation, not a claim that every source is integrated.

The user supplied six websites and authorized additional useful sources. The register keeps every supplied source, including those unsuitable for direct collection. Remote extraction results may be cached. A separate direct HTTP assessment was made from the local machine where indicated. Public accessibility and a robots allowance do not establish a data reuse license.

## Supplied sources

| Source | Evidence from this assessment | Proposed role |
| --- | --- | --- |
| [ScholarPal for Palestinians](https://scholarpal.io/scholarships-for-palestinians) | Direct HTTP 200; 57 distinct scholarship-detail links found on this page. The content includes funding/degree labels, estimated closing months, and unknown deadlines. Robots allowed the assessed index for the assessment user agent. | Discovery adapter candidate. Preserve estimated/unknown deadlines and follow official links before presenting a deadline as confirmed. |
| [Scholarship Finder](https://scholarship-finder.fly.dev) | Main-page extraction showed a failed/loading catalogue. Following the site's own [low-data page](https://scholarship-finder.fly.dev/lite) succeeded with direct HTTP 200 and 30 distinct `/s/` detail links. It exposes degree, funding, deadline, cycle, and last-checked labels for examples. Robots allowed the assessed low-data page. | Primary pilot candidate using the public low-data index and detail pages, after field parsing and individual detail-path checks. Do not infer the entire catalogue has only 30 entries. |
| [DAAD](https://www.daad.de/en/) | The home page links to scholarship information. The [scholarship database](https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/) returned direct HTTP 200, but no `detail=` links were found in that particular raw response; extracted/search results did expose detail records. Robots on the `www2` host returned 404. A [Palestinian in-country scholarship detail](https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=57652675) describes selected West Bank universities and eligibility. | Official reference and detail-page candidate. Search-result pagination/discovery remains unverified. Country in DAAD's search can mean residence/application origin, not citizenship. |
| [IEFA awards](https://www.iefa.org/scholarships) | Direct HTTP 200; 40 distinct award-detail links on the assessed first page. Extracted index reported 1,565 total items, including older academic cycles. Robots allowed the assessed index. [An example award](https://www.iefa.org/scholarships/3726/MPOWER_MBA_Scholarship) exposes nationality, host countries, requirements, official information, and a month/day deadline without a year. | Primary pilot candidate. Test pagination and details separately; never infer that all indexed awards are open or that a missing deadline year is the current year. |
| [Mastersportal scholarship search](https://www.mastersportal.com/search/scholarships/master) | Remote extraction did not yield a useful scholarship list. The direct HTTP check returned 403 Forbidden. | Keep as a reference-only discovery link. No bypass or dependency on an unconfirmed public API. |
| [Amideast West Bank Facebook](https://www.facebook.com/AMIDEASTWB/) | Remote extraction exposed the page shell, not usable scholarship posts. No Facebook post API or export was confirmed. | Preserve as a supplied reference. Prefer the official Amideast scholarship website below for program information. |

Link counts above describe one directly inspected index response. They are not unique verified scholarship totals or counts of currently open opportunities. Robot checks covered only the assessed target URLs, not every detail/pagination route.

## Official sources added to the plan

| Added source | What it provides | Readiness and limitations |
| --- | --- | --- |
| [Amideast West Bank scholarships](https://www.amideast.org/west-bank/find-a-scholarship) | Official scholarship and exchange categories for Palestinian students, including undergraduate and graduate study. | Direct HTTP 200. Traverse individual program pages and record application cycles and official requirements; this category page is not itself a current award. |
| [Erasmus Mundus catalogue](https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en) | Joint master's programs, participating universities, countries, and links to program sites. [Student guidance](https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters) describes study across multiple institutions. | Direct HTTP 200. The catalogue explicitly warns that some programs may no longer offer Erasmus Mundus scholarships. Verify funding and deadlines on each program website. Suitable for multiple map placements. |
| [Türkiye Scholarships criteria](https://www.turkiyeburslari.gov.tr/scholarshipsprograms) and [program portal](https://www.turkiyeburslari.gov.tr/) | Official degrees, academic thresholds, nationality exceptions, age conditions, and program/university search. | Remote extraction succeeded. Direct local request failed certificate validation, so automated collection is not yet ready. Resolve the trust chain normally; do not disable TLS verification. Do not assume all-country eligibility has no exceptions. |
| [Chevening Palestine](https://www.chevening.org/scholarship/palestine/) | Official Palestine award information and links to eligible UK master's courses. [Eligibility guidance](https://www.chevening.org/resource-hub/guidance/eligibility) includes conditions beyond the proposed five profile fields. | Remote extraction succeeded; the direct local check timed out. Retry conservatively during adapter evaluation. A country-wide award is not a guaranteed scholarship at every UK university. |
| [Bseisu Foundation scholarships](https://www.bseisufoundation.org/scholarships) | Partner university awards relevant to Palestinian, Lebanese, Syrian, and Jordanian applicants. | Official search excerpts were retrieved. [How to apply](https://www.bseisufoundation.org/how-to-apply) says applications go to university/organization partners and conditions vary. Check each partner award, residency condition, and cycle. Direct local collection has not been tested. |
| [Goldsmiths Palestinian Scholarship](https://www.gold.ac.uk/fees-funding/scholarships/palestinian-scholarship/) | A specific official university scholarship with degree, nationality/residence conditions, funding, and an application cycle. | Official search excerpts were retrieved. Useful as a precise university example; openings and deadlines must come from the current official page. Direct local collection has not been tested. |

Amideast is now integrated through individual public programme pages: graduate/undergraduate categories and the SGFP page. Destination mappings were reviewed separately from nationality/residence; SGFP is upcoming forFall2027 with a partial tuition gap, not a fully funded currently open award. The Hope Fund Supplemental explicit2026 closure is retained. The other candidate rows above remain unintegrated unless already present through a distinct discovery adapter. An opportunity's presence on any page does not establish a student's eligibility.

[Scholars4dev](https://www.scholars4dev.com/) was added as a bounded public discovery adapter: two index pages, at most20 detail records, excluding listicles and sponsored rows. The actual run collected19 and published19 acknowledged Kafka events with0 errors. It preserves aggregator provenance and ambiguous or not-yet-announced scholarship deadlines. Admission deadlines are not substituted for scholarship deadlines; regression checks cover Stockholm and Geneva programme pages.

## Geographic reference added to the plan

[ROR](https://ror.readme.io/docs/rest-api) supplies research-organization identities, official websites, and geographic fields. Its [schema](https://ror.readme.io/docs/schema-v2-1) and [data dump documentation](https://ror.readme.io/docs/data-dump) describe the available data and CC0 data dump.

Use it to reconcile university names and countries, with source attribution stored in the enrichment record. GeoNames-derived coordinates are city-level references, not evidence of a specific campus building. Unresolved names stay unresolved. Country-wide, multi-country, and online-only scholarships must not receive fabricated campus points.

## Source record rules

- Keep the original listing URL and the official program/application URL separately.
- Store observed/fetched time separately from the source's own last-checked time and an actual official verification time.
- Preserve application year/cycle, original deadline text, date precision, timezone when supplied, and confidence. A historical month/day deadline must not be silently moved into a new year.
- Explicitly distinguish nationality, residence, country of origin in a particular provider's form, and destination.
- Keep unknown GPA, degree, field, nationality, or location fields as unknown. Generic labels such as unrestricted require their original context and any exceptions.
- Preserve source-specific records and conflicts before canonical grouping. Matching titles do not prove identical awards or application cycles.
- The verified-open filter requires recent official evidence for the current cycle, not an aggregator's future deadline alone. The default discovery view includes clearly labeled unverified listings and excludes known closed calls. Preserve rolling application status only when the official source explicitly supports it. Treat evidence older than seven days as stale until rechecked; a source outage does not establish closure.
- Unresolved duplicate candidates may remain visible as unverified listings, but only identity-and-cycle-resolved groups contribute to the confirmed opportunity count.
- A failed source check must not expire or delete opportunities. Track source health independently.
- Activate an automatic adapter only after its public access conditions, list/detail extraction, pagination or coverage bound, official-link provenance, and change detection have been checked. Supported attributed imports/replay remain distinct from live collection.

## Initial collection scope

Start with the low-data Scholarship Finder pages and a bounded IEFA sample, then validate selected official program pages. Add ScholarPal as a discovery source and expand official adapters after the end-to-end path works. Record actual raw and canonical counts at each import.

Test repeated observations, changed deadlines, conflicting source details, unknown deadlines, stale academic cycles, multiple university placements, and source failures. Any generated variants used for testing or scalability evaluation are tagged and counted separately from real scholarships.
