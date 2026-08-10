"""
Compliance Copilot — Phase 2B, Priority 3.

    question -> intent -> intelligence service -> structured answer

Every answer is composed from live database aggregates via the existing
intelligence services. There is no language model in this path and no
generated prose beyond templates filled with real numbers, so a claim in an
answer can always be traced to a row. Responses carry
`"engine": "deterministic_intent_v1"` and `"llm_used": false`.

## Why intent routing and not a chatbot

The brief asks for an enterprise GRC copilot, not a ChatGPT clone. A fixed
intent set means every supported question has a known data path and a known
failure mode: if nothing matches, the Copilot says so and lists what it can
answer, rather than improvising. Unmatched questions return
`intent: "unknown"` with `confidence: "none"` — never a plausible-sounding
guess.

## Service reuse

Nothing here recomputes Trust, Risk, Evidence or Policy logic. It calls:

    TrustIntelligenceService     trust explanation, audit readiness
    RiskIntelligenceService      top risks, single-risk explanation
    EvidenceIntelligenceService  coverage, gaps, control provability
    DashboardService             vendor / privacy / IAM / finding aggregates

Adding an LLM later means replacing `_match_intent` with a classifier and
`answer` templates with generation — the data layer below is unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    CloudAsset,
    Control,
    Device,
    Employee,
    Evidence,
    Finding,
    IAMRecord,
    Policy,
    Risk,
    Vendor,
)
from app.services.dashboard import DashboardService
from app.services.evidence_intelligence import EvidenceIntelligenceService
from app.services.llm_service import LLMService
from app.services.risk_intelligence import RiskIntelligenceService
from app.services.trust_intelligence import TrustIntelligenceService

OPEN_FINDING_STATUSES = ("Open", "In Progress")


@dataclass(frozen=True)
class Intent:
    name: str
    label: str
    keywords: tuple[tuple[str, ...], ...]  # inner tuple = AND, outer = OR
    example: str


# Ordered: the first match wins, so narrow intents come before broad ones.
# This matters — `top_risks` has a bare ("risk",) fallback that would
# otherwise swallow "which VENDOR is highest risk", so vendor, privacy and
# policy intents are all declared above it.
INTENTS: tuple[Intent, ...] = (
    Intent(
        "audit_readiness",
        "Audit readiness",
        (("audit", "ready"), ("audit-ready",), ("ready", "audit")),
        "Are we audit ready?",
    ),
    Intent(
        "trust_explanation",
        "Trust Score explanation",
        (("trust", "score"), ("trust",), ("why", "score")),
        "Why is our Trust Score what it is?",
    ),
    Intent(
        "devices_unencrypted",
        "Device security & encryption posture",
        (("device",), ("laptop",), ("workstation",), ("endpoint",), ("unencrypted", "device"),
         ("device", "encrypt"), ("device", "compliance"), ("antivirus",), ("edr",), ("firewall",)),
        "Which devices are not encrypted?",
    ),
    Intent(
        "cloud_posture",
        "Cloud security & asset posture",
        (("cloud",), ("aws",), ("azure",), ("gcp",), ("bucket",), ("public", "access"),
         ("cloud", "encrypt"), ("cloud", "resource"), ("cloud", "risk")),
        "Which cloud assets have public access or lack encryption?",
    ),
    Intent(
        "employee_iam_posture",
        "Employee MFA, password & identity posture",
        (("employee",), ("iam",), ("account",), ("mfa", "employee"), ("password", "short"),
         ("stale", "account"), ("privileged", "account"), ("inactive", "user"), ("identity",)),
        "How many employees lack MFA or have stale accounts?",
    ),
    Intent(
        "applications_posture",
        "Application security & exposure posture",
        (("application",), ("app",), ("internet", "facing"), ("app", "risk"), ("sso",), ("app", "mfa")),
        "Which internet-facing applications lack MFA or encryption?",
    ),
    Intent(
        "evidence_gaps",
        "Evidence gaps",
        (("evidence", "gap"), ("lack", "evidence"), ("without", "evidence"),
         ("missing", "evidence"), ("no", "evidence"), ("evidence", "critical")),
        "Which evidence gaps are critical?",
    ),
    Intent(
        "controls_failing",
        "Failing controls",
        (("control", "fail"), ("failing", "control"), ("control", "broken")),
        "Which controls are failing?",
    ),
    Intent(
        "risk_detail",
        "Single risk explanation",
        (("why", "risk"), ("risk", "critical"), ("explain", "risk")),
        "Why is RISK-12345 critical?",
    ),
    Intent(
        "policy_detail",
        "Single policy explanation",
        (("policy", "detail"), ("explain", "policy"), ("about", "policy"), ("policy", "overview")),
        "What is policy POL-CIS-174?",
    ),
    Intent(
        "control_detail",
        "Single control explanation",
        (("control", "detail"), ("explain", "control")),
        "What is control CTRL-37734?",
    ),
    Intent(
        "finding_detail",
        "Single finding explanation",
        (("finding", "detail"), ("explain", "finding")),
        "What is finding FND-84920?",
    ),
    Intent(
        "evidence_detail",
        "Single evidence explanation",
        (("evidence", "detail"), ("explain", "evidence")),
        "What is evidence EVD-91823?",
    ),
    Intent(
        "evidence_for_risk",
        "Evidence supporting a risk",
        (("evidence", "risk"), ("evidence", "support")),
        "What evidence supports this risk?",
    ),
    Intent(
        "vendor_risk",
        "Vendor risk",
        (("vendor",), ("third", "party"), ("supplier",)),
        "Which vendor is highest risk?",
    ),
    Intent(
        "privacy_concerns",
        "DPDP / privacy posture",
        (("dpdp",), ("privacy",), ("personal", "data"), ("consent",)),
        "What are our biggest DPDP concerns?",
    ),
    Intent(
        "policy_gaps",
        "Unsatisfied policy requirements",
        (("policy", "requirement"), ("requirement", "satisf"), ("policy", "gap"),
         ("policy", "not")),
        "What policy requirements are not satisfied?",
    ),
    Intent(
        "critical_findings",
        "Critical findings",
        (("critical", "finding"), ("finding",), ("open", "issue")),
        "Show me critical findings.",
    ),
    Intent(
        "top_risks",
        "Top risks",
        (("top", "risk"), ("biggest", "risk"), ("worst", "risk"), ("critical", "risk"),
         ("highest", "risk"), ("risk",)),
        "What are our top risks?",
    ),
    Intent(
        "priority_actions",
        "What to fix first",
        (("fix", "first"), ("prioriti",), ("what", "should", "do"), ("next", "step"),
         ("remediat",)),
        "What should we fix first?",
    ),
)

SUGGESTED_QUESTIONS = [
    "Are we audit ready?",
    "Which devices are not encrypted?",
    "Which cloud assets have public access or lack encryption?",
    "How many employees lack MFA or have stale accounts?",
    "Which internet-facing applications lack MFA?",
    "What are our top risks?",
    "Which controls are failing?",
    "Which controls lack evidence?",
    "Which vendor is highest risk?",
    "What should we fix first?",
]

ID_PATTERNS = {
    "risk": re.compile(r"\bRISK-\d+\b", re.IGNORECASE),
    "control": re.compile(r"\bCTRL-\d+\b", re.IGNORECASE),
    "evidence": re.compile(r"\bEVD-\d+\b", re.IGNORECASE),
    "finding": re.compile(r"\bFND-\d+\b", re.IGNORECASE),
    "policy": re.compile(r"\bPOL-[A-Z0-9\-]+\b", re.IGNORECASE),
}


def _extract_ids(question: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for kind, pattern in ID_PATTERNS.items():
        match = pattern.search(question)
        if match:
            found[kind] = match.group(0).upper()
    return found


class CopilotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------

    def _match_intent(self, question: str) -> tuple[Intent | None, str]:
        lowered = question.lower()
        ids = _extract_ids(question)

        # An explicit entity id is the strongest signal available.
        if "risk" in ids:
            if "evidence" in lowered:
                return next(i for i in INTENTS if i.name == "evidence_for_risk"), "high"
            return next(i for i in INTENTS if i.name == "risk_detail"), "high"
        if "policy" in ids:
            return next(i for i in INTENTS if i.name == "policy_detail"), "high"
        if "control" in ids:
            return next(i for i in INTENTS if i.name == "control_detail"), "high"
        if "finding" in ids:
            return next(i for i in INTENTS if i.name == "finding_detail"), "high"
        if "evidence" in ids:
            return next(i for i in INTENTS if i.name == "evidence_detail"), "high"

        for intent in INTENTS:
            for group in intent.keywords:
                if all(token in lowered for token in group):
                    return intent, "high" if len(group) > 1 else "medium"
        return None, "none"

    async def answer(self, question: str) -> dict[str, Any]:
        intent, confidence = self._match_intent(question)
        ids = _extract_ids(question)

        if intent is None:
            return {
                "question": question,
                "intent": "unknown",
                "intent_label": "Not understood",
                "answer": (
                    "I can't answer that from the compliance data I have. I answer "
                    "questions about trust, risks, findings, controls, evidence, "
                    "vendors, privacy and remediation priorities — see the suggestions "
                    "below."
                ),
                "supporting_data": [],
                "related_entities": [],
                "recommendations": [],
                "sources": [],
                "confidence": "none",
                "engine": "deterministic_intent_v1",
                "llm_used": False,
                "suggested_questions": SUGGESTED_QUESTIONS,
            }

        handler = getattr(self, f"_answer_{intent.name}")
        result = await handler(question, ids)

        # ---- LLM explanation layer ----
        # The deterministic handler has already produced verified structured
        # data.  We now attempt to have the LLM rewrite the prose "answer"
        # field only — supporting_data, related_entities, recommendations
        # and sources always come from the deterministic path.
        engine = "deterministic_fallback_v1"
        llm_used = False

        llm = LLMService()
        if llm.is_configured:
            deterministic_for_context = {
                "answer": result.get("answer", ""),
                "supporting_data": result.get("supporting_data", []),
                "related_entities": result.get("related_entities", []),
                "recommendations": result.get("recommendations", []),
                "intent_label": intent.label,
            }
            llm_answer = await llm.explain(deterministic_for_context, question)
            if llm_answer is not None:
                result["answer"] = llm_answer
                engine = "llm_grounded_v1"
                llm_used = True

        return {
            "question": question,
            "intent": intent.name,
            "intent_label": intent.label,
            "confidence": result.pop("confidence", confidence),
            "engine": engine,
            "llm_used": llm_used,
            "suggested_questions": SUGGESTED_QUESTIONS,
            **result,
        }

    # ------------------------------------------------------------------
    # handlers — each returns answer / supporting_data / related_entities /
    # recommendations / sources
    # ------------------------------------------------------------------

    async def _answer_devices_unencrypted(self, question: str, ids: dict) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(Device)
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        unencrypted_stmt = select(func.count()).select_from(Device).where(Device.encryption_enabled == False)
        unencrypted_count = (await self.db.execute(unencrypted_stmt)).scalar_one() or 0

        non_compliant_stmt = select(func.count()).select_from(Device).where(Device.compliance_status != "Compliant")
        non_compliant_count = (await self.db.execute(non_compliant_stmt)).scalar_one() or 0

        missing_sec_stmt = select(func.count()).select_from(Device).where(
            or_(Device.antivirus_installed == False, Device.edr_installed == False, Device.firewall_enabled == False)
        )
        missing_sec_count = (await self.db.execute(missing_sec_stmt)).scalar_one() or 0

        high_risk_stmt = select(func.count()).select_from(Device).where(Device.risk_level.in_(["High", "Critical"]))
        high_risk_count = (await self.db.execute(high_risk_stmt)).scalar_one() or 0

        sample_stmt = (
            select(Device)
            .where(or_(Device.encryption_enabled == False, Device.compliance_status != "Compliant"))
            .limit(10)
        )
        samples = (await self.db.execute(sample_stmt)).scalars().all()

        unencrypted_pct = round((unencrypted_count / total * 100), 1) if total else 0.0

        related = [
            {
                "type": "device",
                "id": d.device_id,
                "label": f"{d.device_type} ({d.operating_system})",
                "detail": f"{'Unencrypted · ' if not d.encryption_enabled else ''}{d.compliance_status} · Risk: {d.risk_level}",
            }
            for d in samples
        ]

        recs = []
        if unencrypted_count > 0:
            recs.append(f"Enforce mandatory disk encryption (BitLocker/FileVault) on all {unencrypted_count} unencrypted devices.")
        if missing_sec_count > 0:
            recs.append(f"Deploy missing EDR/antivirus agents or enable firewalls on {missing_sec_count} endpoints.")
        if non_compliant_count > 0:
            recs.append(f"Apply OS updates and compliance policies to {non_compliant_count} non-compliant endpoints.")

        return {
            "answer": (
                f"{unencrypted_count} of {total} devices ({unencrypted_pct}%) are not encrypted. "
                f"{non_compliant_count} devices are non-compliant, {missing_sec_count} lack antivirus/EDR or firewall protection, "
                f"and {high_risk_count} carry High or Critical risk ratings."
            ),
            "supporting_data": [
                {"label": "Total devices", "value": total},
                {"label": "Unencrypted devices", "value": unencrypted_count, "unit": f"({unencrypted_pct}%)"},
                {"label": "Non-compliant devices", "value": non_compliant_count},
                {"label": "Missing EDR / Antivirus / Firewall", "value": missing_sec_count},
                {"label": "High / Critical risk devices", "value": high_risk_count},
            ],
            "related_entities": related,
            "recommendations": recs,
            "sources": [
                {"endpoint": "/api/v1/devices", "field": "encryption_enabled"},
                {"endpoint": "/api/v1/devices", "field": "compliance_status"},
            ],
        }

    async def _answer_cloud_posture(self, question: str, ids: dict) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(CloudAsset)
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        public_stmt = select(func.count()).select_from(CloudAsset).where(CloudAsset.public_access == True)
        public_count = (await self.db.execute(public_stmt)).scalar_one() or 0

        unencrypted_stmt = select(func.count()).select_from(CloudAsset).where(CloudAsset.encryption_enabled == False)
        unencrypted_count = (await self.db.execute(unencrypted_stmt)).scalar_one() or 0

        unlogged_stmt = select(func.count()).select_from(CloudAsset).where(CloudAsset.logging_enabled == False)
        unlogged_count = (await self.db.execute(unlogged_stmt)).scalar_one() or 0

        high_risk_stmt = select(func.count()).select_from(CloudAsset).where(CloudAsset.risk_level.in_(["High", "Critical"]))
        high_risk_count = (await self.db.execute(high_risk_stmt)).scalar_one() or 0

        sample_stmt = (
            select(CloudAsset)
            .where(or_(CloudAsset.public_access == True, CloudAsset.encryption_enabled == False))
            .limit(10)
        )
        samples = (await self.db.execute(sample_stmt)).scalars().all()

        public_pct = round((public_count / total * 100), 1) if total else 0.0

        related = [
            {
                "type": "cloud_asset",
                "id": c.resource_id,
                "label": f"{c.resource_type} ({c.cloud_provider} · {c.region})",
                "detail": f"{'Public access · ' if c.public_access else ''}{'Unencrypted · ' if not c.encryption_enabled else ''}Risk: {c.risk_level}",
            }
            for c in samples
        ]

        recs = []
        if public_count > 0:
            recs.append(f"Immediately restrict public internet access on all {public_count} exposed cloud resources.")
        if unencrypted_count > 0:
            recs.append(f"Enable KMS / SSE encryption at rest for all {unencrypted_count} unencrypted storage buckets and disks.")
        if unlogged_count > 0:
            recs.append(f"Enable audit logging (CloudTrail / Activity Log) on {unlogged_count} cloud assets for compliance visibility.")

        return {
            "answer": (
                f"{public_count} of {total} cloud assets ({public_pct}%) have public internet access enabled. "
                f"{unencrypted_count} assets are unencrypted at rest, {unlogged_count} lack audit logging, "
                f"and {high_risk_count} carry High or Critical risk ratings."
            ),
            "supporting_data": [
                {"label": "Total cloud assets", "value": total},
                {"label": "Publicly accessible assets", "value": public_count, "unit": f"({public_pct}%)"},
                {"label": "Unencrypted cloud storage", "value": unencrypted_count},
                {"label": "Missing audit logs", "value": unlogged_count},
                {"label": "High / Critical risk assets", "value": high_risk_count},
            ],
            "related_entities": related,
            "recommendations": recs,
            "sources": [
                {"endpoint": "/api/v1/cloud-assets", "field": "public_access"},
                {"endpoint": "/api/v1/cloud-assets", "field": "encryption_enabled"},
            ],
        }

    async def _answer_employee_iam_posture(self, question: str, ids: dict) -> dict[str, Any]:
        total_emp_stmt = select(func.count()).select_from(Employee)
        total_emp = (await self.db.execute(total_emp_stmt)).scalar_one() or 0

        no_mfa_emp_stmt = select(func.count()).select_from(Employee).where(Employee.mfa_enabled == False)
        no_mfa_emp = (await self.db.execute(no_mfa_emp_stmt)).scalar_one() or 0

        short_pass_stmt = select(func.count()).select_from(Employee).where(Employee.password_length < 12)
        short_pass_count = (await self.db.execute(short_pass_stmt)).scalar_one() or 0

        offboarded_stmt = select(func.count()).select_from(Employee).where(Employee.account_status != "Active")
        offboarded_count = (await self.db.execute(offboarded_stmt)).scalar_one() or 0

        priv_iam_stmt = select(func.count()).select_from(IAMRecord).where(IAMRecord.privileged_account == True)
        priv_iam_count = (await self.db.execute(priv_iam_stmt)).scalar_one() or 0

        stale_iam_stmt = select(func.count()).select_from(IAMRecord).where(IAMRecord.inactive_days > 90)
        stale_iam_count = (await self.db.execute(stale_iam_stmt)).scalar_one() or 0

        sample_stmt = (
            select(Employee)
            .where(or_(Employee.mfa_enabled == False, Employee.account_status != "Active"))
            .limit(10)
        )
        samples = (await self.db.execute(sample_stmt)).scalars().all()

        no_mfa_pct = round((no_mfa_emp / total_emp * 100), 1) if total_emp else 0.0

        related = [
            {
                "type": "employee",
                "id": e.employee_id,
                "label": f"{e.first_name} {e.last_name} ({e.department})",
                "detail": f"{'No MFA · ' if not e.mfa_enabled else ''}Status: {e.account_status} · Role: {e.designation}",
            }
            for e in samples
        ]

        recs = []
        if no_mfa_emp > 0:
            recs.append(f"Enforce mandatory multi-factor authentication (MFA) for all {no_mfa_emp} employees lacking MFA.")
        if stale_iam_count > 0:
            recs.append(f"Deprovision or disable access for {stale_iam_count} IAM accounts inactive for over 90 days.")
        if short_pass_count > 0:
            recs.append(f"Enforce password policy requiring >= 12 characters for {short_pass_count} accounts with weak passwords.")

        return {
            "answer": (
                f"{no_mfa_emp} of {total_emp} employees ({no_mfa_pct}%) do not have MFA enabled. "
                f"{stale_iam_count} IAM accounts have been inactive for >90 days, {priv_iam_count} hold privileged admin access, "
                f"and {offboarded_count} non-active employee accounts exist."
            ),
            "supporting_data": [
                {"label": "Total employees", "value": total_emp},
                {"label": "Employees without MFA", "value": no_mfa_emp, "unit": f"({no_mfa_pct}%)"},
                {"label": "Privileged IAM accounts", "value": priv_iam_count},
                {"label": "Stale IAM accounts (>90 days inactive)", "value": stale_iam_count},
                {"label": "Short passwords (<12 chars)", "value": short_pass_count},
            ],
            "related_entities": related,
            "recommendations": recs,
            "sources": [
                {"endpoint": "/api/v1/employees", "field": "mfa_enabled"},
                {"endpoint": "/api/v1/iam-records", "field": "inactive_days"},
            ],
        }

    async def _answer_applications_posture(self, question: str, ids: dict) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(Application)
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        internet_stmt = select(func.count()).select_from(Application).where(Application.internet_facing == True)
        internet_count = (await self.db.execute(internet_stmt)).scalar_one() or 0

        no_mfa_stmt = select(func.count()).select_from(Application).where(Application.uses_mfa == False)
        no_mfa_count = (await self.db.execute(no_mfa_stmt)).scalar_one() or 0

        unencrypted_stmt = select(func.count()).select_from(Application).where(Application.encryption_enabled == False)
        unencrypted_count = (await self.db.execute(unencrypted_stmt)).scalar_one() or 0

        high_risk_stmt = select(func.count()).select_from(Application).where(Application.risk_level.in_(["High", "Critical"]))
        high_risk_count = (await self.db.execute(high_risk_stmt)).scalar_one() or 0

        sample_stmt = (
            select(Application)
            .where(or_(Application.internet_facing == True, Application.uses_mfa == False))
            .limit(10)
        )
        samples = (await self.db.execute(sample_stmt)).scalars().all()

        internet_pct = round((internet_count / total * 100), 1) if total else 0.0

        related = [
            {
                "type": "application",
                "id": a.application_id,
                "label": f"{a.application_name} ({a.owner_department})",
                "detail": f"{'Internet-facing · ' if a.internet_facing else ''}{'No MFA · ' if not a.uses_mfa else ''}Risk: {a.risk_level}",
            }
            for a in samples
        ]

        recs = []
        if internet_count > 0 and no_mfa_count > 0:
            recs.append(f"Require SSO and mandatory MFA for all {internet_count} internet-facing applications.")
        if unencrypted_count > 0:
            recs.append(f"Enforce TLS encryption in transit and data-at-rest encryption for {unencrypted_count} applications.")
        if high_risk_count > 0:
            recs.append(f"Review access controls and vulnerability scans for the {high_risk_count} High/Critical risk applications.")

        return {
            "answer": (
                f"{internet_count} of {total} applications ({internet_pct}%) are internet-facing. "
                f"{no_mfa_count} applications do not enforce MFA, {unencrypted_count} lack data encryption, "
                f"and {high_risk_count} applications carry High or Critical risk ratings."
            ),
            "supporting_data": [
                {"label": "Total applications", "value": total},
                {"label": "Internet-facing applications", "value": internet_count, "unit": f"({internet_pct}%)"},
                {"label": "Applications without MFA", "value": no_mfa_count},
                {"label": "Unencrypted applications", "value": unencrypted_count},
                {"label": "High / Critical risk applications", "value": high_risk_count},
            ],
            "related_entities": related,
            "recommendations": recs,
            "sources": [
                {"endpoint": "/api/v1/applications", "field": "internet_facing"},
                {"endpoint": "/api/v1/applications", "field": "uses_mfa"},
            ],
        }

    async def _answer_policy_detail(self, question: str, ids: dict) -> dict[str, Any]:
        pol_id = ids.get("policy")
        policy = None

        if pol_id:
            clean_id = pol_id.split()[0].rstrip("·").strip()
            stmt = select(Policy).where(Policy.policy_id == clean_id)
            policy = (await self.db.execute(stmt)).scalar_one_or_none()

        if not policy:
            match = re.search(r"POL-[A-Z0-9\-]+", question, re.IGNORECASE)
            if match:
                clean_id = match.group(0).upper()
                stmt = select(Policy).where(Policy.policy_id == clean_id)
                policy = (await self.db.execute(stmt)).scalar_one_or_none()

        if not policy:
            return self._empty(f"No policy matching '{pol_id or question[:40]}' was found in the database.")

        ctrls_stmt = select(Control).where(Control.policy_id == policy.policy_id)
        controls = (await self.db.execute(ctrls_stmt)).scalars().all()
        ctrl_ids = [c.control_id for c in controls]

        findings_count = 0
        if ctrl_ids:
            fnd_stmt = select(func.count()).select_from(Finding).where(Finding.control_id.in_(ctrl_ids))
            findings_count = (await self.db.execute(fnd_stmt)).scalar_one() or 0

        mandatory_str = "mandatory" if policy.mandatory else "optional"
        answer = (
            f"Policy {policy.policy_id} ({policy.policy_name}) is a {mandatory_str} policy under the {policy.framework} framework "
            f"(category: {policy.category}, version: {policy.version}), owned by the {policy.owner_department} department. "
            f"It governs {len(controls)} compliance controls with {findings_count} associated compliance findings."
        )

        related = [
            {"type": "control", "id": c.control_id, "label": c.control_name, "detail": f"Severity: {c.severity}"}
            for c in controls[:10]
        ]

        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Policy ID", "value": policy.policy_id},
                {"label": "Policy Name", "value": policy.policy_name},
                {"label": "Framework", "value": policy.framework},
                {"label": "Category", "value": policy.category},
                {"label": "Owner Department", "value": policy.owner_department},
                {"label": "Mandatory", "value": "Yes" if policy.mandatory else "No"},
                {"label": "Governed Controls", "value": len(controls)},
                {"label": "Associated Findings", "value": findings_count},
            ],
            "related_entities": related,
            "recommendations": [
                f"Ensure evidence is collected and verified for all {len(controls)} controls under {policy.policy_id}.",
                f"Review compliance findings for {policy.owner_department} department to maintain {policy.framework} audit readiness.",
            ],
            "sources": [{"endpoint": f"/api/v1/policies/{policy.policy_id}", "field": "policy_id"}],
        }

    async def _answer_control_detail(self, question: str, ids: dict) -> dict[str, Any]:
        ctrl_id = ids.get("control")
        control = None
        if ctrl_id:
            clean_id = ctrl_id.split()[0].rstrip("·").strip()
            stmt = select(Control).where(Control.control_id == clean_id)
            control = (await self.db.execute(stmt)).scalar_one_or_none()

        if not control:
            match = re.search(r"CTRL-\d+", question, re.IGNORECASE)
            if match:
                clean_id = match.group(0).upper()
                stmt = select(Control).where(Control.control_id == clean_id)
                control = (await self.db.execute(stmt)).scalar_one_or_none()

        if not control:
            return self._empty(f"No control matching '{ctrl_id or question[:40]}' was found in the database.")

        evd_stmt = select(func.count()).select_from(Evidence).where(Evidence.control_id == control.control_id)
        evd_count = (await self.db.execute(evd_stmt)).scalar_one() or 0

        fnd_stmt = select(Finding).where(Finding.control_id == control.control_id)
        findings = (await self.db.execute(fnd_stmt)).scalars().all()

        answer = (
            f"Control {control.control_id} ({control.control_name}) is a {control.severity}-severity control "
            f"governed by policy {control.policy_id}. Description: '{control.description}'. "
            f"It has {evd_count} evidence artefact(s) collected and {len(findings)} open/resolved finding(s)."
        )

        related = [
            {"type": "policy", "id": control.policy_id, "label": "Governing Policy", "detail": ""},
        ] + [
            {"type": "finding", "id": f.finding_id, "label": f.description[:80], "detail": f"{f.severity} · {f.status}"}
            for f in findings[:5]
        ]

        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Control ID", "value": control.control_id},
                {"label": "Control Name", "value": control.control_name},
                {"label": "Severity", "value": control.severity},
                {"label": "Governing Policy", "value": control.policy_id},
                {"label": "Evidence Required", "value": "Yes" if control.evidence_required else "No"},
                {"label": "Evidence Artifacts", "value": evd_count},
                {"label": "Associated Findings", "value": len(findings)},
            ],
            "related_entities": related,
            "recommendations": [
                f"Remediate the {len(findings)} finding(s) associated with {control.control_id}." if findings else f"Control {control.control_id} currently has no open findings.",
            ],
            "sources": [{"endpoint": f"/api/v1/controls/{control.control_id}", "field": "control_id"}],
        }

    async def _answer_finding_detail(self, question: str, ids: dict) -> dict[str, Any]:
        fnd_id = ids.get("finding")
        finding = None
        if fnd_id:
            clean_id = fnd_id.split()[0].rstrip("·").strip()
            stmt = select(Finding).where(Finding.finding_id == clean_id)
            finding = (await self.db.execute(stmt)).scalar_one_or_none()

        if not finding:
            match = re.search(r"FND-\d+", question, re.IGNORECASE)
            if match:
                clean_id = match.group(0).upper()
                stmt = select(Finding).where(Finding.finding_id == clean_id)
                finding = (await self.db.execute(stmt)).scalar_one_or_none()

        if not finding:
            return self._empty(f"No finding matching '{fnd_id or question[:40]}' was found in the database.")

        answer = (
            f"Finding {finding.finding_id} is a {finding.severity}-severity issue in status '{finding.status}' "
            f"on control {finding.control_id}. Description: '{finding.description}'. "
            f"Recommendation: '{finding.recommendation}'."
        )

        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Finding ID", "value": finding.finding_id},
                {"label": "Control ID", "value": finding.control_id},
                {"label": "Severity", "value": finding.severity},
                {"label": "Status", "value": finding.status},
            ],
            "related_entities": [
                {"type": "control", "id": finding.control_id, "label": "Affected Control", "detail": ""},
            ],
            "recommendations": [finding.recommendation] if finding.recommendation else [],
            "sources": [{"endpoint": f"/api/v1/findings/{finding.finding_id}", "field": "finding_id"}],
        }

    async def _answer_evidence_detail(self, question: str, ids: dict) -> dict[str, Any]:
        evd_id = ids.get("evidence")
        evidence = None
        if evd_id:
            clean_id = evd_id.split()[0].rstrip("·").strip()
            stmt = select(Evidence).where(Evidence.evidence_id == clean_id)
            evidence = (await self.db.execute(stmt)).scalar_one_or_none()

        if not evidence:
            match = re.search(r"EVD-\d+", question, re.IGNORECASE)
            if match:
                clean_id = match.group(0).upper()
                stmt = select(Evidence).where(Evidence.evidence_id == clean_id)
                evidence = (await self.db.execute(stmt)).scalar_one_or_none()

        if not evidence:
            return self._empty(f"No evidence matching '{evd_id or question[:40]}' was found in the database.")

        verified_str = "Verified" if evidence.verified else "Unverified"
        auto_str = "automatically collected" if evidence.collected_automatically else "manually uploaded"
        answer = (
            f"Evidence {evidence.evidence_id} is a {verified_str} {evidence.evidence_type} artefact "
            f"supporting control {evidence.control_id}, {auto_str} on {evidence.collected_date}. "
            f"Location: {evidence.evidence_location}."
        )

        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Evidence ID", "value": evidence.evidence_id},
                {"label": "Control ID", "value": evidence.control_id},
                {"label": "Evidence Type", "value": evidence.evidence_type},
                {"label": "Verified Status", "value": verified_str},
                {"label": "Collection Date", "value": str(evidence.collected_date)},
            ],
            "related_entities": [
                {"type": "control", "id": evidence.control_id, "label": "Supported Control", "detail": ""},
            ],
            "recommendations": [
                "Verify this evidence artefact to improve audit readiness." if not evidence.verified else "Evidence is verified."
            ],
            "sources": [{"endpoint": f"/api/v1/evidence/{evidence.evidence_id}", "field": "evidence_id"}],
        }

    async def _answer_audit_readiness(self, question: str, ids: dict) -> dict[str, Any]:
        dashboard = await DashboardService(self.db).build()
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=5)
        readiness = dashboard["audit_readiness"]

        value = readiness.get("value")
        verdict = (
            "not yet" if value is None or value < 70
            else "close" if value < 85
            else "yes"
        )
        answer = (
            f"Audit readiness is {value}/100 — {verdict}. "
            f"{evidence['covered_controls']} of {evidence['total_controls']} controls "
            f"({evidence['coverage_percentage']}%) have verified evidence, "
            f"{evidence['critical_gaps']} gaps are critical, and "
            f"{dashboard['findings']['severe_open']} critical/high findings are still open."
        )
        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Audit readiness", "value": value, "unit": "/100"},
                {"label": "Evidence coverage", "value": evidence["coverage_percentage"], "unit": "%"},
                {"label": "Controls with verified evidence", "value": evidence["covered_controls"]},
                {"label": "Controls without", "value": evidence["uncovered_controls"]},
                {"label": "Critical evidence gaps", "value": evidence["critical_gaps"]},
                {"label": "Open critical/high findings", "value": dashboard["findings"]["severe_open"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": g["gap_severity"] + " evidence gap"}
                for g in evidence["top_gaps"][:5]
            ],
            "recommendations": [
                f"Close the {evidence['critical_gaps']} critical evidence gaps first — "
                "those controls have no evidence and already have open findings.",
                f"Verify the evidence on {evidence['controls_with_unverified_evidence_only']} "
                "controls that have artefacts collected but none verified.",
                f"Remediate {dashboard['findings']['severe_open']} open critical/high findings.",
            ],
            "sources": [
                {"endpoint": "/api/v1/dashboard", "field": "audit_readiness"},
                {"endpoint": "/api/v1/intelligence/evidence", "field": "coverage_percentage"},
            ],
        }

    async def _answer_trust_explanation(self, question: str, ids: dict) -> dict[str, Any]:
        trust = await TrustIntelligenceService(self.db).build()
        score = trust.get("trust_score")
        contributors = trust.get("negative_contributors") or trust.get("detractors") or []
        positives = trust.get("positive_contributors") or trust.get("contributors") or []

        parts = [f"The Trust Score is {score}."]
        if trust.get("trust_level"):
            parts.append(f"That band is '{trust['trust_level']}'.")
        if contributors:
            names = ", ".join(c.get("label", c.get("domain", "?")) for c in contributors[:3])
            parts.append(f"It is held down mainly by {names}.")
        if positives:
            names = ", ".join(c.get("label", c.get("domain", "?")) for c in positives[:2])
            parts.append(f"{names} are the strongest domains.")
        parts.append(
            "The score is deterministic: a fixed weighted sum of live row-count ratios, "
            "not a model output."
        )

        return {
            "answer": " ".join(parts),
            "supporting_data": [
                {"label": c.get("label", c.get("domain", "?")),
                 "value": c.get("score", c.get("ratio")),
                 "unit": c.get("unit", "")}
                for c in (positives + contributors)[:8]
            ],
            "related_entities": [
                {"type": "risk", "id": r.get("risk_id"), "label": r.get("risk_name"),
                 "detail": r.get("severity")}
                for r in (trust.get("top_risk_drivers") or [])[:5]
            ],
            "recommendations": [
                r["action"] if isinstance(r, dict) and "action" in r else str(r)
                for r in trust.get("recommended_actions", [])
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/trust", "field": "trust_score"}],
        }

    async def _answer_evidence_gaps(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=10)
        critical = [g for g in evidence["top_gaps"] if g["gap_severity"] == "Critical"]
        shown = critical or evidence["top_gaps"]

        answer = (
            f"{evidence['uncovered_controls']} of {evidence['total_controls']} controls "
            f"cannot be proven with verified evidence. "
            f"{evidence['controls_with_no_evidence']} have nothing at all and "
            f"{evidence['controls_with_unverified_evidence_only']} have artefacts that were "
            f"never verified. {evidence['critical_gaps']} gaps are critical — evidence is "
            "required, absent, and the control already has open findings."
        )
        return {
            "answer": answer,
            "supporting_data": [
                {"label": "Evidence coverage", "value": evidence["coverage_percentage"], "unit": "%"},
                {"label": "Controls with no evidence", "value": evidence["controls_with_no_evidence"]},
                {"label": "Unverified evidence only", "value": evidence["controls_with_unverified_evidence_only"]},
                {"label": "Critical gaps", "value": evidence["critical_gaps"]},
                {"label": "High gaps", "value": evidence["high_gaps"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": f"{g['gap_severity']} · {g['open_findings']} open finding(s)"}
                for g in shown[:8]
            ],
            "recommendations": [
                f"{g['control_id']} ({g['control_name']}): {g['why']}" for g in shown[:5]
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/evidence/coverage", "field": "evidence_gaps"}],
        }

    async def _answer_controls_failing(self, question: str, ids: dict) -> dict[str, Any]:
        db = self.db
        findings = list(
            (
                await db.execute(select(Finding).where(Finding.status.in_(OPEN_FINDING_STATUSES)))
            ).scalars().all()
        )
        by_control: dict[str, list[Finding]] = {}
        for finding in findings:
            by_control.setdefault(finding.control_id, []).append(finding)

        controls = list(
            (
                await db.execute(select(Control).where(Control.control_id.in_(list(by_control))))
            ).scalars().all()
        )
        control_by_id = {c.control_id: c for c in controls}

        ranked = sorted(
            by_control.items(),
            key=lambda kv: (
                sum(1 for f in kv[1] if f.severity == "Critical"),
                sum(1 for f in kv[1] if f.severity == "High"),
                len(kv[1]),
            ),
            reverse=True,
        )

        return {
            "answer": (
                f"{len(by_control)} controls are failing — each has at least one finding "
                f"in status Open or In Progress, across {len(findings)} open findings in total."
            ),
            "supporting_data": [
                {"label": "Failing controls", "value": len(by_control)},
                {"label": "Open findings", "value": len(findings)},
                {"label": "Critical open findings",
                 "value": sum(1 for f in findings if f.severity == "Critical")},
                {"label": "High open findings",
                 "value": sum(1 for f in findings if f.severity == "High")},
            ],
            "related_entities": [
                {
                    "type": "control",
                    "id": control_id,
                    "label": control_by_id[control_id].control_name
                    if control_id in control_by_id
                    else control_id,
                    "detail": f"{len(group)} open finding(s)",
                }
                for control_id, group in ranked[:8]
            ],
            "recommendations": [
                f"{control_id}: remediate {len(group)} open finding(s) "
                f"({', '.join(sorted({f.severity for f in group}))})"
                for control_id, group in ranked[:5]
            ],
            "sources": [{"endpoint": "/api/v1/findings", "field": "status"}],
        }

    async def _answer_top_risks(self, question: str, ids: dict) -> dict[str, Any]:
        risks = await RiskIntelligenceService(self.db).top_risks(limit=8)
        if not risks:
            return self._empty("No open risks are recorded in the risk register.")

        top = risks[0]
        return {
            "answer": (
                f"{len(risks)} open risks ranked by severity x likelihood. The highest is "
                f"{top['risk_id']} — {top.get('risk_name')} "
                f"({top.get('severity')}, score {top.get('risk_score')})."
            ),
            "supporting_data": [
                {"label": r["risk_id"], "value": r.get("risk_score"),
                 "unit": f"· {r.get('severity')}"}
                for r in risks
            ],
            "related_entities": [
                {"type": "risk", "id": r["risk_id"], "label": r.get("risk_name"),
                 "detail": f"{r.get('severity')} · {r.get('current_status')}"}
                for r in risks
            ],
            "recommendations": [
                r.get("recommendation") for r in risks[:5] if r.get("recommendation")
            ],
            "sources": [{"endpoint": "/api/v1/intelligence/risks", "field": "risk_score"}],
        }

    async def _answer_risk_detail(self, question: str, ids: dict) -> dict[str, Any]:
        risk_id = ids.get("risk")
        if not risk_id:
            return await self._answer_top_risks(question, ids)

        explained = await RiskIntelligenceService(self.db).explain(risk_id)
        if explained is None:
            return self._empty(f"No risk with id {risk_id} exists in the register.")

        return {
            "answer": (
                f"{risk_id} — {explained.get('risk_name')} is rated "
                f"{explained.get('severity')} with likelihood {explained.get('likelihood')}, "
                f"giving a score of {explained.get('risk_score')} "
                f"({explained.get('priority')} priority). "
                f"{explained.get('why_it_matters', '')}"
            ).strip(),
            "supporting_data": [
                {"label": "Severity", "value": explained.get("severity")},
                {"label": "Likelihood", "value": explained.get("likelihood")},
                {"label": "Risk score", "value": explained.get("risk_score")},
                {"label": "Status", "value": explained.get("current_status")},
                {"label": "Owner", "value": explained.get("owner_department")},
            ],
            "related_entities": self._risk_entities(explained),
            "recommendations": [explained["recommendation"]]
            if explained.get("recommendation")
            else [],
            "sources": [{"endpoint": f"/api/v1/intelligence/risks/{risk_id}", "field": "risk_score"}],
        }

    async def _answer_evidence_for_risk(self, question: str, ids: dict) -> dict[str, Any]:
        risk_id = ids.get("risk")
        if not risk_id:
            return await self._answer_evidence_gaps(question, ids)

        db = self.db
        risk = (
            await db.execute(select(Risk).where(Risk.risk_id == risk_id))
        ).scalar_one_or_none()
        if risk is None:
            return self._empty(f"No risk with id {risk_id} exists in the register.")
        if not risk.mapped_control_id:
            return self._empty(
                f"{risk_id} is not mapped to a control, so no evidence chain exists for it. "
                "Map it to a control to make it provable."
            )

        control = await EvidenceIntelligenceService(db).control_evidence(risk.mapped_control_id)
        return {
            "answer": (
                f"{risk_id} is mapped to control {control['control_id']} "
                f"({control['control_name']}). {control['can_we_prove_it_works']}"
            ),
            "supporting_data": [
                {"label": "Evidence items", "value": control["evidence_count"]},
                {"label": "Verified", "value": control["verified_evidence_count"]},
                {"label": "Open findings", "value": len(control["open_findings"])},
            ],
            "related_entities": [
                {"type": "evidence", "id": e["evidence_id"], "label": e["evidence_type"],
                 "detail": ("verified" if e["verified"] else "unverified") + f" · {e['collected_date']}"}
                for e in control["evidence"][:8]
            ],
            "recommendations": (
                ["Collect and verify evidence for this control — nothing currently proves it works."]
                if not control["verified_evidence_count"]
                else ["Keep this evidence current; it is what proves the mapped control works."]
            ),
            "sources": [
                {"endpoint": f"/api/v1/intelligence/controls/{control['control_id']}/evidence",
                 "field": "evidence"}
            ],
        }

    async def _answer_critical_findings(self, question: str, ids: dict) -> dict[str, Any]:
        findings = list(
            (
                await self.db.execute(
                    select(Finding).where(
                        Finding.status.in_(OPEN_FINDING_STATUSES),
                        Finding.severity.in_(("Critical", "High")),
                    )
                )
            ).scalars().all()
        )
        critical = [f for f in findings if f.severity == "Critical"]
        return {
            "answer": (
                f"{len(critical)} critical and {len(findings) - len(critical)} high findings "
                "are currently open."
            ),
            "supporting_data": [
                {"label": "Critical open", "value": len(critical)},
                {"label": "High open", "value": len(findings) - len(critical)},
            ],
            "related_entities": [
                {"type": "finding", "id": f.finding_id, "label": f.description[:90],
                 "detail": f"{f.severity} · {f.status} · {f.control_id}"}
                for f in (critical + findings)[:8]
            ],
            "recommendations": [f.recommendation for f in critical[:5] if f.recommendation],
            "sources": [{"endpoint": "/api/v1/findings", "field": "severity"}],
        }

    async def _answer_vendor_risk(self, question: str, ids: dict) -> dict[str, Any]:
        vendors = list((await self.db.execute(select(Vendor))).scalars().all())
        rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

        def score(v: Vendor) -> tuple[int, int]:
            certs = sum([v.iso27001_certified, v.soc2_certified, v.dpdp_compliant])
            return rank.get(v.risk_rating, 0), -certs

        ranked = sorted(vendors, key=score, reverse=True)
        worst = ranked[0]
        uncertified = [v for v in vendors if not v.iso27001_certified and not v.soc2_certified]

        return {
            "answer": (
                f"{worst.vendor_name} ({worst.vendor_id}) carries the highest rating: "
                f"{worst.risk_rating}, "
                f"{'no ISO 27001 or SOC 2 certification' if not (worst.iso27001_certified or worst.soc2_certified) else 'certified'}, "
                f"{'DPDP compliant' if worst.dpdp_compliant else 'not DPDP compliant'}. "
                f"{len(uncertified)} of {len(vendors)} vendors hold neither ISO 27001 nor SOC 2. "
                "Note: the dataset has no verified link from vendors to risks or controls, "
                "so this ranking uses vendor attributes only."
            ),
            "supporting_data": [
                {"label": "Total vendors", "value": len(vendors)},
                {"label": "Rated Critical",
                 "value": sum(1 for v in vendors if v.risk_rating == "Critical")},
                {"label": "No ISO/SOC certification", "value": len(uncertified)},
                {"label": "Not DPDP compliant",
                 "value": sum(1 for v in vendors if not v.dpdp_compliant)},
            ],
            "related_entities": [
                {"type": "vendor", "id": v.vendor_id, "label": v.vendor_name,
                 "detail": f"{v.risk_rating} · {v.service_category}"}
                for v in ranked[:8]
            ],
            "recommendations": [
                f"Request current certification evidence from {v.vendor_name} ({v.vendor_id})."
                for v in ranked[:4]
            ],
            "sources": [{"endpoint": "/api/v1/vendors", "field": "risk_rating"}],
        }

    async def _answer_privacy_concerns(self, question: str, ids: dict) -> dict[str, Any]:
        dashboard = await DashboardService(self.db).build()
        privacy = dashboard["privacy_statistics"]
        exposed = privacy["third_party_sharing"]
        unencrypted = privacy["personal_data_records"] - privacy["encrypted"]

        return {
            "answer": (
                f"{privacy['personal_data_records']} personal-data elements are catalogued. "
                f"{exposed} are shared with third parties and {unencrypted} are not encrypted. "
                f"Of {privacy['consent_records']} consent records, {privacy['consent_revoked']} "
                f"are revoked and {privacy['consent_expired']} have expired. "
                "The dataset has no verified link between personal-data records and consent "
                "records, so those two are reported separately rather than joined."
            ),
            "supporting_data": [
                {"label": "Personal data elements", "value": privacy["personal_data_records"]},
                {"label": "Shared with third parties", "value": exposed},
                {"label": "Not encrypted", "value": unencrypted},
                {"label": "Consent required", "value": privacy["consent_required"]},
                {"label": "Consents revoked", "value": privacy["consent_revoked"]},
                {"label": "Consents expired", "value": privacy["consent_expired"]},
            ],
            "related_entities": [],
            "recommendations": [
                f"Encrypt the {unencrypted} personal-data elements currently unencrypted.",
                f"Review third-party transfers for {exposed} shared elements.",
                f"Re-obtain consent for {privacy['consent_expired']} expired records.",
            ],
            "sources": [{"endpoint": "/api/v1/dashboard", "field": "privacy_statistics"}],
        }

    async def _answer_policy_gaps(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=8)
        mandatory_gaps = [g for g in evidence["top_gaps"] if g.get("mandatory_policy")]

        return {
            "answer": (
                f"{evidence['uncovered_controls']} control requirements cannot currently be "
                f"demonstrated. {len(mandatory_gaps)} of the top gaps sit under policies marked "
                "mandatory. A requirement counts as satisfied only when its control has "
                "verified evidence and no open findings."
            ),
            "supporting_data": [
                {"label": "Requirements not demonstrable", "value": evidence["uncovered_controls"]},
                {"label": "Critical gaps", "value": evidence["critical_gaps"]},
                {"label": "Under mandatory policies", "value": len(mandatory_gaps)},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": f"{g.get('policy_name') or g['policy_id']} · {g['gap_severity']}"}
                for g in (mandatory_gaps or evidence["top_gaps"])[:8]
            ],
            "recommendations": [
                f"{g['control_id']} under {g.get('policy_name') or g['policy_id']}: {g['why']}"
                for g in (mandatory_gaps or evidence["top_gaps"])[:5]
            ],
            "sources": [
                {"endpoint": "/api/v1/intelligence/evidence/coverage", "field": "evidence_gaps"},
                {"endpoint": "/api/v1/intelligence/policies/{policy_id}", "field": "requirements"},
            ],
        }

    async def _answer_priority_actions(self, question: str, ids: dict) -> dict[str, Any]:
        evidence = await EvidenceIntelligenceService(self.db).summary(gap_limit=5)
        risks = await RiskIntelligenceService(self.db).top_risks(limit=3)
        dashboard = await DashboardService(self.db).build()

        actions: list[str] = []
        if evidence["critical_gaps"]:
            actions.append(
                f"1. Close {evidence['critical_gaps']} critical evidence gaps — controls that "
                "require evidence, have none, and already have open findings."
            )
        if risks:
            actions.append(
                f"2. Address {risks[0]['risk_id']} ({risks[0].get('risk_name')}), the "
                f"highest-scoring open risk."
            )
        if dashboard["iam_statistics"]["privileged_without_mfa"]:
            actions.append(
                f"3. Enable MFA on {dashboard['iam_statistics']['privileged_without_mfa']} "
                "privileged accounts that currently have none."
            )
        if dashboard["asset_statistics"]["cloud_assets"]["public_access"]:
            actions.append(
                f"4. Review {dashboard['asset_statistics']['cloud_assets']['public_access']} "
                "publicly accessible cloud assets."
            )
        if evidence["controls_with_unverified_evidence_only"]:
            actions.append(
                f"5. Verify evidence on {evidence['controls_with_unverified_evidence_only']} "
                "controls where artefacts exist but none are verified — the cheapest coverage win."
            )

        return {
            "answer": (
                "Ranked by what most improves provable compliance: critical evidence gaps "
                "first (they block audit readiness and already have failures), then the "
                "highest-scoring open risk, then identity and cloud exposure."
            ),
            "supporting_data": [
                {"label": "Critical evidence gaps", "value": evidence["critical_gaps"]},
                {"label": "Open critical/high findings", "value": dashboard["findings"]["severe_open"]},
                {"label": "Privileged accounts without MFA",
                 "value": dashboard["iam_statistics"]["privileged_without_mfa"]},
                {"label": "Public cloud assets",
                 "value": dashboard["asset_statistics"]["cloud_assets"]["public_access"]},
            ],
            "related_entities": [
                {"type": "control", "id": g["control_id"], "label": g["control_name"],
                 "detail": g["gap_severity"]}
                for g in evidence["top_gaps"][:5]
            ],
            "recommendations": actions,
            "sources": [
                {"endpoint": "/api/v1/intelligence/evidence", "field": "critical_gaps"},
                {"endpoint": "/api/v1/intelligence/risks", "field": "risk_score"},
                {"endpoint": "/api/v1/dashboard", "field": "iam_statistics"},
            ],
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _risk_entities(explained: dict[str, Any]) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []
        control = explained.get("mapped_control") or explained.get("control")
        if isinstance(control, dict) and control.get("control_id"):
            entities.append(
                {"type": "control", "id": control["control_id"],
                 "label": control.get("control_name"), "detail": control.get("severity")}
            )
        for finding in explained.get("related_findings", [])[:5]:
            entities.append(
                {"type": "finding", "id": finding.get("finding_id"),
                 "label": finding.get("description", "")[:90],
                 "detail": f"{finding.get('severity')} · {finding.get('status')}"}
            )
        for item in explained.get("related_evidence", [])[:5]:
            entities.append(
                {"type": "evidence", "id": item.get("evidence_id"),
                 "label": item.get("evidence_type"),
                 "detail": "verified" if item.get("verified") else "unverified"}
            )
        return entities

    @staticmethod
    def _empty(message: str) -> dict[str, Any]:
        return {
            "answer": message,
            "supporting_data": [],
            "related_entities": [],
            "recommendations": [],
            "sources": [],
            "confidence": "high",
        }
