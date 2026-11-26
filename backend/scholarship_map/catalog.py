"""Time-sensitive catalogue projections; raw provenance stays unchanged."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import Scholarship, utcnow


def deadline_sort_key(record: Scholarship) -> datetime:
    if not record.deadline:
        return datetime.max.replace(tzinfo=timezone.utc)
    closing = datetime.fromisoformat(record.deadline.replace("Z", "+00:00"))
    if len(record.deadline) == 10:
        closing = datetime.combine(closing.date(), time.max)
    if closing.tzinfo is None:
        closing = closing.replace(tzinfo=ZoneInfo(record.deadline_timezone or "UTC"))
    return closing.astimezone(timezone.utc)


def application_state(record: Scholarship, now: datetime | None = None) -> str:
    now = now or utcnow()
    if record.reported_status == "closed":
        return "closed"
    local_now = now.astimezone(ZoneInfo(record.deadline_timezone)) if record.deadline_timezone else now
    if record.deadline and record.deadline_confidence == "confirmed":
        closing = datetime.fromisoformat(record.deadline.replace("Z", "+00:00"))
        if len(record.deadline) == 10:
            expired = closing.date() < local_now.date()
        else:
            expired = closing.replace(tzinfo=closing.tzinfo or local_now.tzinfo) < now
        if expired:
            return "closed"
    if record.opens_at:
        opening = datetime.fromisoformat(record.opens_at.replace("Z", "+00:00"))
        if len(record.opens_at) == 10:
            starts_later = opening.date() > local_now.date()
        else:
            starts_later = opening.replace(tzinfo=opening.tzinfo or local_now.tzinfo) > now
        if starts_later:
            return "upcoming"
    verified = record.official_verified_at
    if (not verified or verified > now + timedelta(minutes=5) or now - verified > timedelta(days=7)
            or not record.official_url or not record.identity_resolved):
        return "unverified"
    if record.reported_status == "upcoming":
        return "upcoming"
    if record.reported_status == "open" and record.open_evidence in {"accepting_applications", "rolling"}:
        return "open"
    if (record.open_evidence == "date_window" and record.opens_at and record.deadline
            and record.deadline_confidence == "confirmed"):
        return "open"
    return "unverified"


def public_record(record: Scholarship, now: datetime | None = None) -> dict:
    return record.model_dump(mode="json") | {"application_state": application_state(record, now)}


def map_groups(records: list[Scholarship], now: datetime | None = None) -> dict:
    groups: dict[str, dict] = {}
    countries = {}
    confirmed_ids = set()
    for record in records:
        if record.identity_resolved:
            confirmed_ids.add(record.id)
        for code in record.countries:
            group = countries.setdefault(code, {"country":code,"scholarship_ids":set(),"confirmed_ids":set(),"university_ids":set(),"unlocated_ids":set()})
            group["scholarship_ids"].add(record.id)
            if record.identity_resolved:
                group["confirmed_ids"].add(record.id)
            locations = [p.id for p in record.placements if p.country==code and p.precision in {"city","campus"}]
            group["university_ids"].update(locations)
            if not locations:
                group["unlocated_ids"].add(record.id)
        for place in record.placements:
            key = f"{place.country}:{place.id}"
            group = groups.setdefault(key, place.model_dump() | {
                "key": key, "scholarship_ids": [], "confirmed_scholarship_ids": [],
                "confirmed_count": 0, "unverified_count": 0,
            })
            if record.id not in group["scholarship_ids"]:
                group["scholarship_ids"].append(record.id)
                group["confirmed_count" if record.identity_resolved else "unverified_count"] += 1
                if record.identity_resolved:
                    group["confirmed_scholarship_ids"].append(record.id)
    return {
        "countries":[{"country":code,"listing_count":len(row["scholarship_ids"]),
                      "confirmed_count":len(row["confirmed_ids"]),"university_count":len(row["university_ids"]),
                      "unlocated_count":len(row["unlocated_ids"])} for code,row in sorted(countries.items())],
        "groups": list(groups.values()), "opportunity_count": len(confirmed_ids),
        "unverified_listing_count": len(records) - len(confirmed_ids),
        "placement_count": sum(len(record.placements) for record in records),
        "unmapped_count": sum(not record.placements for record in records),
    }
