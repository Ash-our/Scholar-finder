"""Prepare reviewed location updates. This script never publishes or writes Mongo.

Run with the project's Python environment from any working directory. A second
run with --cache-only must produce the same proposal, with zero API requests.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from scholarship_map.collectors.enrichment import LocationEnricher
from scholarship_map.models import Scholarship


def coverage(records):
    mapped = [r for r in records if any(p.precision != "country" for p in r.placements)]
    locations = {(p.source_url, p.lat, p.lon) for r in records for p in r.placements if p.precision != "country"}
    return {"records": len(records), "records_with_institution_locations": len(mapped),
            "records_without_institution_locations": len(records) - len(mapped),
            "institution_placements": sum(p.precision != "country" for r in records for p in r.placements),
            "unique_institution_locations": len(locations),
            "unique_city_coordinates": len({(lat, lon) for _, lat, lon in locations})}


def unresolved_named_hosts(unresolved):
    """Separate actual named hosts from donor names and unspecified host lists.

    The complete decision log remains in the report, including programmes whose
    academic subunit lacks a separate ROR identity but whose parent was located.
    """
    named, other = [], []
    named_reasons = {"destination_country_conflict", "source_identity_conflict",
                     "programme_campus_requires_review", "no_compatible_city_coordinates",
                     "ambiguous_ror_identity"}
    non_hosts = re.compile(r"participating|German university|University or college in Taiwan|"
                           r"Japanese (?:universities|language institutions)|Partnering higher|"
                           r"consortium|American Institute for Boys and Men|Midlands Graduate School|"
                           r"CGIAR|College JumpStart", re.IGNORECASE)
    for entry in unresolved:
        decision = entry["decision"]
        query = decision.get("query", entry["provider"] or entry["title"])
        is_named = decision["reason"] in named_reasons or (
            decision["reason"] == "no_exact_ror_name_or_reviewed_alias" and
            re.search(r"universit|institut|istituto|college|school|library|centre|center|bibliothek|"
                      r"fraunhofer|\bIED\b", query, re.IGNORECASE)
            and not non_hosts.search(query))
        # These two subunits have an already-located university parent in the
        # same source listing; do not count them as missing university hosts.
        if query in {"Keough School of Global Affairs", "Harvard Kennedy School"}:
            is_named = False
        compact = {"id": entry["id"], "name": query, "reason": decision["reason"],
                   "evidence_url": decision.get("evidence_url", entry["official_url"] or entry["source_url"])}
        if decision.get("required_city"):
            compact["required_city"] = decision["required_city"]
        (named if is_named else other).append(compact)
    return named, other


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "sample.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime" / "university-locations")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--max-requests", type=int, default=300)
    args = parser.parse_args()
    original = [Scholarship.model_validate_json(line) for line in args.input.read_text("utf8").splitlines() if line]
    enricher = LocationEnricher(ROOT, allow_network=not args.cache_only, max_requests=args.max_requests)
    enriched, changed, audit = [], [], []
    for index, record in enumerate(original):
        result, decisions = enricher.enrich(record)
        enriched.append(result)
        is_changed = result != record
        if is_changed:
            changed.append(result)
        audit.append({"id": record.id, "title": record.title, "provider": record.provider,
                      "source_url": record.source_url, "official_url": record.official_url,
                      "countries_before": record.countries, "countries_after": result.countries,
                      "changed": is_changed, "decisions": decisions,
                      "added_placements": [p.model_dump() for p in result.placements if p not in record.placements]})
        if (index + 1) % 25 == 0:
            print(f"Processed {index + 1}/{len(original)}; API requests {enricher.requests}; changed {len(changed)}",
                  flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    proposal = "".join(r.model_dump_json() + "\n" for r in changed)
    proposal_path = args.output / "proposed.jsonl"
    proposal_path.write_text(proposal, encoding="utf8")
    (args.output / "enriched-all.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in enriched), encoding="utf8")
    unresolved = [entry | {"decision": decision} for entry in audit for decision in entry["decisions"]
                  if decision["status"] == "unresolved"]
    reasons = dict(Counter(item["decision"]["reason"] for item in unresolved))
    named_hosts, non_specific_hosts = unresolved_named_hosts(unresolved)
    report = {"input": str(args.input.resolve()), "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
              "proposal_sha256": hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
              "changed_records": len(changed), "before": coverage(original), "after": coverage(enriched),
              "api_requests": enricher.requests, "cache_hits": enricher.cache_hits, "cache_only": args.cache_only,
              "ror_cache_query_count": len(enricher.cache),
              "unresolved_named_institutions": named_hosts,
              "generic_online_non_host_or_located_parent": non_specific_hosts,
              "unresolved_reasons": reasons, "request_failures": enricher.failures,
              "source_corrections_requiring_review": [x for x in unresolved if x["decision"]["reason"] in {
                  "destination_country_conflict", "source_identity_conflict", "programme_campus_requires_review",
                  "no_compatible_city_coordinates"}],
              "unique_locations": list({(p.source_url, p.lat, p.lon): p.model_dump()
                                        for r in enriched for p in r.placements if p.precision != "country"}.values()),
              "records": audit, "unresolved": unresolved}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    (args.output / "unresolved-named.json").write_text(json.dumps(named_hosts, ensure_ascii=False, indent=2),
                                                     encoding="utf8")
    print(json.dumps({k: report[k] for k in ["changed_records", "before", "after", "api_requests", "cache_hits",
                                          "proposal_sha256", "unresolved_reasons"]}, ensure_ascii=False, indent=2))
    return 1 if enricher.failures or any(
        reason in {"cache_miss", "request_budget_exhausted"} or reason.startswith("incomplete_search_")
        for reason in reasons
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
