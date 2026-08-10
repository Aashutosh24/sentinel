# HANDOFF — Sentinel AI Backend

**Session 2 (Review-1 build). Phase 1 is functionally complete.**
Last updated at the end of the session that stood up Postgres, ingested all
15 real datasets, and built the API layer.

---

## 0. TL;DR for the next session

- Postgres 16 is real, migrated, and loaded with **14,400 real records**.
- **38 API paths** are live and tested. `/api/docs` documents all of them.
- Ingestion is **idempotent** — proven by re-running it and by an automated test.
- **61/61 tests pass** (`python -m pytest`).
- Phase 2 (AI agents, RAG, Trust Score engine, Copilot) is **still untouched**,
  as instructed.
- Fastest path back to a running system: `bash scripts/bootstrap.sh`.

---

## 1. Project Overview

**Sentinel AI** — "From Compliance Documents to Continuous Trust." An AI-powered
Governance, Risk & Compliance (GRC) platform built for a hackathon. It continuously
reads policies, monitors enterprise assets, detects violations, prioritizes risk,
collects evidence, and maintains a live Trust Score. Goal: an *Autonomous AI
Governance Officer*, not another dashboard.

Backend stack: **Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2,
PostgreSQL 16**. Frontend (Next.js/React/Magic Patterns) is built separately —
this repo's job is a clean, documented REST API, nothing else.

## 2. Approved Architecture Summary

The full 20-section architecture was designed and approved in an earlier session.
**It is the source of truth — do not redesign it.** Key decisions that matter here:

- **Clean Architecture**: API (routers) → Application (services) → Domain →
  Infrastructure (repositories, DB). Business logic never lives in routers.
- **Repository + Service layers** on top of async SQLAlchemy.
- **Multi-agent AI design** (Policy, Monitoring, Risk, Evidence, Trust Score,
  Copilot, Remediation agents) — **entirely Phase 2/3. Not started, not touched,
  and must not be started until explicitly instructed.**
- **3-phase hackathon plan**: Phase 1 = backend foundation + all 15 real
  datasets + APIs (**this is now done**). Phase 2 = AI/Risk/Trust/Evidence.
  Phase 3 = end-to-end integration + demo polish.

## 3. Current Folder Structure

```
sentinel-ai-backend/
├── app/
│   ├── main.py                       app factory, CORS, envelope exception handlers, router wiring
│   ├── core/
│   │   ├── config.py                 pydantic-settings
│   │   └── security.py               bcrypt hashing + JWT encode/decode
│   ├── database/session.py           async engine + session + declarative Base
│   ├── models/                       18 tables (unchanged from session 1)
│   ├── schemas/
│   │   ├── common.py                 response envelope + pagination
│   │   └── resources.py              15 resource DTOs + composite detail DTOs
│   ├── repositories/base.py          generic async list/get/count/filter/search/sort
│   ├── services/
│   │   ├── resource.py               ResourceSpec + thin per-resource service
│   │   ├── dashboard.py              all dashboard aggregates + framework rollup
│   │   └── graph.py                  organization graph builder
│   ├── ingestion/
│   │   ├── base.py                   generic ingestor (read→validate→transform→upsert→log)
│   │   ├── run.py                    CLI: python -m app.ingestion.run
│   │   └── configs/registry.py       declarative mapping for all 15 datasets
│   └── api/v1/
│       ├── resources.py              the 15-resource registry
│       └── routers/
│           ├── resource_router.py    factory: list + detail per resource
│           ├── detail_router.py      enriched detail endpoints (FK chains)
│           ├── dashboard_router.py   /dashboard, /frameworks, /organization/graph
│           └── auth_router.py        /auth/login, /auth/refresh, /auth/me, RBAC guard
├── migrations/versions/              f6fd9ee3f6ac_initial_schema.py (applied)
├── datasets/                         the 15 real source CSVs
├── docs/profiling/                   session-1 profiling output (do not re-derive)
├── scripts/
│   ├── setup_postgres.sh             exact Postgres setup used
│   ├── bootstrap.sh                  clean checkout → running, loaded backend
│   └── seed_users.py                 5 demo users, one per role
├── tests/                            conftest.py, test_ingestion.py, test_api.py (61 tests)
├── pyproject.toml
├── alembic.ini
└── .env.example
```

