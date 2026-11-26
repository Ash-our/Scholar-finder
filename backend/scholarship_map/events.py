from datetime import datetime
from hashlib import sha256
import json

from .models import ObservationEvent, Scholarship, STORAGE_FIELDS


def content_hash(record: Scholarship) -> str:
    payload = record.model_dump(mode="json", exclude={"fetched_at"} | STORAGE_FIELDS)
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def make_event(record: Scholarship, observed_at: datetime, event_type="discovered", mode="live", run_id=None):
    digest = content_hash(record)
    identity = f"{record.source_id}:{record.source_record_id}:{digest}:{observed_at.isoformat()}:{run_id or ''}"
    return ObservationEvent(
        event_id=sha256(identity.encode()).hexdigest(), source_id=record.source_id,
        source_record_id=record.source_record_id, event_type=event_type,
        observed_at=observed_at, content_hash=digest, scholarship=record, mode=mode, run_id=run_id,
    )


def is_newer(event: ObservationEvent, previous_time: datetime, previous_id: str) -> bool:
    return (event.observed_at, event.event_id) > (previous_time, previous_id)
