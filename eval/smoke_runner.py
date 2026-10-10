"""
eval/smoke_runner.py: Infrastructure Smoke-Test Runner for Day 1.

CONSTRAINTS:
1. Isolated outputs: Writes ONLY to results/smoke/.
2. Fixed cases: BS-1-A, BS-1-C, CC-1-B, PS-1-B.
3. Tests metric code using tests/fixtures/dummy_labels.json.
4. Does NOT write to results/results.json or results/raw/.
5. Does NOT produce final Day 1 evaluation claims.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.detector import SensitiveDataDetector, evaluate_detection_recall
from experiment.planner import MinimizationPlanner
from experiment.policy import enforce_policy_floor
from experiment.transform import apply_minimization
from eval.comparators import compare_answers
from eval.metrics import compute_metrics

CORPUS_DIR = PROJECT_ROOT / "corpus"
PLANTED_PATH = CORPUS_DIR / "planted.json"
TASKS_PATH = PROJECT_ROOT / "tasks" / "tasks.json"
DUMMY_LABELS_PATH = PROJECT_ROOT / "tests" / "fixtures" / "dummy_labels.json"

SMOKE_OUTPUT_DIR = PROJECT_ROOT / "results" / "smoke"
SMOKE_RAW_DIR = SMOKE_OUTPUT_DIR / "raw"

# Fixed smoke cases chosen for diverse infrastructure coverage
SMOKE_CASE_IDS = ["BS-1-A", "BS-1-C", "CC-1-B", "PS-1-B"]


def mock_task_executor(text: str, task: str, schema_id: str) -> Any:
    """Deterministic mock executor to test R0/R1 pipeline without consuming API spend."""
    if schema_id == "spending_summary":
        # Returns spending amounts found in text
        if "450.00" in text:
            return {"food": 450.00}
        return {"food": 0.0}

    if schema_id == "identity_check":
        # Verifies if Aarav Sharma or last 4 digits 5781 are present
        has_name = "Aarav Sharma" in text
        has_acct = "5781" in text
        return {"is_mine": has_name or has_acct, "matches_owner": True}

    if schema_id == "balance_summary":
        if "32450.00" in text:
            return {"balance": 32450.00}
        return {"balance": 0.0}

    if schema_id == "salary_summary":
        if "55000.00" in text:
            return {"basic": 55000.00, "net": 87450.00}
        return {"basic": 0.0, "net": 0.0}

    return {"summary": "generic_summary"}


def run_smoke_test() -> Dict[str, Any]:
    SMOKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SMOKE_RAW_DIR.mkdir(parents=True, exist_ok=True)

    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        all_tasks = json.load(f)
    tasks_by_id = {t["case_id"]: t for t in all_tasks}

    with open(DUMMY_LABELS_PATH, "r", encoding="utf-8") as f:
        dummy_fixture = json.load(f)
    dummy_labels = dummy_fixture.get("labels", {})

    detector = SensitiveDataDetector(presidio_engine=None)
    planner = MinimizationPlanner(live_client=None)

    eval_cases: List[Dict[str, Any]] = []
    detected_cache: Dict[str, Any] = {}

    for case_id in SMOKE_CASE_IDS:
        task_info = tasks_by_id[case_id]
        doc_id = task_info["doc_id"]
        task_text = task_info["task"]
        is_trap = task_info["is_trap"]
        schema_id = task_info["answer_schema_id"]

        doc_file = CORPUS_DIR / f"{doc_id}.txt"
        with open(doc_file, "r", encoding="utf-8") as f:
            original_text = f.read()

        # Detection & Skeleton
        if doc_id not in detected_cache:
            fields, skeleton = detector.detect_in_text(original_text, doc_id)
            detected_cache[doc_id] = (fields, skeleton)
        else:
            fields, skeleton = detected_cache[doc_id]

        # Planner
        raw_plan, retries = planner.plan(case_id, task_text, is_trap, skeleton)

        # Policy Floor
        enforced_plan, violations = enforce_policy_floor(raw_plan, is_trap)

        # Deterministic Transform -> R1 input
        r1_text, removed_values = apply_minimization(original_text, fields, enforced_plan["decisions"])

        # Invariant check: R1 Contract
        for val in removed_values:
            assert val not in r1_text, f"Contract violation: removed value '{val}' leaked into R1"

        # R0 Executions (Stability check: run twice)
        r0_a = mock_task_executor(original_text, task_text, schema_id)
        r0_b = mock_task_executor(original_text, task_text, schema_id)
        is_unstable = (r0_a != r0_b)

        # R1 Execution
        r1 = mock_task_executor(r1_text, task_text, schema_id)

        # Comparator
        is_preserved, match_reason = compare_answers(r0_a, r1, schema_id)

        case_record = {
            "case_id": case_id,
            "doc_id": doc_id,
            "task": task_text,
            "is_trap": is_trap,
            "is_unstable": is_unstable,
            "is_preserved": is_preserved,
            "match_reason": match_reason,
            "plan_decisions": enforced_plan["decisions"],
            "policy_violations": violations,
            "r0": r0_a,
            "r1": r1,
            "retries": retries,
        }
        eval_cases.append(case_record)

        # Write raw run artifact under results/smoke/raw/
        raw_file = SMOKE_RAW_DIR / f"{case_id}_smoke.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(case_record, f, indent=2)

    # Compute smoke detection recall
    det_report = evaluate_detection_recall({k: v[0] for k, v in detected_cache.items()}, PLANTED_PATH, detector.ambiguous_orgs)

    # Compute smoke metrics using dummy labels fixture
    smoke_metrics = compute_metrics(eval_cases, dummy_labels, det_report["recall"])

    # Write smoke outputs
    with open(SMOKE_OUTPUT_DIR / "smoke_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "smoke_cases": SMOKE_CASE_IDS,
            "metrics": smoke_metrics,
            "eval_cases": eval_cases
        }, f, indent=2)

    with open(SMOKE_OUTPUT_DIR / "smoke_failures.json", "w", encoding="utf-8") as f:
        json.dump(smoke_metrics.get("failures", []), f, indent=2)

    # Write human-readable smoke report
    report_md = f"""# Day 1 Infrastructure Smoke-Test Report

