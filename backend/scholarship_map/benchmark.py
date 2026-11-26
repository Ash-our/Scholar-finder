"""Reproducible measured evaluation; generated variants never enter the catalogue."""
from contextlib import contextmanager
from itertools import product
from hashlib import sha256
import json
from pathlib import Path
import sys
from threading import Event, Thread
from time import perf_counter
import tracemalloc

from .models import Scholarship, utcnow
from .settings import ROOT
from .similarity import candidate_frame, exact_pairs, token_set
from .spark_runtime import spark_session


class PeakMemory:
    def __enter__(self):
        import psutil
        self.process = psutil.Process()
        self.stop_event = Event()
        self.peak = self.rss()
        self.baseline = self.peak
        self.thread = Thread(target=self.sample, daemon=True)
        self.thread.start()
        return self

    def rss(self):
        import psutil
        total = 0
        for process in [self.process, *self.process.children(recursive=True)]:
            try:
                total += process.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total

    def sample(self):
        while not self.stop_event.wait(0.1):
            self.peak = max(self.peak, self.rss())

    def __exit__(self, *_):
        self.peak = max(self.peak, self.rss())
        self.stop_event.set()
        self.thread.join()


def workloads(records, sizes):
    real = [{"id": record.id, "title": record.title, "provider": record.provider,
             "description": record.description, "official_url": record.official_url or "", "cycle": record.cycle or ""}
            for record in records]
    yield "real_collected", real
    for size in sizes:
        variants = []
        for index in range(size):
            base = real[index % len(real)]
            variants.append(base | {"id": f"generated-{index:06}",
                "description": base["description"] + f" benchmark variant group{index // len(real)}"})
        yield f"generated_variants_{size}", variants


def run_benchmark(snapshot=None, sizes=(100, 250), tables=(4, 8, 16, 32), thresholds=(0.65, 0.80), output=None):
    from pyspark.sql.types import StructField, StructType, StringType
    source = Path(snapshot or ROOT / "data" / "sample.jsonl")
    source_bytes = source.read_bytes()
    source_hash = sha256(source_bytes).hexdigest()
    frozen = ROOT / "benchmarks" / "snapshots" / (source_hash[:16] + ".jsonl")
    frozen.parent.mkdir(parents=True, exist_ok=True)
    if not frozen.exists():
        frozen.write_bytes(source_bytes)
    records = [Scholarship.model_validate_json(line) for line in source_bytes.decode("utf8").splitlines() if line.strip()]
    if not records:
        raise ValueError("A nonempty attributed snapshot is required")
    spark = spark_session("ScholarshipMapMinHashEvaluation", with_connectors=False)
    results = []
    started = utcnow()
    schema = StructType([StructField(name, StringType(), False) for name in
                         ["id", "title", "provider", "description", "official_url", "cycle"]])
    try:
        for label, workload in workloads(records, sizes):
            prep_start = perf_counter()
            features = {row["id"]: token_set(" ".join([row["title"], row["provider"], row["description"]]))
                        for row in workload}
            preparation = perf_counter() - prep_start
            feature_bytes = sum(sys.getsizeof(value) + sum(sys.getsizeof(token) for token in value)
                                for value in features.values())
            frame = spark.createDataFrame(workload, schema=schema)
            exact = {}
            for threshold in thresholds:
                tracemalloc.start()
                begin = perf_counter()
                with PeakMemory() as measured:
                    truth = exact_pairs(features, threshold)
                elapsed = perf_counter() - begin
                _, peak_python = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                exact[threshold] = truth
                results.append({"workload": label, "generated": label != "real_collected", "records": len(workload),
                    "method": "exhaustive_exact_jaccard", "similarity_threshold": threshold, "pairs": len(truth),
                    "seconds": elapsed + preparation, "python_tracemalloc_peak_bytes": peak_python,
                    "observed_process_tree_peak_rss_bytes": measured.peak,
                    "process_tree_baseline_rss_bytes": measured.baseline,
                    "raw_feature_storage_estimate_bytes": feature_bytes})
            for num_tables, threshold in product(tables, thresholds):
                cache = None
                begin = perf_counter()
                try:
                    with PeakMemory() as measured:
                        pairs, cache, params = candidate_frame(frame, num_tables, threshold)
                        found = {(row.left_id, row.right_id) for row in pairs.select("left_id", "right_id").collect()} if pairs is not None else set()
                    elapsed = perf_counter() - begin
                    truth = exact[threshold]
                    tp, fp, fn = len(found & truth), len(found - truth), len(truth - found)
                    negative = len(workload) * (len(workload) - 1) // 2 - len(truth)
                    row = {"workload": label, "generated": label != "real_collected", "records": len(workload),
                        "method": "spark_minhash_lsh", **params, "pairs": len(found),
                        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
                        "precision": tp / len(found) if found else None,
                        "recall": tp / len(truth) if truth else None,
                        "false_positive_rate": fp / negative if negative else None,
                        "false_negative_rate": fn / len(truth) if truth else None,
                        "seconds": elapsed, "observed_process_tree_peak_rss_bytes": measured.peak,
                        "process_tree_baseline_rss_bytes": measured.baseline,
                        "signature_payload_estimate_bytes": params["records"] * num_tables * 8,
                        "raw_feature_storage_estimate_bytes": feature_bytes}
                    results.append(row)
                    print(json.dumps({key: row[key] for key in ["workload", "num_hash_tables", "similarity_threshold", "seconds", "recall"]}), flush=True)
                finally:
                    if cache is not None:
                        cache.unpersist()
    finally:
        spark.stop()
    report = {"started_at": started.isoformat(), "finished_at": utcnow().isoformat(),
              "snapshot": "snapshots/" + frozen.name, "snapshot_sha256": source_hash,
              "real_source_records": len(records), "seed": 17,
              "spark_version": "4.0.3", "results": results,
              "methodology": {
                  "error": "Compare final approximate candidates to exhaustive raw-token Jaccard pairs at identical thresholds; undefined rates are null.",
                  "timing": "Exact includes Python token preparation and pair enumeration. Approximate includes Spark preprocessing, CountVectorizer fitting, MinHash index, similarity join and collection. Spark startup and source loading are excluded for both.",
                  "memory": "Process-tree RSS sampled every 100ms includes Python/JVM/runtime and is not isolated index memory; baseline is recorded. Signature payload and Python raw-feature storage are explicit estimates, not measured total index memory.",
                  "interpretation": "Small real datasets may favor the exact method. Generated workloads are declared variants, not additional genuine scholarships. No speedup or accuracy is assumed.",
              }}
    target = Path(output or ROOT / "benchmarks" / "results" / "minhash-results.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print("Benchmark results:", target, flush=True)
    return report
