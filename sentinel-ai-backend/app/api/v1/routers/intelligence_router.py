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

from app.database.session import get_db
from app.services.copilot import INTENTS, SUGGESTED_QUESTIONS, CopilotService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.policy_intelligence import PolicyIntelligenceService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.trust_intelligence import TrustIntelligenceService

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
    question: str = Field(..., min_length=3, max_length=500)


@router.post(
    "/copilot/query",
    tags=["copilot"],
    summary="Ask the Compliance Copilot a question answered from live database data",
    description=(
        "Intent routing over the existing intelligence services — no language model is "
        "involved (`llm_used: false`). Every figure in an answer comes from a live "
        "query, and every answer carries the endpoints it was composed from. A question "
        "that matches no intent returns `intent: \"unknown\"` and the supported "
        "questions, rather than an improvised answer."
    ),
    response_model=None,
)
async def copilot_query(body: CopilotQuery, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await CopilotService(db).answer(body.question)
    return {"data": result, "error": None}


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
