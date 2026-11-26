from datetime import datetime, timezone

import pytest


@pytest.fixture
def now():
    return datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


@pytest.fixture
def award_data(now):
    return {
        "id": "award-a-2027", "source_id": "official", "source_record_id": "a",
        "title": "Engineering Masters Scholarship", "provider": "Example University",
        "source_url": "https://example.org/award", "official_url": "https://example.org/award",
        "cycle": "2027", "countries": ["DE"], "degrees": ["master"],
        "fields": ["engineering"], "funding": "full", "nationalities": ["PS", "JO"],
        "minimum_gpa": 80, "gpa_scale": 100, "deadline": "2026-12-14",
        "deadline_confidence": "confirmed", "reported_status": "open",
        "official_verified_at": now, "open_evidence": "accepting_applications",
        "identity_resolved": True, "fetched_at": now,
    }