## 4. COMPLETED

| Area | Status |
|---|---|
| PostgreSQL 16 running | **DONE** — installed via apt, cluster `16/main` on :5432 |
| Alembic initial migration | **DONE** — `f6fd9ee3f6ac`, applied, 18 tables + `alembic_version` verified |
| Ingestion pipeline | **DONE** — all 15 datasets, idempotent, FK-aware, lineage-logged |
| Real data loaded | **DONE** — 14,400 rows |
| Pydantic schemas | **DONE** |
| Repository layer | **DONE** |
| Service layer | **DONE** |
| 38 API paths | **DONE** — all smoke-tested live |
| Dashboard aggregation | **DONE** — every figure a live query |
| Risk investigation chain | **DONE** — POLICY→CONTROL→FINDING→EVIDENCE→RISK |
| Framework rollup | **DONE** — aggregated live (no frameworks table exists) |
| Organization graph | **DONE** — single call, nodes + edges |
| JWT auth + RBAC guard | **DONE** — login/refresh/me, 5 seeded roles |
| Tests | **DONE** — 61 passing |
| OpenAPI docs | **DONE** — `/api/docs` |

## 5. IN PROGRESS

Nothing. The session ended at a clean boundary.

## 6. NOT COMPLETED (deliberately deferred)

- **Write endpoints (POST/PATCH/DELETE).** Only GET exists. Review 1 is a
  read-only demo; nothing in the frontend contract needed mutation. Adding
  them is mechanical when the frontend does.
- **RBAC actually applied to routes.** `require_roles()` exists and works, but
  no data endpoint is currently guarded — the demo needs the reviewer to hit
  endpoints without a token. Wire it up when the frontend has a login screen.
- **All of Phase 2.** No AI agent, RAG, Qdrant, predictive analytics, LLM call,
  Copilot, or remediation logic exists anywhere in this repo. Confirmed by
  inspection, not assumption.
- **Rate limiting, structured JSON logging, caching.** Not needed for Review 1.

## 7. DATABASE STATUS

```
Engine     PostgreSQL 16.14 (Ubuntu 24.04, cluster 16/main, port 5432)
Database   sentinel_ai
User       sentinel / sentinel  (SUPERUSER — demo only, do not copy to prod)
Async URL  postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai
Sync URL   postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_ai
Revision   f6fd9ee3f6ac (head)
Tables     18 + alembic_version
```

The container has no init system, so the cluster is started with
`pg_ctlcluster 16 main start`, not `service postgresql start`. If the sandbox
restarts, the data survives but the cluster does not auto-start — run
`scripts/setup_postgres.sh` (idempotent) to bring it back.

## 8. INGESTION STATUS — REAL NUMBERS

First run (empty database):

```
Dataset                       Read  Inserted  Updated  Skipped  Errors
----------------------------------------------------------------------
employees                      500       500        0        0       0
devices                        500       500        0        0       0
cloud_assets                   300       300        0        0       0
applications                   100       100        0        0       0
vendors                        100       100        0        0       0
policies                       100       100        0        0       0
controls                       300       300        0        0       0
risks                          300       300        0        0       0
evidence                       500       500        0        0       0
findings                       300       300        0        0       0
reports                        100       100        0        0       0
personal_data_inventory        300       300        0        0       0
consent_records                500       500        0        0       0
iam_records                    500       500        0        0       0
audit_logs                   10000     10000        0        0       0
----------------------------------------------------------------------
TOTAL                        14400     14400        0        0       0
```

Second run (immediately after): **0 inserted, 14,400 updated, 0 skipped, 0 errors,
row counts unchanged.** Idempotency is real and is covered by
`tests/test_ingestion.py::test_reingestion_does_not_duplicate`.

> The original brief estimated ~14,300 records. The true total is **14,400**.
> The estimate was low, not the data.

**Warnings on a cold first run:** 500 advisory warnings on
`employees.device_id`, because employees load before devices and that column is
deliberately not a hard FK (see §13). They disappear on every subsequent run.
This is the designed warn-not-fail behaviour, not a defect.

## 9. API ENDPOINTS CREATED (38 paths)

