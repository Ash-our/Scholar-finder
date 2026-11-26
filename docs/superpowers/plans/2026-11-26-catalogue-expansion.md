# Catalogue expansion correction

User correction: a website showing only two scholarships does not deliver useful global discovery. Implementation remains authorized; no further design approval is required for completing the original outcome.

Root causes: default verified-open filter concealed unverified discovery records, per-source25-record limit truncated Finder's12 public pages, IEFA pagination was missing, and only two source adapters were active. Automated official-call verification was also absent.

Acceptance:

- Default discovery includes open, upcoming and unverified records, excludes closed records, and prioritizes verified open calls. Unknown eligibility/deadlines remain explicitly unknown.
- Collect all available current Finder pages (bounded400), add public ScholarPal collections/details and reviewed official university programmes. Keep source-level limits visible and repeatable.
- Read official call pages live using cycle/title/deadline-specific proof rules; publish changes through Kafka/Spark/Mongo. A failed or changed proof cannot be silently presented as newly verified.
- Preserve the exact-open filter, source/cycle histories, map/list ID agreement, pagination and optional profile behavior.
- Demonstrate at least200 visible real discovery listings and at least10 genuinely checked current open calls; do not fabricate records or promote all unknown calls to open.
- Verify actual API/database counts, new parsers/proof guards, full tests/build and production desktop/mobile flows. Refresh Spark batch insights and document actual final counts.

Files: collectors/{scholarpal,official,verification,runner,iefa}.py; cli.py; source_register.py; api.py; frontend types/labels/defaults/list; data/official-programmes.json and verification-rules.json; launcher limits; tests and operation docs.
