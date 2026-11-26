# Official call verification

The catalogue is a discovery tool. Its default view includes open calls, future calls and explicitly unverified listings, excluding known closed calls. The separate verified-open filter remains available.

`data/verification-rules.json` contains reviewed call-specific evidence rules, not a generic claim that all source results are open. Each rule pins the source title, cycle and deadline, the official URL, and multiple expected phrases about the programme/current window. `collectors/verification.py` reads the official page directly through the same bounded robots-aware HTTPS client, checks the evidence, records the actual read time and a SHA-256 digest, and publishes changes through Kafka. Eligibility fields remain uncertain unless their source supports them.

The collector rechecks configured Finder calls during its six-hour collection cycle. `python -m scholarship_map.cli verify` rechecks stored configured calls without crawling the Finder catalogue again. Four additional official programme seeds are read by the `official` adapter. A seed by itself is not verification; its current official page must be fetched and assessed. All rules/seeds were compared with actual native HTML on26 November2026.

If a page is inaccessible, prior evidence keeps its original date and expires under the normal seven-day rule. If a successful read contradicts the reviewed proof or announces closure, fresh verification is removed. Rolling/automatic programmes have an explicit internal review horizon; it is not a fabricated application deadline. Changed cycles or source deadlines require renewed review before old field corrections can apply.

A checked opening does not establish that a particular student is eligible. Examples include additional residence, admission, gender, age, language, prior-degree and research constraints. The five-field profile cannot establish these conditions.

Important distinctions:

- Maastricht requires the master's admission file before10 December2026, followed by the scholarship application by1 February2027. The earlier prerequisite is retained as the actionable date, and both are explained.
- ETH ESOP closes at11:59AM CET on30 November2026 according to the separately checked official admission-dates page; it is not midnight.
- CURE is for researchers who have completed a PhD, not funding to earn a PhD.
- PARC requires Palestinian PhD students or PhD-qualified researchers and a specified field-research plan.
- Queen Mary awards are capacity-limited; the rolling label does not guarantee that funding remains.
- Reading's programme is automatic consideration, not a separate scholarship application deadline.

The frozen50-record MinHash experiment remains a historical benchmark. Adding real catalogue data does not alter or inflate its original sample size or measured outcomes.
