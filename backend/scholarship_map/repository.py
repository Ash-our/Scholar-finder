"""MongoDB is the application's durable store; writes tolerate micro-batch retries."""
from datetime import timezone
from hashlib import sha256

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from .models import ObservationEvent, Scholarship, STORAGE_FIELDS, utcnow
from .settings import Settings


class MongoRepository:
    def __init__(self, config: Settings):
        self.client = MongoClient(config.mongo_uri, tz_aware=True, connect=False,
                                  serverSelectionTimeoutMS=2500, connectTimeoutMS=2500, maxPoolSize=15)
        self.db = self.client[config.mongo_database]

    def close(self):
        self.client.close()

    def ping(self):
        return self.client.admin.command("ping")["ok"] == 1

    def ensure_indexes(self):
        self.db.scholarships.create_index([("countries", ASCENDING)])
        self.db.scholarships.create_index([("degrees", ASCENDING)])
        self.db.scholarships.create_index([("funding", ASCENDING), ("deadline", ASCENDING)])
        self.db.ingest_events.create_index([("observed_at", ASCENDING)])
        self.db.ingest_events.create_index([("processed_at", ASCENDING)])
        self.db.ingest_events.create_index([("scholarship_id", ASCENDING), ("processed_at", ASCENDING)])
        self.db.scholarships.create_index([("added_at", ASCENDING)])
        self.db.source_records.create_index([("source_id", ASCENDING), ("source_record_id", ASCENDING)])
        self.db.insight_catalogue.create_index([("_snapshot_run_id", ASCENDING), ("countries", ASCENDING)])
        self.db.insight_catalogue.create_index([("_snapshot_run_id", ASCENDING), ("degrees", ASCENDING)])

    def records(self, query=None):
        for doc in self.db.scholarships.find(query or {}):
            yield Scholarship.model_validate({key: value for key, value in doc.items() if not key.startswith("_")})

    def get(self, key):
        doc = self.db.scholarships.find_one({"_id": key})
        if doc:
            return Scholarship.model_validate({k: v for k, v in doc.items() if not k.startswith("_")})
        return None

    @staticmethod
    def _newer_filter(key, event):
        return {"_id": key, "$or": [
            {"_observed_at": {"$exists": False}},
            {"_observed_at": {"$lt": event.observed_at}},
            {"_observed_at": event.observed_at, "_event_id": {"$lt": event.event_id}},
        ]}

    def apply_event(self, event: ObservationEvent, transport=None) -> str:
        if event.mode == "replay" and not self.db.name.endswith("_demo"):
            raise ValueError("Replay requires a separate database ending in _demo")
        if self.db.ingest_events.find_one({"_id": event.event_id}, {"_id": 1}):
            return "duplicate"
        record = event.scholarship.model_dump(mode="json", exclude=STORAGE_FIELDS)
        processed_at = utcnow()
        prior_identity = self.db.scholarships.find_one({"_id": record["id"]}, {"cycle": 1})
        if prior_identity is not None and prior_identity.get("cycle") != record.get("cycle"):
            # A provider may reuse one URL/record ID for a later year's call.
            # Retain the earlier application cycle instead of overwriting it.
            identity = f"{record['id']}|{record.get('cycle') or 'unknown'}"
            record["id"] = record["id"][:125] + "-" + sha256(identity.encode()).hexdigest()[:20]
        metadata = {"_observed_at": event.observed_at, "_event_id": event.event_id,
                    "_mode": event.mode, "_content_hash": event.content_hash,
                    "updated_at": processed_at, "last_event_id": event.event_id,
                    "last_observed_at": event.observed_at, "ingestion_mode": event.mode}
        source_key = f"{event.source_id}:{event.source_record_id}"
        # Write data before the audit marker. A crash before the marker can be
        # retried safely; writing a marker first could permanently lose the data.
        for collection, key in [(self.db.source_records, source_key), (self.db.scholarships, record["id"])]:
            try:
                result = collection.update_one(self._newer_filter(key, event),
                                               {"$set": record | metadata, "$setOnInsert": {"added_at": processed_at}}, upsert=True)
                applied = bool(result.modified_count or result.upserted_id)
            except DuplicateKeyError:
                applied = False  # A newer/equal version already owns this ID.
            if event.mode in {"live", "replay"}:
                collection.update_one({"_id":key,"first_streamed_at":None},{"$set":{"first_streamed_at":processed_at}})
                collection.update_one({"_id": key}, {"$min": {"first_streamed_at": processed_at}})
        self.db.ingest_events.update_one({"_id": event.event_id}, {"$setOnInsert": {
            "observed_at": event.observed_at, "processed_at": processed_at, "source_id": event.source_id,
            "event_type": event.event_type, "scholarship_id": record["id"], "mode": event.mode,
            "run_id": event.run_id, "applied": applied, "title": record.get("title_ar") or record["title"],
            "transport": transport,
        }}, upsert=True)
        return "applied" if applied else "stale"

    def backfill_timestamps(self):
        changed = 0
        for doc in self.db.scholarships.find({"added_at": None}):
            events = list(self.db.ingest_events.find({"scholarship_id": doc["_id"], "processed_at": {"$exists": True}})
                          .sort("processed_at", ASCENDING))
            if not events:
                continue  # No invented date when the audit history is absent.
            applied = [event for event in events if event.get("applied", True)]
            latest = next((event for event in events if event.get("_id") == doc.get("_event_id")), (applied or events)[-1])
            streamed = next((event for event in events if event.get("mode") in {"live", "replay"}), None)
            values = {"added_at": events[0]["processed_at"], "updated_at": latest["processed_at"],
                      "first_streamed_at": streamed["processed_at"] if streamed else None,
                      "last_event_id": str(latest.get("_id")) if latest.get("_id") else None,
                      "last_observed_at": latest.get("observed_at"), "ingestion_mode": latest.get("mode")}
            result = self.db.scholarships.update_one({"_id": doc["_id"], "added_at": None}, {"$set": values})
            changed += result.modified_count
        return changed

    def recent_events(self, limit=30):
        items = []
        for event in self.db.ingest_events.find({"mode": {"$in": ["live", "replay"]}}).sort("processed_at", -1).limit(limit):
            record = self.db.scholarships.find_one({"_id": event["scholarship_id"]}, {"title":1,"title_ar":1})
            items.append({"event_id": str(event["_id"]), "scholarship_id": event["scholarship_id"],
                "title": event.get("title") or ((record.get("title_ar") or record.get("title")) if record else event["scholarship_id"]),
                **{key: event.get(key) for key in ["source_id", "event_type", "observed_at", "processed_at", "mode", "applied", "transport"]}})
        return items

    def record_invalid(self, raw, error, batch_id=None):
        self.db.invalid_events.insert_one({"raw": str(raw)[:10000], "error": str(error)[:1000],
                                           "batch_id": batch_id, "recorded_at": utcnow()})

    def save_source_run(self, source_id, **values):
        self.db.source_runs.update_one({"_id": source_id}, {"$set": values | {"source_id": source_id}}, upsert=True)

    def source_status(self):
        return [{k: v for k, v in doc.items() if k != "_id"} for doc in self.db.source_runs.find()]

    def collection_schedule(self):
        doc = self.db.pipeline_status.find_one({"_id":"collector_schedule"})
        if not doc:
            return None
        heartbeat=doc.get("last_heartbeat_at")
        return {k:v for k,v in doc.items() if k!="_id"} | {"scheduler_connected":bool(heartbeat and (utcnow()-heartbeat).total_seconds()<45)}

    def insights(self):
        doc = self.db.insights.find_one({"_id": "latest"})
        return {k: v for k, v in doc.items() if k != "_id"} if doc else None

    def insight_records(self, query, run_id):
        for doc in self.db.insight_catalogue.find((query or {}) | {"_snapshot_run_id": run_id}):
            yield Scholarship.model_validate({key: value for key, value in doc.items() if not key.startswith("_")})

    def stream_status(self):
        windows = [{k: v for k, v in doc.items() if k != "_id"}
                   for doc in self.db.stream_windows.find().sort("window_start", -1).limit(100)]
        runtime = self.db.pipeline_status.find_one({"_id":"runtime"}) or {}
        heartbeat = runtime.get("last_heartbeat_at")
        return {"windows": windows, "runtime": {k:v for k,v in runtime.items() if k!="_id"},
                "processor_connected": bool(heartbeat and (utcnow()-heartbeat).total_seconds() < 25 and runtime.get("status")=="running" and len(runtime.get("active_queries",[]))>=2),
                "processed_events": self.db.ingest_events.count_documents({"mode": {"$in": ["live", "replay"]}}),
                "imported_events": self.db.ingest_events.count_documents({"mode": "import"}),
                "invalid_events": self.db.invalid_events.count_documents({})}
