from pathlib import Path

from scholarship_map.collectors.finder import parse_index
from scholarship_map.collectors.iefa import parse_detail
from scholarship_map.collectors.normalize import parse_deadline, extract_gpa, degrees_in
from scholarship_map.collectors.enrichment import apply_curation
from scholarship_map.models import Scholarship

FIXTURES = Path(__file__).parent / "fixtures"


def test_finder_reads_explicit_fields_without_claiming_official_verification(now):
    records = parse_index((FIXTURES / "finder.html").read_text("utf8"), now)
    assert len(records) == 1
    award = records[0]
    assert award.degrees == ["master"]
    assert award.countries == ["AE"]
    assert award.funding == "full"
    assert award.deadline == "2026-11-30"
    assert award.official_url.startswith("https://gsu.ac.ae/")
    assert award.official_verified_at is None
    assert award.nationalities == []


def test_iefa_does_not_invent_year_or_official_link(now):
    record = parse_detail((FIXTURES / "iefa.html").read_text("utf8"),
                          "https://www.iefa.org/scholarships/3726/MPOWER_MBA_Scholarship", now)
    assert record.countries == ["CA", "US"]
    assert record.nationalities == ["*"]
    assert record.deadline is None
    assert record.deadline_confidence == "recurring"
    assert record.official_url is None
    assert record.degrees == ["master"]


def test_estimated_deadline_and_explicit_grade_scale():
    assert parse_deadline("Usually October (estimated)") == (None, "estimated")
    assert parse_deadline("July 31") == (None, "recurring")
    assert extract_gpa("minimum CGPA 3.0 on a 4.0 scale or equivalent") == (3.0, 4.0)
    assert extract_gpa("GPA 3.0 required") == (None, None)


def test_postdoctoral_is_not_a_funded_phd_degree():
    assert degrees_in("Postdoctoral") == ["postdoc"]
    assert degrees_in("Post-doctoral fellowship") == ["postdoc"]


def test_residence_in_a_country_does_not_become_nationality(now):
    html = (FIXTURES / "finder.html").read_text("utf8").replace("Not specified", "Students residing in Lebanon")
    assert parse_index(html, now)[0].nationalities == []


def test_prior_qualification_is_not_the_funded_degree(now):
    html = (FIXTURES / "iefa.html").read_text("utf8").replace("MPOWER MBA Scholarship", "Research award")
    html = html.replace("A scholarship for full-time MBA students.", "Applicants must hold a master's degree.")
    assert parse_detail(html, "https://www.iefa.org/scholarships/3726/example", now).degrees == []


def test_curation_does_not_override_new_cycle_or_changed_deadline(award_data):
    record = Scholarship(**(award_data | {"id": "finder-5138", "source_id": "finder", "source_record_id": "5138",
        "title": "University of Luxembourg YADIAS Doctoral Fellowships 2027 (Young Academics Doctoral fellows IAS)",
        "cycle": "2027 application cycle", "deadline": "2027-11-30", "identity_resolved": False}))
    assert apply_curation(record) == record
    changed = record.model_copy(update={"cycle": "2026 application cycle", "deadline": "2026-12-15"})
    assert apply_curation(changed) == changed
    reviewed = record.model_copy(update={"cycle": "2026 application cycle", "deadline": "2026-11-30"})
    assert apply_curation(reviewed).deadline == "2026-11-30T14:00:00+01:00"
