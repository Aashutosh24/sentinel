You are continuing **Sentinel AI**, a full-stack GRC platform, for a hackathon.
This is a continuation session. **Phase 2B backend intelligence is complete and
tested; its frontend UI is not built.** That gap is your first job.

## Read first

1. `HANDOFF.md` — read the **PHASE 2B** section at the end. It covers the
   evidence coverage formula, why there is no LLM, the mapping-honesty rules,
   and the known limitations.
2. `IMPLEMENTATION_STATUS.md` — the per-priority DONE/NOT DONE tracker.

## Bring it up

```bash
# backend
cd sentinel-ai-backend
bash scripts/setup_postgres.sh      # the cluster does not survive a restart; data does
cp .env.example .env                # REQUIRED — a missing .env makes uvicorn fail silently
alembic upgrade head
python -m app.ingestion.run         # only if the DB is empty; expect TOTAL 14400
python scripts/seed_users.py
uvicorn app.main:app --reload --port 8000

# frontend
npm install
chmod +x node_modules/.bin/*        # some sandboxes need this
npm run dev
```

Verify the baseline before trusting anything written above:

```bash
python -m pytest                    # expect 105 passed, 1 skipped
curl http://localhost:8000/api/v1/intelligence/evidence | head -c 300
curl -X POST http://localhost:8000/api/v1/copilot/query \
  -H 'Content-Type: application/json' -d '{"question":"Are we audit ready?"}'
node node_modules/vite/bin/vite.js build   # must exit 0
```

## Hard rules

- **Do not rebuild the backend.** Models, schema, migrations, ingestion,
  dashboard, graph, Trust/Risk/Evidence/Policy/Copilot services all work.
  If you change backend code, re-run `python -m pytest` — **105 passed,
  1 skipped is the baseline. Do not weaken or delete tests.**
- **Do not redesign the UI.** Preserve the dark cyber identity, Command
  Center, graph, charts, drawers, animations. Add components; don't restyle.
- **Do not claim AI where there is none.** No LLM is configured. Policy
  analysis and the Copilot are deterministic and every response says so
  (`llm_used: false`). Surface that honestly in the UI — a small "rule-based"
  or "deterministic" label — rather than implying generation.
- **Do not invent relationships.** Vendors link to nothing. Reports don't link
  to findings. Personal data doesn't link to consent. Evidence freshness is not
  derivable. Respect these; tests enforce some of them.
- **Do not start RAG, Qdrant, or a multi-agent framework.**

## Do these, in order

1. **Frontend for the three Phase 2B features — highest value by far.**
   The typed API bindings already exist in `src/services/api.ts`; nothing new
   is needed on the backend:

   | Binding | Build |
   |---|---|
   | `getEvidenceIntelligence()` / `getEvidenceCoverage()` | Evidence Coverage panel + Gap drawer on the Evidence Repository page |
   | `getControlEvidence(controlId)` | "Can we prove this control works?" section in the control drawer |
   | `analyzePolicyText()` / `analyzeStoredPolicy()` | "Analyze Policy" workflow on the Policies page — requirements → mapped controls → current state → gaps |
   | `askCopilot()` / `getCopilotSuggestions()` | Replace the seeded conversation on `pages/Copilot.tsx` with real answers: answer text, supporting-data tiles, related-entity cards, recommendations, source references |

   Use `useApiResource` + `AsyncSection` for loading/error/retry, as every
   other connected page does. Render `mapping_note` ("No verified control
   mapping found.") wherever it appears — that string is the honesty guarantee
   and must be visible, not filtered out.

2. **Remediation Intelligence (Priority 4).** `RemediationService` over
   risk / finding / control / evidence gap, returning
   `recommended_action, priority, owner, reason, expected_outcome,
   required_evidence`. Much of the raw material already exists —
   `findings.recommendation` is a real column, and Evidence Intelligence
   already produces per-gap `why` text. Recommendations only; execute nothing.

3. **Continuous Monitoring (Priority 5)** — only if 1 and 2 are done. A simple
   database-backed change check. No Kafka, no streaming.

## Checkpoint discipline

A session two back ran out of budget before producing a ZIP. This session
checkpointed after each priority and refreshed the ZIP each time — keep doing
that. **Produce a verified ZIP at roughly the halfway point, then refresh it.**

Exclude: `node_modules`, `dist`, `.env`, `__pycache__`, `.pytest_cache`,
`*.egg-info`. Verify by extracting to a clean directory, importing the backend,
running the tests, and building the frontend.
