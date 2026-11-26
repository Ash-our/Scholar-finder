from scholarship_map.collectors.scholars4dev import parse_detail
from scholarship_map.collectors.amideast import parse_detail as parse_amideast
from scholarship_map.catalog import application_state


def test_scholarship_deadline_not_admission_deadline(now):
    html='''<div class="band-in"><h1>Stockholm scholarships</h1></div><dl class="facts">
    <div><dt>Offered by</dt><dd>Stockholm University</dd></div><div><dt>Degree</dt><dd>Masters Degree</dd></div>
    <div><dt>Study in</dt><dd>Sweden</dd></div><div><dt>Annual deadline</dt><dd>15 Jan 2027</dd></div></dl>
    <main><article class="entry-scholarship post-123"><p><strong>Application instructions:</strong></p>
    <p>Apply for admission by 15 January 2027. The 2027 scholarship deadline has not been announced yet.</p>
    <p><strong>Scholarship value/duration:</strong></p><p>Tuition fees only. Living costs are not included.</p></article></main>'''
    record=parse_detail(html,"https://www.scholars4dev.com/stockholm",now)
    assert record.deadline is None and record.deadline_confidence=="unknown"
    assert record.official_verified_at is None
    assert record.countries==["SE"]


def test_future_amideast_round_is_upcoming_and_partial(now):
    html='''<main id="content"><h1>SGFP - Sousou Graduate Fellows Program</h1><div class="field--name-body">
    Supports master's and PhD study in the United States and United Kingdom for Fall 2027.
    It covers the remaining tuition gap. Palestinian identity or descent is required.
    Opens: January 15, 2027 Closes: April 15, 2027</div></main>'''
    record=parse_amideast(html,"https://www.amideast.org/sgfp",now)
    assert record.funding=="partial"
    assert record.nationalities==[]  # Descent is not citizenship.
    assert record.countries==["GB","US"]
    assert record.degrees==["master","phd"]
    assert application_state(record,now)=="upcoming"


def test_amideast_origin_does_not_become_study_destination(now):
    html='''<main id="content"><h1>Ireland-Palestine Scholarship Programme</h1>
    <div class="field--name-body">Palestinian students living in Palestine may study a one-year master's degree in Ireland.</div></main>'''
    record=parse_amideast(html,"https://www.amideast.org/ireland-palestine",now)
    assert record.countries==["IE"]


def test_explicit_amideast_past_closure_is_not_a_discovery_candidate(now):
    html='''<main id="content"><h1>Hope Fund - Supplemental</h1><div class="field--name-body">
    Palestinian students study in the United States. Application closed on June 20, 2026.</div></main>'''
    record=parse_amideast(html,"https://www.amideast.org/hope-fund-supplemental",now)
    assert application_state(record,now)=="closed"
    assert record.deadline=="2026-06-20"