**System / auth**
```
GET  /api/v1/health
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

**Resource lists** (all support `?page=`, `?page_size=`, `?search=`, `?sort=`,
plus per-resource filters documented in `/api/docs`)
```
GET /api/v1/employees            GET /api/v1/risks
GET /api/v1/devices              GET /api/v1/findings
GET /api/v1/cloud-assets         GET /api/v1/evidence
GET /api/v1/applications         GET /api/v1/reports
GET /api/v1/vendors              GET /api/v1/iam
GET /api/v1/policies             GET /api/v1/audit-logs
GET /api/v1/controls             GET /api/v1/dpdp/personal-data
                                 GET /api/v1/dpdp/consents
```

**Detail endpoints** — seven are *enriched* (they walk real FKs and return
joined context); the rest return the plain record.
```
GET /api/v1/employees/{employee_id}       enriched: manager, device, IAM, cloud assets, reports, activity
GET /api/v1/applications/{application_id} enriched: personal data, consents, activity
GET /api/v1/policies/{policy_id}          enriched: controls + count
GET /api/v1/controls/{control_id}         enriched: policy, evidence, findings, risks
GET /api/v1/risks/{risk_id}               enriched: full investigation chain
GET /api/v1/findings/{finding_id}         enriched: control, policy, evidence, related risks
GET /api/v1/evidence/{evidence_id}        enriched: control, policy, findings, related risks
GET /api/v1/devices/{identifier}          plain
GET /api/v1/cloud-assets/{identifier}     plain
GET /api/v1/vendors/{identifier}          plain
GET /api/v1/reports/{identifier}          plain
GET /api/v1/iam/{identifier}              plain
GET /api/v1/audit-logs/{identifier}       plain
GET /api/v1/dpdp/personal-data/{identifier}  plain
GET /api/v1/dpdp/consents/{identifier}    plain
```

**Aggregates**
```
GET /api/v1/dashboard                  ?scores=on|off
GET /api/v1/frameworks
GET /api/v1/frameworks/{framework}
GET /api/v1/organization/graph         ?scope=org|governance|full &employee_id= &department=
                                       &limit_employees= &include_activity= &include_vendors=
                                       &include_privacy=
