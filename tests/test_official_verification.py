from scholarship_map.collectors.verification import verified_from_html
from scholarship_map.models import Scholarship


def test_verification_requires_current_call_proof_and_source_identity(award_data, now):
    record = Scholarship(**(award_data | {"official_verified_at": None}))
    rule = {"url": record.official_url, "match": {"cycle": "2027", "deadline": "2026-12-14"},
            "patterns": [r"Engineering Masters", r"2027", r"14 December 2026", r"Applications are open"]}
    good = '<main>Engineering Masters 2027. Applications are open. Deadline 14 December 2026.</main>'
    assert verified_from_html(record, rule, good, now).official_verified_at == now
    assert verified_from_html(record, rule, good.replace('2027','2025'), now).official_verified_at is None
    other = record.model_copy(update={"cycle": "2028"})
    assert verified_from_html(other, rule, good, now).official_verified_at is None


def test_official_closure_cannot_reuse_old_open_proof(award_data, now):
    record = Scholarship(**award_data)
    rule = {"url": record.official_url, "match": {"cycle": "2027"}, "patterns": ["2027"]}
    result = verified_from_html(record, rule, '<main>2027. Applications are now closed.</main>', now)
    assert result.official_verified_at is None
    assert result.reported_status == "unknown"
