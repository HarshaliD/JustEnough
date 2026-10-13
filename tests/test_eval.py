"""
tests/test_eval.py: Unit tests for evaluator components.
Tests:
1. Number, list, and free-text comparators.
2. Metrics computation with dummy fixture.
3. Smoke runner executes cleanly and isolates all files under results/smoke/.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from eval.comparators import compare_answers, compare_lists, compare_numbers, compare_free_text
from eval.metrics import compute_metrics
from eval.smoke_runner import run_smoke_test, SMOKE_OUTPUT_DIR


def test_comparators():
    # 0.5% relative tolerance
    assert compare_numbers(100.0, 100.4) is True  # 0.4% diff -> pass
    assert compare_numbers(100.0, 100.6) is False  # 0.6% diff -> fail
    assert compare_numbers("1,200.00", 1200) is True

    # List set equality
    assert compare_lists(["a", "b"], ["b", "a"]) is True
    assert compare_lists(["a", "b"], ["a", "c"]) is False

    # Free text rubric matching
    rubric = {"required_facts": ["rent", "deposit"]}
    match, reason = compare_free_text("The rent is 38k and deposit is 114k.", "The rent is 38k and deposit is 114k.", rubric)
    assert match is True
    match_fail, _ = compare_free_text("Only rent.", "Only rent.", rubric)
    assert match_fail is False


def test_smoke_runner_isolation():
    metrics = run_smoke_test()
    assert metrics["total_cases_evaluated"] == 4
    assert metrics["answer_preservation"] >= 0.75

    # Check that outputs are strictly under results/smoke/
    assert (SMOKE_OUTPUT_DIR / "smoke_results.json").exists()
    assert (SMOKE_OUTPUT_DIR / "smoke_failures.json").exists()
    assert (SMOKE_OUTPUT_DIR / "smoke_report.md").exists()
    assert (SMOKE_OUTPUT_DIR / "raw" / "BS-1-A_smoke.json").exists()

    # Verify that results/results.json and results/raw do NOT exist
    assert not (PROJECT_ROOT / "results" / "results.json").exists()
    assert not (PROJECT_ROOT / "results" / "raw").exists()
    print("\nEvaluator test passed: comparators, metrics, and smoke output isolation verified.")


def test_actual_ground_truth_loading():
    """Verifies that the actual ground_truth/labels.json loads without errors, has 30 cases, and covers 16 categories."""
    from eval.metrics import load_ground_truth, CANONICAL_CATEGORIES

    gt_path = PROJECT_ROOT / "ground_truth" / "labels.json"
    assert gt_path.exists()

    loaded = load_ground_truth(gt_path)
    assert len(loaded) == 30, f"Expected 30 cases in labels.json, got {len(loaded)}"

    for case_id, cat_map in loaded.items():
        assert set(cat_map.keys()) == CANONICAL_CATEGORIES, f"Case {case_id} categories mismatch canonical set"
        for cat, info in cat_map.items():
            assert "present" in info and isinstance(info["present"], bool)
            assert "required" in info and isinstance(info["required"], bool)
            assert "acceptable_actions" in info and isinstance(info["acceptable_actions"], list)
            assert len(info["acceptable_actions"]) > 0
            assert "ambiguous" in info and isinstance(info["ambiguous"], bool)


def test_ground_truth_loader_malformed_structures():
    """Verifies that malformed or missing label structures raise ValueError and never silently default to empty dicts."""
    import pytest
    from eval.metrics import load_ground_truth

    # Missing file
    with pytest.raises(ValueError, match="does not exist"):
        load_ground_truth("nonexistent/path/labels.json")

    # Empty dictionary
    with pytest.raises(ValueError, match="non-empty"):
        load_ground_truth({})

    # Missing cases mapping
    with pytest.raises(ValueError, match="missing 'cases'"):
        load_ground_truth({"some_key": {}})

    # Case missing labels/categories
    with pytest.raises(ValueError, match="missing 'labels' or 'categories'"):
        load_ground_truth({"cases": {"CASE-1": {"task": "dummy"}}})

    # Category missing acceptable_actions
    with pytest.raises(ValueError, match="missing required field 'acceptable_actions'"):
        load_ground_truth({
            "cases": {
                "CASE-1": {
                    "labels": {
                        "person_name": {"present": True, "required": True, "ambiguous": False}
                    }
                }
            }
        })

    # Category with invalid action
    with pytest.raises(ValueError, match="Invalid action"):
        load_ground_truth({
            "cases": {
                "CASE-1": {
                    "labels": {
                        "person_name": {
                            "present": True,
                            "required": True,
                            "ambiguous": False,
                            "acceptable_actions": ["INVALID_ACTION"],
                        }
                    }
                }
            }
        })


def test_ground_truth_present_false_and_ambiguous_filtering():
    """Verifies that present: false is excluded and ambiguous labels are excluded from agreement scoring but counted."""
    mock_gt = {
        "cases": {
            "CASE-1": {
                "labels": {
                    # Cat 1: present, not ambiguous, required, acceptable KEEP, action KEEP -> agreement +1, no over-redaction
                    "person_name": {
                        "present": True, "required": True, "acceptable_actions": ["KEEP"], "ambiguous": False
                    },
                    # Cat 2: present=False -> skipped! Must not count in under-redaction even if KEEP
                    "account_identifier": {
                        "present": False, "required": False, "acceptable_actions": ["DROP"], "ambiguous": False
                    },
                    # Cat 3: present=True, ambiguous=True -> excluded from agreement scoring, increments ambiguous_count
                    "counterparty_name": {
                        "present": True, "required": False, "acceptable_actions": ["DROP"], "ambiguous": True
                    },
                    # Cat 4: present=True, required=True, acceptable KEEP, action DROP -> over-redaction hit!
                    "amount": {
                        "present": True, "required": True, "acceptable_actions": ["KEEP"], "ambiguous": False
                    },
                    # Cat 5: present=True, required=False, acceptable DROP, action KEEP -> under-redaction hit!
                    "merchant": {
                        "present": True, "required": False, "acceptable_actions": ["DROP"], "ambiguous": False
                    },
                }
            }
        }
    }

    eval_cases = [{
        "case_id": "CASE-1",
        "doc_id": "D1",
        "is_preserved": True,
        "plan_decisions": {
            "person_name": {"action": "KEEP"},
            "account_identifier": {"action": "KEEP"},  # present=False in GT -> must NOT count as under-redaction
            "counterparty_name": {"action": "DROP"},   # ambiguous=True -> excluded from agreement
            "amount": {"action": "DROP"},              # over-redaction!
            "merchant": {"action": "KEEP"},            # under-redaction!
        }
    }]

    metrics = compute_metrics(eval_cases, ground_truth_labels=mock_gt)

    assert metrics["ambiguous_labels_count"] == 1
    # Eligible non-ambiguous present categories: person_name, amount, merchant (3 total)
    assert metrics["label_agreement_eligible"] == 3
    # Agreed: person_name (KEEP in [KEEP]), merchant is KEEP not in [DROP], amount is DROP not in [KEEP]
    assert metrics["label_agreements_count"] == 1
    assert metrics["label_agreement_rate"] == round(1 / 3, 4)

    # Over-redaction: required present categories are person_name, amount (2 total). amount was DROP -> 1 over-redaction
    assert metrics["over_redaction_eligible"] == 2
    assert metrics["over_redactions_count"] == 1
    assert metrics["over_redaction_rate"] == 0.5

    # Under-redaction: non-required present categories is merchant (1 total; account_identifier was present=False so excluded!)
    assert metrics["under_redaction_eligible"] == 1
    assert metrics["under_redactions_count"] == 1
    assert metrics["under_redaction_rate"] == 1.0


def test_answer_preservation_stable_vs_unstable_and_unevaluable():
    """Verifies that unstable and unevaluable cases are excluded from the primary answer-preservation denominator."""
    eval_cases = [
        {"case_id": "C-1", "is_preserved": True, "is_unstable": False},    # stable preserved
        {"case_id": "C-2", "is_preserved": False, "is_unstable": False},   # stable failed
        {"case_id": "C-3", "is_preserved": True, "is_unstable": True},     # unstable baseline (excluded!)
        {
            "case_id": "C-4",
            "is_preserved": False,
            "is_unstable": False,
            "match_reason": "human_rubric_required",  # unevaluable (excluded from stable!)
        },
    ]

    metrics = compute_metrics(eval_cases)
    assert metrics["total_cases_evaluated"] == 4
    assert metrics["stable_cases"] == 2
    assert metrics["unstable_cases"] == 1
    assert metrics["unevaluable_cases"] == 1
    assert metrics["preserved_cases"] == 1
    # Primary denominator is stable cases: 1 / 2 = 0.5 (50.0%)
    assert metrics["answer_preservation"] == 0.5
    assert metrics["unstable_cases_list"] == ["C-3"]


def test_decision_consistency():
    """Verifies calculation of 3-run decision consistency and not_measured state when repeated plans are absent."""
    # Scenario A: Repeated plans supplied
    repeated_plans = {
        "C-1": [
            {"person_name": {"action": "KEEP"}, "merchant": {"action": "KEEP"}},
            {"person_name": {"action": "KEEP"}, "merchant": {"action": "KEEP"}},
            {"person_name": {"action": "KEEP"}, "merchant": {"action": "KEEP"}},
        ],
        "C-2": [
            {"person_name": {"action": "DROP"}, "merchant": {"action": "DROP"}},
            {"person_name": {"action": "DROP"}, "merchant": {"action": "KEEP"}},  # merchant differs on run 2
            {"person_name": {"action": "DROP"}, "merchant": {"action": "DROP"}},
        ],
    }

    eval_cases = [
        {"case_id": "C-1", "is_preserved": True},
        {"case_id": "C-2", "is_preserved": True},
    ]

    metrics_with_repeats = compute_metrics(eval_cases, repeated_plans=repeated_plans)
    assert metrics_with_repeats["decision_consistency_status"] == "measured"
    assert metrics_with_repeats["consistency_eligible_decisions"] == 4
    assert metrics_with_repeats["consistent_decisions_count"] == 3
    assert metrics_with_repeats["decision_consistency"] == 0.75

    # Scenario B: No repeated plans supplied -> must report not_measured, NOT 1.0!
    metrics_without_repeats = compute_metrics(eval_cases)
    assert metrics_without_repeats["decision_consistency"] is None
    assert "not_measured" in metrics_without_repeats["decision_consistency_status"]


def test_sensitive_field_reduction_actions_and_leaks():
    """Verifies instance-based reduction across all 6 actions, leak penalty, and unavailable status when missing."""
    # Scenario A: Field instances provided covering all 6 actions
    # Retention weights: KEEP=1.0, DROP=0.0, MASK_PARTIAL=0.25, GENERALIZE=0.25, PSEUDONYMIZE=0.50, AGGREGATE=0.25
    eval_cases = [{
        "case_id": "C-1",
        "is_preserved": True,
        "plan_decisions": {
            "cat_keep": {"action": "KEEP"},
            "cat_drop": {"action": "DROP"},
            "cat_mask": {"action": "MASK_PARTIAL"},
            "cat_gen": {"action": "GENERALIZE"},
            "cat_pseudo": {"action": "PSEUDONYMIZE"},
            "cat_agg": {"action": "AGGREGATE"},
        },
        "detected_fields": [
            {"category": "cat_keep", "value": "v1"},
            {"category": "cat_drop", "value": "v2"},
            {"category": "cat_mask", "value": "v3"},
            {"category": "cat_gen", "value": "v4"},
            {"category": "cat_pseudo", "value": "v5"},
            {"category": "cat_agg", "value": "v6"},
        ]
    }]

    metrics = compute_metrics(eval_cases)
    assert metrics["total_sensitive_instances"] == 6
    # Retained: 1.0 + 0.0 + 0.25 + 0.25 + 0.50 + 0.25 = 2.25
    assert metrics["retained_sensitive_instances"] == 2.25
    # Reduction: (6 - 2.25) / 6 = 3.75 / 6 = 0.625
    assert metrics["sensitive_field_reduction"] == 0.625
    assert metrics["sensitive_field_reduction_status"] == "measured"

    # Scenario B: Leaked value penalty: DROP action but value was leaked
    eval_cases_leaked = [{
        "case_id": "C-LEAK",
        "is_preserved": True,
        "plan_decisions": {"cat_drop": {"action": "DROP"}},
        "detected_fields": [{"category": "cat_drop", "value": "secret_name"}],
        "removed_values_leaked": ["secret_name"],  # Leaked into R1!
    }]
    metrics_leak = compute_metrics(eval_cases_leaked)
    assert metrics_leak["retained_sensitive_instances"] == 1.0  # Penalized as full retention
    assert metrics_leak["sensitive_field_reduction"] == 0.0

    # Scenario C: No instance artifacts supplied -> must report unavailable, never invent data
    eval_cases_no_fields = [{"case_id": "C-NOFIELDS", "is_preserved": True}]
    metrics_no_fields = compute_metrics(eval_cases_no_fields)
    assert metrics_no_fields["sensitive_field_reduction"] is None
    assert "unavailable" in metrics_no_fields["sensitive_field_reduction_status"]


def test_zero_eligible_denominators():
    """Verifies that zero eligible denominators return None rather than 0.0."""
    metrics_empty = compute_metrics([])
    assert metrics_empty["answer_preservation"] is None
    assert metrics_empty["sensitive_field_reduction"] is None
    assert metrics_empty["decision_consistency"] is None
    assert metrics_empty["trap_check_rate"] is None
    assert metrics_empty["label_agreement_rate"] is None
    assert metrics_empty["over_redaction_rate"] is None
    assert metrics_empty["under_redaction_rate"] is None

    # Cases evaluated, but zero required labels -> over_redaction_rate is None
    mock_gt = {
        "cases": {
            "C-1": {
                "labels": {
                    "merchant": {"present": True, "required": False, "acceptable_actions": ["KEEP"], "ambiguous": False}
                }
            }
        }
    }
    cases = [{"case_id": "C-1", "is_preserved": True, "plan_decisions": {"merchant": {"action": "KEEP"}}}]
    metrics = compute_metrics(cases, ground_truth_labels=mock_gt)
    assert metrics["over_redaction_rate"] is None  # 0 required labels
    assert metrics["under_redaction_rate"] == 0.0  # 1 non-required label, 0 under-redactions (KEEP in acceptable)


def test_trap_and_matching_nontrap_pairwise_check():
    """Verifies pairwise trap check across document families."""
    # Doc 1: Passes pairwise (trap retains identity; non-trap minimizes it)
    # Doc 2: Fails pairwise (non-trap fails to minimize identity)
    eval_cases = [
        # Doc BS-1
        {
            "case_id": "BS-1-C",
            "doc_id": "BS-1",
            "is_trap": True,
            "is_preserved": True,
            "plan_decisions": {"person_name": {"action": "KEEP"}},  # identity retained
        },
        {
            "case_id": "BS-1-A",
            "doc_id": "BS-1",
            "is_trap": False,
            "is_preserved": True,
            "plan_decisions": {"person_name": {"action": "DROP"}, "account_identifier": {"action": "DROP"}},
        },
        # Doc BS-2
        {
            "case_id": "BS-2-C",
            "doc_id": "BS-2",
            "is_trap": True,
            "is_preserved": True,
            "plan_decisions": {"person_name": {"action": "KEEP"}},
        },
        {
            "case_id": "BS-2-A",
            "doc_id": "BS-2",
            "is_trap": False,
            "is_preserved": True,
            "plan_decisions": {"person_name": {"action": "KEEP"}},  # Violation: non-trap KEPT identity!
        },
    ]

    metrics = compute_metrics(eval_cases)
    assert metrics["trap_check_mode"] == "pairwise"
    assert metrics["trap_pairs_evaluated"] == 2
    assert metrics["trap_pairs_passed"] == 1
    assert metrics["trap_check_rate"] == 0.5


def test_failure_attribution_and_missing_evidence():
    """Verifies that failures are attributed across the 4 frozen categories and unattributed when evidence is missing."""
    eval_cases = [
        # 1. Detection miss
        {"case_id": "F-1", "is_preserved": False, "failure_stage": "detection", "failure_evidence": "detector missed CIF"},
        # 2. Planner error
        {"case_id": "F-2", "is_preserved": False, "failure_stage": "planner", "failure_evidence": "policy floor violation"},
        # 3. Ambiguous label
        {"case_id": "F-3", "is_preserved": False, "failure_stage": "ground_truth", "failure_evidence": "label ambiguous"},
        # 4. Comparison error
        {"case_id": "F-4", "is_preserved": False, "failure_stage": "comparator", "failure_evidence": "numeric_out_of_tolerance"},
        # 5. Missing evidence -> unattributed (never defaulting to comparison error!)
        {"case_id": "F-5", "is_preserved": False},
    ]

    metrics = compute_metrics(eval_cases)
    counts = metrics["failure_counts"]
    assert counts["detection miss"] == 1
    assert counts["planner error"] == 1
    assert counts["ambiguous label"] == 1
    assert counts["comparison error"] == 1
    assert counts["unattributed"] == 1


def test_load_answer_schemas():
    """Verifies that schemas/answer_schemas.json loads cleanly and defines all 17 schema IDs."""
    from eval.comparators import load_answer_schemas

    schemas = load_answer_schemas()
    assert len(schemas) == 17, f"Expected 17 schemas, got {len(schemas)}"

    phase1_schemas = [
        "identity_check", "balance_summary", "transaction_total", "deduction_summary",
        "spending_summary", "cashflow_summary", "salary_summary", "usage_summary",
        "top_transactions", "payment_due", "bill_summary",
    ]
    for s_id in phase1_schemas:
        assert s_id in schemas, f"Phase 1 schema '{s_id}' missing in schemas/answer_schemas.json"
        assert "type" in schemas[s_id] or "oneOf" in schemas[s_id] or "anyOf" in schemas[s_id]


def test_phase1_deterministic_comparators():
    """Direct tests for matching and non-matching outputs for all 11 Phase 1 schemas."""
    from eval.comparators import compare_answers

    # 1. identity_check: True match, False match, mismatch, and no-truthiness-fallback check
    # 1a. True == True
    match, _ = compare_answers({"is_mine": True}, {"is_mine": True}, "identity_check")
    assert match is True
    # 1b. False == False (explicit False identity verdict)
    match_false, reason = compare_answers({"is_mine": False}, {"is_mine": False}, "identity_check")
    assert match_false is True, f"Failed on False == False identity verdict: {reason}"
    # 1c. True != False
    mismatch, _ = compare_answers({"is_mine": True}, {"is_mine": False}, "identity_check")
    assert mismatch is False
    # 1d. Ensure False is not overridden by truthiness fallback when multiple keys exist
    # R0 has is_mine=False (explicit boolean); R1 has is_mine=True -> must be False mismatch
    mismatch_bug, _ = compare_answers({"is_mine": False, "matches_owner": True}, {"is_mine": True}, "identity_check")
    assert mismatch_bug is False

    # 2. balance_summary: tolerance match & out-of-tolerance mismatch
    match, _ = compare_answers({"total_balance": 32450.0}, {"balance": 32550.0}, "balance_summary")
    assert match is True  # ~0.3% diff <= 0.5%
    mismatch, _ = compare_answers({"total_balance": 32450.0}, {"total_balance": 33000.0}, "balance_summary")
    assert mismatch is False

    # 3. transaction_total: tolerance match & mismatch
    match, _ = compare_answers({"total_amount": 1450.0}, {"upi_total": 1455.0}, "transaction_total")
    assert match is True  # ~0.34% diff <= 0.5%
    mismatch, _ = compare_answers({"total_amount": 1450.0}, {"total_amount": 1800.0}, "transaction_total")
    assert mismatch is False

    # 4. deduction_summary: tolerance match & mismatch
    match, _ = compare_answers({"total_deductions": 11800.0}, {"total": 11800.0}, "deduction_summary")
    assert match is True
    mismatch, _ = compare_answers({"total_deductions": 11800.0}, {"total_deductions": 10000.0}, "deduction_summary")
    assert mismatch is False

    # 5. spending_summary: case-insensitive keys, numeric tolerance, category mismatch
    r0_spend = {"food": 450.0, "travel": 1200.0}
    r1_spend = {"Food": 451.0, "TRAVEL": 1200.0}
    match, _ = compare_answers(r0_spend, r1_spend, "spending_summary")
    assert match is True
    mismatch_key, _ = compare_answers({"food": 450.0}, {"groceries": 450.0}, "spending_summary")
    assert mismatch_key is False
    mismatch_val, _ = compare_answers({"food": 450.0}, {"food": 550.0}, "spending_summary")
    assert mismatch_val is False

    # 6. cashflow_summary: inflow & outflow tolerance, mismatch
    r0_cash = {"total_inflow": 50000.0, "total_outflow": 30000.0}
    r1_cash = {"inflow": 50100.0, "outflow": 30050.0}
    match, _ = compare_answers(r0_cash, r1_cash, "cashflow_summary")
    assert match is True
    mismatch, _ = compare_answers(r0_cash, {"total_inflow": 45000.0, "total_outflow": 30000.0}, "cashflow_summary")
    assert mismatch is False

    # 7. salary_summary: components match & mismatch
    r0_sal = {"basic": 55000.0, "net": 87450.0}
    r1_sal = {"Basic": 55100.0, "Net": 87450.0}
    match, _ = compare_answers(r0_sal, r1_sal, "salary_summary")
    assert match is True
    mismatch, _ = compare_answers(r0_sal, {"basic": 60000.0, "net": 87450.0}, "salary_summary")
    assert mismatch is False

    # 8. usage_summary: units & charges tolerance, mismatch
    r0_use = {"billed_consumption": 420.0, "total_charges": 4180.0}
    r1_use = {"units": 421.0, "total_amount": 4190.0}
    match, _ = compare_answers(r0_use, r1_use, "usage_summary")
    assert match is True
    mismatch, _ = compare_answers(r0_use, {"billed_consumption": 300.0, "total_charges": 4180.0}, "usage_summary")
    assert mismatch is False

    # 9. top_transactions: numeric lists order-insensitive descending, tolerance, length mismatch
    r0_top = [18500.0, 12400.0, 9500.0]
    r1_top = [12400.0, 18550.0, 9520.0]  # different order, within 0.5% tolerance
    match, _ = compare_answers(r0_top, r1_top, "top_transactions")
    assert match is True
    # Object list format with amount
    match_objs, _ = compare_answers(
        [{"amount": 18500.0, "desc": "laptop"}, {"amount": 12400.0, "desc": "flight"}],
        [{"amount": 18500.0}, {"amount": 12400.0}],
        "top_transactions"
    )
    assert match_objs is True
    mismatch, _ = compare_answers([18500.0, 12400.0], [18500.0, 10000.0], "top_transactions")
    assert mismatch is False

    # 10. payment_due: amount tolerance & ISO date normalization vs DD-Mon-YYYY
    r0_due = {"amount_due": 48920.0, "due_date": "2026-09-20"}
    r1_due = {"total_due": 48950.0, "payment_due_date": "20-Sep-2026"}
    match, _ = compare_answers(r0_due, r1_due, "payment_due")
    assert match is True
    # Date mismatch
    mismatch_date, _ = compare_answers(
        {"amount_due": 48920.0, "due_date": "2026-09-20"},
        {"amount_due": 48920.0, "due_date": "2026-09-25"},
        "payment_due"
    )
    assert mismatch_date is False
    # Amount mismatch
    mismatch_amt, _ = compare_answers(
        {"amount_due": 48920.0, "due_date": "2026-09-20"},
        {"amount_due": 40000.0, "due_date": "2026-09-20"},
        "payment_due"
    )
    assert mismatch_amt is False

    # 11. bill_summary: bill_amount tolerance & date normalization
    r0_bill = {"bill_amount": 4180.0, "due_date": "2026-09-25"}
    r1_bill = {"total_amount": 4185.0, "due_date": "25-Sep-2026"}
    match, _ = compare_answers(r0_bill, r1_bill, "bill_summary")
    assert match is True
    mismatch_date, _ = compare_answers(
        {"bill_amount": 4180.0, "due_date": "2026-09-25"},
        {"bill_amount": 4180.0, "due_date": "2026-10-25"},
        "bill_summary"
    )
    assert mismatch_date is False


if __name__ == "__main__":
    test_comparators()
    test_smoke_runner_isolation()
    test_actual_ground_truth_loading()
    test_ground_truth_loader_malformed_structures()
    test_ground_truth_present_false_and_ambiguous_filtering()
    test_answer_preservation_stable_vs_unstable_and_unevaluable()
    test_decision_consistency()
    test_sensitive_field_reduction_actions_and_leaks()
    test_zero_eligible_denominators()
    test_trap_and_matching_nontrap_pairwise_check()
    test_failure_attribution_and_missing_evidence()
    test_load_answer_schemas()
    test_phase1_deterministic_comparators()
    print("\nAll evaluator regression tests passed successfully.")