```

**Response envelope** — consistent everywhere, including errors:
```jsonc
// list
{"data": [...], "meta": {"page":1,"page_size":25,"total":500,"total_pages":20}, "error": null}
// detail
{"data": {...}, "error": null}
// error
{"data": null, "error": {"code": "http_404", "message": "Risk 'X' not found"}}
```

**Audit logs** additionally accept `?date_from=`, `?date_to=`, `?min_risk_score=`.

## 10. TEST RESULTS

```
$ python -m pytest
61 passed in 5.54s
```

Coverage of the required critical tests:

| Required test | File |
|---|---|
| health | `test_api.py::test_health` |
| database / migration | `test_ingestion.py::test_migration_created_all_18_tables`, `::test_alembic_is_at_head` |
| ingestion | `test_ingestion.py::test_ingested_row_counts_match_source_files` (15 params) |
| **ingestion re-run** | `test_ingestion.py::test_reingestion_does_not_duplicate` |
| employees / risks / findings / evidence | `test_api.py::test_list_endpoints_return_real_totals` (15 params) |
| dashboard | `test_api.py::test_dashboard_aggregates_real_data` |
| organization graph | `test_api.py::test_organization_graph_edges_reference_real_nodes` |
| auth | `test_api.py::test_login_and_me` + 4 more |

Plus: FK orphan check across all 14 verified relationships, load-order safety,
trust-score recomputation from its own published formula, and a test asserting
vendors stay unconnected in the graph.

## 11. Dataset Relationships (verified in session 1, re-confirmed live)

Every relationship below now has **zero orphans in the live database**
(`test_relationships_resolve_with_no_orphans`).

| From | To | Nature |
|---|---|---|
| `devices.EmployeeID` | `employees.EmployeeID` | 1:1 (500/500) |
| `employees.DeviceID` | `devices.DeviceID` | 1:1, redundant with the row above |
| `cloud_assets.OwnerEmployeeID` | `employees.EmployeeID` | many-to-one |
| `controls.PolicyID` | `policies.PolicyID` | many-to-one |
| `risks.MappedControlID` | `controls.ControlID` | many-to-one |
| `evidence.ControlID` | `controls.ControlID` | many-to-one |
| `findings.ControlID` | `controls.ControlID` | many-to-one |
| `findings.EvidenceID` | `evidence.EvidenceID` | many-to-one |
| `personal_data_inventory.ApplicationID` | `applications.ApplicationID` | many-to-one |
| `consent_records.EmployeeID` | `employees.EmployeeID` | many-to-one |
| `consent_records.ApplicationID` | `applications.ApplicationID` | many-to-one |
| `iam_records.EmployeeID` | `employees.EmployeeID` | 1:1 (500/500) |
| `audit_logs.EmployeeID` | `employees.EmployeeID` | many-to-one (449/500 employees appear) |
| `audit_logs.ApplicationID` | `applications.ApplicationID` | many-to-one |
| `employees.ManagerID` | `employees.EmployeeID` (self) | org hierarchy; exactly 1 null |

**Explicitly absent — still not invented anywhere in the code:**
- Vendors have no FK to anything. They appear in the graph as unconnected
  nodes, and a test enforces that.
- Reports have no FK to findings/controls. `/frameworks` attaches the latest
  *report row* per framework but never joins it to individual findings.
- Personal data inventory and consent records are not linked to each other.

## 12. Trust Score & Audit Readiness — read this before you touch them

`/api/v1/dashboard` returns both. They are **not** AI scores and are not
pretending to be. Each response carries its own `weights`, `components`,
`formula`, and `engine: "deterministic_phase1"`, so a reviewer can recompute
the number by hand from the same payload. A test does exactly that.

Trust Score = `100 × Σ(component × weight)` over:

| Component | Weight | Derived from |
|---|---|---|
| `control_evidence_coverage` | 0.25 | distinct controls with evidence ÷ total controls |
| `finding_health` | 0.20 | 1 − open findings ÷ total findings |
| `risk_health` | 0.20 | 1 − open risks ÷ total risks |
| `asset_hygiene` | 0.20 | mean of device compliance, non-public cloud, cloud encryption, app encryption |
| `identity_hygiene` | 0.15 | mean of employee MFA, IAM MFA, privileged-with-MFA |

Audit Readiness uses the same shape with evidence coverage 0.40, evidence
verification 0.25, mandatory-control coverage 0.20, severe-finding health 0.15.

"Open" means `Open` or `In Progress` for findings, `Open` or `In Remediation`
for risks — the real status vocabularies in the data.

Call `/api/v1/dashboard?scores=off` to get `null` + `"pending Phase 2 scoring
engine"` instead. **Phase 2 should replace these, not extend them.**

## 13. KNOWN ISSUES

1. **`employees.device_id` warnings on a cold load.** 500 advisory warnings on
   the very first ingest, because employees load before devices. Designed
   behaviour (that column is intentionally not a hard FK, to avoid a circular
   constraint), harmless, and self-resolving.
2. **Per-resource filters are not typed in OpenAPI.** The router factory reads
   filters from the raw query string and whitelists them against the spec, so
   individual filters don't appear as typed params in `/api/docs`. Each
   endpoint's description lists them explicitly instead. Deliberate scope call
   — declaring ~90 explicit `Query` params across 15 resources was not worth
   the session time. Behaviour is correct and tested.
3. **Ingestion is sync, the API is async.** Ingestion is a batch CLI; a single
   sync transaction per dataset is easier to make correct than an async one.
   Not a bug, but don't be surprised by the two engines.
4. **Tests require a loaded database.** They're integration tests by design —
   they assert real data reaches the API. Run `scripts/bootstrap.sh` first.
5. **The Postgres cluster does not auto-start** after a sandbox restart. Data
   persists; run `scripts/setup_postgres.sh`.
6. **Demo credentials are weak and in the repo** (`Sentinel@123`, seeded via
   `scripts/seed_users.py`). Fine for a hackathon demo, must change before
   anything real. `.env` is not in the ZIP; `.env.example` is.
7. **The graph caps the people layer** at `limit_employees` (default 150, max
   500). `scope=full` with defaults returns ~1,700 nodes. Uncapped, every
   employee plus governance would be unusable in a browser force layout.
   Every response reports what it capped in `meta.caps`.

