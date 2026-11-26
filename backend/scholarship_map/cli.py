"""Course-friendly commands; normal collection always uses the real broker."""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import time
from uuid import uuid4

from .events import make_event
from .models import Scholarship, utcnow
from .repository import MongoRepository
from .settings import ROOT, settings


def ensure_topics(config):
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError
    admin = KafkaAdminClient(bootstrap_servers=config.kafka_bootstrap, request_timeout_ms=15000)
    try:
        existing = set(admin.list_topics())
        for name in [config.kafka_topic, config.kafka_topic + ".demo"]:
            if name not in existing:
                try:
                    admin.create_topics([NewTopic(name, num_partitions=3, replication_factor=1)])
                except TopicAlreadyExistsError:
                    pass
    finally:
        admin.close()


def replay_snapshot(snapshot, rate=10, run_id=None):
    from kafka import KafkaProducer
    config = settings()
    ensure_topics(config)
    source = Path(snapshot)
    payload = source.read_bytes()
    records = [Scholarship.model_validate_json(line) for line in payload.decode("utf8").splitlines() if line.strip()]
    if rate <= 0 or rate > 1000:
        raise ValueError("Replay rate must be in (0, 1000]")
    run_id = run_id or uuid4().hex
    repo = MongoRepository(config)
    digest = sha256(payload).hexdigest()
    repo.db.replay_runs.update_one({"_id": run_id}, {"$setOnInsert": {
        "base_time": utcnow(), "snapshot_sha256": digest, "rate": rate,
    }}, upsert=True)
    run = repo.db.replay_runs.find_one({"_id": run_id})
    if run["snapshot_sha256"] != digest or run["rate"] != rate:
        raise ValueError("This run ID already identifies another snapshot/rate")
    producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap, acks="all", enable_idempotence=True,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(), key_serializer=lambda key: key.encode())
    try:
        for index, record in enumerate(records):
            event = make_event(record, run["base_time"] + timedelta(seconds=index / rate), mode="replay", run_id=run_id)
            producer.send(config.kafka_topic + ".demo", key=record.id, value=event.model_dump(mode="json")).get(timeout=30)
            time.sleep(1 / rate)
    finally:
        producer.flush(timeout=30)
        producer.close()
        repo.close()
    print(json.dumps({"mode": "replay", "topic": config.kafka_topic + ".demo", "run_id": run_id,
                      "records": len(records), "rate_per_second": rate}), flush=True)


def import_snapshot(path):
    from .collectors.enrichment import apply_curation
    source = Path(path)
    digest = sha256(source.read_bytes()).hexdigest()
    repo = MongoRepository(settings())
    counts = {}
    try:
        repo.ensure_indexes()
        for line in source.read_text("utf8").splitlines():
            if line.strip():
                record = apply_curation(Scholarship.model_validate_json(line))
                result = repo.apply_event(make_event(record, record.fetched_at, mode="import", run_id=digest))
                counts[result] = counts.get(result, 0) + 1
    finally:
        repo.close()
    print(json.dumps({"mode": "attributed_snapshot_import", "results": counts}), flush=True)


def repeat(action, watch, interval, status_key=None):
    from threading import Event, Thread
    repo = MongoRepository(settings()) if status_key else None
    stopped = Event()

    def status(**values):
        if repo:
            repo.db.pipeline_status.update_one({"_id": status_key},
                {"$set": values | {"last_heartbeat_at": utcnow()}}, upsert=True)

    def heartbeat():
        while not stopped.wait(15):
            try:
                status()
            except Exception:
                pass

    thread = Thread(target=heartbeat, daemon=True) if repo else None
    if thread:
        thread.start()
    try:
        while True:
            started = time.monotonic()
            started_at = utcnow()
            status(status="running", run_started_at=started_at, interval_seconds=interval,
                   next_run_at=started_at + timedelta(seconds=interval) if watch else None)
            succeeded = True
            try:
                action()
            except Exception as error:
                succeeded = False
                if not watch:
                    raise
                print(f"Run failed: {type(error).__name__}: {error}", flush=True)
            remaining = max(1, interval - (time.monotonic() - started))
            status(status="waiting" if watch else "finished", last_finished_at=utcnow(),
                   last_run_succeeded=succeeded,
                   next_run_at=utcnow() + timedelta(seconds=remaining) if watch else None)
            if not watch:
                return
            stopped.wait(remaining)
    finally:
        stopped.set()
        if thread:
            thread.join(timeout=3)
        if repo:
            repo.close()


