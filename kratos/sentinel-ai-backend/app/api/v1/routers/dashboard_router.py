"""Dashboard, framework rollup and organization graph endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.dashboard import DashboardService, framework_summaries
from app.services.graph import GraphService

router = APIRouter()


@router.get(
    "/dashboard",
    tags=["dashboard"],
    summary="Command Center aggregate — every figure computed live from the database",
    description=(
        "Single aggregation call for the Command Center screen. Pass `?scores=off` to "
        "return `trust_score` / `audit_readiness` as explicit nulls instead of the "
        "deterministic Phase 1 score."
    ),
    response_model=None,
)
async def dashboard(
    scores: str = Query("on", pattern="^(on|off)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    payload = await DashboardService(db).build(include_scores=scores == "on")
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    return {"data": payload, "error": None}


@router.get(
    "/frameworks",
    tags=["frameworks"],
    summary="Framework rollup (aggregated live — there is no frameworks table)",
    response_model=None,
)
async def frameworks(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    summaries = await framework_summaries(db)
    return {
        "data": summaries,
        "meta": {
            "count": len(summaries),
            "derivation": "policies -> controls -> evidence/findings, grouped by policies.framework",
            "note": "Framework is a shared vocabulary across policies and reports, not a table.",
        },
        "error": None,
    }


@router.get("/frameworks/{framework}", tags=["frameworks"], summary="One framework's rollup", response_model=None)
async def framework_detail(framework: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    summaries = await framework_summaries(db)
    match = next((s for s in summaries if s["framework"].lower() == framework.lower()), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Framework '{framework}' not found")
    return {"data": match, "error": None}


@router.get(
    "/organization/graph",
    tags=["organization"],
    summary="Graph-ready nodes + edges in a single call",
    description=(
        "One request instead of twenty. `scope=org` returns the people layer "
        "(employees, devices, IAM identities, cloud assets); `scope=governance` returns "
        "policies -> controls -> findings/evidence/risks; `scope=full` returns both. "
        "Every edge maps to a verified foreign key — see `meta.relationship_sources`."
    ),
    response_model=None,
)
async def organization_graph(
    scope: str = Query("full", pattern="^(org|governance|full)$"),
    employee_id: str | None = Query(None, description="Focus the people layer on one employee's neighbourhood"),
    department: str | None = Query(None),
    limit_employees: int = Query(150, ge=1, le=500),
    include_activity: bool = Query(False, description="Add aggregated employee->application ACCESSED/CONSENTED_TO edges"),
    include_vendors: bool = Query(False, description="Add vendors as unconnected nodes (no FK exists)"),
    include_privacy: bool = Query(False, description="Add application->personal_data PROCESSES edges"),
    aggregated: bool = Query(False, description="Return high-level Enterprise GRC Relationship Map"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if aggregated:
        graph = await GraphService(db).build_aggregated()
    else:
        graph = await GraphService(db).build(
            scope=scope,
            employee_id=employee_id,
            department=department,
            limit_employees=limit_employees,
            include_activity=include_activity,
            include_vendors=include_vendors,
            include_privacy=include_privacy,
        )
    return {"data": graph, "error": None}
