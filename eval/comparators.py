"""
eval/comparators.py: Answer Equivalence Comparators for Day 1.

Section 8 Protocol:
- Numbers: within 0.5% relative tolerance (0.005)
- Lists: set equality
- Free text: all key facts in human rubric are present (rubric fact matching)
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple


def compare_numbers(n0: Any, n1: Any, rel_tol: float = 0.005) -> bool:
    try:
        f0 = float(str(n0).replace(",", "").strip())
        f1 = float(str(n1).replace(",", "").strip())
        if math.isnan(f0) or math.isnan(f1):
            return False
        if f0 == f1:
            return True
        diff = abs(f0 - f1)
        denom = max(abs(f0), abs(f1), 1e-9)
        return (diff / denom) <= rel_tol
    except (ValueError, TypeError):
        return False


def compare_lists(l0: Any, l1: Any) -> bool:
    if not isinstance(l0, list) or not isinstance(l1, list):
        return False
    # Set equality (normalized string representation)
    s0 = {str(x).strip().lower() for x in l0}
    s1 = {str(x).strip().lower() for x in l1}
    return s0 == s1


def compare_free_text(t0: str, t1: str, rubric: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Compares free-text answers. If human rubric facts are provided, verifies presence.
    If no rubric facts exist, returns False with reason 'rubric_facts_missing_human_review_required'.
    """
    if not rubric or not rubric.get("required_facts"):
        # Without human-authored rubric, free text equivalence cannot be automatically asserted
        return False, "human_rubric_required"

    t1_lower = str(t1).lower()
    missing_facts = []
    for fact in rubric["required_facts"]:
        if str(fact).lower() not in t1_lower:
            missing_facts.append(fact)

    if missing_facts:
        return False, f"missing_facts: {missing_facts}"
    return True, "facts_matched"


def compare_answers(
    r0: Any,
    r1: Any,
    schema_id: str,
    rubric: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Compares structured outputs R0 and R1 according to answer_schema_id.
    Returns (is_match, reason).
    """
    if r0 is None or r1 is None:
        return False, "null_response"

    # Identity check schemas
    if schema_id == "identity_check":
        # Usually boolean match or ownership verdict
        if isinstance(r0, dict) and isinstance(r1, dict):
            m0 = r0.get("is_mine") or r0.get("matches_owner")
            m1 = r1.get("is_mine") or r1.get("matches_owner")
            if m0 is not None and m1 is not None:
                return (m0 == m1), "boolean_verdict_match" if m0 == m1 else "boolean_verdict_mismatch"
        return (str(r0).strip().lower() == str(r1).strip().lower()), "identity_string_comparison"

    # Numeric summary schemas (e.g. balance_summary, transaction_total, deduction_summary)
    if schema_id in ("balance_summary", "transaction_total", "deduction_summary"):
        if isinstance(r0, (int, float)) or (isinstance(r0, str) and re.match(r"^[\d\.,]+$", r0.strip())):
            match = compare_numbers(r0, r1)
            return match, "numeric_within_tolerance" if match else "numeric_out_of_tolerance"
        if isinstance(r0, dict) and isinstance(r1, dict):
            # Check main amount field
            for key in ("balance", "total", "amount", "total_deductions"):
                if key in r0 and key in r1:
                    match = compare_numbers(r0[key], r1[key])
                    return match, f"field_{key}_match" if match else f"field_{key}_mismatch"

    # List schemas (e.g. top_transactions, suspicious_transactions)
    if schema_id in ("top_transactions",) and isinstance(r0, list) and isinstance(r1, list):
        match = compare_lists(r0, r1)
        return match, "list_set_equality" if match else "list_set_mismatch"

    # Dict of numbers (e.g. spending_summary, salary_summary)
    if isinstance(r0, dict) and isinstance(r1, dict):
        all_keys = set(r0.keys()).union(r1.keys())
        for k in all_keys:
            if k not in r0 or k not in r1:
                return False, f"missing_key_{k}"
            val0, val1 = r0[k], r1[k]
            if isinstance(val0, (int, float)) or (isinstance(val0, str) and re.match(r"^[\d\.,]+$", str(val0).strip())):
                if not compare_numbers(val0, val1):
                    return False, f"numeric_mismatch_in_{k}"
            elif str(val0).strip().lower() != str(val1).strip().lower():
                return False, f"value_mismatch_in_{k}"
        return True, "dict_keys_and_values_matched"

    # Free text fallback
    if isinstance(r0, str) and isinstance(r1, str):
        if r0.strip().lower() == r1.strip().lower():
            return True, "exact_text_match"
        return compare_free_text(r0, r1, rubric)

    return (r0 == r1), "generic_equality"
