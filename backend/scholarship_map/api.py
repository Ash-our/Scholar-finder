from contextlib import asynccontextmanager
from collections import Counter
from datetime import datetime, timezone
import math
import re
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pymongo.errors import PyMongoError
import pycountry

from .catalog import application_state, deadline_sort_key, map_groups, public_record
from .matching import recommend
from .models import Profile, utcnow
from .repository import MongoRepository
from .settings import ROOT, settings
from .source_register import SOURCES


class Filters(BaseModel):
    q: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=2)
    degree: str = Field(default="", max_length=30)
    field: str = Field(default="", max_length=100)
    funding: str = Field(default="", max_length=30)
    placement: str = Field(default="", max_length=150)
    bbox: str = Field(default="", max_length=150)
    status: Literal["discover", "open", "upcoming", "closed", "unverified", "all"] = "discover"
    sort: Literal["deadline", "newest", "added", "title"] = "deadline"
    offset: int = Field(default=0, ge=0, le=1000000)
    limit: int = Field(default=30, ge=1, le=100)

    @field_validator("bbox")
    @classmethod
    def valid_bounds(cls, value):
        if value:
            try:
                west, south, east, north = [float(part) for part in value.split(",")]
            except ValueError:
                raise ValueError("حدود الخريطة غير صالحة")
            if (not all(math.isfinite(v) for v in [west, south, east, north])
                    or not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90)):
                raise ValueError("حدود الخريطة غير صالحة")
        return value


def in_bounds(place, value):
    if not value:
        return True
    west, south, east, north = [float(part) for part in value.split(",")]
    longitude = west <= place.lon <= east if west <= east else place.lon >= west or place.lon <= east
    return south <= place.lat <= north and longitude


