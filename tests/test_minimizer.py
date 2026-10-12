"""
tests/test_minimizer.py: Unit tests for minimizer and transformer safety:
1. Schemas validation (schemas/plan.schema.json).
2. Prompt injection defense escaping.
3. Policy floor clamping (government_id & account_identifier).
4. Deterministic transforms for all 6 actions with edge cases (KEEP, DROP, MASK_PARTIAL, GENERALIZE, PSEUDONYMIZE, AGGREGATE).
5. Error handling: invalid offsets and text slice mismatches raise ValueError (no silent skips).
6. Deterministic overlap resolution between detected spans.
7. Verified removal bookkeeping (removed_values records only verified replacements).
8. Privacy: test outputs and exception strings never leak raw sensitive values.
"""

from pathlib import Path
from unittest.mock import MagicMock
import json
import os
import pytest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.detector import DetectedField
from experiment.planner import MinimizationPlanner, CATEGORIES, debug_inspect_prompt
from experiment.policy import enforce_policy_floor
from experiment.transform import apply_minimization, resolve_span_overlaps, transform_value


def test_policy_floor():
    # Attempting to KEEP government_id and account_identifier must fail and clamp
    raw_plan = {
        "case_id": "TEST-POLICY-1",
        "decisions": {
            "government_id": {"action": "KEEP", "reason": "Model tried to keep ID.", "confidence": 0.9},
            "account_identifier": {"action": "KEEP", "reason": "Model tried to keep account.", "confidence": 0.9},
            "person_name": {"action": "KEEP", "reason": "Identity check.", "confidence": 0.95},
        },
        "unsure": [],
        "task_output_schema": {}
    }

    enforced, violations = enforce_policy_floor(raw_plan)

    assert len(violations) == 2, f"Expected 2 violations, got {len(violations)}"
    assert enforced["decisions"]["government_id"]["action"] == "DROP"
    assert enforced["decisions"]["account_identifier"]["action"] == "MASK_PARTIAL"
    assert enforced["decisions"]["person_name"]["action"] == "KEEP"


def test_all_six_actions_normal_and_edge_cases():
    pseudo_map = {}
    counter = {}

    # 1. KEEP: value unchanged
    assert transform_value("Aarav Sharma", "person_name", "KEEP", pseudo_map, counter) == "Aarav Sharma"

    # 2. DROP: replaced with category placeholder
    assert transform_value("Aarav Sharma", "person_name", "DROP", pseudo_map, counter) == "[REDACTED:PERSON_NAME]"
    assert transform_value("9845012345", "contact", "DROP", pseudo_map, counter) == "[REDACTED:CONTACT]"

    # 3. MASK_PARTIAL: normal >= 4 digits, 2-3 digits, and edge cases
    assert transform_value("30981245781", "account_identifier", "MASK_PARTIAL", pseudo_map, counter) == "XXXX-XXXX-5781"
    assert transform_value("4532-8901-2345-6789", "account_identifier", "MASK_PARTIAL", pseudo_map, counter) == "XXXX-XXXX-6789"
    assert transform_value("12", "account_identifier", "MASK_PARTIAL", pseudo_map, counter) == "XXXX-12"
    assert transform_value("1", "account_identifier", "MASK_PARTIAL", pseudo_map, counter) == "XXXX"

    # 4. GENERALIZE: ISO date, DD-Mon-YYYY, DOB age bracket, PIN code, amounts, generic
    assert transform_value("2026-09-02", "transaction_date", "GENERALIZE", pseudo_map, counter) == "2026-09"
    assert transform_value("15-Sep-2026", "transaction_date", "GENERALIZE", pseudo_map, counter) == "Sep-2026"
    assert transform_value("1992-06-15", "date_of_birth", "GENERALIZE", pseudo_map, counter) == "Age bracket: 30s"
    assert transform_value("Flat 402, New Delhi 110024", "address", "GENERALIZE", pseudo_map, counter) == "[Region PIN: 110024]"
    assert transform_value("450.00", "amount", "GENERALIZE", pseudo_map, counter) == "< 1K"
    assert transform_value("32450.00", "balance", "GENERALIZE", pseudo_map, counter) == "10K - 1L"
    assert transform_value("General Text", "clause_text", "GENERALIZE", pseudo_map, counter) == "[GENERALIZED:CLAUSE_TEXT]"

    # 5. PSEUDONYMIZE: consistent mapping for same value, increments for distinct values
    p1 = transform_value("Vendor Alpha", "counterparty_name", "PSEUDONYMIZE", pseudo_map, counter)
    assert p1 == "Counterparty_name_1"
    p1_repeat = transform_value("Vendor Alpha", "counterparty_name", "PSEUDONYMIZE", pseudo_map, counter)
    assert p1_repeat == "Counterparty_name_1"
    p2 = transform_value("Vendor Beta", "counterparty_name", "PSEUDONYMIZE", pseudo_map, counter)
    assert p2 == "Counterparty_name_2"

    # 6. AGGREGATE: replaced with aggregate placeholder
    assert transform_value("450.00", "amount", "AGGREGATE", pseudo_map, counter) == "[AGGREGATED:AMOUNT]"


