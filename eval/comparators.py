"""
eval/comparators.py: Deterministic Answer Equivalence Comparators for JustEnough.

Section 8 Protocol & Phase 1 Specifications:
- Numbers: within 0.5% relative tolerance (rel_tol=0.005)
- Numeric lists: paired elements compared within 0.5% relative tolerance
- General lists: set equality
- Dates: ISO normalization (YYYY-MM-DD) applied strictly to date-enabled schemas (payment_due, bill_summary)
- Identity checks: explicit boolean verdict comparison (without truthiness fallback bug)
- Free text: human-authored required facts verification (rubric fact matching)
"""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_PATH = PROJECT_ROOT / "schemas" / "answer_schemas.json"

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%d %B %Y",
]


def load_answer_schemas() -> Dict[str, Any]:
    """Loads canonical answer schemas from schemas/answer_schemas.json."""
    if not SCHEMAS_PATH.exists():
        raise FileNotFoundError(f"Answer schemas file not found at {SCHEMAS_PATH}")
    with open(SCHEMAS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("schemas", {})


def compare_numbers(n0: Any, n1: Any, rel_tol: float = 0.005) -> bool:
    """
    Compares two numeric values within a relative tolerance.
    Handles numeric strings, floats, and ints.
    """
    try:
        s0 = str(n0).replace(",", "").replace("$", "").replace("INR", "").replace("₹", "").strip()
        s1 = str(n1).replace(",", "").replace("$", "").replace("INR", "").replace("₹", "").strip()
        f0 = float(s0)
        f1 = float(s1)
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
    """Standard list comparison via set equality of normalized lowercase string values."""
    if not isinstance(l0, list) or not isinstance(l1, list):
        return False
    s0 = {str(x).strip().lower() for x in l0}
    s1 = {str(x).strip().lower() for x in l1}
    return s0 == s1


def compare_numeric_lists(l0: Any, l1: Any, rel_tol: float = 0.005) -> Tuple[bool, str]:
    """
    Compares two lists of numeric values or transaction objects.
    Applies 0.5% relative tolerance to paired elements sorted descending.
    """
    if not isinstance(l0, list) or not isinstance(l1, list):
        return False, "not_lists"

    if len(l0) != len(l1):
        return False, f"list_length_mismatch: {len(l0)} vs {len(l1)}"

    # Helper to extract a float amount from an item (either number or dict with 'amount')
    def get_amount(item: Any) -> Optional[float]:
        if isinstance(item, (int, float)):
            return float(item)
        if isinstance(item, dict):
            for k in ("amount", "total", "value", "price"):
                if k in item and isinstance(item[k], (int, float, str)):
                    try:
                        return float(str(item[k]).replace(",", "").strip())
                    except ValueError:
                        pass
        if isinstance(item, str):
            try:
                return float(item.replace(",", "").strip())
            except ValueError:
                return None
        return None

    nums0 = [get_amount(x) for x in l0]
    nums1 = [get_amount(x) for x in l1]

    # If all items in both lists are numeric, sort descending and compare each pair
    if all(x is not None for x in nums0) and all(x is not None for x in nums1):
        s0 = sorted(nums0, reverse=True)  # type: ignore
        s1 = sorted(nums1, reverse=True)  # type: ignore
        for i, (v0, v1) in enumerate(zip(s0, s1)):
            if not compare_numbers(v0, v1, rel_tol=rel_tol):
                return False, f"numeric_list_item_mismatch_at_rank_{i+1}: {v0} vs {v1}"
        return True, "numeric_list_matched"

    # Fallback to standard set equality if elements are not numeric
    if compare_lists(l0, l1):
        return True, "list_set_equality"
    return False, "list_mismatch"


def normalize_date(val: Any) -> Optional[str]:
    """
    Normalizes a date string or object to standard ISO 'YYYY-MM-DD'.
    Only called for schemas where dates are explicitly expected.
    """
    if val is None:
        return None
    s = str(val).strip()
    # Try parsing against standard date formats
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex search for ISO YYYY-MM-DD
    m_iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    # Return trimmed lowercase representation as fallback
    return s.lower()


def compare_dates(d0: Any, d1: Any) -> Tuple[bool, str]:
    """Compares two dates after ISO normalization."""
    if d0 is None or d1 is None:
        return False, "null_date"
    n0 = normalize_date(d0)
    n1 = normalize_date(d1)
    if n0 == n1:
        return True, "date_matched"
    return False, f"date_mismatch: {n0} vs {n1}"


def compare_free_text(t0: str, t1: str, rubric: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Compares free-text answers against human-authored required facts.
    Returns (False, 'human_rubric_required') if rubric facts are missing.
    """
    if not rubric or not rubric.get("required_facts"):
        return False, "human_rubric_required"

    t1_lower = str(t1).lower()
    missing_facts = []
    for fact in rubric["required_facts"]:
        if str(fact).lower() not in t1_lower:
            missing_facts.append(fact)

    if missing_facts:
        return False, f"missing_facts: {missing_facts}"
    return True, "facts_matched"


def _extract_boolean_verdict(obj: Any) -> Optional[bool]:
    """
    Extracts an explicit boolean verdict without using truthiness fallback.
    Prevents the bug where False was treated as falsy and overwritten.
    """
    if isinstance(obj, bool):
        return obj

    if isinstance(obj, dict):
        for key in ("is_mine", "matches_owner", "verdict"):
            if key in obj:
                val = obj[key]
                if isinstance(val, bool):
                    return val
                if isinstance(val, str):
                    s = val.strip().lower()
                    if s in ("true", "yes", "match", "matched", "verified"):
                        return True
                    if s in ("false", "no", "mismatch", "mismatched", "unverified"):
                        return False

    if isinstance(obj, str):
        s = obj.strip().lower()
        if s in ("true", "yes", "match", "matched", "verified"):
            return True
        if s in ("false", "no", "mismatch", "mismatched", "unverified"):
            return False

    return None


def _extract_numeric_field(obj: Any, candidate_keys: Tuple[str, ...]) -> Optional[float]:
    """Extracts a numeric float value from a dict or direct numeric/string."""
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, str):
        try:
            return float(obj.replace(",", "").strip())
        except ValueError:
            pass
    if isinstance(obj, dict):
        for k in candidate_keys:
            if k in obj and obj[k] is not None:
                val = obj[k]
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    try:
                        return float(val.replace(",", "").strip())
                    except ValueError:
                        pass
    return None


# --- Phase 1 Deterministic Specialized Comparators ---

def _compare_identity_check(r0: Any, r1: Any) -> Tuple[bool, str]:
    v0 = _extract_boolean_verdict(r0)
    v1 = _extract_boolean_verdict(r1)
    if v0 is None or v1 is None:
        # Fallback to string equality if boolean verdict not formatted
        s0 = str(r0).strip().lower()
        s1 = str(r1).strip().lower()
        if s0 == s1:
            return True, "identity_string_matched"
        return False, "invalid_or_missing_identity_verdict"

    if v0 == v1:
        return True, "boolean_verdict_match"
    return False, "boolean_verdict_mismatch"


def _compare_single_numeric(r0: Any, r1: Any, schema_id: str, candidate_keys: Tuple[str, ...]) -> Tuple[bool, str]:
    n0 = _extract_numeric_field(r0, candidate_keys)
    n1 = _extract_numeric_field(r1, candidate_keys)
    if n0 is None or n1 is None:
        return False, f"missing_numeric_field_in_{schema_id}"
    match = compare_numbers(n0, n1, rel_tol=0.005)
    return match, ("numeric_within_tolerance" if match else "numeric_out_of_tolerance")


def _compare_spending_summary(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "spending_summary_expected_dict"

    dict0 = r0.get("categories", r0) if isinstance(r0.get("categories"), dict) else r0
    dict1 = r1.get("categories", r1) if isinstance(r1.get("categories"), dict) else r1

    keys0 = {str(k).strip().lower(): k for k in dict0.keys() if k != "total_spending"}
    keys1 = {str(k).strip().lower(): k for k in dict1.keys() if k != "total_spending"}

    if set(keys0.keys()) != set(keys1.keys()):
        diff = set(keys0.keys()) ^ set(keys1.keys())
        return False, f"spending_category_mismatch: {diff}"

    for norm_k in keys0:
        orig0 = keys0[norm_k]
        orig1 = keys1[norm_k]
        val0 = dict0[orig0]
        val1 = dict1[orig1]
        if not compare_numbers(val0, val1, rel_tol=0.005):
            return False, f"spending_amount_mismatch_in_{norm_k}: {val0} vs {val1}"

    # Also compare total_spending if present in both
    if "total_spending" in r0 and "total_spending" in r1:
        if not compare_numbers(r0["total_spending"], r1["total_spending"], rel_tol=0.005):
            return False, f"total_spending_mismatch: {r0['total_spending']} vs {r1['total_spending']}"

    return True, "spending_summary_matched"


def _compare_cashflow_summary(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "cashflow_summary_expected_dict"

    inflow0 = _extract_numeric_field(r0, ("total_inflow", "inflow", "credits"))
    inflow1 = _extract_numeric_field(r1, ("total_inflow", "inflow", "credits"))
    outflow0 = _extract_numeric_field(r0, ("total_outflow", "outflow", "debits"))
    outflow1 = _extract_numeric_field(r1, ("total_outflow", "outflow", "debits"))

    if inflow0 is None or inflow1 is None:
        return False, "missing_inflow_amount"
    if outflow0 is None or outflow1 is None:
        return False, "missing_outflow_amount"

    if not compare_numbers(inflow0, inflow1, rel_tol=0.005):
        return False, f"inflow_mismatch: {inflow0} vs {inflow1}"
    if not compare_numbers(outflow0, outflow1, rel_tol=0.005):
        return False, f"outflow_mismatch: {outflow0} vs {outflow1}"

    # Net cashflow check if present in both
    net0 = _extract_numeric_field(r0, ("net_cashflow", "net"))
    net1 = _extract_numeric_field(r1, ("net_cashflow", "net"))
    if net0 is not None and net1 is not None:
        if not compare_numbers(net0, net1, rel_tol=0.005):
            return False, f"net_cashflow_mismatch: {net0} vs {net1}"

    return True, "cashflow_summary_matched"


def _compare_salary_summary(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "salary_summary_expected_dict"

    keys0 = {str(k).strip().lower(): k for k in r0.keys()}
    keys1 = {str(k).strip().lower(): k for k in r1.keys()}

    if set(keys0.keys()) != set(keys1.keys()):
        diff = set(keys0.keys()) ^ set(keys1.keys())
        return False, f"salary_keys_mismatch: {diff}"

    for norm_k in keys0:
        val0 = r0[keys0[norm_k]]
        val1 = r1[keys1[norm_k]]
        if isinstance(val0, (int, float, str)) and isinstance(val1, (int, float, str)):
            if not compare_numbers(val0, val1, rel_tol=0.005):
                return False, f"salary_numeric_mismatch_in_{norm_k}: {val0} vs {val1}"
        elif val0 != val1:
            return False, f"salary_value_mismatch_in_{norm_k}"

    return True, "salary_summary_matched"


def _compare_usage_summary(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "usage_summary_expected_dict"

    units0 = _extract_numeric_field(r0, ("billed_consumption", "billed_consumption_units", "consumption", "units"))
    units1 = _extract_numeric_field(r1, ("billed_consumption", "billed_consumption_units", "consumption", "units"))
    charges0 = _extract_numeric_field(r0, ("total_charges", "total_amount", "charges", "amount"))
    charges1 = _extract_numeric_field(r1, ("total_charges", "total_amount", "charges", "amount"))

    if units0 is None or units1 is None:
        return False, "missing_consumption_units"
    if charges0 is None or charges1 is None:
        return False, "missing_charges_amount"

    if not compare_numbers(units0, units1, rel_tol=0.005):
        return False, f"consumption_units_mismatch: {units0} vs {units1}"
    if not compare_numbers(charges0, charges1, rel_tol=0.005):
        return False, f"total_charges_mismatch: {charges0} vs {charges1}"

    return True, "usage_summary_matched"


def _compare_payment_due(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "payment_due_expected_dict"

    amt0 = _extract_numeric_field(r0, ("amount_due", "total_outstanding_due", "total_amount_due", "total_due", "amount"))
    amt1 = _extract_numeric_field(r1, ("amount_due", "total_outstanding_due", "total_amount_due", "total_due", "amount"))
    if amt0 is None or amt1 is None:
        return False, "missing_amount_due"

    if not compare_numbers(amt0, amt1, rel_tol=0.005):
        return False, f"amount_due_mismatch: {amt0} vs {amt1}"

    # Normalize dates only where schema expects dates
    date0 = r0.get("due_date") or r0.get("payment_due_date")
    date1 = r1.get("due_date") or r1.get("payment_due_date")
    if date0 is not None and date1 is not None:
        date_match, date_reason = compare_dates(date0, date1)
        if not date_match:
            return False, date_reason

    # Minimum payment if present in both
    min0 = _extract_numeric_field(r0, ("minimum_amount_due", "minimum_payment"))
    min1 = _extract_numeric_field(r1, ("minimum_amount_due", "minimum_payment"))
    if min0 is not None and min1 is not None:
        if not compare_numbers(min0, min1, rel_tol=0.005):
            return False, f"minimum_payment_mismatch: {min0} vs {min1}"

    return True, "payment_due_matched"


def _compare_bill_summary(r0: Any, r1: Any) -> Tuple[bool, str]:
    if not isinstance(r0, dict) or not isinstance(r1, dict):
        return False, "bill_summary_expected_dict"

    amt0 = _extract_numeric_field(r0, ("bill_amount", "total_amount", "amount", "payable_amount"))
    amt1 = _extract_numeric_field(r1, ("bill_amount", "total_amount", "amount", "payable_amount"))
    if amt0 is None or amt1 is None:
        return False, "missing_bill_amount"

    if not compare_numbers(amt0, amt1, rel_tol=0.005):
        return False, f"bill_amount_mismatch: {amt0} vs {amt1}"

    date0 = r0.get("due_date") or r0.get("payment_due_date")
    date1 = r1.get("due_date") or r1.get("payment_due_date")
    if date0 is not None and date1 is not None:
        date_match, date_reason = compare_dates(date0, date1)
        if not date_match:
            return False, date_reason

    return True, "bill_summary_matched"


def compare_answers(
    r0: Any,
    r1: Any,
    schema_id: str,
    rubric: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """
    Compares structured outputs R0 and R1 according to answer_schema_id.
    Dispatches directly to Phase 1 specialized deterministic comparators.
    """
    if r0 is None or r1 is None:
        return False, "null_response"

    # --- Phase 1 Schemas Dispatcher ---

    # 1. Identity Check
    if schema_id == "identity_check":
        return _compare_identity_check(r0, r1)

    # 2. Balance Summary
    if schema_id == "balance_summary":
        return _compare_single_numeric(r0, r1, schema_id, ("total_balance", "balance", "total", "amount"))

    # 3. Transaction Total
    if schema_id == "transaction_total":
        return _compare_single_numeric(r0, r1, schema_id, ("total_amount", "upi_total", "total", "amount"))

    # 4. Deduction Summary
    if schema_id == "deduction_summary":
        return _compare_single_numeric(r0, r1, schema_id, ("total_deductions", "total", "amount"))

    # 5. Spending Summary
    if schema_id == "spending_summary":
        return _compare_spending_summary(r0, r1)

    # 6. Cashflow Summary
    if schema_id == "cashflow_summary":
        return _compare_cashflow_summary(r0, r1)

    # 7. Salary Summary
    if schema_id == "salary_summary":
        return _compare_salary_summary(r0, r1)

    # 8. Usage Summary
    if schema_id == "usage_summary":
        return _compare_usage_summary(r0, r1)

    # 9. Top Transactions
    if schema_id == "top_transactions":
        return compare_numeric_lists(r0, r1, rel_tol=0.005)

    # 10. Payment Due
    if schema_id == "payment_due":
        return _compare_payment_due(r0, r1)

    # 11. Bill Summary
    if schema_id == "bill_summary":
        return _compare_bill_summary(r0, r1)

    # --- Fallback Paths for Phase 2 & Phase 3 ---
    # Free-text rubric fallback
    if isinstance(r0, str) and isinstance(r1, str):
        if r0.strip().lower() == r1.strip().lower():
            return True, "exact_text_match"
        return compare_free_text(r0, r1, rubric)

    # Generic list set equality
    if isinstance(r0, list) and isinstance(r1, list):
        match = compare_lists(r0, r1)
        return match, "list_set_equality" if match else "list_set_mismatch"

    # Generic dict equality with numeric tolerance
    if isinstance(r0, dict) and isinstance(r1, dict):
        all_keys = set(r0.keys()).union(r1.keys())
        for k in all_keys:
            if k not in r0 or k not in r1:
                return False, f"missing_key_{k}"
            val0, val1 = r0[k], r1[k]
            if isinstance(val0, (int, float, str)) and isinstance(val1, (int, float, str)):
                if not compare_numbers(val0, val1, rel_tol=0.005):
                    return False, f"numeric_mismatch_in_{k}"
            elif str(val0).strip().lower() != str(val1).strip().lower():
                return False, f"value_mismatch_in_{k}"
        return True, "dict_keys_and_values_matched"

    return (r0 == r1), "generic_equality"
