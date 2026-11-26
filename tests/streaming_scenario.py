"""Real Kafka/Spark/Mongo scenario in a unique, explicitly synthetic demo namespace.

Run using the Spark-enabled virtual environment. Existing project data is not
modified. The retained scenario namespace is printed for inspection.
"""
from datetime import timedelta
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic

from scholarship_map.api import create_app
from scholarship_map.events import make_event
from scholarship_map.models import Scholarship, utcnow
from scholarship_map.repository import MongoRepository
from scholarship_map.settings import ROOT, settings
from scholarship_map.spark_runtime import spark_session
from scholarship_map.streaming import build_queries


def run_scenario():
    token = uuid4().hex[:10]
    base_config = settings()
    config = base_config.model_copy(update={
        "mongo_database": f"scholarshipmap_scenario_{token}_demo",
        "kafka_topic": f"scholarships.scenario.{token}",
        "checkpoint_dir": str(ROOT / ".runtime" / "scenarios" / token / "checkpoints"),
    })
    admin = KafkaAdminClient(bootstrap_servers=config.kafka_bootstrap)
    admin.create_topics([NewTopic(config.kafka_topic, num_partitions=1, replication_factor=1)])
    admin.close()
    repo = MongoRepository(config)
    repo.ensure_indexes()
    snapshot = ROOT / "data" / "sample.jsonl"
    original = Scholarship.model_validate_json(next(line for line in snapshot.read_text("utf8").splitlines() if line.strip()))
    main = original.model_copy(update={"id": f"scenario-{token}-main", "source_record_id": f"scenario-{token}-main",
                                       "title": "Explicit replay scenario: original"})
    base_time = utcnow().replace(microsecond=0)
    first = make_event(main, base_time, mode="replay", run_id=token)
    updated = main.model_copy(update={"title": "Explicit replay scenario: updated"})
    second = make_event(updated, base_time + timedelta(minutes=20), "updated", mode="replay", run_id=token)
    late_record = main.model_copy(update={"id": f"scenario-{token}-late", "source_record_id": f"scenario-{token}-late"})
    late = make_event(late_record, base_time - timedelta(minutes=20), mode="replay", run_id=token)
    producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap, acks="all", enable_idempotence=True)
    spark = spark_session("ScholarshipMapRealIntegrationScenario")
    progress = []

    def process_phase():
        queries = build_queries(spark, config, available_now=True)
        try:
            for query in queries:
                if not query.awaitTermination(120):
                    raise TimeoutError("Scenario query did not finish")
            progress.extend(item for query in queries for item in query.recentProgress)
        finally:
            for query in queries:
                if query.isActive:
                    query.stop()

    def publish(event):
        producer.send(config.kafka_topic, key=event.scholarship.id.encode(),
                      value=event.model_dump_json().encode()).get(timeout=30)

    try:
        measured_start = perf_counter()
        publish(first)
        publish(first)  # Intentional duplicate delivery, not a second scholarship.
        producer.send(config.kafka_topic, value=b"{malformed-json").get(timeout=30)
        process_phase()
        assert repo.db.scholarships.count_documents({}) == 1
        assert repo.db.ingest_events.count_documents({}) == 1
        assert repo.db.invalid_events.count_documents({}) == 1
        api = TestClient(create_app(repo))
        assert api.get(f"/api/scholarships/{main.id}").status_code == 200
        first_latency = perf_counter() - measured_start

        publish(second)
        process_phase()
        assert repo.get(main.id).title == updated.title
        publish(late)
        process_phase()
        assert repo.get(late_record.id) is not None
        assert repo.db.scholarships.count_documents({}) == 2
        assert repo.db.ingest_events.count_documents({}) == 3
        assert api.get(f"/api/scholarships/{late_record.id}").status_code == 200
        dropped = sum(operator.get("numRowsDroppedByWatermark", 0)
                      for item in progress for operator in item.get("stateOperators", []))
        assert dropped >= 1, "Late observation should be excluded from the stateful metrics, not catalogue ingestion"
        report = {"status": "passed", "mode": "explicit_replay_integration_scenario", "run_id": token,
            "database": config.mongo_database, "topic": config.kafka_topic, "spark_version": spark.version,
            "producer_to_storage_and_api_seconds": round(first_latency, 3),
            "catalogue_records": 2, "unique_events": 3, "invalid_records": 1,
            "rows_dropped_by_watermark": dropped,
            "checks": ["real Kafka input", "duplicate catalogue idempotency", "invalid record quarantine",
                       "updated record preserved", "late record stored in catalogue", "late metrics excluded",
                       "real MongoDB sink", "public FastAPI read"],
            "completed_at": utcnow().isoformat()}
        path = ROOT / "benchmarks" / "results" / "streaming-scenario.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2), flush=True)
        return report
    finally:
        producer.close()
        spark.stop()
        repo.close()


if __name__ == "__main__":
    run_scenario()
