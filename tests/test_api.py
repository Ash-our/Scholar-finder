from fastapi.testclient import TestClient

from scholarship_map.api import create_app
from scholarship_map.models import Scholarship


class ReadRepository:
    def __init__(self, records):
        self.items = records

    def records(self, query=None):
        return iter(self.items)

    def get(self, key):
        return next((r for r in self.items if r.id == key), None)

    def ping(self):
        return True

    def source_status(self):
        return []

    def insights(self):
        return None

    def ensure_indexes(self):
        pass


def client_for(records, now):
    return TestClient(create_app(ReadRepository(records), clock=lambda: now))


def test_list_map_and_filters_use_same_ids(award_data, now):
    client = client_for([Scholarship(**award_data)], now)
    result = client.get("/api/scholarships?country=DE&status=open").json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == award_data["id"]
    assert client.get("/api/scholarships?country=GB").json()["total"] == 0
    assert client.get("/api/map?country=GB").json()["groups"] == []


def test_pagination_counts_all_matches(award_data, now):
    records = [Scholarship(**(award_data | {"id": str(i)})) for i in range(3)]
    result = client_for(records, now).get("/api/scholarships?limit=1&offset=1").json()
    assert len(result["items"]) == 1
    assert result["total"] == 3
    assert result["confirmed_count"] == 3


def test_deadlines_sort_by_absolute_time_across_timezones(award_data, now):
    later = Scholarship(**(award_data | {"id": "later", "deadline": "2026-12-01T09:00:00-06:00"}))
    earlier = Scholarship(**(award_data | {"id": "earlier", "deadline": "2026-12-01T14:00:00+01:00"}))
    items = client_for([later, earlier], now).get("/api/scholarships").json()["items"]
    assert [item["id"] for item in items] == ["earlier", "later"]


def test_unknown_details_and_invalid_filters(award_data, now):
    client = client_for([Scholarship(**award_data)], now)
    assert client.get("/api/scholarships/missing").status_code == 404
    assert client.get("/api/scholarships?limit=50000").status_code == 422
    assert client.get("/api/scholarships?status=fake").status_code == 422


def test_recommendations_validate_profile_and_explain_results(award_data, now):
    client = client_for([Scholarship(**award_data)], now)
    profile = {"nationality": "PS", "gpa": 85, "gpa_scale": 100,
               "field": "engineering", "degree": "master", "preferred_countries": ["DE"]}
    response = client.post("/api/recommendations", json=profile)
    assert response.status_code == 200
    assert response.json()["items"][0]["match"]["reasons"]
    assert client.post("/api/recommendations", json=profile | {"gpa": 105}).status_code == 422
    assert client.post("/api/recommendations", json=profile | {"nationality": "CA"}).json()["total"] == 0


def test_default_discovery_shows_unverified_and_excludes_closed(award_data, now):
    record = Scholarship(**(award_data | {"official_verified_at": None, "identity_resolved": False}))
    closed = Scholarship(**(award_data | {"id": "closed", "deadline": "2026-11-01"}))
    client = client_for([record, closed], now)
    assert client.get("/api/scholarships").json()["total"] == 1
    assert client.get("/api/scholarships?status=open").json()["total"] == 0
    result = client.get("/api/scholarships?status=unverified").json()
    assert result["total"] == 1
    assert result["confirmed_count"] == 0


def test_discovery_keeps_verified_open_results_before_unknown_deadlines(award_data, now):
    unknown = Scholarship(**(award_data | {"id": "unknown", "official_verified_at": None, "deadline": "2026-12-01"}))
    verified = Scholarship(**award_data)
    result = client_for([unknown, verified], now).get("/api/scholarships").json()
    assert [row["id"] for row in result["items"]] == [verified.id, unknown.id]
    assert result["status_counts"] == {"open": 1, "unverified": 1}


def test_map_area_restricts_results_and_rejects_bad_bounds(award_data, now):
    record = Scholarship(**(award_data | {"placements": [
        {"id": "berlin", "name": "Berlin", "country": "DE", "lat": 52.5, "lon": 13.4,
         "precision": "city", "source_url": "https://example.org/berlin"}
    ]}))
    client = client_for([record], now)
    assert client.get("/api/scholarships?bbox=10,50,15,54").json()["total"] == 1
    assert client.get("/api/scholarships?bbox=-10,40,0,45").json()["total"] == 0
    assert client.get("/api/scholarships?bbox=oops").status_code == 422


def test_country_map_counts_all_awards_and_keeps_selected_country_placements(award_data, now):
    record = Scholarship(**(award_data | {"countries":["DE","NL"],"placements":[
        {"id":"de-uni","name":"University in Germany","country":"DE","lat":51,"lon":10,"precision":"city","source_url":"https://example.org/de"},
        {"id":"nl-uni","name":"University in Netherlands","country":"NL","lat":52,"lon":5,"precision":"city","source_url":"https://example.org/nl"}]}))
    client = client_for([record], now)
    overview=client.get("/api/map").json()
    assert {row["country"]:row["listing_count"] for row in overview["countries"]} == {"DE":1,"NL":1}
    selected=client.get("/api/map?country=DE").json()
    assert {place["country"] for place in selected["groups"]} == {"DE"}


def test_activity_api_returns_real_event_times_and_no_payload(award_data, now):
    class ActivityRepository(ReadRepository):
        def recent_events(self, limit=30):
            return [{"event_id":"event-1","scholarship_id":award_data["id"],"processed_at":now,"observed_at":now,
                     "source_id":"official","title":"Award","mode":"live","event_type":"discovered","applied":True,"transport":{"topic":"scholarships.raw","partition":0,"offset":2}}]
        def stream_status(self):
            return {"processed_events":1,"invalid_events":0,"windows":[],"processor_connected":True}
        def collection_schedule(self):
            return None
    client=TestClient(create_app(ActivityRepository([]), clock=lambda:now))
    result=client.get("/api/stream/activity").json()
    assert result["events"][0]["processed_at"] == now.isoformat()
    assert result["streaming"]["processor_connected"]
    assert "scholarship" not in result["events"][0]


def test_insights_apply_current_filters_to_a_spark_snapshot(award_data, now):
    class SnapshotRepository(ReadRepository):
        def insights(self):
            return {"snapshot_run_id": "test-snapshot", "computed_at": now.isoformat(), "engine": "Spark SQL"}

        def insight_records(self, query, run_id):
            assert run_id == "test-snapshot"
            return iter(self.items)

    records = [Scholarship(**award_data), Scholarship(**(award_data | {"id": "uk", "countries": ["GB"], "degrees": ["bachelor"]}))]
    client = TestClient(create_app(SnapshotRepository(records), clock=lambda: now))
    result = client.get("/api/insights?country=DE").json()
    assert result["ready"]
    assert result["data"]["total_listings"] == 1
    assert result["data"]["by_country"] == [{"country": "DE", "opportunities": 1}]
    profile = {"nationality": "PS", "gpa": 85, "gpa_scale": 100,
               "field": "engineering", "degree": "master", "preferred_countries": []}
    personalized = client.post("/api/personalized-insights", json=profile).json()
    assert personalized["data"]["total_listings"] == 1