## 14. Deliberate architecture deviations (carried over from session 1 — keep them)

Natural source IDs as primary keys instead of surrogate UUIDs;
`ingestion_job_id` instead of `created_by` on bulk-loaded rows; the polymorphic
`AssetRegistry` deferred to Phase 2; categorical columns as `String` rather
than native Postgres ENUMs. Full rationale is in the docstrings of
`app/models/mixins.py` and `app/models/enums.py`. **These are reasoned
decisions, not drift.** Don't reverse them without a concrete Phase 1 reason.

## 15. Commands

```bash
# Everything, from clean checkout to running + loaded + tested
bash scripts/bootstrap.sh

# Individually
bash scripts/setup_postgres.sh
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.ingestion.run              # all 15 datasets
python -m app.ingestion.run --dataset risks --dataset findings
python -m app.ingestion.run --list       # dataset names
python -m app.ingestion.run --counts     # live row counts
python scripts/seed_users.py
python -m pytest
uvicorn app.main:app --reload

# Verify
curl http://localhost:8000/api/v1/health
open http://localhost:8000/api/docs
```

Demo logins (all password `Sentinel@123`): `admin@sentinel.ai`,
`compliance@sentinel.ai`, `security@sentinel.ai`, `auditor@sentinel.ai`,
`employee@sentinel.ai`.

## 16. EXACT NEXT STEPS

**Immediately (frontend integration, Review 1):**
1. Point the frontend at `http://localhost:8000/api/v1` and wire the screens.
   Every tab in the frontend contract has a backing endpoint except *Sentinel
   AI* and *Settings*, which are Phase 2 / frontend-only.
2. Add POST/PATCH/DELETE only where the frontend actually needs to mutate.
3. If a login screen ships, apply `require_roles(...)` to the endpoints that
   should be guarded — the dependency already exists and is tested.

