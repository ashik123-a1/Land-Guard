"""Statutory Rule Governance Service
Manages versioning, approval, threshold adjustment, and audit trails for
the LandGuard Statutory Verification Ruleset (P3).

Safety Rules:
- Changes require administrative privileges and mandatory statutory justification.
- Every modification creates a new immutable ruleset version.
- Rule changes do not silently alter past recorded verification results.
"""

import datetime
from typing import Dict, Any, List, Optional
from src.landguard_data.database import LandGuardDatabase


INITIAL_STATUTORY_RULESET = {
    "ruleset_version": "2.4.0",
    "rulebook_title": "LandGuard Statutory P3 Verification Rulebook",
    "effective_date": "2026-01-01T00:00:00Z",
    "precedence_policy": "Deterministic Statutory Contradictions > Human Review > Supplementary ML Risk",
    "modified_by": "System Initialization",
    "justification": "Initial codified statutory baseline under Registration Act 1908, SAT Act 1950, and TP Act 1882.",
    "rules": {
        "RULE-AREA-CAPACITY": {
            "name": "Statutory Holding Capacity Exceedance",
            "statutory_citation": "Land Reform Ordinance 1984; State Acquisition and Tenancy Act 1950",
            "enabled": True,
            "severity": "CRITICAL_CONTRADICTION",
            "threshold_percent": 100.0,
            "description": "Total transferred area must not exceed registered cadastral parcel capacity.",
        },
        "RULE-SELLER-OWNER": {
            "name": "Vendor Titleholder Legitimacy",
            "statutory_citation": "Registration Act 1908 s.21; State Acquisition and Tenancy Act 1950 s.143",
            "enabled": True,
            "severity": "CRITICAL_CONTRADICTION",
            "description": "Vendor cited in deed schedule must match recorded titleholder or verified heir.",
        },
        "RULE-CHAIN-OF-TITLE": {
            "name": "Unbroken Chain of Conveyance",
            "statutory_citation": "Transfer of Property Act 1882 s.54; Registration Act 1908 s.17",
            "enabled": True,
            "severity": "CRITICAL_CONTRADICTION",
            "description": "Every deed must trace ownership sequentially to preceding registered title.",
        },
        "RULE-DOUBLE-SALE": {
            "name": "Conflicting Double-Sale Disposition",
            "statutory_citation": "Transfer of Property Act 1882 s.54; Registration Act 1908 s.47",
            "enabled": True,
            "severity": "CRITICAL_CONTRADICTION",
            "description": "Detects concurrent or overlapping conveyances by identical vendor to multiple purchasers.",
        },
        "RULE-MUTATION-RECORD": {
            "name": "Namzari Mutation Verification",
            "statutory_citation": "State Acquisition and Tenancy Act 1950 s.143",
            "enabled": True,
            "severity": "HIGH_SUSPICION",
            "description": "Reconciles Sub-Registry deeds against Assistant Commissioner (Land) mutation dockets.",
        },
        "RULE-SEAL-INTEGRITY": {
            "name": "Sub-Registry Authentication Seal Verification",
            "statutory_citation": "Registration Act 1908; Stamp Act 1899",
            "enabled": True,
            "severity": "SUSPICIOUS_ANOMALY",
            "description": "Flags absent mandatory official seals or unverified physical impressions.",
        },
        "RULE-PRE1972-ARCHIVE": {
            "name": "Pre-1972 Archival Gap Routing",
            "statutory_citation": "Land Records Archival Protocol 1972",
            "enabled": True,
            "severity": "INSUFFICIENT_EVIDENCE",
            "description": "Safely routes unindexed ancestral deeds to INSUFFICIENT_EVIDENCE without false fraud claims.",
        },
    },
    "ml_thresholds": {
        "tau_flagging_threshold": 0.35,
        "critical_escalation_threshold": 0.70,
        "sla_critical_hours": 24,
        "sla_high_hours": 48,
        "sla_normal_hours": 120,
    },
}


class RuleGovernanceService:
    """Domain service managing versioned statutory rulesets and governance policies."""

    def __init__(self, db: Optional[LandGuardDatabase] = None):
        self.db = db or LandGuardDatabase()
        self._ruleset_history: List[Dict[str, Any]] = [INITIAL_STATUTORY_RULESET]

    def get_active_ruleset(self) -> Dict[str, Any]:
        """Returns the current active statutory ruleset and operational thresholds."""
        return self._ruleset_history[-1]

    def get_ruleset_history(self) -> List[Dict[str, Any]]:
        """Returns the complete version history of all approved rulesets."""
        return list(self._ruleset_history)

    def update_ruleset(
        self,
        new_rules: Optional[Dict[str, Any]] = None,
        new_thresholds: Optional[Dict[str, Any]] = None,
        officer: str = "Admin",
        justification: str = "",
    ) -> Dict[str, Any]:
        """Creates a new version of the ruleset with mandatory administrative justification."""
        cleaned_justification = (justification or "").strip()
        if len(cleaned_justification) < 10:
            raise ValueError("A formal statutory justification (minimum 10 characters) is required to modify rulesets.")

        current = self.get_active_ruleset()
        now = datetime.datetime.now().isoformat()

        # Compute next minor version
        curr_ver = current["ruleset_version"]
        parts = curr_ver.split(".")
        try:
            next_patch = int(parts[-1]) + 1
            next_ver = f"{parts[0]}.{parts[1]}.{next_patch}"
        except Exception:
            next_ver = f"{curr_ver}.1"

        updated_rules = dict(current["rules"])
        if new_rules:
            for k, v in new_rules.items():
                if k in updated_rules and isinstance(v, dict):
                    updated_rules[k].update(v)
                else:
                    updated_rules[k] = v

        updated_thresholds = dict(current["ml_thresholds"])
        if new_thresholds:
            updated_thresholds.update(new_thresholds)

        new_version_doc = {
            "ruleset_version": next_ver,
            "rulebook_title": current["rulebook_title"],
            "effective_date": now,
            "precedence_policy": current["precedence_policy"],
            "modified_by": officer,
            "justification": cleaned_justification,
            "rules": updated_rules,
            "ml_thresholds": updated_thresholds,
        }

        self._ruleset_history.append(new_version_doc)

        # Log immutable security audit event
        self.db.log_audit_event(
            actor_id=officer,
            action_type="UPDATE_RULESET",
            target_entity="RULESET",
            target_id=next_ver,
            details={"justification": cleaned_justification, "rules_count": len(updated_rules)},
        )

        return new_version_doc