def create_app(repository=None, clock=utcnow):
    config = settings()
    repo = repository if repository is not None else MongoRepository(config)

    @asynccontextmanager
    async def lifespan(app):
        try:
            repo.ensure_indexes()
            if hasattr(repo,"backfill_timestamps"):
                repo.backfill_timestamps()
        except PyMongoError:
            pass  # Keep health and a useful 503 response available during startup.
        yield
        if repository is None:
            repo.close()

    app = FastAPI(title="خريطة المنح", version="0.1.0", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=800)
    app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins.split(","),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(PyMongoError)
    async def storage_error(request: Request, error: PyMongoError):
        return JSONResponse(status_code=503, content={"detail": "قاعدة البيانات غير متاحة حاليًا، حاول لاحقًا"})

    def selected(filters, now, snapshot_run_id=None):
        query = {}
        for attr, key in [("country", "countries"), ("degree", "degrees"), ("field", "fields"), ("funding", "funding")]:
            if value := getattr(filters, attr):
                query[key] = value.upper() if attr == "country" else value
        if filters.q:
            escaped = re.escape(filters.q)
            query["$or"] = [{key: {"$regex": escaped, "$options": "i"}}
                            for key in ["title", "title_ar", "provider"]]
        if filters.placement:
            query["placements.id"] = filters.placement
        result = []
        source_rows = repo.insight_records(query, snapshot_run_id) if snapshot_run_id else repo.records(query)
        for record in source_rows:
            if filters.country and filters.country.upper() not in record.countries:
                continue
            if filters.degree and filters.degree not in record.degrees:
                continue
            if filters.field and filters.field not in record.fields:
                continue
            if filters.funding and filters.funding != record.funding:
                continue
            if filters.placement and not any(place.id == filters.placement for place in record.placements):
                continue
            if filters.bbox and not any(in_bounds(place, filters.bbox) for place in record.placements):
                continue
            text = f"{record.title} {record.title_ar or ''} {record.provider}".casefold()
            if filters.q.casefold() not in text:
                continue
            state = application_state(record, now)
            if filters.status == "discover" and state == "closed":
                continue
            if filters.status not in {"all", "discover"} and state != filters.status:
                continue
            result.append(record)
        return result

    def response(filters, profile=None):
        now = clock()
        records = selected(filters, now)
        matches = {}
        if profile:
            for record in records:
                matches[record.id] = recommend(record, profile)
            records = [record for record in records if matches[record.id].compatible]
        if filters.sort == "newest":
            records.sort(key=lambda item: item.fetched_at, reverse=True)
        elif filters.sort == "added":
            records.sort(key=lambda item: item.added_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        elif filters.sort == "title":
            records.sort(key=lambda item: item.title_ar or item.title)
        else:
            status_order = {"open": 0, "upcoming": 1, "unverified": 2, "closed": 3}
            records.sort(key=lambda item: (status_order[application_state(item, now)], deadline_sort_key(item), item.title))
        if profile:
            records.sort(key=lambda item: matches[item.id].score, reverse=True)
        items = [public_record(record, now) | ({"match": matches[record.id].model_dump()} if profile else {})
                 for record in records[filters.offset:filters.offset + filters.limit]]
        mapped_records = [record.model_copy(update={
            "countries":[c for c in record.countries if not filters.country or c==filters.country.upper()],
            "placements":[p for p in record.placements if in_bounds(p, filters.bbox) and (not filters.country or p.country==filters.country.upper())],
        }) for record in records]
        return {"items": items, "total": len(records), "offset": filters.offset, "limit": filters.limit,
                "status_counts": dict(Counter(application_state(record, now) for record in records)),
                "confirmed_count": sum(r.identity_resolved for r in records),
                "unverified_listing_count": sum(not r.identity_resolved for r in records),
                "map": map_groups(mapped_records, now), "generated_at": now.isoformat(),
                "last_fetched_at": max((r.fetched_at for r in records), default=None)}

    @app.get("/api/health")
    def health():
        repo.ping()
        return {"status": "ok", "application": "scholarship-map", "storage": "mongodb", "database": config.mongo_database}

    @app.get("/api/meta")
    def metadata():
        database_name = repo.db.name if isinstance(repo, MongoRepository) else config.mongo_database
        return {"mode": "replay" if database_name.endswith("_demo") else "live",
                "countries": sorted(({"code": c.alpha_2, "name": c.name} for c in pycountry.countries),
                                     key=lambda c: c["name"]),
                "fields": ["computer_science", "engineering", "business", "medicine", "natural_sciences",
                           "social_sciences", "arts", "law", "education", "agriculture", "all"],
                "degrees": ["bachelor", "master", "phd", "postdoc", "research", "other"]}

    @app.get("/api/scholarships")
    def scholarships(filters: Annotated[Filters, Query()]):
        return response(filters)

    @app.get("/api/map")
    def locations(filters: Annotated[Filters, Query()]):
        return response(filters)["map"]

    @app.post("/api/map")
    def personalized_locations(profile: Profile, filters: Annotated[Filters, Query()]):
        return response(filters, profile)["map"]

    @app.post("/api/recommendations")
    def recommendations(profile: Profile, filters: Annotated[Filters, Query()]):
        return response(filters, profile)

    @app.get("/api/scholarships/{scholarship_id}")
    def detail(scholarship_id: str):
        record = repo.get(scholarship_id)
        if not record:
            raise HTTPException(404, "المنحة غير موجودة")
        return public_record(record, clock())

    @app.get("/api/sources")
    def sources():
        runs = {run["source_id"]: run for run in repo.source_status()}
        return {"sources": [source | {"last_run": runs.get(source["id"])} for source in SOURCES],
                "streaming": repo.stream_status() if hasattr(repo, "stream_status") else None,
                "schedule":repo.collection_schedule() if hasattr(repo,"collection_schedule") else None}

    @app.get("/api/stream/activity")
    def activity(limit: int = Query(default=30, ge=1, le=100)):
        return {"events":repo.recent_events(limit) if hasattr(repo,"recent_events") else [],
                "streaming":repo.stream_status() if hasattr(repo,"stream_status") else None,
                "schedule":repo.collection_schedule() if hasattr(repo,"collection_schedule") else None,
                "generated_at":clock()}

    def insight_response(filters, profile=None):
        result = repo.insights()
        if not result or not result.get("snapshot_run_id"):
            return {"ready": False, "data": None}
        now = clock()
        records = selected(filters, now, snapshot_run_id=result["snapshot_run_id"])
        if profile:
            records = [record for record in records if recommend(record, profile).compatible]
        def dimensions(attribute, label):
            counts = Counter()
            for record in records:
                values = getattr(record, attribute)
                counts.update(set(values) if isinstance(values, list) else [values])
            return [{label: key, "opportunities": count} for key, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
        statuses = Counter(application_state(record, now) for record in records)
        deadlines = sorted((record for record in records if record.deadline and application_state(record, now) == "open"), key=deadline_sort_key)
        return {"ready": True, "data": result | {
            "total_listings": len(records), "confirmed_opportunities": sum(record.identity_resolved for record in records),
            "by_country": dimensions("countries", "country"), "by_degree": dimensions("degrees", "degree"),
            "by_funding": dimensions("funding", "funding"),
            "by_status": [{"status": key, "listings": value} for key, value in sorted(statuses.items())],
            "upcoming_deadlines": [{"id": r.id, "title": r.title_ar or r.title, "deadline": r.deadline} for r in deadlines[:12]],
            "scope": "current_filters_and_profile_over_materialized_spark_snapshot",
        }}

    @app.get("/api/insights")
    def insights(filters: Annotated[Filters, Query()]):
        return insight_response(filters)

    @app.post("/api/personalized-insights")
    def personalized_insights(profile: Profile, filters: Annotated[Filters, Query()]):
        return insight_response(filters, profile)

    web_dist = ROOT / "frontend" / "dist"
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="website")
    return app


app = create_app()
