from datetime import timedelta

import pytest
from pydantic import ValidationError

from scholarship_map.models import Profile, Scholarship
from scholarship_map.matching import recommend
from scholarship_map.catalog import application_state, map_groups


def profile(**changes):
    return Profile(**({"nationality": "PS", "gpa": 85, "gpa_scale": 100,
        "field": "engineering", "degree": "master", "preferred_countries": ["DE"]} | changes))


def test_known_ineligible_nationality_is_excluded(award_data):
    result = recommend(Scholarship(**award_data), profile(nationality="CA"))
    assert result.compatible is False
    assert any("الجنسية" in reason for reason in result.excluded_reasons)


def test_gpa_exact_boundary_passes(award_data):
    assert recommend(Scholarship(**award_data), profile(gpa=80)).compatible
    assert not recommend(Scholarship(**award_data), profile(gpa=79.9)).compatible


def test_gpa_scale_is_not_converted_linearly(award_data):
    result = recommend(Scholarship(**award_data), profile(gpa=3.9, gpa_scale=4))
    assert result.compatible
    assert any("مقياس" in reason for reason in result.uncertainties)


def test_unknown_nationality_is_potential_match(award_data):
    result = recommend(Scholarship(**(award_data | {"nationalities": []})), profile())
    assert result.compatible
    assert result.status == "potential"


def test_preferred_country_is_ranking_not_hard_rejection(award_data):
    record = Scholarship(**award_data)
    preferred = recommend(record, profile())
    other = recommend(record, profile(preferred_countries=["GB"]))
    assert other.compatible
    assert preferred.score > other.score


def test_invalid_gpa_and_nationality_rejected():
    with pytest.raises(ValidationError):
        profile(gpa=4.5, gpa_scale=4)
    with pytest.raises(ValidationError):
        profile(nationality="NOT-A-COUNTRY")


def test_aggregator_deadline_does_not_establish_open(award_data, now):
    record = Scholarship(**(award_data | {"official_verified_at": None}))
    assert application_state(record, now) == "unverified"


def test_stale_evidence_does_not_appear_open(award_data, now):
    record = Scholarship(**(award_data | {"official_verified_at": now - timedelta(days=8)}))
    assert application_state(record, now) == "unverified"


def test_future_opening_and_expired_cycle(award_data, now):
    assert application_state(Scholarship(**(award_data | {"opens_at": "2027-01-01"})), now) == "upcoming"
    assert application_state(Scholarship(**(award_data | {"deadline": "2026-11-25"})), now) == "closed"


def test_invalid_timezone_rejected_when_loading_a_record(award_data):
    with pytest.raises(ValidationError):
        Scholarship(**(award_data | {"deadline_timezone": "Unknown/Timezone"}))


def test_opening_timestamp_uses_instant_and_offset(award_data, now):
    record = Scholarship(**(award_data | {"opens_at": "2026-11-26T18:00:00+02:00", "open_evidence": "date_window"}))
    assert application_state(record, now) == "upcoming"
    assert application_state(record, now + timedelta(hours=5)) == "open"


def test_date_window_requires_confirmed_closing_date(award_data, now):
    record = Scholarship(**(award_data | {"opens_at": "2026-09-01", "open_evidence": "date_window", "deadline_confidence": "estimated"}))
    assert application_state(record, now) == "unverified"


def test_multiple_placements_do_not_inflate_opportunity_count(award_data, now):
    record = Scholarship(**(award_data | {"placements": [
        {"id": "a", "name": "City A", "country": "DE", "lat": 52.5, "lon": 13.4,
         "precision": "city", "source_url": "https://example.org/a"},
        {"id": "b", "name": "City B", "country": "DE", "lat": 50.1, "lon": 8.6,
         "precision": "city", "source_url": "https://example.org/b"},
    ]}))
    result = map_groups([record], now)
    assert result["opportunity_count"] == 1
    assert result["placement_count"] == 2
    assert all(group["scholarship_ids"] == [record.id] for group in result["groups"])
