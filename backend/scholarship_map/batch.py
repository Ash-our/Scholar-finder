"""Spark SQL reads MongoDB; near-duplicate candidates never overwrite listings."""
from hashlib import sha256
import json
from uuid import uuid4

from .catalog import application_state
from .models import Scholarship, utcnow
from .repository import MongoRepository
from .settings import Settings, settings
from .similarity import candidate_frame, safe_to_merge
from .spark_runtime import spark_session


def state_from_json(raw):
    return application_state(Scholarship.model_validate_json(raw))


def save_pairs(rows, configuration, run_id):
    repo = MongoRepository(Settings(**configuration))
    try:
        for row in rows:
            key = sha256(f"{row.left_id}:{row.right_id}".encode()).hexdigest()
            permitted = safe_to_merge({"title": row.left_title, "cycle": row.left_cycle, "official_url": row.left_url},
                                      {"title": row.right_title, "cycle": row.right_cycle, "official_url": row.right_url})
            repo.db.near_duplicate_candidates.update_one({"_id": key}, {"$set": {
                "left_id": row.left_id, "right_id": row.right_id, "jaccard": row.jaccard,
                "identity_evidence_matches": permitted, "run_id": run_id, "computed_at": utcnow(),
                "action": "candidate_only_no_automatic_merge",
            }}, upsert=True)
    finally:
        repo.close()


def save_snapshot(rows, configuration, run_id):
    from pymongo import ReplaceOne
    repo = MongoRepository(Settings(**configuration))
    operations = []
    try:
        for row in rows:
            record = Scholarship.model_validate_json(row.payload)
            key = f"{run_id}:{record.id}"
            operations.append(ReplaceOne({"_id": key}, {"_id": key, "_snapshot_run_id": run_id} | record.model_dump(mode="json"), upsert=True))
            if len(operations) >= 500:
                repo.db.insight_catalogue.bulk_write(operations, ordered=False)
                operations.clear()
        if operations:
            repo.db.insight_catalogue.bulk_write(operations, ordered=False)
    finally:
        repo.close()


def run_batch():
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType
    config = settings()
    repo = MongoRepository(config)
    if repo.db.scholarships.count_documents({}) == 0:
        print("No catalogue records yet; batch will run after ingestion", flush=True)
        repo.close()
        return None
    spark = spark_session("ScholarshipMapBatch")
    cached = None
    states = None
    try:
        raw = (spark.read.format("mongodb").option("database", config.mongo_database)
               .option("collection", "scholarships").load())
        columns = [column for column in raw.columns if not column.startswith("_")]
        frame = raw.select(*columns)
        states = frame.withColumn("application_state", F.udf(state_from_json, StringType())(F.to_json(F.struct(*columns)))).cache()
        run_id = uuid4().hex
        states.createOrReplaceTempView("scholarships")
        queries = {
            "by_country": "SELECT country, COUNT(DISTINCT id) AS opportunities FROM scholarships LATERAL VIEW EXPLODE(countries) c AS country GROUP BY country ORDER BY opportunities DESC, country",
            "by_degree": "SELECT degree, COUNT(DISTINCT id) AS opportunities FROM scholarships LATERAL VIEW EXPLODE(degrees) d AS degree GROUP BY degree ORDER BY opportunities DESC, degree",
            "by_funding": "SELECT funding, COUNT(DISTINCT id) AS opportunities FROM scholarships GROUP BY funding ORDER BY opportunities DESC, funding",
            "by_status": "SELECT application_state AS status, COUNT(*) AS listings FROM scholarships GROUP BY application_state ORDER BY listings DESC",
            "source_completeness": "SELECT source_id, COUNT(*) AS listings, SUM(CASE WHEN SIZE(countries) > 0 THEN 1 ELSE 0 END) AS known_destination, SUM(CASE WHEN SIZE(degrees) > 0 THEN 1 ELSE 0 END) AS known_degree, SUM(CASE WHEN SIZE(fields) > 0 THEN 1 ELSE 0 END) AS known_field, SUM(CASE WHEN deadline IS NOT NULL THEN 1 ELSE 0 END) AS dated_deadline, SUM(CASE WHEN official_url IS NOT NULL THEN 1 ELSE 0 END) AS official_link FROM scholarships GROUP BY source_id ORDER BY source_id",
            "upcoming_deadlines": "SELECT id, COALESCE(title_ar, title) AS title, deadline FROM scholarships WHERE application_state = 'open' AND deadline IS NOT NULL ORDER BY CAST(deadline AS TIMESTAMP), id LIMIT 12",
        }
        insights = {key: [row.asDict() for row in spark.sql(sql).collect()] for key, sql in queries.items()}
        counts = spark.sql("SELECT COUNT(*) AS total, SUM(CASE WHEN identity_resolved THEN 1 ELSE 0 END) AS confirmed FROM scholarships").first()
        insights.update(computed_at=utcnow().isoformat(), engine="Apache Spark SQL 4.0.3 + MongoDB Connector 11.1.0",
                        total_listings=counts.total, confirmed_opportunities=counts.confirmed or 0,
                        scope="all_collected_listings_not_all_world_scholarships",
                        sql_queries=queries)
        pairs, cached, params = candidate_frame(frame, num_tables=8, threshold=0.65)
        pair_count = pairs.count() if pairs is not None else 0
        if pair_count:
            pairs.foreachPartition(lambda rows: save_pairs(rows, config.model_dump(), run_id))
        payloads = states.select(F.to_json(F.struct(*columns)).alias("payload"))
        payloads.foreachPartition(lambda rows: save_snapshot(rows, config.model_dump(), run_id))
        previous = repo.insights()
        insights.update(near_duplicate_pairs=pair_count, lsh_parameters=params, lsh_run_id=run_id,
                        snapshot_run_id=run_id)
        repo.db.insights.replace_one({"_id": "latest"}, {"_id": "latest"} | insights, upsert=True)
        retained_runs = [run_id] + ([previous["snapshot_run_id"]] if previous and previous.get("snapshot_run_id") else [])
        # Only obsolete derived analytics snapshots are reclaimed; source data,
        # scholarship history, and event records are never deleted here.
        repo.db.insight_catalogue.delete_many({"_snapshot_run_id": {"$nin": retained_runs}})
        print(json.dumps({"batch": "complete", "records": counts.total, "candidate_pairs": pair_count,
                          "computed_at": insights["computed_at"]}), flush=True)
        return insights
    finally:
        if cached is not None:
            cached.unpersist()
        if states is not None:
            states.unpersist()
        spark.stop()
        repo.close()