> **NOTICE**: This report was generated during preliminary infrastructure validation.
> It tests the end-to-end execution pipeline using mock executors and `{DUMMY_LABELS_PATH.name}`.
> It DOES NOT constitute official Day 1 experimental findings.

## Evaluated Smoke Cases
- {' | '.join(SMOKE_CASE_IDS)}

## Smoke Metrics (Infrastructure Sanity Check)
- Total Cases: {smoke_metrics['total_cases_evaluated']}
- Preserved Cases: {smoke_metrics['preserved_cases']} ({smoke_metrics['answer_preservation'] * 100:.1f}%)
- Unstable Cases: {smoke_metrics['unstable_cases']}
- Sensitive Field Reduction: {smoke_metrics['sensitive_field_reduction'] * 100:.1f}%
- Trap Check Pass Rate: {smoke_metrics['trap_check_rate'] * 100:.1f}%
- Detection Mode: {detector.mode}
- Detection Recall (on smoke docs): {smoke_metrics['detection_recall'] * 100:.1f}%

## Output Isolation
All smoke outputs are isolated under `results/smoke/`.
No files in `results/raw/` or `results/results.json` were created.

## Cleanup Instructions for Tomorrow's Full Run
Before executing tomorrow's real experiment with human-signed labels:
```powershell
Remove-Item -Recurse -Force results/smoke
```
"""
    with open(SMOKE_OUTPUT_DIR / "smoke_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    return smoke_metrics


if __name__ == "__main__":
    metrics = run_smoke_test()
    print("Smoke test completed successfully.")
    print(f"Cases tested: {SMOKE_CASE_IDS}")
    print(f"Answer preservation: {metrics['answer_preservation'] * 100:.1f}%")
    print(f"Sensitive field reduction: {metrics['sensitive_field_reduction'] * 100:.1f}%")
    print(f"Smoke outputs saved in: {SMOKE_OUTPUT_DIR}")
