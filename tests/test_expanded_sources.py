import json

from scholarship_map.collectors import scholarpal
from scholarship_map.collectors.iefa import collect as collect_iefa


def test_scholarpal_public_structured_data_preserves_uncertainty(now):
    html = '''<main><h1>Palestinian Scholarship Programme</h1>
    <p data-testid="detail-institution">Trinity College Dublin</p>
    <div><p>Country</p><p>Ireland</p></div>
    <p data-testid="detail-deadline" data-deadline-state="unconfirmed">Deadline not confirmed</p>
    <a href="https://tcd.ie/">Provider's home page</a>
    <script type="application/ld+json">{"@type":"EducationalOccupationalProgram",
    "name":"Trinity College Dublin — Palestinian Scholarship Programme", "description":"Support for displaced students.",
    "occupationalCategory":"Bachelor's", "offers":{"description":"Fully funded (tuition + living costs)"}}</script></main>'''
    record = scholarpal.parse_detail(html, "https://scholarpal.io/scholarships/trinity-palestinian", now)
    assert record.countries == ["IE"]
    assert record.degrees == ["bachelor"]
    assert record.funding == "full"
    assert record.official_url is None  # A provider home page is not the call.
    assert record.deadline is None
    assert record.official_verified_at is None
    assert record.nationalities == []


def test_iefa_follows_public_pagination_once_and_deduplicates(monkeypatch, now):
    seen = []
    class Client:
        def get(self, url):
            seen.append(url)
            if "page=2" in url:
                return '<a href="/scholarships/100/A">A</a><a href="/scholarships/101/B">B</a><li class="page-item pager-next"><a href="/scholarships?page=1">»</a></li>'
            return '<a href="/scholarships/100/A">A</a><li class="page-item pager-next"><a href="/scholarships?page=2">»</a></li>'
    monkeypatch.setattr("scholarship_map.collectors.iefa.parse_detail", lambda html,url,at: url)
    assert len(collect_iefa(Client(), 2, now)) == 2
    assert sum("/100/" in url for url in seen) == 1
    assert sum("page=2" in url for url in seen) == 1


def test_scholarpal_index_uses_program_urls_not_navigation():
    html = '<script type="application/ld+json">' + json.dumps({"@type":"CollectionPage", "itemListElement":[
        {"url":"https://scholarpal.io/scholarships/award-a"}, {"url":"https://scholarpal.io/scholarships/award-a"}
    ]}) + '</script><a href="/register">Register</a>'
    assert scholarpal.parse_index(html) == ["https://scholarpal.io/scholarships/award-a"]