def test_transformer_error_handling_and_no_silent_skips():
    text = "Account: 30981245781 Date: 2026-09-02"

    # 1. Invalid out of bounds offsets must raise ValueError
    invalid_bounds_field = DetectedField("F_BAD_1", "account_identifier", "30981245781", {"line": 1, "start_char": 9, "end_char": 500}, "test", 1.0, "[ACCT]")
    with pytest.raises(ValueError) as excinfo:
        apply_minimization(text, [invalid_bounds_field], {"account_identifier": {"action": "DROP"}})
    assert "out of bounds" in str(excinfo.value)
    # Ensure error message does not expose raw sensitive value
    assert "30981245781" not in str(excinfo.value)

    # 2. Text slice mismatch must raise ValueError and NOT silently skip
    mismatched_field = DetectedField("F_BAD_2", "account_identifier", "99999999999", {"line": 1, "start_char": 9, "end_char": 20}, "test", 1.0, "[ACCT]")
    with pytest.raises(ValueError) as excinfo_mismatch:
        apply_minimization(text, [mismatched_field], {"account_identifier": {"action": "DROP"}})
    assert "Text mismatch" in str(excinfo_mismatch.value)
    assert "99999999999" not in str(excinfo_mismatch.value)


def test_deterministic_overlap_resolution():
    text = "Contact info: user@example.com at 2026-09-02"
    # Overlapping fields:
    # Field 1: custom regex for email (start: 14, end: 30), confidence 0.95
    f1_custom = DetectedField("F1", "contact", "user@example.com", {"line": 1, "start_char": 14, "end_char": 30}, "custom_pattern:email", 0.95, "[EMAIL]")
    # Field 2: Presidio partial match (start: 14, end: 25), confidence 0.85
    f2_presidio = DetectedField("F2", "contact", "user@exampl", {"line": 1, "start_char": 14, "end_char": 25}, "presidio:EMAIL", 0.85, "[EMAIL]")
    # Field 3: Non-overlapping field (start: 34, end: 44)
    f3_date = DetectedField("F3", "transaction_date", "2026-09-02", {"line": 1, "start_char": 34, "end_char": 44}, "custom_pattern:date", 0.95, "[DATE]")

    resolved = resolve_span_overlaps([f2_presidio, f1_custom, f3_date])

    # Custom regex (F1) must win over Presidio (F2) on overlap
    assert len(resolved) == 2
    assert resolved[0].id == "F1"
    assert resolved[1].id == "F3"


def test_verified_removal_bookkeeping():
    text = "Account: 30981245781 Amount: 450.00"
    fields = [
        DetectedField("F1", "account_identifier", "30981245781", {"line": 1, "start_char": 9, "end_char": 20}, "test", 1.0, "[ACCT]"),
        DetectedField("F2", "amount", "450.00", {"line": 1, "start_char": 29, "end_char": 35}, "test", 1.0, "[AMT]"),
    ]

    decisions = {
        "account_identifier": {"action": "DROP"},
        "amount": {"action": "KEEP"},
    }

    minimized, removed = apply_minimization(text, fields, decisions)

    # Only dropped field should be recorded in removed_values
    assert removed == ["30981245781"]
    assert "30981245781" not in minimized
    assert "450.00" in minimized
    assert "[REDACTED:ACCOUNT_IDENTIFIER]" in minimized