def main():
    parser = argparse.ArgumentParser(description="Scholarship Map: Arabic website and big-data pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create the project MongoDB indexes and Kafka topics")
    collect = commands.add_parser("collect", help="Poll the supported real sources")
    collect.add_argument("--sources", nargs="+", choices=["finder", "iefa", "scholarpal", "official","scholars4dev","amideast"], default=["amideast","scholars4dev","finder", "official", "scholarpal", "iefa"])
    collect.add_argument("--limit", type=int, default=None, help="Override per-source coverage limits")
    collect.add_argument("--sink", choices=["kafka", "mongo"], default="kafka")
    collect.add_argument("--snapshot")
    collect.add_argument("--watch", action="store_true")
    collect.add_argument("--interval", type=int, default=21600)
    stream = commands.add_parser("stream", help="Run real Spark Kafka ingestion and stateful windows")
    stream.add_argument("--available-now", action="store_true")
    stream.add_argument("--demo", action="store_true")
    batch = commands.add_parser("batch", help="Run Spark SQL and near-duplicate detection")
    batch.add_argument("--watch", action="store_true")
    batch.add_argument("--interval", type=int, default=900)
    replay = commands.add_parser("replay", help="Replay only into the separate .demo topic")
    replay.add_argument("--snapshot", default=str(ROOT / "data" / "sample.jsonl"))
    replay.add_argument("--rate", type=float, default=10)
    replay.add_argument("--run-id")
    imported = commands.add_parser("import-snapshot", help="Explicit offline import; not a streaming verification")
    imported.add_argument("--snapshot", default=str(ROOT / "data" / "sample.jsonl"))
    benchmark = commands.add_parser("benchmark", help="Measure actual Spark MinHash against exact Jaccard")
    benchmark.add_argument("--snapshot", default=str(ROOT / "data" / "sample.jsonl"))
    benchmark.add_argument("--sizes", default="100,250")
    benchmark.add_argument("--output", default=str(ROOT / "benchmarks" / "results" / "minhash-results.json"))
    serve = commands.add_parser("serve", help="Serve the API and built Arabic website")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    commands.add_parser("stats", help="Print real stored pipeline counters")
    commands.add_parser("verify", help="Recheck reviewed official calls and publish verified changes through Kafka")
    args = parser.parse_args()
    if args.command == "init":
        config = settings()
        repo = MongoRepository(config)
        try:
            repo.ensure_indexes()
            repo.backfill_timestamps()
            ensure_topics(config)
        finally:
            repo.close()
        print("MongoDB indexes and raw/demo Kafka topics are ready", flush=True)
    elif args.command == "collect":
        if (args.limit is not None and not 1 <= args.limit <= 500) or args.interval < 60:
            parser.error("--limit must be 1..500 and --interval at least 60 seconds")
        from .collectors.runner import collect_sources
        repeat(lambda: collect_sources(args.sources, args.limit, args.sink, args.snapshot), args.watch, args.interval,"collector_schedule" if args.watch else None)
    elif args.command == "stream":
        from .streaming import run_streaming
        run_streaming(args.available_now, args.demo)
    elif args.command == "verify":
        from .collectors.verification import verify_catalogue
        verify_catalogue()
    elif args.command == "batch":
        if args.interval < 60:
            parser.error("--interval must be at least 60 seconds")
        from .batch import run_batch
        repeat(run_batch, args.watch, args.interval)
    elif args.command == "replay":
        replay_snapshot(args.snapshot, args.rate, args.run_id)
    elif args.command == "import-snapshot":
        import_snapshot(args.snapshot)
    elif args.command == "benchmark":
        from .benchmark import run_benchmark
        sizes = tuple(int(size) for size in args.sizes.split(",") if size)
        if any(not 1 <= size <= 2000 for size in sizes):
            parser.error("Generated benchmark sizes must be 1..2000")
        run_benchmark(args.snapshot, sizes=sizes, output=args.output)
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("scholarship_map.api:app", host=args.host, port=args.port)
    elif args.command == "stats":
        repo = MongoRepository(settings())
        try:
            print(json.dumps({"catalogue_records": repo.db.scholarships.count_documents({}),
                              **repo.stream_status(), "sources": repo.source_status()}, default=str, ensure_ascii=False, indent=2))
        finally:
            repo.close()


if __name__ == "__main__":
    main()
