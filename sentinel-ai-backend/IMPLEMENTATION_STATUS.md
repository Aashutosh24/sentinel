# Implementation Status

Honest tracker. If it's not marked DONE, treat it as not existing.
Updated at the end of session 2 (the Review-1 build).

**Headline: Phase 1 is complete. Phase 2 has not been started.**

---

## PHASE 1 — Backend Foundation + Real Dataset Integration

### Step 1 — Dataset Audit
- [x] **DONE** (session 1) — All 15 CSVs profiled. Output: `docs/profiling/profile_report.txt`.
- [x] **DONE** (session 1) — Data-quality scan. Zero issues found.

### Step 2 — Relationship Discovery
- [x] **DONE** (session 1) — Empirical value-overlap check. Output: `docs/profiling/relationships.txt`.
- [x] **DONE** (session 2) — Re-confirmed against the live database: zero orphans
      across all 14 verified FKs (`test_relationships_resolve_with_no_orphans`).

### Step 3 — Database Implementation
- [x] **DONE** — All 18 SQLAlchemy models (unchanged this session; they were correct).
- [x] **DONE** — Alembic revision `f6fd9ee3f6ac` generated and applied against a
      **real PostgreSQL 16.14**. 18 tables + `alembic_version` verified present.
- [ ] **TODO** — Indexes reviewed under real query patterns. Current indexes are
      first-pass choices on FK/filter columns; they have not been load-tested.
      Nothing is slow at 14,400 rows, so this is not urgent.

### Step 4 — Data Ingestion Engine
- [x] **DONE** — `app/ingestion/`: generic `DatasetIngestor`, declarative
      per-dataset configs in `configs/registry.py`, CLI in `run.py`.
- [x] **DONE** — Idempotent upsert via `INSERT ... ON CONFLICT (pk) DO UPDATE`,
      with inserted-vs-updated measured through Postgres `xmax` rather than guessed.
- [x] **DONE** — All 15 datasets loaded: **14,400 rows, 0 errors, 0 skipped**.
- [x] **DONE** — Re-run verified: 0 inserted, 14,400 updated, counts unchanged.
- [x] **DONE** — Lineage written to `ingestion_jobs` / `ingestion_logs`.

### Step 5 — Data Quality (ingestion-time)
- [x] **DONE** — Type coercion + required-field validation per column; rows that
      fail are logged and skipped, never silently dropped.
- [x] **DONE** — FK-aware loading: missing parent nulls a nullable FK, skips a
      non-nullable one, and warns-but-keeps for advisory links
      (`employees.device_id`).
- [x] **DONE** — In-file duplicate-PK handling (last row wins, earlier counted skipped).

### Step 6 — Backend Foundation
- [x] **DONE** — App factory, pydantic-settings config, CORS, `/api/v1/health`.
- [x] **DONE** — Async SQLAlchemy engine/session.
- [x] **DONE** — Router package structure built out under `app/api/v1/routers/`.
- [x] **DONE** — Exception handlers now wrap HTTP + validation errors in the same
      `{data, error}` envelope as successful responses.
- [ ] **TODO** — Structured JSON logging beyond `logging.basicConfig`. Not needed
      for Review 1.

### Step 7 — Authentication
- [x] **DONE** — bcrypt password hashing (`app/core/security.py`).
- [x] **DONE** — `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`,
      `GET /api/v1/auth/me`.
- [x] **DONE** — `get_current_user` dependency + `require_roles(...)` RBAC guard.
- [x] **DONE** — 5 demo users seeded, one per role (`scripts/seed_users.py`).
- [ ] **TODO** — `require_roles(...)` is not yet *applied* to any data endpoint.
      Deliberate: the Review-1 demo needs endpoints reachable without a login.
      One-line change per route when the frontend has auth.

### Step 8 — API Layer
- [x] **DONE** — 38 paths. 15 resource lists, 15 detail endpoints (7 of them
      enriched with real FK joins), 4 auth, health, dashboard, 2 framework,
      organization graph.
- [x] **DONE** — Pagination, search, filtering, sorting on every list endpoint.
- [x] **DONE** — Range filters on audit logs (`date_from`, `date_to`, `min_risk_score`).
- [ ] **TODO** — POST/PATCH/DELETE. Read-only was sufficient for Review 1.

