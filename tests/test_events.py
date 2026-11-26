from datetime import timedelta

from scholarship_map.events import content_hash, make_event, is_newer
from scholarship_map.models import Scholarship


def test_fetch_time_alone_is_not_a_content_change(award_data, now):
    a = Scholarship(**award_data)
    b = Scholarship(**(award_data | {"fetched_at": now + timedelta(hours=6)}))
    assert content_hash(a) == content_hash(b)


def test_retries_have_stable_id_but_return_to_previous_content_is_a_new_event(award_data, now):
    record = Scholarship(**award_data)
    a = make_event(record, now)
    assert a.event_id == make_event(record, now).event_id
    assert a.event_id != make_event(record, now + timedelta(hours=1)).event_id


def test_older_event_cannot_undo_newer_data(award_data, now):
    old = make_event(Scholarship(**award_data), now)
    new = make_event(Scholarship(**(award_data | {"title": "Updated"})), now + timedelta(seconds=1))
    assert is_newer(new, old.observed_at, old.event_id)
    assert not is_newer(old, new.observed_at, new.event_id)
    assert not is_newer(new, new.observed_at, new.event_id)
def test_storage_timestamps_are_not_source_content(award_data, now):
    from scholarship_map.events import content_hash
    from scholarship_map.models import Scholarship
    record = Scholarship(**award_data)
    assert content_hash(record) == content_hash(record.model_copy(update={"added_at": now, "updated_at": now, "last_event_id": "stored"}))
