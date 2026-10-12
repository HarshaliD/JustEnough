"""
experiment/run_single_case.py: Single Synthetic-Case Live Integration Runner.

Executes ONE case with live Gemini planner and deterministic transformation.
Guarantees:
- Zero API calls when run with --mock.
- Strictly isolated to one case (default: BS-1-A).
- Performs prompt privacy verification before API call.
- Validates plan schema and enforces deterministic policy floor.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.detector import SensitiveDataDetector
from experiment.planner import MinimizationPlanner
from experiment.policy import enforce_policy_floor
from experiment.transform import apply_minimization


def run_single_case(case_id: str = "BS-1-A", live_mode: bool = False, debug_prompt: bool = True) -> None:
    if debug_prompt:
        os.environ["JUSTENOUGH_DEBUG_PROMPT"] = "1"

    # 1. Load task definition
    tasks_path = PROJECT_ROOT / "tasks" / "tasks.json"
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    task_info = next((t for t in tasks if t["case_id"] == case_id), None)
    if not task_info:
        raise ValueError(f"Case ID '{case_id}' not found in tasks/tasks.json")

    doc_id = task_info["doc_id"]
    task_text = task_info["task"]
    schema_id = task_info["answer_schema_id"]

    # 2. Load synthetic document
    doc_path = PROJECT_ROOT / "corpus" / f"{doc_id}.txt"
    with open(doc_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    print(f"\n=======================================================")
    print(f"JustEnough Single-Case Test: {case_id}")
    print(f"Document: {doc_id} | Task: '{task_text}'")
    print(f"Answer Schema ID: {schema_id} | Mode: {'LIVE (Gemini)' if live_mode else 'MOCK'}")
    print(f"=======================================================\n")

    # 3. Detect sensitive fields and build typed skeleton
    detector = SensitiveDataDetector(presidio_engine=None)
    fields, skeleton = detector.detect_in_text(original_text, doc_id)
    raw_sensitive_values = [f.value for f in fields]

    print(f"Detected {len(fields)} sensitive field instances.")
    print(f"Skeleton length: {len(skeleton)} characters.")

    # 4. Initialize Planner
    planner = MinimizationPlanner(live_mode=live_mode)

    # 5. Plan minimization
    print("\nRequesting minimization plan...")
    raw_plan, retries = planner.plan(
        case_id=case_id,
        task=task_text,
        skeleton=skeleton,
        answer_schema_id=schema_id,
        raw_sensitive_values=raw_sensitive_values
    )

    print(f"Plan received successfully. Retries: {retries}")

    # 6. Schema validation
    is_valid = planner.validate_plan_schema(raw_plan, expected_case_id=case_id)
    print(f"Schema Validation Passed: {is_valid}")
    if not is_valid:
        raise ValueError("Plan failed schema validation.")

    # 7. Policy Floor Enforcement
    enforced_plan, violations = enforce_policy_floor(raw_plan)
    print(f"Policy Floor Violations Clamped: {len(violations)}")
    for v in violations:
        print(f"  - Category '{v['category']}': model proposed '{v['model_action']}', clamped to '{v['clamped_action']}'")

    # 8. Deterministic Transformation
    minimized_text, removed_values = apply_minimization(
        original_text=original_text,
        detected_fields=fields,
        plan_decisions=enforced_plan["decisions"]
    )

    # 9. Verify R1 Contract
    for val in removed_values:
        assert val not in minimized_text, f"Contract violation: Removed value '{val}' leaked into minimized text!"

    print(f"\nDeterministic minimization completed.")
    print(f"Original text length: {len(original_text)} chars | Minimized text length: {len(minimized_text)} chars.")
    print(f"Fields dropped/redacted: {len(removed_values)}")

    # 10. Summary Decisions Display (safe: only categories, actions, reasons)
    print("\nMinimization Decisions Summary:")
    for cat, dec in enforced_plan["decisions"].items():
        print(f"  {cat:22s} -> {dec['action']:15s} (conf: {dec.get('confidence', 0.0):.2f}) | {dec.get('reason', '')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run single synthetic case integration test.")
    parser.add_argument("--case-id", default="BS-1-A", help="Case ID to test (default: BS-1-A)")
    parser.add_argument("--live", action="store_true", help="Execute live Gemini API call")
    parser.add_argument("--no-debug-prompt", action="store_true", help="Disable prompt debug printing")

    args = parser.parse_args()
    run_single_case(
        case_id=args.case_id,
        live_mode=args.live,
        debug_prompt=not args.no_debug_prompt
    )
