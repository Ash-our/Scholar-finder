# Reproducible evaluation

`results/minhash-results.json` is produced by the real Spark MinHash experiment, not hand-entered results. `results/streaming-scenario.json` is produced only after the genuine Kafka/Spark/Mongo replay scenario passes.

The MinHash experiment compares the same word-bigram Jaccard threshold against exhaustive exact pairs. Hash-table counts are 4, 8, 16 and 32; similarity thresholds are 0.65 and 0.80; random seed is 17. The collected corpus is measured separately from explicitly generated variants at 100 and 250 records. Increasing the workload does not increase the number of genuine scholarships.

Approximate timing includes Spark feature processing, vocabulary/index construction, similarity join and result transfer. Exact timing includes Python feature preparation and exhaustive comparisons. Process-tree RSS includes JVM overhead, and its baseline is recorded. Signature/raw-feature sizes are estimates and are explicitly labeled. The report does not claim isolated memory savings or speedup from a small Spark workload.

The `snapshots` directory freezes the evaluated input. Use the report's SHA-256 and snapshot path when reproducing a particular run. Source data was retrieved from the attributed sites on 26 November 2026. Earlier snapshots can contain earlier normalization/curation labels; benchmark features are title, provider and description, not eligibility decisions. Snapshots are historical inputs, not promises of currently open calls.

## Observed results

Run completed26 November2026 on Windows, Spark4.0.3, seed17. Selected rows below use similarity0.65 and8 hash tables; the JSON contains all30 rows, including thresholds0.65/0.80 and4/8/16/32 tables.

| Workload | Exact seconds | Spark LSH seconds | Reference pairs | TP / FP / FN |
| --- | ---: | ---: | ---: | --- |
|50 real collected records |0.021591 |11.613753 |1 |1 /0 /0 |
|100 generated variants |0.047517 |11.462345 |54 |54 /0 /0 |
|250 generated variants |0.232634 |11.572692 |525 |525 /0 /0 |

All24 approximate result rows had no observed errors on these workloads. The real corpus has no reference pairs at0.80, so its precision/recall are null rather than an invented perfect score. Small, closely related generated variants are not proof of accuracy on a diverse large corpus. Exact Jaccard was faster at every measured size; Spark startup/distributed-operation overhead dominates this experiment.

For the50-record0.65 case: exact observed process-tree peak RSS454,447,104 bytes (baseline454,385,664);8-table LSH peak1,010,216,960 (baseline694,833,152). The LSH signature payload estimate is3,200 bytes, excluding Spark, JVM, vocabulary, vectors, Python objects and joins; it is **not** a measured total-memory saving. Shared-JVM warmup/caching and process baselines differ across sequential trials, so raw RSS differences should not be treated as isolated index measurements.

Frozen source SHA-256: `0c403267fff3a6c8aba57994af0330041e9ac835a0dfb9885b2bdf9538102911`.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scholarship_map.cli benchmark
.\.venv\Scripts\python.exe -m scholarship_map.cli benchmark --snapshot benchmarks/snapshots/initial-50-records.jsonl
.\.venv\Scripts\python.exe tests/streaming_scenario.py
```

The integration scenario uses a newly named topic/database ending in `_demo`; it tests a duplicated event, malformed JSON, a record update and an event that is too late for the window watermark but must still enter the catalogue. It never injects these artificial changes into the normal catalogue.