def test_deterministic_transformations_and_r1_contract():
    original_text = (
        "Statement for Aarav Sharma.\n"
        "Account: 30981245781\n"
        "Mobile: +91-9845012345\n"
        "Date: 2026-09-02\n"
        "Paid to Priya Patel amount INR 1200.00\n"
    )

    detected_fields = [
        DetectedField("F1", "account_identifier", "30981245781", {"line": 2, "start_char": 37, "end_char": 48}, "test", 1.0, "[ACCT]"),
        DetectedField("F2", "contact", "+91-9845012345", {"line": 3, "start_char": 57, "end_char": 71}, "test", 1.0, "[PHONE]"),
        DetectedField("F3", "transaction_date", "2026-09-02", {"line": 4, "start_char": 78, "end_char": 88}, "test", 1.0, "[DATE]"),
        DetectedField("F4", "counterparty_name", "Priya Patel", {"line": 5, "start_char": 97, "end_char": 108}, "test", 1.0, "[NAME]"),
    ]

    decisions = {
        "account_identifier": {"action": "MASK_PARTIAL"},
        "contact": {"action": "DROP"},
        "transaction_date": {"action": "GENERALIZE"},
        "counterparty_name": {"action": "PSEUDONYMIZE"},
    }

    minimized, removed_values = apply_minimization(original_text, detected_fields, decisions)

    # R1 CONTRACT VERIFICATION: Removed values must be strictly absent
    for removed in removed_values:
        assert removed not in minimized, f"Leaked value in R1 text: {removed}"

    assert "+91-9845012345" not in minimized
    assert "30981245781" not in minimized
    assert "2026-09-02" not in minimized
    assert "Priya Patel" not in minimized

    # Check transformed values
    assert "XXXX-XXXX-5781" in minimized
    assert "[REDACTED:CONTACT]" in minimized
    assert "2026-09" in minimized
    assert "Counterparty_name_1" in minimized


def test_planner_prompt_and_schema():
    planner = MinimizationPlanner(live_mode=False)
    prompt = planner.build_prompt("BS-1-A", "Summarize spending", "Account: [ACCT]", answer_schema_id="spending_summary")
    assert "<document_data>" in prompt
    assert "</document_data>" in prompt
    assert "Expected Task Schema ID: spending_summary" in prompt

    plan, retries = planner.plan("BS-1-A", "Summarize spending", "Account: [ACCT]")
    assert planner.validate_plan_schema(plan, expected_case_id="BS-1-A")
    assert plan["case_id"] == "BS-1-A"
    assert retries == 0
    # All 16 categories must be present
    assert set(plan["decisions"].keys()) == set(CATEGORIES)


def test_schema_validation_strictness():
    planner = MinimizationPlanner(live_mode=False)
    valid_plan, _ = planner.plan("BS-1-A", "Summarize spending", "Account: [ACCT]")
    assert planner.validate_plan_schema(valid_plan, "BS-1-A")

    # 1. Missing category must fail
    missing_cat_plan = json.loads(json.dumps(valid_plan))
    del missing_cat_plan["decisions"]["account_identifier"]
    assert not planner.validate_plan_schema(missing_cat_plan)

    # 2. Unknown category must fail
    unknown_cat_plan = json.loads(json.dumps(valid_plan))
    unknown_cat_plan["decisions"]["unknown_extra"] = {"action": "DROP", "reason": "invalid", "confidence": 0.5}
    assert not planner.validate_plan_schema(unknown_cat_plan)

    # 3. Invalid action must fail
    invalid_action_plan = json.loads(json.dumps(valid_plan))
    invalid_action_plan["decisions"]["account_identifier"]["action"] = "REMOVE"
    assert not planner.validate_plan_schema(invalid_action_plan)

    # 4. Out-of-bounds confidence must fail
    invalid_conf_plan = json.loads(json.dumps(valid_plan))
    invalid_conf_plan["decisions"]["account_identifier"]["confidence"] = 1.5
    assert not planner.validate_plan_schema(invalid_conf_plan)

    # 5. Empty reason must fail
    empty_reason_plan = json.loads(json.dumps(valid_plan))
    empty_reason_plan["decisions"]["account_identifier"]["reason"] = "   "
    assert not planner.validate_plan_schema(empty_reason_plan)

    # 6. Mismatched case_id must fail
    assert not planner.validate_plan_schema(valid_plan, expected_case_id="BS-2-B")


