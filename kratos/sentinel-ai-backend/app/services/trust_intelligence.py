"""
Trust Intelligence — Phase 2, Priority 1.

Upgrades (does NOT replace) the Phase 1 deterministic Trust Score in
DashboardService. That service still owns the actual formula and the five
weighted components (`control_evidence_coverage`, `finding_health`,
`risk_health`, `asset_hygiene`, `identity_hygiene`) — this service calls it,
then adds the explanation layer: banding, contributor ranking, a real score
history (see app/models/trust.py), concrete risk drivers, and recommended
actions. Every number below is either read straight out of
`DashboardService.build()` or computed from a live query against Risk/
Finding/Control/Evidence — nothing is invented.

Level 1 of the AI Strategy in the brief ("deterministic intelligence").
Structured so Level 2 (LLM enhancement) can later replace `_recommend()`
and the narrative in `top_risk_drivers` without touching the scoring path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Control, Finding, Risk, TrustScoreSnapshot
from app.services.dashboard import DashboardService

LEVEL_BANDS = (
    (85, "Strong"),
    (70, "Adequate"),
    (50, "At Risk"),
    (0, "Critical"),
)

# A domain counts as a positive contributor above this, negative below this.
# Deliberately not 0.5/0.5 — a component sitting at exactly "half" isn't
# meaningfully helping or hurting, so it's reported as neutral instead of
# padding one list or the other with noise.
POSITIVE_THRESHOLD = 0.80
NEGATIVE_THRESHOLD = 0.60

DOMAIN_LABELS = {
    "control_evidence_coverage": "Evidence coverage",
    "finding_health": "Finding health",
    "risk_health": "Risk health",
    "asset_hygiene": "Asset hygiene",
    "identity_hygiene": "IAM hygiene",
}


def _level(score: float) -> str:
    for floor, label in LEVEL_BANDS:
        if score >= floor:
            return label
    return "Critical"


class TrustIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(self) -> dict[str, Any]:
        db = self.db
        dashboard = await DashboardService(db).build(include_scores=True)
        trust = dashboard["trust_score"]
        readiness = dashboard["audit_readiness"]

        if trust.get("value") is None:
            return {
                "trust_score": None,
                "status": trust.get("status", "pending Phase 2 scoring engine"),
                "note": "Deterministic score unavailable — call /dashboard without ?scores=off first.",
            }

        domains = [
            {
                "key": key,
                "label": DOMAIN_LABELS.get(key, key),
                "value": value,
                "value_pct": round(value * 100, 1),
                "weight": trust["weights"][key],
                "contribution_points": round(value * trust["weights"][key] * 100, 2),
            }
            for key, value in trust["components"].items()
        ]
        domains.sort(key=lambda d: d["contribution_points"], reverse=True)

        positive = [d for d in domains if d["value"] >= POSITIVE_THRESHOLD]
        negative = sorted(
            (d for d in domains if d["value"] < NEGATIVE_THRESHOLD),
            key=lambda d: d["value"],
        )

        top_risk_drivers = await self._top_risk_drivers()
        score_change = await self._record_and_diff(trust["value"], readiness["value"], trust["components"])
        recommended_actions = await self._recommend(negative, top_risk_drivers, dashboard)

        return {
            "trust_score": trust["value"],
            "trust_level": _level(trust["value"]),
            "engine": trust["engine"],
            "formula": trust["formula"],
            "trust_domains": domains,
            "positive_contributors": positive,
            "negative_contributors": negative,
            "score_change": score_change,
            "top_risk_drivers": top_risk_drivers,
            "evidence_coverage": dashboard["evidence_coverage"],
            "control_coverage": dashboard["compliance_coverage"],
            "audit_readiness": readiness,
            "recommended_actions": recommended_actions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": trust["note"],
        }

    async def _top_risk_drivers(self, limit: int = 5) -> list[dict[str, Any]]:
        """Real open Critical/High risks, ranked. Not a model score — a
        direct read of the same rows a reviewer would click into on the
        Risk Center screen."""
        stmt = (
            select(Risk)
            .where(Risk.severity.in_(("Critical", "High")))
            .where(Risk.current_status.in_(("Open", "In Remediation")))
            .order_by(
                (Risk.severity == "Critical").desc(),
                desc(Risk.risk_id),
            )
            .limit(limit)
        )
        risks = (await self.db.execute(stmt)).scalars().all()

        drivers = []
        for risk in risks:
            open_findings = 0
            if risk.mapped_control_id:
                count_stmt = select(Finding).where(
                    Finding.control_id == risk.mapped_control_id,
                    Finding.status.in_(("Open", "In Progress")),
                )
                open_findings = len((await self.db.execute(count_stmt)).scalars().all())
            drivers.append(
                {
                    "risk_id": risk.risk_id,
                    "risk_name": risk.risk_name,
                    "severity": risk.severity,
                    "status": risk.current_status,
                    "owner_department": risk.owner_department,
                    "mapped_control_id": risk.mapped_control_id,
                    "open_findings_on_control": open_findings,
                }
            )
        return drivers

    async def _record_and_diff(
        self, trust_score: float, audit_readiness: float, components: dict[str, float]
    ) -> dict[str, Any]:
        """Persist this computation as a snapshot, then diff against the
        immediately preceding one. Real history, real delta — see
        app/models/trust.py for why this table exists."""
        prior_stmt = select(TrustScoreSnapshot).order_by(desc(TrustScoreSnapshot.computed_at)).limit(1)
        prior = (await self.db.execute(prior_stmt)).scalar_one_or_none()

        snapshot = TrustScoreSnapshot(
            trust_score=trust_score,
            audit_readiness=audit_readiness,
            components=components,
        )
        self.db.add(snapshot)
        await self.db.commit()

        if prior is None:
            return {
                "delta": None,
                "prior_score": None,
                "prior_computed_at": None,
                "status": "baseline — this is the first recorded snapshot, nothing to compare against yet",
            }
        return {
            "delta": round(trust_score - prior.trust_score, 1),
            "prior_score": prior.trust_score,
            "prior_computed_at": prior.computed_at.isoformat(),
            "status": "compared against the immediately preceding snapshot",
        }

    async def _recommend(
        self,
        negative: list[dict[str, Any]],
        top_risk_drivers: list[dict[str, Any]],
        dashboard: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Deterministic, template-based — every number plugged in is a
        real count from this call. Labelled `generated_by` so nothing
        downstream mistakes this for an LLM. This is exactly the seam
        the brief asks for: swap the template for an LLM call later
        without touching what feeds it."""
        actions: list[dict[str, Any]] = []

        critical_open = dashboard["findings"]["critical_open"]
        if critical_open > 0:
            control_ids = sorted({d["mapped_control_id"] for d in top_risk_drivers if d["mapped_control_id"]})
            control_ref = f" (controls: {', '.join(control_ids[:3])})" if control_ids else ""
            actions.append(
                {
                    "priority": "Critical",
                    "action": f"Resolve {critical_open} open Critical-severity finding(s){control_ref}.",
                    "basis": "findings.severity = Critical AND findings.status IN (Open, In Progress)",
                }
            )

        gap = dashboard["evidence_coverage"]["controls_without_evidence"]
        if gap > 0:
            actions.append(
                {
                    "priority": "High",
                    "action": f"Attach evidence to {gap} control(s) with none on file.",
                    "basis": "controls with zero rows in evidence for that control_id",
                }
            )

        priv_no_mfa = dashboard["iam_statistics"]["privileged_without_mfa"]
        if priv_no_mfa > 0:
            actions.append(
                {
                    "priority": "High",
                    "action": f"Enforce MFA on {priv_no_mfa} privileged account(s) currently without it.",
                    "basis": "iam_records.privileged_account = true AND mfa_enabled = false",
                }
            )

        vendor_ratings = dashboard["vendor_risk"]["by_risk_rating"]
        high_risk_vendors = vendor_ratings.get("Critical", 0) + vendor_ratings.get("High", 0)
        if high_risk_vendors > 0:
            actions.append(
                {
                    "priority": "Medium",
                    "action": f"Review {high_risk_vendors} vendor(s) rated Critical/High risk.",
                    "basis": "vendors.risk_rating IN (Critical, High)",
                }
            )

        for item in actions:
            item["generated_by"] = "deterministic_rules_v1"
        return actions[:5]
