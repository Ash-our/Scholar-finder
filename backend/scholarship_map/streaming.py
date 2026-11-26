"""Two genuine Kafka-backed Spark Structured Streaming queries."""
from hashlib import sha256
import json
from pathlib import Path
from threading import Event, Thread

from pydantic import ValidationError

from .models import ObservationEvent, utcnow
from .repository import MongoRepository
from .settings import Settings, settings
from .spark_runtime import spark_session


def valid_event_json(raw: str) -> bool:
    try:
        ObservationEvent.model_validate_json(raw)
        return True
    except (ValidationError, TypeError, ValueError):
        return False


def window_key(source: str, event_type: str, start: str) -> str:
    return sha256(f"{source}|{event_type}|{start}".encode()).hexdigest()


def ingest_partition(rows, configuration, batch_id):
    repo = MongoRepository(Settings(**configuration))
    try:
        for row in rows:
            try:
                event = ObservationEvent.model_validate_json(row.raw)
            except (ValidationError, ValueError, TypeError) as error:
                key = f"{row.topic}:{row.partition}:{row.offset}"
                repo.db.invalid_events.update_one({"_id": key}, {"$setOnInsert": {
                    "raw": (row.raw or "")[:10000], "error": str(error)[:1000],
                    "batch_id": batch_id, "recorded_at": utcnow(),
                }}, upsert=True)
                continue
            if row.normalized_title:
                event.scholarship.title = row.normalized_title
            repo.apply_event(event, transport={"topic":row.topic,"partition":row.partition,"offset":row.offset})
        repo.db.pipeline_status.update_one({"_id": "ingestion"}, {"$set": {
            "last_processed_at": utcnow(), "batch_id": batch_id, "engine": "Spark Structured Streaming",
        }}, upsert=True)
    finally:
        repo.close()


def metrics_partition(rows, configuration, batch_id):
    repo = MongoRepository(Settings(**configuration))
    try:
        for row in rows:
            key = window_key(row.source_id, row.event_type, row.window_start)
            repo.db.stream_windows.update_one({"_id": key}, {"$set": {
                "source_id": row.source_id, "event_type": row.event_type,
                "window_start": row.window_start, "window_end": row.window_end,
                "count": row["count"], "updated_at": utcnow(), "batch_id": batch_id,
                "measure": "observations", "watermark": "10 minutes", "window": "5 minutes",
            }}, upsert=True)
    finally:
        repo.close()


def build_queries(spark, config: Settings, available_now=False):
    from pyspark.sql import functions as F
    from pyspark.sql.types import BooleanType
    raw = (spark.readStream.format("kafka")
           .option("kafka.bootstrap.servers", config.kafka_bootstrap)
           .option("subscribe", config.kafka_topic).option("startingOffsets", "earliest")
           .option("maxOffsetsPerTrigger", 1000).option("failOnDataLoss", "true").load()
           .selectExpr("CAST(value AS STRING) AS raw", "topic", "partition", "offset")
           .withColumn("normalized_title", F.trim(F.get_json_object("raw", "$.scholarship.title"))))
    configuration = config.model_dump()
    checkpoint = Path(config.checkpoint_dir).resolve()

    def ingest_batch(batch, batch_id):
        batch.foreachPartition(lambda rows: ingest_partition(rows, configuration, batch_id))

    ingest_writer = (raw.writeStream.queryName("scholarship_catalogue")
                     .option("checkpointLocation", (checkpoint / "catalogue").as_uri())
                     .foreachBatch(ingest_batch))
    valid = raw.filter(F.udf(valid_event_json, BooleanType())("raw"))
    events = valid.select(
        F.get_json_object("raw", "$.source_id").alias("source_id"),
        F.get_json_object("raw", "$.event_type").alias("event_type"),
        F.to_timestamp(F.get_json_object("raw", "$.observed_at")).alias("observed_at"),
    )
    windows = (events.withWatermark("observed_at", "10 minutes")
               .groupBy(F.window("observed_at", "5 minutes"), "source_id", "event_type").count()
               .select("source_id", "event_type", "count",
                       F.date_format("window.start", "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").alias("window_start"),
                       F.date_format("window.end", "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").alias("window_end")))

    def metrics_batch(batch, batch_id):
        batch.foreachPartition(lambda rows: metrics_partition(rows, configuration, batch_id))

    metrics_writer = (windows.writeStream.queryName("source_observation_windows").outputMode("update")
                      .option("checkpointLocation", (checkpoint / "windows").as_uri())
                      .foreachBatch(metrics_batch))
    if available_now:
        ingest_writer = ingest_writer.trigger(availableNow=True)
        metrics_writer = metrics_writer.trigger(availableNow=True)
    else:
        ingest_writer = ingest_writer.trigger(processingTime="5 seconds")
        metrics_writer = metrics_writer.trigger(processingTime="5 seconds")
    return [ingest_writer.start(), metrics_writer.start()]


def run_streaming(available_now=False, demo=False):
    config = settings()
    if demo:
        config = config.model_copy(update={"mongo_database": config.mongo_database + "_demo",
                                           "kafka_topic": config.kafka_topic + ".demo",
                                           "checkpoint_dir": config.checkpoint_dir + "/demo"})
    spark = spark_session("ScholarshipMapStreaming")
    queries = []
    stopped = Event()
    heartbeat_thread = None
    try:
        queries = build_queries(spark, config, available_now)
        def heartbeat():
            repo = MongoRepository(config)
            try:
                while not stopped.is_set():
                    try:
                        repo.db.pipeline_status.update_one({"_id":"runtime"}, {"$set":{
                            "status":"running", "last_heartbeat_at":utcnow(), "engine":"Spark Structured Streaming",
                            "topic":config.kafka_topic, "active_queries":[q.name for q in queries if q.isActive],
                        }}, upsert=True)
                    except Exception:
                        pass  # A heartbeat failure must not change event processing.
                    stopped.wait(5)
            finally:
                try:
                    repo.db.pipeline_status.update_one({"_id":"runtime"}, {"$set":{"status":"stopped","last_heartbeat_at":utcnow()}}, upsert=True)
                finally:
                    repo.close()
        heartbeat_thread = Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        print(json.dumps({"streaming": "started", "queries": [query.name for query in queries],
                          "topic": config.kafka_topic, "database": config.mongo_database}), flush=True)
        if available_now:
            for query in queries:
                query.awaitTermination()
            print(json.dumps({"progress": [q.lastProgress for q in queries]}, default=str), flush=True)
        else:
            spark.streams.awaitAnyTermination()
    finally:
        stopped.set()
        if heartbeat_thread:
            heartbeat_thread.join(timeout=6)
        for query in queries:
            if query.isActive:
                query.stop()
        spark.stop()
