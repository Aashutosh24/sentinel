You are continuing work on **Sentinel AI**, an AI-powered Governance, Risk &
Compliance platform, for a hackathon. This is a continuation session picking
up a checkpoint left by a prior session that deliberately stopped after
Phase 2 Priorities 1-2 to guarantee a verified handoff.

## Before you write or change anything

1. Read `HANDOFF.md` in full, especially the "PHASE 2 UPDATE" section at
   the end - it documents exactly what Trust Intelligence and Risk
   Intelligence do, why, and what's verified vs. not.
2. Read `IMPLEMENTATION_STATUS.md` in full, especially its Phase 2 table.
3. Confirm the environment still works:
   ```bash
   service postgresql start   # the service process does not survive between
                               # some tool-call boundaries in this sandbox;
                               # the on-disk data does - this happened once
                               # already this session with zero data loss
   pip install -e ".[dev]"
   alembic upgrade head       # should report "already at head", not error
   python3 -m pytest -q       # expect: 67 passed, 1 skipped
   ```
4. If data is missing (fresh environment, not just a stopped service):
   ```bash
   python3 -m app.ingestion.run     # expect: TOTAL 14400 inserted, 0 errors
   python3 scripts/seed_users.py    # needed before login-dependent tests/demo
   ```

## Hard rules

- **DO NOT redesign the architecture** (Clean Architecture layering,
  Postgres schema, the 5-component deterministic Trust Score formula).
- **DO NOT rewrite `app/services/trust_intelligence.py` or
  `risk_intelligence.py` from scratch.** They're built, tested, and
  verified against real data. Extend them or add new services beside them.
- **DO NOT invent relationships not present in the data.** Everything
  about the 15 real datasets is verified in `docs/profiling/` and
  summarized in `HANDOFF.md`. In particular: Vendors have no FK to
  anything; Risk has no FK to specific assets, only `owner_department`
  (a correlation, not a relationship - see `_department_footprint` in
  `risk_intelligence.py` for how that's handled honestly).
- **DO NOT fabricate metrics, scores, or AI results.** Every number in
  the intelligence layer traces back to a live query. If you add an LLM
  call, label its output distinctly from the deterministic
  `"generated_by": "deterministic_rules_v1"` fields already in place.
- **DO NOT break the 67/68 test baseline.** Run `pytest` after every
  change. If a change legitimately requires updating a test's
  expectation, update it - don't delete or weaken it to make it pass.
- **Prioritize a working hackathon MVP** over completeness across all 9
  Phase 2 priorities.

## Your task, in order (per the Phase 2 brief's own stopping rule)

The brief that drove this work is explicit: "If enough time remains for
three [features]: Policy -> Control -> Risk -> Evidence -> Trust -> Copilot."
Trust and Risk are done. Continue in this order:

1. **Priority 3 - Evidence Intelligence.** Create
   `app/services/evidence_intelligence.py`: per-control required vs.
   available evidence, coverage %, gaps, freshness (using
   `evidence.collected_date`, real column, already ingested), related
   findings/risks via the same `control_id` join pattern the other two
   services use. Add `GET /api/v1/intelligence/evidence/{control_id}` (or
   a coverage-by-control list) to `intelligence_router.py`. Write tests
   in the style of `tests/test_intelligence.py`.
2. **Priority 4 - Policy Intelligence.** The brief explicitly says: don't
   build RAG first, build the smallest reliable pipeline; if no LLM
   access, build a deterministic extraction layer clearly structured for
   later LLM replacement (same pattern as `_recommend()` in
   `trust_intelligence.py`) - never present deterministic extraction as
   generative AI.
3. **Priority 5 - Compliance Copilot.** `POST /api/v1/copilot/query`,
   answering from real data (reuse Trust/Risk/Evidence Intelligence as
   the data sources a rule-based or LLM-backed copilot draws from - this
   is exactly what "Sentinel Orchestrator" (Priority 8) formalizes later,
   but you don't need that layer to make Copilot work now).
4. Only after 3-5 are solid and tested: Remediation (6), Monitoring (7),
   Orchestrator (8), RAG (9), each following the same
   "build -> verify against real data -> test -> document -> checkpoint"
   discipline this session and the ones before it used.
5. **Frontend wiring is still open for Trust + Risk Intelligence too** -
   the existing Command Center / Risk Center screens work against
   `/dashboard` and `/risks/{id}`; adding the new explanation panels the
   original brief describes (positive/negative contributors, "why is this
   risk important", recommended actions) from `/intelligence/trust` and
   `/intelligence/risks/{id}` is pure UI addition, no backend change
   needed, and would make the existing verified backend work visible.

## Checkpoint discipline

If you get close to a context/usage limit before finishing: stop starting
new work, run the full test suite, update `HANDOFF.md` /
`IMPLEMENTATION_STATUS.md` with what's actually true (not what was
planned), and produce a freshly verified zip - extracted into a clean
directory and re-imported, not just asserted to exist. That discipline
is why this handoff is trustworthy; keep it going.
