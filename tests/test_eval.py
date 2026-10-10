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


if __name__ == "__main__":
    test_comparators()
    test_smoke_runner_isolation()
