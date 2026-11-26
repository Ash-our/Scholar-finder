# Scholarship Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build the approved Arabic scholarship map and a real Kafka → Spark → MongoDB pipeline with two collectors and reproducible evaluation.

**Architecture:** Shared Python domain contracts serve collectors, idempotent MongoDB writes, FastAPI and Spark jobs. React/Vite/Leaflet consumes the API. Docker Compose is the portable full-stack runtime; local native services may be used for verification without modifying system installations.

**Tech Stack:** Python 3.12/3.13, FastAPI/Pydantic/PyMongo, PySpark 4.0.3 with Java 21 and Scala 2.13 Kafka integration, MongoDB Spark Connector 11.1.0, React/TypeScript/Vite, Leaflet. Spark 4.0.3 supersedes 4.0.1 to include the official SPARK-53759 Windows worker fix.

**Spec:** `docs/superpowers/specs/2026-11-26-scholarship-map-design.md`

## Global Constraints

- Arabic UI with RTL layout. Map geography remains LTR.
- Browse first; optional five-field personalization including GPA scale metadata.
- Kafka, stateful Structured Streaming with watermark, Spark SQL batch work, MongoDB and measured MinHash LSH.
- Preserve source/cycle identity, deadline confidence and location precision; no invented eligibility or campus coordinates.
- No publication, third-party messaging or fabricated contribution history.
- The user explicitly approved implementation. Execute inline without another approval round. Do not commit because commits have not been requested.

## Review Focus

- Unknown/estimated deadlines and stale official evidence never appear as confirmed open.
- A GPA on a different grading basis is uncertain, not linearly converted.
- Repeated or older events cannot duplicate records or undo newer information.
- Country-wide, multi-country and unknown locations do not inflate canonical totals.
- Source failure, empty filters and aborted requests remain usable and accurately labeled.

## File structure and contracts

`backend/scholarship_map/` owns domain models, matching, repository, API, collectors and Spark entry points. `tests/` exercises public contracts. `frontend/src/` separates API/types, catalogue state, map, listing, profile, detail and insights. `infra/` and `scripts/` own runtime setup. `data/` retains attributed snapshots with observation times, not fabricated live records. `docs/` records operation and evidence.

### Task 1: Domain and eligibility

Files: `pyproject.toml`, `backend/scholarship_map/models.py`, `matching.py`, `catalog.py`, `tests/test_matching.py`, `tests/test_catalog.py`.
Interfaces: `Scholarship`, `Profile`, `ObservationEvent`; `recommend(scholarship, profile)` returns reasons, unmet/unknown conditions and preference score; `application_state(record, now)` enforces verified status.
- [x] Write/run failing tests for incompatible nationality, unknown eligibility, incomparable GPA, exact GPA boundary and stale/future deadlines.
- [x] Implement typed validation, eligibility explanations and canonical map grouping.
- [x] Run focused pytest tests; expected all pass.

### Task 2: Durable repository and FastAPI

Files: `repository.py`, `api.py`, `settings.py`, `tests/test_api.py`, `tests/test_repository.py`.
Interfaces: MongoRepository implements `apply_event`, `list_scholarships`, `get_scholarship`, `source_status`, `insights`; `create_app(repository=None)` supports a memory repository in tests only.
- [x] Write/run failing API tests for pagination/filtering, unknown detail, GPA validation and map/list identity; repository tests for duplicates/older versions.
- [x] Implement MongoDB indexes, retry-safe conditional updates, health/readiness and read endpoints plus POST recommendations.
- [x] Run pytest; expected all pass; verify real Mongo writes when service is available.

### Task 3: Two collectors and attributed data

Files: `collectors/http.py`, `collectors/finder.py`, `collectors/iefa.py`, `collectors/runner.py`, `events.py`, `tests/test_collectors.py`, `data/README.md`.
Interfaces: source adapters return `Scholarship` source records; `make_event(record, observed_at)` supplies deterministic source/content identity; runner publishes via Kafka producer.
- [x] Retain bounded real HTML fixtures and write failing parser tests: date without year, funding, official links, unknown fields and relative links.
- [x] Implement rate-limited policy-aware index/detail requests, normalization and persistent change detection; log each source run.
- [x] Execute both collectors, retain attributed normalized JSONL and report real counts; run parser tests.

### Task 4: Streaming and Spark batch processing

Files: `streaming.py`, `batch.py`, `spark_schema.py`, `tests/test_events.py`, `tests/test_streaming.py`, `infra/Dockerfile.spark`, `docker-compose.yml`.
Interfaces: Kafka JSON events use model schema; two checkpointed Spark queries call shared idempotent sinks; batch writes `insights` and `near_duplicate_candidates`.
- [x] Write failing tests for event validation/idempotency and deterministic window keys; prepare an integration test requiring real Kafka/Mongo/Spark.
- [x] Implement Kafka ingestion, invalid events, five-minute source/event windows with ten-minute watermark, Mongo sinks and late-event distinction.
- [x] Implement Spark SQL Mongo queries and scheduled/on-demand batch execution.
- [x] Run available focused/integration checks and explicitly record unavailable runtime checks.

### Task 5: Probabilistic benchmark

Files: `similarity.py`, `benchmark.py`, `tests/test_similarity.py`, `benchmarks/README.md`.
Interfaces: `token_set(text)`, exact Jaccard baseline and Spark `MinHashLSH` evaluation produce one JSON results file with provenance, parameters, errors, memory and time.
- [x] Write/run failing tests for known Jaccard pairs, empty features, cycle separation and deterministic workload labels.
- [x] Implement exact reference plus actual Spark MinHash parameter sweep and candidate verification; keep unresolved pairs separate.
- [x] Run a real benchmark if Spark is available, label synthetic variants, retain actual results only.

### Task 6: Arabic website

Files: `frontend/package.json`, `src/{App,api,types,labels}.tsx/ts`, `src/components/`, `src/styles.css`, `tests/`.
Interfaces: backend API response schemas are authoritative; all filters/recommendations/map markers refer to canonical IDs.
- [x] Establish screenshot-derived tokens: white surfaces, plum text, violet accent, pale lilac selection, fine borders, Arabic readable typography, split map/list.
- [x] Implement synchronized map/cards, filters, mobile layout, optional profile, scholarship detail and official links, insights/source activity, loading/error/empty states.
- [x] Add meaningful UI behavior tests; run TypeScript/build and test commands.
- [x] Exercise real API in desktop/mobile browser, inspect console and screenshots; fix issues.

### Task 7: Integration, operating instructions and independent review

Files: `README.md`, `scripts/`, `.env.example`, `.gitignore`, `docs/operations.md`, `docs/verification.md`.
- [x] Supply one-command Docker operation, collection/replay/batch/benchmark commands and Windows local launch helpers.
- [x] Run complete Python/frontend suites, production build, available service integration and browser flows.
- [x] Ask a fresh reviewer to inspect the integrated implementation against the approved spec, resolve material findings, then rerun affected checks.
- [x] Record commands, counts and environment limits without claiming unexecuted streaming or benchmark success.