def test_mock_mode_no_evaluator_leakage():
    planner = MinimizationPlanner(live_mode=False)

    # Identity verification task without is_trap flag
    id_plan, _ = planner.plan("BS-1-C", "Is this statement mine?", "Account: [ACCT]")
    assert id_plan["decisions"]["person_name"]["action"] == "KEEP"
    assert id_plan["decisions"]["account_identifier"]["action"] == "MASK_PARTIAL"
    assert id_plan["decisions"]["merchant"]["action"] == "DROP"

    # Spending task without is_trap flag
    spend_plan, _ = planner.plan("BS-1-A", "Summarize my spending by category", "Account: [ACCT]")
    assert spend_plan["decisions"]["merchant"]["action"] == "KEEP"
    assert spend_plan["decisions"]["account_identifier"]["action"] == "DROP"


def test_live_mode_dispatch_and_mocked_gemini():
    planner = MinimizationPlanner(live_mode=False)
    valid_plan_data, _ = planner.plan("BS-1-A", "Summarize spending", "Account: [ACCT]")

    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_plan_data)
    mock_gemini_client.generate_content.return_value = mock_response

    live_planner = MinimizationPlanner(live_client=mock_gemini_client)
    result_plan, retries = live_planner.plan("BS-1-A", "Summarize spending", "Account: [ACCT]")

    # Verify generate_content was actually called
    assert mock_gemini_client.generate_content.called
    assert result_plan["case_id"] == "BS-1-A"
    assert retries == 0


def test_live_mode_api_failure_no_silent_mock_fallback():
    mock_gemini_client = MagicMock()
    mock_gemini_client.generate_content.side_effect = RuntimeError("Simulated Gemini API quota exceeded")

    live_planner = MinimizationPlanner(live_client=mock_gemini_client)

    # Must raise RuntimeError and NOT silently return a mock plan
    with pytest.raises(RuntimeError) as excinfo:
        live_planner.plan("BS-1-A", "Summarize spending", "Account: [ACCT]")

    assert "Live planner failed" in str(excinfo.value)
    assert "Mock fallback is strictly prohibited" in str(excinfo.value)


def test_live_mode_missing_credentials(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # MinimizationPlanner(live_mode=True) without credentials must fail safely
    with pytest.raises(ValueError) as excinfo:
        MinimizationPlanner(live_mode=True, live_client=None)
    assert "GEMINI_API_KEY not found" in str(excinfo.value)


def test_prompt_debug_privacy_and_activation(monkeypatch, capsys):
    # 1. Disabled by default
    monkeypatch.delenv("JUSTENOUGH_DEBUG_PROMPT", raising=False)
    debug_inspect_prompt("BS-1-A", "gemini-flash-latest", "system prompt", "user prompt")
    captured = capsys.readouterr()
    assert captured.out == ""

    # 2. Enabled when JUSTENOUGH_DEBUG_PROMPT=1
    monkeypatch.setenv("JUSTENOUGH_DEBUG_PROMPT", "1")
    debug_inspect_prompt("BS-1-A", "gemini-flash-latest", "system prompt", "user prompt with [ACCT]")
    captured = capsys.readouterr()
    assert "[TEMPORARY DEBUG] PROMPT PAYLOAD" in captured.out
    assert "Case ID: BS-1-A" in captured.out

    # 3. Privacy guard against raw sensitive values
    with pytest.raises(ValueError) as exc_raw:
        debug_inspect_prompt(
            "BS-1-A", "gemini-flash-latest", "system", "Prompt with Aarav Sharma",
            raw_sensitive_values=["Aarav Sharma"]
        )
    assert "Raw sensitive value detected" in str(exc_raw.value)

    # 4. Privacy guard against unmasked PAN patterns
    with pytest.raises(ValueError) as exc_pan:
        debug_inspect_prompt("BS-1-A", "gemini-flash-latest", "system", "Prompt with ABCDE1234F")
    assert "Unmasked PAN pattern detected" in str(exc_pan.value)


if __name__ == "__main__":
    test_policy_floor()
    test_all_six_actions_normal_and_edge_cases()
    test_transformer_error_handling_and_no_silent_skips()
    test_deterministic_overlap_resolution()
    test_verified_removal_bookkeeping()
    test_deterministic_transformations_and_r1_contract()
    test_planner_prompt_and_schema()
    test_schema_validation_strictness()
    test_mock_mode_no_evaluator_leakage()
    test_live_mode_dispatch_and_mocked_gemini()
    test_live_mode_api_failure_no_silent_mock_fallback()
    print("\nAll minimizer and transformer safety tests passed successfully.")
