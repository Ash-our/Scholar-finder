import json
from pathlib import Path

import httpx
import pytest
from scholarship_map.collectors import enrichment
from scholarship_map.models import Placement, Scholarship


def organization(name, country="DE", identifier="01example", aliases=(), lat=52.5, lon=13.4):
    return {"id": f"https://ror.org/{identifier}", "status": "active",
            "names": [{"value": value, "types": ["ror_display" if i == 0 else "alias"]}
                      for i, value in enumerate((name, *aliases))],
            "locations": [{"geonames_details": {"country_code": country, "lat": lat, "lng": lon}}]}


@pytest.fixture
def ror(tmp_path, monkeypatch):
    monkeypatch.setattr(enrichment, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "countries.json").write_text(json.dumps({"source_url": "https://example.org/geo",
        "countries": {"DE": {"name": "Germany", "lat": 51, "lon": 10},
                      "GB": {"name": "United Kingdom", "lat": 55, "lon": -3}}}), encoding="utf8")
    replies, requests = {}, []

    def get(url, params=None, **kwargs):
        requests.append((url, params))
        query = params["query"].strip('"').replace('\\', '') if params else url.rsplit("/", 1)[-1]
        return httpx.Response(200, json={"items": replies.get(query, [])}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    return tmp_path, replies, requests


def award(award_data, **changes):
    return Scholarship(**(award_data | changes))


def cities(record):
    return [place for place in record.placements if place.precision != "country"]


def test_existing_country_and_city_do_not_prevent_other_hosts(award_data, ror):
    _, replies, _ = ror
    replies["Beta University"] = [organization("Beta University", "GB", "02beta")]
    first = Placement(id="01alpha", name="Alpha University", country="DE", lat=52, lon=13,
                      precision="city", source_url="https://ror.org/01alpha")
    country = Placement(id="country-GB", name="United Kingdom", country="GB", lat=55, lon=-3,
                        precision="country", source_url="https://example.org/geo")
    record = award(award_data, provider="Alpha University; Beta University", countries=["DE", "GB"],
                   placements=[first, country])
    result = enrichment.attach_locations(record, use_ror=True)
    assert first in result.placements and country in result.placements
    assert {place.name for place in cities(result)} == {"Alpha University", "Beta University"}
    assert record.placements == [first, country]


def test_empty_countries_fill_from_explicit_hosts_and_repeat_is_idempotent(award_data, ror):
    _, replies, requests = ror
    replies["Alpha University"] = [organization("Alpha University")]
    replies["Beta University"] = [organization("Beta University", "GB", "02beta")]
    record = award(award_data, provider="Alpha University, Beta University", countries=[])
    result = enrichment.attach_locations(record, use_ror=True)
    assert result.countries == ["DE", "GB"]
    assert {place.country for place in cities(result)} == {"DE", "GB"}
    request_count = len(requests)
    assert enrichment.attach_locations(result, use_ror=True) == result
    assert len(requests) == request_count


def test_and_list_but_not_and_within_one_name(award_data, ror):
    _, replies, _ = ror
    replies["Alpha University"] = [organization("Alpha University")]
    replies["Institute of Science and Technology"] = [organization("Institute of Science and Technology",
                                                                         identifier="02beta")]
    record = award(award_data, provider="Alpha University and Institute of Science and Technology")
    assert len(cities(enrichment.attach_locations(record, use_ror=True))) == 2


def test_institution_in_title_when_provider_empty(award_data, ror):
    _, replies, _ = ror
    replies["Alpha University"] = [organization("Alpha University")]
    record = award(award_data, provider="", title="Alpha University – Excellence Scholarships")
    assert [place.name for place in cities(enrichment.attach_locations(record, use_ror=True))] == ["Alpha University"]


def test_reviewed_alias_requires_evidence_and_honors_destination(award_data, ror):
    root, replies, _ = ror
    (root / "data" / "institution-locations.json").write_text(json.dumps({"aliases": {
        "AUni": {"name": "Alpha University", "evidence_url": "https://alpha.example/about"}}}), encoding="utf8")
    replies["Alpha University"] = [organization("Alpha University")]
    assert len(cities(enrichment.attach_locations(award(award_data, provider="AUni"), use_ror=True))) == 1
    assert not cities(enrichment.attach_locations(award(award_data, provider="AUni", countries=["GB"]), use_ror=True))


@pytest.mark.parametrize("items", [
    [organization("Alpha University of Applied Sciences")],
    [organization("Alpha University"), organization("Alpha University", identifier="02other")],
    [organization("Alpha University", "GB")],
])
def test_fuzzy_ambiguous_or_country_mismatched_results_stay_unlocated(award_data, ror, items):
    _, replies, _ = ror
    replies["Alpha University"] = items
    result = enrichment.attach_locations(award(award_data, provider="Alpha University"), use_ror=True)
    assert not cities(result)


def test_online_university_never_uses_headquarters(award_data, ror):
    _, replies, requests = ror
    replies["University of the People"] = [organization("University of the People", "US")]
    result = enrichment.attach_locations(award(award_data, provider="University of the People", countries=[]),
                                         use_ror=True)
    assert result.countries == [] and result.placements == []
    assert requests == []


def test_unspecified_universities_and_administrator_title_are_not_hosts(award_data, ror):
    _, replies, requests = ror
    replies["ETH Zurich"] = [organization("ETH Zurich", "CH")]
    record = award(award_data, provider="A suitable academic host institution selected by the applicant",
                   title="Branco Weiss Fellowship (Society in Science, ETH Zurich)", countries=[])
    assert not cities(enrichment.attach_locations(record, use_ror=True))
    assert requests == []


def test_specific_campus_not_silently_replaced_with_headquarters(award_data, ror):
    _, replies, _ = ror
    replies["Luiss Business School"] = [organization("Luiss Business School", "IT")]
    result = enrichment.attach_locations(award(award_data, provider="Luiss Business School in Amsterdam",
                                               countries=["NL"]), use_ror=True)
    assert not cities(result)


def test_failed_request_does_not_poison_cache(award_data, ror, monkeypatch):
    root, _, _ = ror
    def fail(*args, **kwargs):
        raise httpx.ConnectError("temporary outage")
    monkeypatch.setattr(httpx, "get", fail)
    result = enrichment.attach_locations(award(award_data, provider="Alpha University"), use_ror=True)
    assert not cities(result)
    cache = root / ".runtime" / "ror-institutions-v2.json"
    assert not cache.exists() or not json.loads(cache.read_text(encoding="utf8"))


def test_named_campus_is_not_dropped_from_provider(award_data, ror):
    _, replies, requests = ror
    replies["Alpha University"] = [organization("Alpha University")]
    result = enrichment.attach_locations(award(award_data, provider="Alpha University, Metropolitan campus"),
                                         use_ror=True)
    assert not cities(result) and requests == []


def test_comma_within_university_name_does_not_resolve_parent_administration(award_data, ror):
    _, replies, _ = ror
    replies["University of London"] = [organization("University of London", "GB")]
    record = award(award_data, provider="Royal Holloway, University of London", countries=["GB"])
    assert not cities(enrichment.attach_locations(record, use_ror=True))


def test_reviewed_record_cannot_leak_to_changed_source_title(award_data, ror):
    root, replies, _ = ror
    (root / "data" / "institution-locations.json").write_text(json.dumps({"records": {
        award_data["id"]: {"match": {"title": "Old award title"},
                           "evidence_url": "https://alpha.example/old", "hosts": ["Alpha University"]}}}),
                           encoding="utf8")
    replies["Alpha University"] = [organization("Alpha University")]
    record = award(award_data, provider="Foundation")
    assert not cities(enrichment.attach_locations(record, use_ror=True))


def test_reviewed_city_constraint_does_not_use_other_campus(award_data, ror):
    root, replies, _ = ror
    (root / "data" / "institution-locations.json").write_text(json.dumps({"records": {
        award_data["id"]: {"match": {"provider": "Alpha University Amsterdam campus"},
            "evidence_url": "https://alpha.example/programme", "hosts": [{"name": "Alpha University",
                                                                          "city": "Amsterdam"}]}}}), encoding="utf8")
    replies["Alpha University"] = [organization("Alpha University")]
    result = enrichment.attach_locations(award(award_data, provider="Alpha University Amsterdam campus"), use_ror=True)
    assert not cities(result)


def test_cache_only_reports_missing_evidence_without_http(award_data, ror):
    root, _, requests = ror
    resolver = enrichment.LocationEnricher(root, allow_network=False)
    result, audit = resolver.enrich(award(award_data, provider="Alpha University"))
    assert not cities(result) and requests == []
    assert audit[0]["reason"] == "cache_miss"


def test_nias_current_amsterdam_fellowship_rejects_old_wassenaar_ror_point(award_data, ror):
    root, replies, _ = ror
    references = json.loads((Path(__file__).resolve().parents[1] / "data" / "institution-locations.json")
                            .read_text(encoding="utf8"))
    (root / "data" / "institution-locations.json").write_text(json.dumps(references), encoding="utf8")
    name = "Netherlands Institute for Advanced Study in the Humanities and Social Sciences"
    stale = organization(name, "NL", "04z3wz653", lat=52.14583, lon=4.40278)
    stale["locations"][0]["geonames_details"]["name"] = "Wassenaar"
    replies[name] = [stale]
    record = award(award_data, id="finder-2164", provider="Netherlands Institute for Advanced Study (NIAS-KNAW)",
                   title="NIAS Safe Haven Fellowship for Scholars at Risk (first semester 2027-2028)",
                   countries=["NL"])
    result, audit = enrichment.LocationEnricher(root).enrich(record)
    assert not cities(result)
    assert audit[0]["reason"] == "no_compatible_city_coordinates"
    assert audit[0]["required_city"] == "Amsterdam"


def test_birzeit_external_scholarships_portal_is_not_a_study_host(award_data, ror):
    root, replies, requests = ror
    references = json.loads((Path(__file__).resolve().parents[1] / "data" / "institution-locations.json")
                            .read_text(encoding="utf8"))
    (root / "data" / "institution-locations.json").write_text(json.dumps(references), encoding="utf8")
    replies["Birzeit University"] = [organization("Birzeit University", "PS")]
    record = award(award_data, id="scholarpal-06b303eaaa252f9cf169fd66", provider="",
                   title="Birzeit University – External Scholarships Portal", countries=["PS"],
                   description="financial aid and external scholarship matching for Palestinian students")
    result, audit = enrichment.LocationEnricher(root).enrich(record)
    assert not cities(result) and requests == []
    assert audit[0]["reason"] == "scholarship_portal_not_study_host"


def test_inferred_consortium_countries_cannot_disambiguate_instn_on_second_pass(award_data, ror):
    root, replies, _ = ror
    references = json.loads((Path(__file__).resolve().parents[1] / "data" / "institution-locations.json")
                            .read_text(encoding="utf8"))
    (root / "data" / "institution-locations.json").write_text(json.dumps(references), encoding="utf8")
    name = "Institut national des sciences et techniques nucléaires"
    replies[name] = [organization(name, "FR", "05nddf786"), organization(name, "MG", "02other")]
    replies["Aix-Marseille University"] = [organization("Aix-Marseille University", "FR", "01aix")]
    match = references["records"]["finder-2948"]["match"]
    record = award(award_data, id="finder-2948", countries=[], **match)
    resolver = enrichment.LocationEnricher(root)
    first, _ = resolver.enrich(record)
    second, audit = resolver.enrich(first)
    assert first.countries == ["FR"] and len(cities(first)) == 1
    assert second == first
    assert any(d.get("query") == name and d.get("reason") == "ambiguous_ror_identity" for d in audit)


def test_fresh_american_award_recovers_reviewed_identity_without_prior_placements(award_data, ror, monkeypatch):
    root, _, requests = ror
    references = json.loads((Path(__file__).resolve().parents[1] / "data" / "institution-locations.json")
                            .read_text(encoding="utf8"))
    (root / "data" / "institution-locations.json").write_text(json.dumps(references), encoding="utf8")
    org = organization("American University", "US", "052w4zt36", lat=38.89511, lon=-77.03637)
    org["locations"][0]["geonames_details"]["name"] = "Washington"

    def get(url, params=None, **kwargs):
        requests.append((url, params))
        payload = org if url.endswith("/052w4zt36") else {"number_of_results": 100, "items": [org]}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    record = award(award_data, id="scholars4dev-7085", source_id="scholars4dev", provider="American University",
                   title="American University Emerging Global Leader Scholarship", countries=["US"], placements=[])
    result = enrichment.attach_locations(record, use_ror=True)
    assert [(p.id, p.country, p.lat, p.lon) for p in cities(result)] == [
        ("052w4zt36", "US", 38.89511, -77.03637)]
    assert result.model_dump(exclude={"placements"}) == record.model_dump(exclude={"placements"})
    assert requests == [("https://api.ror.org/v2/organizations/052w4zt36", None)]
    assert enrichment.attach_locations(record, use_ror=True) == result
    assert len(requests) == 1


@pytest.mark.parametrize("mismatch", ["name", "country", "city", "identifier"])
def test_reviewed_ror_lookup_still_validates_identity_name_country_and_city(award_data, ror, monkeypatch, mismatch):
    root, _, _ = ror
    references = json.loads((Path(__file__).resolve().parents[1] / "data" / "institution-locations.json")
                            .read_text(encoding="utf8"))
    (root / "data" / "institution-locations.json").write_text(json.dumps(references), encoding="utf8")
    org = organization("American University", "US", "052w4zt36")
    org["locations"][0]["geonames_details"]["name"] = "Washington"
    if mismatch == "name":
        org["names"][0]["value"] = "Unrelated University"
    elif mismatch == "country":
        org["locations"][0]["geonames_details"]["country_code"] = "GB"
    elif mismatch == "city":
        org["locations"][0]["geonames_details"]["name"] = "London"
    else:
        org["id"] = "https://ror.org/000000000"

    def get(url, **kwargs):
        return httpx.Response(200, json=org, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    record = award(award_data, id="scholars4dev-7085", source_id="scholars4dev", provider="American University",
                   title="American University Emerging Global Leader Scholarship", countries=["US"], placements=[])
    assert not cities(enrichment.attach_locations(record, use_ror=True))


def paged_ror(monkeypatch, requests, *, fail_second=False):
    first = [organization(f"Other University {i}", identifier=f"other{i}") for i in range(20)]
    exact = organization("Alpha University")

    def get(url, params=None, **kwargs):
        requests.append((url, params))
        page = params.get("page", 1)
        if page == 2 and fail_second:
            raise httpx.ConnectError("second page unavailable")
        return httpx.Response(200, json={"number_of_results": 21, "items": first if page == 1 else [exact]},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)


def test_exact_ror_match_on_later_page_requires_complete_result_set(award_data, ror, monkeypatch):
    root, _, requests = ror
    paged_ror(monkeypatch, requests)
    resolver = enrichment.LocationEnricher(root, max_requests=2)
    result, _ = resolver.enrich(award(award_data, provider="Alpha University"))
    assert [p.name for p in cities(result)] == ["Alpha University"]
    assert [params.get("page", 1) for _, params in requests] == [1, 2]
    assert resolver.cache["alphauniversity"]["number_of_results"] == 21
    assert len(resolver.cache["alphauniversity"]["items"]) == 21


def test_partial_page_budget_and_cache_only_never_fabricate_certainty(award_data, ror, monkeypatch):
    root, _, requests = ror
    paged_ror(monkeypatch, requests)
    record = award(award_data, provider="Alpha University")
    result, audit = enrichment.LocationEnricher(root, max_requests=1).enrich(record)
    assert not cities(result)
    assert audit[0]["reason"] == "incomplete_search_request_budget_exhausted"
    result, audit = enrichment.LocationEnricher(root, allow_network=False).enrich(record)
    assert not cities(result) and len(requests) == 1
    assert audit[0]["reason"] == "incomplete_search_cache_only"
    # A later bounded run resumes from the cached first page, using exactly one request.
    result, _ = enrichment.LocationEnricher(root, max_requests=1).enrich(record)
    assert len(cities(result)) == 1 and len(requests) == 2


def test_partial_page_failure_is_preserved_and_retried(award_data, ror, monkeypatch):
    root, _, requests = ror
    paged_ror(monkeypatch, requests, fail_second=True)
    resolver = enrichment.LocationEnricher(root, max_requests=2)
    result, audit = resolver.enrich(award(award_data, provider="Alpha University"))
    assert not cities(result) and resolver.failures
    assert audit[0]["reason"] == "incomplete_search_request_failed"
    assert len(resolver.cache["alphauniversity"]["items"]) == 20
    paged_ror(monkeypatch, requests)
    result, _ = enrichment.LocationEnricher(root, max_requests=1).enrich(
        award(award_data, provider="The Alpha University"))
    assert len(cities(result)) == 1
    assert requests[-1][1] == {"query": '"Alpha University"', "page": 2}
