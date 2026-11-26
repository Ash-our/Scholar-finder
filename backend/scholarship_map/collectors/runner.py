import json
from pathlib import Path
from uuid import uuid4

from kafka import KafkaProducer

from ..events import content_hash, make_event
from ..models import utcnow
from ..repository import MongoRepository
from ..settings import settings
from . import finder, iefa, scholarpal, official, scholars4dev, amideast
from .enrichment import apply_curation, attach_locations
from .http import PublicClient
from .verification import rules, verify_one
from urllib.parse import urlsplit

ADAPTERS = {"finder": (finder, ["scholarship-finder.fly.dev"]), "iefa": (iefa, ["www.iefa.org"]),
            "scholarpal": (scholarpal, ["scholarpal.io"]),
            "scholars4dev":(scholars4dev,["www.scholars4dev.com","scholars4dev.com"]),
            "amideast":(amideast,["www.amideast.org"])}
SOURCE_LIMITS = {"finder": 400, "iefa": 80, "scholarpal": 150, "official": 30,"scholars4dev":20,"amideast":10}


def collect_sources(source_ids=("amideast","scholars4dev","finder", "official", "scholarpal", "iefa"), limit=None, sink="kafka", snapshot=None, use_ror=True):
    config = settings()
    repo = MongoRepository(config)
    producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap, acks="all", enable_idempotence=True,
                             value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(),
                             key_serializer=lambda value: value.encode()) if sink == "kafka" else None
    records, summaries = [], []
    run_id = uuid4().hex
    try:
        for source_id in source_ids:
            if source_id == "official":
                adapter, hosts = official, [urlsplit(item["source_url"]).hostname for item in official.programmes()]
            else:
                adapter, hosts = ADAPTERS[source_id]
            client = PublicClient(hosts, config.request_delay)
            verifier = PublicClient([urlsplit(rule["url"]).hostname for rule in rules().values()], config.request_delay)
            source_limit = SOURCE_LIMITS[source_id] if limit is None else limit
            started, errors = utcnow(), []
            repo.save_source_run(source_id,status="running",last_started_at=started,planned_limit=source_limit,sink=sink,run_id=run_id)

            def on_error(url, error):
                errors.append({"url": url, "error": str(error)[:300]})
                print(f"[{source_id}] partial error: {url}: {error}", flush=True)

            try:
                print(f"[{source_id}] collecting up to {source_limit} public listings", flush=True)
                collected = adapter.collect(client, source_limit, started, on_error)
                if not collected:
                    raise ValueError("No records parsed; source format or availability needs checking")
                sent = unchanged = 0
                for record in collected:
                    record = apply_curation(record)
                    if source_id != "official":
                        record = verify_one(record, verifier, on_error)
                    record = attach_locations(record, use_ror=use_ror)
                    records.append(record)
                    key = f"{record.source_id}:{record.source_record_id}"
                    prior = repo.db.collector_state.find_one({"_id": key})
                    digest = content_hash(record)
                    if prior and prior.get("content_hash") == digest:
                        unchanged += 1
                        continue
                    event = make_event(record, started, "updated" if prior else "discovered",
                                       mode="live" if producer else "import", run_id=run_id)
                    if producer:
                        producer.send(config.kafka_topic, key=record.id, value=event.model_dump(mode="json")).get(timeout=30)
                    else:
                        repo.apply_event(event)
                    # Persist change detection only after a durable broker ack/sink write.
                    repo.db.collector_state.update_one({"_id": key}, {"$set": {
                        "content_hash": digest, "last_observed_at": started,
                    }}, upsert=True)
                    sent += 1
                summary = {"status": "partial" if errors else "ok", "last_started_at": started,
                           "last_success_at": utcnow(), "records": len(collected), "published": sent,
                           "unchanged": unchanged, "errors": errors, "sink": sink, "run_id": run_id}
            except Exception as error:
                summary = {"status": "error", "last_started_at": started, "last_error_at": utcnow(),
                           "error": str(error)[:500], "sink": sink, "run_id": run_id}
            finally:
                client.close()
                verifier.close()
            repo.save_source_run(source_id, **summary)
            summaries.append({"source_id": source_id} | summary)
            print(json.dumps(summaries[-1], default=str, ensure_ascii=False), flush=True)
        if snapshot:
            path = Path(snapshot)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(record.model_dump_json() for record in records) + "\n", encoding="utf8")
        if any(summary["status"] == "error" for summary in summaries):
            raise RuntimeError("One or more sources failed; see source run records")
        return summaries
    finally:
        if producer:
            producer.flush(timeout=30)
            producer.close()
        repo.close()
