"""
Phase 2 intelligence endpoints — Priority 1 (Trust) and Priority 2 (Risk).

Additive only: nothing here modifies dashboard_router, detail_router, or
their services. Same response envelope and `response_model=None` pattern
as the rest of the API.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.auth_router import require_roles
from app.database.session import get_db
from app.models.enums import UserRole
from app.services.copilot import INTENTS, SUGGESTED_QUESTIONS, CopilotService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.policy_intelligence import PolicyIntelligenceService
from app.services.remediation_intelligence import RemediationIntelligenceService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.trust_intelligence import TrustIntelligenceService
from app.services.monitoring_intelligence import ContinuousMonitoringService
from app.services.sentinel_orchestrator import SentinelOrchestratorService

router = APIRouter()


@router.get(
    "/intelligence/trust",
    tags=["intelligence"],
    summary="Explainable Trust Score: level, contributors, drivers, recommendations",
    description=(
        "Upgrades the Phase 1 deterministic Trust Score (unchanged, still computed by "
        "DashboardService) with an explanation layer: which domains are helping/hurting, "
        "the real change since the last time this endpoint was called, the top risks "
        "driving the score down, and deterministic recommended actions."
    ),
    response_model=None,
)
async def trust_intelligence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await TrustIntelligenceService(db).build()
    return {"data": result, "error": None}


@router.get(
    "/intelligence/risks",
    tags=["intelligence"],
    summary="Open risks ranked by a transparent numeric score, each with drivers and a recommendation",
    response_model=None,
)
async def risk_intelligence_top(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = await RiskIntelligenceService(db).top_risks(limit=limit)
    return {
        "data": results,
        "meta": {"count": len(results), "ranking": "severity_weight * likelihood_weight, both fixed scales"},
        "error": None,
    }


@router.get(
    "/intelligence/risks/{risk_id}",
    tags=["intelligence"],
    summary="Why this risk is important, what's affected, and what to do about it",
    response_model=None,
)
async def risk_intelligence_detail(risk_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await RiskIntelligenceService(db).explain(risk_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Risk '{risk_id}' not found")
    return {"data": result, "error": None}


@router.get(
    "/intelligence/remediation",
    tags=["intelligence"],
    summary="Top open findings that require remediation, prioritized by severity",
    response_model=None,
)
async def remediation_intelligence_top(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = await RemediationIntelligenceService(db).top_remediations(limit=limit)
    return {
        "data": results,
        "meta": {"count": len(results), "ranking": "severity"},
        "error": None,
    }


@router.get(
    "/intelligence/remediation/{finding_id}",
    tags=["intelligence"],
    summary="Deep dive into a specific finding and its step-by-step remediation plan",
    response_model=None,
)
async def remediation_intelligence_detail(finding_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await RemediationIntelligenceService(db).explain_remediation(finding_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    return {"data": result, "error": None}


@router.get(
    "/intelligence/monitoring/anomalies",
    tags=["intelligence"],
    summary="Recent high-risk actions and failed sensitive operations from audit logs",
    response_model=None,
)
async def continuous_monitoring_anomalies(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = await ContinuousMonitoringService(db).get_anomalies(limit=limit)
    return {
        "data": results,
        "meta": {"count": len(results), "criteria": "risk_score >= 80 OR result == 'Failure'"},
        "error": None,
    }


@router.get(
    "/intelligence/monitoring/metrics",
    tags=["intelligence"],
    summary="Aggregated metrics for continuous monitoring dashboard",
    response_model=None,
)
async def continuous_monitoring_metrics(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = await ContinuousMonitoringService(db).get_metrics()
    return {"data": results, "error": None}


@router.get(
    "/intelligence/orchestrator/summary",
    tags=["intelligence", "orchestrator"],
    summary="State of the Union executive summary across all intelligence engines",
    response_model=None,
)
async def orchestrator_summary(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    results = await SentinelOrchestratorService(db).generate_executive_summary()
    return {"data": results, "error": None}


@router.get(
    "/intelligence/evidence",
    tags=["intelligence"],
    summary="Evidence posture summary: coverage, gap counts, top gaps by severity",
    description=(
        "Header-level answer to 'can we prove our controls work'. Coverage counts a "
        "control as covered only when it has at least one VERIFIED evidence item; the "
        "formula and adequacy rule ship in the response. No freshness judgement is made "
        "— the dataset defines no validity period."
    ),
    response_model=None,
)
async def evidence_intelligence(
    gap_limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await EvidenceIntelligenceService(db).summary(gap_limit=gap_limit)
    return {"data": result, "error": None}


@router.get(
    "/intelligence/evidence/coverage",
    tags=["intelligence"],
    summary="Full evidence coverage including every gap and a per-framework breakdown",
    response_model=None,
)
async def evidence_coverage(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await EvidenceIntelligenceService(db).coverage()
    gaps = result["evidence_gaps"]
    return {
        "data": result,
        "meta": {"gap_count": len(gaps), "formula": result["formula"]},
        "error": None,
    }


@router.get(
    "/intelligence/evidence/{evidence_id}",
    tags=["intelligence"],
    summary="One evidence item: what it proves, which findings cite it, which risks it touches",
    response_model=None,
)
async def evidence_detail(evidence_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await EvidenceIntelligenceService(db).explain_evidence(evidence_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
    return {"data": result, "error": None}


@router.get(
    "/intelligence/controls/{control_id}/evidence",
    tags=["intelligence"],
    summary="Can we prove this control works? Evidence, open findings and related risks",
    response_model=None,
)
async def control_evidence(control_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await EvidenceIntelligenceService(db).control_evidence(control_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Control '{control_id}' not found")
    return {"data": result, "error": None}


class PolicyAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Raw policy text to analyse")
    title: str | None = Field(None, description="Optional document title")


@router.post(
    "/intelligence/policy/analyze",
    tags=["intelligence"],
    summary="Extract requirements from policy text and map them to real controls",
    description=(
        "Deterministic, rule-based extraction — **no LLM is configured in this "
        "project**, and the response says so (`llm_used: false`, "
        "`engine: rule_based_v1`). Requirements that do not clear the lexical match "
        "threshold are returned unmapped with 'No verified control mapping found.' "
        "rather than matched to a nearest guess. Each mapped requirement is then "
        "assessed against real evidence, findings and risks."
    ),
    response_model=None,
)
async def analyze_policy(
    body: PolicyAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await PolicyIntelligenceService(db).analyze_text(body.text, title=body.title)
    return {"data": result, "error": None}


@router.get(
    "/intelligence/policies/{policy_id}",
    tags=["intelligence"],
    summary="Analyse a stored policy: its real controls, coverage and compliance gaps",
    response_model=None,
)
async def analyze_stored_policy(
    policy_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    result = await PolicyIntelligenceService(db).analyze_stored_policy(policy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return {"data": result, "error": None}


class CopilotQuery(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


@router.post(
    "/copilot/query",
    tags=["copilot"],
    summary="Ask the Compliance Copilot a question answered from live database data",
    description=(
        "Intent routing over the existing intelligence services, now upgraded to "
        "fast-path deterministic intents first to reduce LLM latency, and falling back to "
        "the general GRC engine."
    ),
    response_model=None,
)
async def copilot_query(body: CopilotQuery, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.grc_engine.reasoning_service import answer as general_answer
    from app.services.copilot import CopilotService
    
    # 1. Fast path for known deterministic intents (saves 1 LLM call)
    copilot = CopilotService(db)
    intent, confidence = copilot._match_intent(body.question)
    if intent is not None and confidence == "high":
        legacy_result = await copilot.answer(body.question)
        return {"data": legacy_result, "error": None}

    # 2. Ask the new general engine. It falls back to CopilotService internally if needed.
    result = await general_answer(db, body.question)

    if result.legacy_result:
        # If it fell back to CopilotService, return the exact old schema
        return {"data": result.legacy_result, "error": None}

    # Map GeneralAnswer to the legacy schema expected by the frontend UI
    supporting_data = []
    if isinstance(result.metrics, dict):
        supporting_data = [{"label": k, "value": v} for k, v in result.metrics.items() if isinstance(v, (int, float, str))]

    related_entities = []
    for e in result.evidence:
        # e is shaped like {"table": "vendors", "name": "Vendor A", ...}
        # map to {"type": ..., "id": ..., "label": ..., "detail": ...}
        keys = list(e.keys())
        type_val = e.get("table", "unknown")
        # Find ID and label heuristically based on the _row_identity dict
        id_val = e.get(keys[1], "?") if len(keys) > 1 else "?"
        label_val = e.get(keys[2], id_val) if len(keys) > 2 else id_val
        related_entities.append({
            "type": type_val,
            "id": str(id_val),
            "label": str(label_val),
            "detail": ""
        })

    return {
        "data": {
            "answer": result.answer,
            "supporting_data": supporting_data,
            "related_entities": related_entities,
            "recommendations": result.recommendations,
            "intent": result.question_type,
            "intent_label": result.question_type.replace("_", " ").title(),
            "confidence": "none" if result.question_type == "unsupported" else ("high" if result.confidence > 0.8 else "medium"),
            "sources": result.datasets_used,
            "engine": result.engine,
            "llm_used": result.llm_used,
        },
        "error": None
    }


class GeneralAIQuery(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    conversation_id: str | None = None
    user_context: dict[str, Any] = Field(default_factory=dict)


# In-memory, single-process conversation memory: conversation_id -> the last
# question and a one-line summary of its answer, so a follow-up like "which
# one is the worst?" can resolve "one" without the caller re-sending full
# history. Deliberately NOT a database table or a cache service — brief
# section 23 asks for multi-turn memory, not durability, and this is a
# hackathon-scope general engine sitting next to a Copilot that already
# keeps its own history client-side. Lost on restart; that's an accepted
# scope boundary, not an oversight.
_CONVERSATION_MEMORY: dict[str, str] = {}
_MAX_CONVERSATIONS = 500


@router.post(
    "/ai/query",
    tags=["ai"],
    summary="General-purpose GRC reasoning: ask any governance/risk/compliance/security/privacy question",
    description=(
        "Unlike /copilot/query (a fixed 12-intent matcher), this endpoint understands "
        "arbitrary natural-language GRC questions: an LLM proposes which precomputed metrics "
        "and/or which real, schema-verified row-level query would answer the question, "
        "every table/column/join name is re-validated against the real database schema before "
        "anything executes (a fabricated relationship is rejected, never approximated), and the "
        "LLM only ever narrates already-fetched, already-correct data — it cannot alter numbers "
        "or invent entity IDs. If the question requires a relationship that doesn't exist in this "
        "schema (e.g. vendor-to-personal-data), the response says so explicitly instead of "
        "guessing (`engine: \"insufficient_data_v1\"`). If the general engine itself is "
        "unavailable (no LLM_API_KEY, timeout, error), this falls back to the existing "
        "deterministic Copilot rather than returning nothing."
    ),
    response_model=None,
)
async def ai_query(body: GeneralAIQuery, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.grc_engine.reasoning_service import answer as general_answer

    context = _CONVERSATION_MEMORY.get(body.conversation_id) if body.conversation_id else None
    result = await general_answer(db, body.question, conversation_context=context)

    if body.conversation_id:
        if len(_CONVERSATION_MEMORY) >= _MAX_CONVERSATIONS:
            _CONVERSATION_MEMORY.pop(next(iter(_CONVERSATION_MEMORY)))
        _CONVERSATION_MEMORY[body.conversation_id] = (
            f"Q: {body.question!r} -> {result.answer[:300]}"
        )

    return {
        "data": {
            "question": result.question,
            "question_type": result.question_type,
            "answer": result.answer,
            "datasets_used": result.datasets_used,
            "records_analyzed": result.records_analyzed,
            "evidence": result.evidence,
            "metrics": result.metrics,
            "recommendations": result.recommendations,
            "confidence": result.confidence,
            "engine": result.engine,
            "llm_used": result.llm_used,
            "reasoning_notes": result.reasoning_notes,
            "missing_data": result.missing_data,
            "available_data": result.available_data,
        },
        "error": None,
    }


@router.get(
    "/copilot/suggestions",
    tags=["copilot"],
    summary="Questions the Copilot can answer from real data",
    response_model=None,
)
async def copilot_suggestions() -> dict[str, Any]:
    return {
        "data": {
            "suggested_questions": SUGGESTED_QUESTIONS,
            "intents": [
                {"intent": i.name, "label": i.label, "example": i.example} for i in INTENTS
            ],
            "engine": "deterministic_intent_v1",
            "llm_used": False,
        },
        "error": None,
    }
