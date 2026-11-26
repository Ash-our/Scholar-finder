import json

from scholarship_map.events import make_event
from scholarship_map.models import Scholarship
from scholarship_map.streaming import valid_event_json, window_key


def test_invalid_payload_is_not_accepted_as_a_valid_stream_event(award_data, now):
    event = make_event(Scholarship(**award_data), now).model_dump(mode="json")
    assert valid_event_json(json.dumps(event))
    event["scholarship"]["title"] = ""
    assert not valid_event_json(json.dumps(event))
    assert not valid_event_json("not-json")


def test_window_upsert_identity_is_stable_and_source_specific():
    a = window_key("finder", "discovered", "2026-11-26T12:00:00Z")
    assert a == window_key("finder", "discovered", "2026-11-26T12:00:00Z")
    assert a != window_key("iefa", "discovered", "2026-11-26T12:00:00Z")
