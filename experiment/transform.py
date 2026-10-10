"""
experiment/transform.py: Deterministic transformation engine for JustEnough Day 1.

Applies the 6 frozen actions to detected fields without any LLM rewriting:
- KEEP: Exact value is retained.
- DROP: Completely replaced with [REDACTED:<CATEGORY>].
- MASK_PARTIAL: Preserves trailing 4 digits (e.g. XXXX-XXXX-1234).
- GENERALIZE: Coarsens resolution (e.g. YYYY-MM-DD -> YYYY-MM, age bracket, PIN).
- PSEUDONYMIZE: Consistent mapping within doc (e.g. Counterparty_1).
- AGGREGATE: Replaces itemized occurrences with [AGGREGATED:<CATEGORY>].

Safety Guarantees:
1. Validates all offsets against text length and checks that text slice matches field value before replacement.
2. Fails safely on any offset mismatch or invalid bounds without silently skipping.
3. Resolves overlapping spans deterministically (custom regex > Presidio > higher confidence > longer span).
4. Records values in removed_values ONLY after replacement has been verified on the text slice.
5. Error messages and logs never leak raw sensitive values.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from experiment.detector import DetectedField


def transform_value(
    value: str,
    category: str,
    action: str,
    pseudonym_map: Dict[str, str],
    category_counter: Dict[str, int]
) -> str:
    """Deterministically transforms a single value based on action semantics."""
    if action == "KEEP":
        return value

    if action == "DROP":
        return f"[REDACTED:{category.upper()}]"

    if action == "MASK_PARTIAL":
        # Extract digits / alphanumeric characters
        clean = re.sub(r"[\s\-]", "", value)
        if len(clean) >= 4:
            trailer = clean[-4:]
            return f"XXXX-XXXX-{trailer}"
        if len(clean) >= 2:
            return f"XXXX-{clean[-2:]}"
        return "XXXX"

    if action == "GENERALIZE":
        # 1. DOB / Age generalization: YYYY-MM-DD -> Age bracket
        if category == "date_of_birth":
            dob_match = re.match(r"^(\d{4})-\d{2}-\d{2}$", value)
            if dob_match:
                year = int(dob_match.group(1))
                approx_age = 2026 - year
                age_band = f"{(approx_age // 10) * 10}s"
                return f"Age bracket: {age_band}"

        # 2. Date generalization: YYYY-MM-DD -> YYYY-MM
        date_iso = re.match(r"^(\d{4}-\d{2})-\d{2}$", value)
        if date_iso:
            return date_iso.group(1)

        # DD-Mon-YYYY -> Mon-YYYY
        date_text = re.match(r"^\d{1,2}-([A-Za-z]{3})-(\d{4})$", value)
        if date_text:
            return f"{date_text.group(1)}-{date_text.group(2)}"

        # 3. Address generalization: extract 6-digit Indian PIN code if present
        pin_match = re.search(r"\b(\d{6})\b", value)
        if pin_match:
            return f"[Region PIN: {pin_match.group(1)}]"

        # 4. Amount generalization: rough order of magnitude
        amt_match = re.search(r"(\d+(?:\.\d{2})?)", value.replace(",", ""))
        if amt_match and category in ("amount", "balance"):
            try:
                amt = float(amt_match.group(1))
                if amt < 1000:
                    return "< 1K"
                elif amt < 10000:
                    return "1K - 10K"
                elif amt < 100000:
                    return "10K - 1L"
                else:
                    return "> 1L"
            except ValueError:
                pass

        return f"[GENERALIZED:{category.upper()}]"

    if action == "PSEUDONYMIZE":
        if value not in pseudonym_map:
            category_counter[category] = category_counter.get(category, 0) + 1
            idx = category_counter[category]
            pseudonym_map[value] = f"{category.capitalize()}_{idx}"
        return pseudonym_map[value]

    if action == "AGGREGATE":
        return f"[AGGREGATED:{category.upper()}]"

    # Default fallback to DROP for unrecognized actions
    return f"[REDACTED:{category.upper()}]"


def resolve_span_overlaps(fields: List[DetectedField]) -> List[DetectedField]:
    """
    Deterministically resolves overlapping spans.
    Precedence rules:
    1. Custom regex patterns take priority over Presidio NLP.
    2. Higher confidence score wins.
    3. Longer span wins.
    4. Earlier start offset wins.
    Returns a strictly non-overlapping list of fields sorted by start_char ascending.
    """
    if not fields:
        return []

    def sort_key(f: DetectedField):
        is_custom = 1 if f.detector.startswith("custom_pattern") else 0
        span_len = f.location["end_char"] - f.location["start_char"]
        return (-is_custom, -f.confidence, -span_len, f.location["start_char"])

    candidates = sorted(fields, key=sort_key)
    accepted: List[DetectedField] = []

    for cand in candidates:
        cs = cand.location["start_char"]
        ce = cand.location["end_char"]
        # Check overlap against all already accepted fields
        has_overlap = False
        for acc in accepted:
            as_ = acc.location["start_char"]
            ae = acc.location["end_char"]
            if not (ce <= as_ or cs >= ae):
                has_overlap = True
                break
        if not has_overlap:
            accepted.append(cand)

    # Sort accepted fields by start_char ascending
    accepted.sort(key=lambda f: f.location["start_char"])
    return accepted


def validate_fields(original_text: str, fields: List[DetectedField]) -> None:
    """
    Validates bounds and text matches for all detected fields.
    Raises ValueError on any mismatch without leaking raw sensitive values.
    """
    text_len = len(original_text)
    for f in fields:
        start = f.location.get("start_char")
        end = f.location.get("end_char")

        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"Transformation failed: Field {f.id} has invalid non-integer location coordinates.")

        if not (0 <= start <= end <= text_len):
            raise ValueError(
                f"Transformation failed: Field {f.id} span [{start}:{end}] is out of bounds for text of length {text_len}."
            )

        actual_slice = original_text[start:end]
        if actual_slice != f.value:
            raise ValueError(
                f"Transformation failed: Text mismatch at span [{start}:{end}] for field {f.id}. "
                f"Expected length {len(f.value)}, found slice length {len(actual_slice)}."
            )


def apply_minimization(
    original_text: str,
    detected_fields: List[DetectedField],
    plan_decisions: Dict[str, Dict[str, Any]],
    strict: bool = True
) -> Tuple[str, List[str]]:
    """
    Deterministically transforms original text into the minimized representation (R1 input).
    Guarantees:
    - Pre-validates all coordinates and slice matches before any replacement.
    - Resolves overlapping spans deterministically.
    - Right-to-left substitution to preserve slice offsets.
    - Verifies removal before adding to removed_values.
    - Raises ValueError on any validation failure; never silently skips unminimized text.

    Returns (minimized_text, removed_values).
    """
    if not detected_fields:
        return original_text, []

    # 1. Deterministic overlap resolution
    resolved_fields = resolve_span_overlaps(detected_fields)

    # 2. Strict validation of coordinates and text slice matches
    if strict:
        validate_fields(original_text, resolved_fields)

    pseudonym_map: Dict[str, str] = {}
    category_counter: Dict[str, int] = {}
    removed_values: List[str] = []

    # 3. Sort fields from right to left (descending start_char) to preserve offsets
    sorted_fields = sorted(resolved_fields, key=lambda f: f.location["start_char"], reverse=True)

    minimized = original_text

    for f in sorted_fields:
        cat = f.category
        val = f.value
        dec = plan_decisions.get(cat, {"action": "DROP"})
        action = dec.get("action", "DROP")

        start = f.location["start_char"]
        end = f.location["end_char"]

        # Double check match before replacing
        if original_text[start:end] != val:
            raise ValueError(
                f"Transformation failed: Pre-replacement slice mismatch at [{start}:{end}] for field {f.id}."
            )

        replacement = transform_value(val, cat, action, pseudonym_map, category_counter)

        # Perform replacement
        minimized = minimized[:start] + replacement + minimized[end:]

        # Verified removal bookkeeping: record only after verified slice substitution
        if action != "KEEP":
            removed_values.append(val)

    return minimized, removed_values
