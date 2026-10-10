"""
experiment/policy.py: Deterministic Policy Floor Enforcement.

Policy Floor rules per DAY1_SPEC.md and AGENTS.md:
- government_id: must be DROP or MASK_PARTIAL, never KEEP.
- account_identifier: must be DROP or MASK_PARTIAL, never KEEP.
The model cannot relax this floor. Any attempt by the model to KEEP a policy-floor category
is deterministically clamped and flagged as a policy violation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

POLICY_FLOOR_CATEGORIES = {
    "government_id": ["DROP", "MASK_PARTIAL"],
    "account_identifier": ["DROP", "MASK_PARTIAL"],
}


def enforce_policy_floor(
    plan: Dict[str, Any],
    is_trap: bool = False
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Applies the deterministic policy floor to a plan JSON.
    Returns (enforced_plan, violations).
    """
    enforced = dict(plan)
    enforced_decisions = dict(plan.get("decisions", {}))
    violations: List[Dict[str, Any]] = []

    for category, decision in enforced_decisions.items():
        if category in POLICY_FLOOR_CATEGORIES:
            action = decision.get("action")
            allowed_actions = POLICY_FLOOR_CATEGORIES[category]

            if action not in allowed_actions:
                # Deterministic clamping:
                # If it was KEEP, clamp to MASK_PARTIAL (or DROP for government_id)
                clamped_action = "MASK_PARTIAL" if category == "account_identifier" else "DROP"
                violations.append({
                    "category": category,
                    "model_action": action,
                    "clamped_action": clamped_action,
                    "reason": f"Policy floor violation: {category} must be in {allowed_actions}, got {action}"
                })
                new_decision = dict(decision)
                new_decision["action"] = clamped_action
                new_decision["reason"] = f"[POLICY_FLOOR_CLAMPED] {decision.get('reason', '')}"
                enforced_decisions[category] = new_decision

    enforced["decisions"] = enforced_decisions
    return enforced, violations