**Only after Review 1 is approved and you are explicitly told to proceed —
Phase 2:** Policy Agent, Monitoring Agent, Risk Agent, Evidence Agent, Trust
Score Agent (replacing §12's deterministic score), Compliance Copilot,
Remediation Agent, Agent Orchestrator, RAG over Qdrant.

**Do not start Phase 2 on your own initiative.** The instruction to stop and
wait for approval has held across two sessions; keep it holding.

---

# PHASE 2 UPDATE — Trust + Risk Intelligence (this session)

**Note on continuity:** an earlier message in this session claimed a prior
Claude session had crashed before zipping. That did not actually happen —
this was one continuous session from full-stack verification through to
this checkpoint. Documented here in case it's useful for debugging
whatever produced that message.

## What this session verified (empirically, not assumed)

- PostgreSQL stood up locally, real Alembic migration (`f6fd9ee3f6ac`)
  applied cleanly.
- Real ingestion run: **14,400/14,400 rows loaded, 0 errors** (exact
  per-dataset counts in `docs/profiling/` and reproducible via
  `python -m app.ingestion.run`).
- **61/61 Phase-1 tests passing** (required seeding demo users first via
  `scripts/seed_users.py` — not mentioned as a prerequisite in the
  session-3 HANDOFF, now noted here).
- Live server smoke test: login, `/dashboard`, `/intelligence/trust`,
  `/intelligence/risks`, `/intelligence/risks/{id}` all hit with curl
  against the real running app, real responses inspected by hand.
- The Postgres *service process* stopped between tool calls at one point
  in this session (sandbox process lifecycle, not a data issue) — the
  on-disk cluster was intact; `service postgresql start` recovered all
  14,400 rows with zero loss. Worth knowing if it happens again.

## What was built — Priority 1: Trust Intelligence

New file: `app/services/trust_intelligence.py` (`TrustIntelligenceService`).

Wraps, does not replace, `DashboardService`'s existing deterministic score
(same 5 weighted components, same formula). Adds:
- `trust_level` — deterministic band (Strong/Adequate/At Risk/Critical).
- `trust_domains` — the 5 components as ranked, labelled, weighted entries.
- `positive_contributors` / `negative_contributors` — domains above 0.80 /
  below 0.60 respectively (both thresholds are constants in the file).
- `score_change` — **real**, not fabricated: a new `trust_score_snapshots`
  table (migration `3e5422bdcfdf`, the only new table this session added)
  stores every computed score; each call diffs against the immediately
  prior one. First-ever call returns an explicit baseline status, not an
  invented delta. Verified in `tests/test_intelligence.py` — a second
  call in the same test run produces `delta == 0.0` exactly, because
  nothing changed between the two calls.
- `top_risk_drivers` — real open Critical/High risk rows, not a model output.
- `recommended_actions` — deterministic templates filled with real live
  counts (open critical findings, controls missing evidence, privileged
  accounts without MFA, high-risk vendors). Every entry carries
  `"generated_by": "deterministic_rules_v1"` so nothing downstream can
  mistake this for LLM output — this is Level 1 of the brief's AI Strategy,
  structured so Level 2 (an LLM call) can replace just `_recommend()` later.

Endpoint: `GET /api/v1/intelligence/trust`. Verified live: real Trust
Score 61.3 ("At Risk"), real domain breakdown, real risk drivers, real
recommendations, all traceable to the 14,400 ingested rows.

## What was built — Priority 2: Risk Intelligence

New file: `app/services/risk_intelligence.py` (`RiskIntelligenceService`).

Builds on the exact same verified FK chain `detail_router.risk_detail`
already uses (`risk.mapped_control_id -> control`, then
`findings.control_id` / `evidence.control_id` for the rest) — does not
duplicate or modify that endpoint, adds an explanation layer beside it:
- `risk_score` — `severity_weight * likelihood_weight`, both fixed
  integer scales, used to rank `top_risks()`.
- `priority` — banded from `risk_score`.
- `risk_drivers` — plain-language sentences built from real control /
  finding / evidence counts for that specific risk.
- `confidence` — **not** a model confidence score; a deterministic label
  for how much structured data actually backs the explanation (no mapped
  control = low, mapped control with both findings and evidence = high).
- `affected_assets` (detail endpoint only) — **explicitly labelled** as a
  department-level correlation via `owner_department`, never presented as
  a verified per-row relationship, because — confirmed empirically back in
  Phase 1 profiling — no such FK exists in the source data. This is the
  one place in the intelligence layer where the honesty requirement in
  the brief ("do not invent relationships") had a real, structurally
  necessary consequence, not just a talking point.

Endpoints: `GET /api/v1/intelligence/risks?limit=N` (ranked list),
`GET /api/v1/intelligence/risks/{risk_id}` (full explanation, 404 for
unknown IDs — verified). Verified live with real risk IDs from the
database (e.g. `RISK-96518`, "Weak Password Policy Enforcement").

## Tests added

`tests/test_intelligence.py` — 7 tests, 6 passing + 1 honest skip (every
risk in this dataset happens to have a mapped control, so the "no mapped
control" graceful-degradation test has nothing to exercise; it's written
correctly and will run the moment such a row exists). Combined suite:
**67 passed, 1 skipped, 68 total** (up from 61/61 — nothing removed or
weakened, everything net-new).

## Explicitly NOT done this session

Evidence Intelligence, Policy Intelligence, Compliance Copilot,
Remediation Intelligence, Continuous Monitoring, Sentinel Orchestrator,
RAG/Knowledge Layer — all Priority 3+ in the Phase 2 brief, all
untouched. No frontend wiring for the two new endpoints either (the
existing Trust Score / Risk Center screens still call `/dashboard` and
`/risks/{id}` exactly as before; connecting them to
`/intelligence/trust` and `/intelligence/risks/{id}` is the natural next
step and is *pure addition* — those screens' existing behavior doesn't
need to change, just gain new panels).

## Files added/changed this session

- `app/models/trust.py` (new) — `TrustScoreSnapshot`
- `app/models/__init__.py` (edited) — registered the new model
- `migrations/versions/3e5422bdcfdf_add_trust_score_snapshots.py` (new, autogenerated)
- `app/services/trust_intelligence.py` (new)
- `app/services/risk_intelligence.py` (new)
- `app/api/v1/routers/intelligence_router.py` (new)
- `app/main.py` (edited) — one import line, one `include_router` line
- `tests/test_intelligence.py` (new)
- Nothing existing was rewritten. `git diff`-equivalent is purely additive
  except the two one-line edits to `models/__init__.py` and `main.py`.