### Step 9 — Dashboard API
- [x] **DONE** — `GET /api/v1/dashboard`, every figure a live aggregate query.
- [x] **DONE** — Trust Score + Audit Readiness as **transparent deterministic**
      scores that publish their own weights, components and formula, labelled
      `engine: "deterministic_phase1"`. `?scores=off` returns explicit nulls.
      This is not an AI score and does not pretend to be. See HANDOFF.md §12.
- [x] **DONE** — Framework rollup aggregated live (there is no frameworks table).

### Step 10 — Frontend Contract
- [x] **DONE** — Every frontend tab except *Sentinel AI* and *Settings* has a
      backing endpoint. Response shapes documented in HANDOFF.md §9 and live at
      `/api/docs`.
- [ ] **N/A** — No frontend code written, correctly, per instructions.

### Step 11 — Testing
- [x] **DONE** — 61 tests, all passing. Covers every required critical test
      including the re-ingestion duplicate check.
- [ ] **TODO** — No unit tests for individual services in isolation. The suite is
      deliberately integration-first: it asserts real data reaches the API, which
      is what the review actually depends on.

### Step 12 — Phase 2 Guard
- [x] **RESPECTED** — No AI agent, Trust Score engine, Copilot, RAG, Qdrant,
      predictive analytics, LLM call, or remediation logic exists anywhere in
      this repo. Verified by inspection at the end of the session.

### Phase 1 Completion Checklist (original brief, honest status)

- [x] All 15 datasets inspected
- [x] Dataset profiling completed
- [x] Relationships identified
- [x] PostgreSQL database running
- [x] Alembic migrations working
- [x] All 15 datasets imported (14,400 rows)
- [x] Duplicate-safe ingestion working (verified twice: manually and by test)
- [x] Data validation working
- [x] Relationships resolved in the DB — zero orphans
- [x] Backend starts successfully
- [x] Authentication works
- [x] APIs work (38 paths)
- [x] Dashboard API works
- [x] OpenAPI documentation works
- [x] Critical tests pass (61/61)
- [x] Frontend can consume the APIs

**Phase 1 is COMPLETE** for Review-1 scope. The open TODOs above (write
endpoints, applied RBAC, index tuning, structured logging) are deliberate
deferrals, not gaps in what was asked for.

---

## PHASE 2 — AI Intelligence + Risk + Trust + Evidence

**NOT STARTED.** Must not begin until explicitly instructed. Scope: Policy
Agent, Monitoring Agent, Risk Agent, Evidence Agent, Trust Score Agent
(deterministic scoring + LLM narrative — it replaces the Phase 1 score, it does
not wrap it), Compliance Copilot, Remediation Agent, Agent Orchestrator, RAG
over Qdrant.

---

## PHASE 3 — Frontend Integration + Demo Polish

**NOT STARTED.** Backend-only repo. This phase is about the frontend team
consuming the API contract without back-and-forth, plus demo rehearsal.

---

# PHASE 2 STATUS UPDATE (this session)

| # | Priority | Status |
|---|---|---|
| 1 | Trust Intelligence Engine | **DONE** — verified live against real data |
| 2 | Risk Intelligence Engine | **DONE** — verified live against real data |
| 3 | Evidence Intelligence | **TODO** — not started |
| 4 | Policy Intelligence | **TODO** — not started |
| 5 | Compliance Copilot | **TODO** — not started |
| 6 | Remediation Intelligence | **TODO** — not started |
| 7 | Continuous Monitoring Engine | **TODO** — not started |
| 8 | Sentinel Orchestrator | **TODO** — not started |
| 9 | RAG / Knowledge Layer | **TODO** — not started |
| — | Frontend wiring for the 2 new endpoints | **TODO** — endpoints exist and are verified; no UI consumes them yet |

**Test baseline: 67 passed, 1 skipped, 68 total collected** (was 61/61 at
the start of this session; nothing weakened or removed, 7 new tests added
for the intelligence layer, 6 of which run and pass — the 7th documents
and correctly skips a graceful-degradation case the current dataset
doesn't happen to contain).

**Database: 20 tables** (19 application tables + `alembic_version`),
**14,400 real records confirmed twice** in this session (once after the
initial migration+ingestion, once again after the Postgres service
process was restarted mid-session — zero data loss).

Per the brief's own stopping rule ("if only enough time remains for one
feature: Trust + Risk. If two: + Copilot.") — this session delivered
exactly the Trust + Risk baseline and stopped there deliberately, rather
than starting Evidence/Policy/Copilot and risking an unfinished, unzipped
state. See NEXT_CLAUDE_PROMPT.md for the recommended order to continue in.
