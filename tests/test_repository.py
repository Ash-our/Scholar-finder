import os
from datetime import timedelta
from uuid import uuid4

import pytest

from scholarship_map.events import make_event
from scholarship_map.models import Scholarship
from scholarship_map.repository import MongoRepository
from scholarship_map.settings import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def repo():
    if os.environ.get("SM_TEST_SERVICES") != "1":
        pytest.skip("Set SM_TEST_SERVICES=1 to test a real local MongoDB")
    name = "scholarshipmap_test_" + uuid4().hex
    repository = MongoRepository(Settings(mongo_database=name))
    repository.ensure_indexes()
    yield repository
    repository.client.drop_database(name)  # Only this fixture's newly-created unique database.
    repository.close()


def test_duplicate_events_have_one_record_and_audit_entry(repo, award_data, now):
    event = make_event(Scholarship(**award_data), now)
    assert repo.apply_event(event) == "applied"
    assert repo.apply_event(event) == "duplicate"
    assert len(list(repo.records())) == 1
    assert repo.db.ingest_events.count_documents({}) == 1


def test_out_of_order_event_preserves_newer_record(repo, award_data, now):
    old = make_event(Scholarship(**award_data), now)
    new = make_event(Scholarship(**(award_data | {"title": "New deadline announcement"})),
                     now + timedelta(minutes=1), "updated")
    repo.apply_event(new)
    assert repo.apply_event(old) == "stale"
    assert repo.get(award_data["id"]).title == "New deadline announcement"


def test_retry_after_audit_marker_loss_keeps_data(repo, award_data, now):
    event = make_event(Scholarship(**award_data), now)
    repo.apply_event(event)
    repo.db.ingest_events.delete_one({"_id": event.event_id})
    repo.apply_event(event)
    assert repo.get(award_data["id"]).title == award_data["title"]
    assert repo.db.ingest_events.count_documents({}) == 1


def test_a_new_application_cycle_preserves_the_previous_cycle(repo, award_data, now):
    repo.apply_event(make_event(Scholarship(**award_data), now))
    next_cycle = Scholarship(**(award_data | {"cycle": "2028", "title": "Next cohort award"}))
    repo.apply_event(make_event(next_cycle, now + timedelta(days=1), "updated"))
    assert {record.cycle for record in repo.records()} == {"2027", "2028"}
    assert repo.get(award_data["id"]).title == award_data["title"]


def test_added_time_survives_updates_retries_and_first_live_transition(repo, award_data, now, monkeypatch):
    monkeypatch.setattr("scholarship_map.repository.utcnow", lambda: now)
    original = make_event(Scholarship(**award_data), now, mode="import")
    repo.apply_event(original)
    assert repo.get(award_data["id"]).added_at == now
    assert repo.get(award_data["id"]).first_streamed_at is None
    repo.db.scholarships.update_one({"_id":award_data["id"]},{"$set":{"first_streamed_at":None}})
    later = now + timedelta(minutes=2)
    monkeypatch.setattr("scholarship_map.repository.utcnow", lambda: later)
    updated = make_event(Scholarship(**(award_data | {"title":"Updated call"})), later, "updated")
    repo.apply_event(updated)
    repo.apply_event(updated)
    record = repo.get(award_data["id"])
    assert record.added_at == now
    assert record.updated_at == later
    assert record.first_streamed_at == later
    assert record.last_event_id == updated.event_id


def test_backfill_uses_real_audit_time_instead_of_fetch_time(repo, award_data, now):
    record = Scholarship(**award_data)
    repo.db.scholarships.insert_one({"_id":record.id} | record.model_dump(mode="json"))
    repo.db.ingest_events.insert_one({"scholarship_id":record.id,"processed_at":now + timedelta(minutes=5),
                                    "observed_at":now,"mode":"live","event_type":"discovered","applied":True})
    assert repo.backfill_timestamps() == 1
    assert repo.get(record.id).added_at == now + timedelta(minutes=5)
    assert repo.get(record.id).first_streamed_at == now + timedelta(minutes=5)
