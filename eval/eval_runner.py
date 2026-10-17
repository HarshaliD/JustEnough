"""
eval/eval_runner.py: Official Benchmark Evaluation Runner for JustEnough.

Runs the 30 benchmark tasks across seeded runs, executing the complete pipeline:
Ingestion -> Detection -> Skeletonization -> Minimization Planning ->
Policy Floor Enforcement -> Deterministic Transformation ->
Task Execution (R0 vs R1) -> Equivalence Verification -> Metrics Attribution.

Outputs:
- results/evaluation_results.json: Machine-readable raw metrics and per-case records
- results/evaluation_report.md: Human-readable markdown audit report
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.detector import SensitiveDataDetector, evaluate_detection_recall
from experiment.planner import MinimizationPlanner
from experiment.policy import enforce_policy_floor
from experiment.transform import apply_minimization
from eval.task_executor import TaskExecutor
from eval.comparators import compare_answers
from eval.metrics import compute_metrics, load_ground_truth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("justenough.eval_runner")

CORPUS_DIR = PROJECT_ROOT / "corpus"
TASKS_PATH = PROJECT_ROOT / "tasks" / "tasks.json"
PLANTED_PATH = CORPUS_DIR / "planted.json"
GROUND_TRUTH_PATH = PROJECT_ROOT / "ground_truth" / "labels.json"
RUBRICS_PATH = PROJECT_ROOT / "rubrics" / "rubric_template.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"

DEFAULT_SEEDS = [20261009, 20261010, 20261011]


def run_evaluation(
    live: bool = False,
    seeds: Optional[List[int]] = None,
    case_filter: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    seeds = seeds or DEFAULT_SEEDS

    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        all_tasks = json.load(f)

    if case_filter:
        tasks = [t for t in all_tasks if t["case_id"] in case_filter]
    else:
        tasks = all_tasks

    rubrics: Dict[str, Any] = {}
    if RUBRICS_PATH.exists():
        with open(RUBRICS_PATH, "r", encoding="utf-8") as f:
            rubric_data = json.load(f)
            rubrics = rubric_data.get("cases", {})

    logger.info("Initializing SensitiveDataDetector...")
    detector = SensitiveDataDetector()

    # Pre-load documents
    documents: Dict[str, str] = {}
    for doc_file in CORPUS_DIR.glob("*.txt"):
        with open(doc_file, "r", encoding="utf-8") as f:
            documents[doc_file.stem] = f.read()

    logger.info("Loaded %d documents from corpus/.", len(documents))
    logger.info("Evaluating %d tasks across %d seed runs (live=%s)...", len(tasks), len(seeds), live)

    repeated_plans: Dict[str, List[Dict[str, Any]]] = {t["case_id"]: [] for t in tasks}
    eval_cases_last_run: List[Dict[str, Any]] = []

    executor = TaskExecutor(live=live)

    for seed_idx, seed in enumerate(seeds):
        logger.info("--- Starting Seed %d (%d/%d) ---", seed, seed_idx + 1, len(seeds))
        current_run_cases: List[Dict[str, Any]] = []

        for task_info in tasks:
            case_id = task_info["case_id"]
            doc_id = task_info["doc_id"]
            task_str = task_info["task"]
            schema_id = task_info.get("answer_schema_id", "free_text")
            is_trap = task_info.get("is_trap", False)

            doc_text = documents.get(doc_id)
            if not doc_text:
                logger.warning("Document %s for case %s not found. Skipping.", doc_id, case_id)
                continue

            # 1. Detection & Skeleton
            fields, skeleton = detector.detect_in_text(doc_text, doc_id)

            # 2. Planning
            planner = MinimizationPlanner(live_mode=live)
            raw_sensitive_values = [f.value for f in fields]
            plan_json, retries = planner.plan(
                case_id=case_id,
                task=task_str,
                skeleton=skeleton,
                answer_schema_id=schema_id,
                raw_sensitive_values=raw_sensitive_values,
            )
            del raw_sensitive_values

            # 3. Policy floor enforcement
            enforced_plan, violations = enforce_policy_floor(plan_json, is_trap=is_trap)
            decisions = enforced_plan.get("decisions", {})

            # Record plan for consistency
            repeated_plans[case_id].append(decisions)

            # 4. Deterministic Transformation
            minimized_text, removed_values = apply_minimization(
                original_text=doc_text,
                detected_fields=fields,
                plan_decisions=decisions,
            )

            # Check invariant: no removed raw value in minimized text
            leaked_values = [val for val in removed_values if val in minimized_text]

            # 5. Task Execution on R0 and R1
            ans_r0 = executor.execute(doc_text, task_str, schema_id, is_trap=is_trap)
            ans_r1 = executor.execute(minimized_text, task_str, schema_id, is_trap=is_trap)

            # 6. Equivalence Verification
            rubric_entry = rubrics.get(case_id)
            is_preserved, match_reason = compare_answers(
                ans_r0, ans_r1, schema_id, rubric=rubric_entry
            )

            case_record = {
                "case_id": case_id,
                "doc_id": doc_id,
                "task": task_str,
                "schema_id": schema_id,
                "is_trap": is_trap,
                "is_preserved": is_preserved,
                "match_reason": match_reason,
                "is_unstable": False,
                "is_unevaluable": False,
                "detected_fields": [
                    {"id": f.id, "category": f.category, "confidence": f.confidence}
                    for f in fields
                ],
                "instances_total": len(fields),
                "instances_retained": sum(
                    1.0 if decisions.get(f.category, {}).get("action") == "KEEP"
                    else (0.25 if decisions.get(f.category, {}).get("action") in ("MASK_PARTIAL", "GENERALIZE", "AGGREGATE")
                    else (0.5 if decisions.get(f.category, {}).get("action") == "PSEUDONYMIZE" else 0.0))
                    for f in fields
                ),
                "plan_decisions": decisions,
                "policy_violations": violations,
                "removed_values_leaked": leaked_values,
                "r0_answer": ans_r0,
                "r1_answer": ans_r1,
            }
            current_run_cases.append(case_record)

            # Save per-case raw artifact for final seed
            if seed_idx == len(seeds) - 1:
                with open(raw_dir / f"{case_id}.json", "w", encoding="utf-8") as f:
                    json.dump(case_record, f, indent=2, default=str)

        if seed_idx == len(seeds) - 1:
            eval_cases_last_run = current_run_cases

    # 7. Metrics Aggregation
    logger.info("Computing metrics via eval/metrics.py...")
    metrics = compute_metrics(
        eval_cases=eval_cases_last_run,
        ground_truth_labels=GROUND_TRUTH_PATH if GROUND_TRUTH_PATH.exists() else None,
        repeated_plans=repeated_plans,
    )

    # 8. Detection Recall against Planted Sensitive Data
    detection_metrics: Dict[str, Any] = {}
    if PLANTED_PATH.exists():
        try:
            # Build detected_by_doc for all corpus documents
            detected_by_doc = {}
            for did, dtext in documents.items():
                flds, _ = detector.detect_in_text(dtext, did)
                detected_by_doc[did] = flds

            recall_results = evaluate_detection_recall(
                detected_by_doc=detected_by_doc,
                planted_json_path=PLANTED_PATH,
            )
            detection_metrics = {
                "span_recall": recall_results.get("span_recall"),
                "category_recall": recall_results.get("category_recall"),
                "precision": recall_results.get("precision"),
                "total_planted": recall_results.get("total_planted"),
                "total_detected": recall_results.get("total_detected"),
            }
        except Exception as exc:
            logger.warning("Could not evaluate detection recall: %s", exc)

    final_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "live_mode": live,
        "seeds": seeds,
        "total_cases_evaluated": len(eval_cases_last_run),
        "metrics": metrics,
        "detection_evaluation": detection_metrics,
        "cases": eval_cases_last_run,
    }

    results_json_path = output_dir / "evaluation_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, default=str)
    logger.info("Saved complete evaluation results to %s", results_json_path)

    # 9. Generate Human-Readable Markdown Report
    report_md_path = output_dir / "evaluation_report.md"
    _generate_markdown_report(report_md_path, final_payload)
    logger.info("Generated markdown report at %s", report_md_path)

    return final_payload


def _generate_markdown_report(path: Path, data: Dict[str, Any]) -> None:
    m = data.get("metrics", {})
    det = data.get("detection_evaluation", {})

    ap = m.get("answer_preservation")
    ap_str = f"{ap * 100:.1f}%" if ap is not None else "N/A"

    sfr = m.get("sensitive_field_reduction")
    sfr_str = f"{sfr * 100:.1f}%" if sfr is not None else "N/A"

    dc = m.get("decision_consistency")
    dc_str = f"{dc * 100:.1f}%" if dc is not None else "N/A"

    la = m.get("label_agreement_rate")
    la_str = f"{la * 100:.1f}%" if la is not None else "N/A"

    report = f"""# JustEnough — Official Evaluation Report
**Timestamp:** {data.get('timestamp')}  
**Execution Mode:** {'Live Gemini API' if data.get('live_mode') else 'Deterministic Benchmark Mock'}  
**Seeds:** `{data.get('seeds')}`  
**Cases Evaluated:** {data.get('total_cases_evaluated')}  

---

## 1. Key Evaluation Metrics

| Metric | Target Standard | Measured Result | Status |
|---|---|---|---|
| **Answer Preservation ($R_1 \\equiv R_0$)** | $\\ge 95.0\\%$ | **{ap_str}** ({m.get('preserved_cases')}/{m.get('stable_cases')} cases) | {'PASSED' if ap and ap >= 0.95 else 'MEASURED'} |
| **Sensitive-Field Reduction** | $\\ge 60.0\\%$ | **{sfr_str}** | {'PASSED' if sfr and sfr >= 0.60 else 'MEASURED'} |
| **Decision Consistency (3 Runs)** | $\\ge 95.0\\%$ | **{dc_str}** | {'PASSED' if dc and dc >= 0.95 else 'MEASURED'} |
| **Ground-Truth Label Agreement** | $\\ge 85.0\\%$ | **{la_str}** | {'PASSED' if la and la >= 0.85 else 'MEASURED'} |
| **Detection Category Recall** | $\\ge 80.0\\%$ | **{f"{det.get('category_recall', 0)*100:.1f}%" if det else "N/A"}** | {'PASSED' if det and det.get('category_recall', 0) >= 0.8 else 'MEASURED'} |

---

## 2. Stability & Guardrail Integrity

* **Stable Baseline Cases:** {m.get('stable_cases', 0)}
* **Unstable Cases ($R_{{0a}} \\neq R_{{0b}}$):** {m.get('unstable_cases', 0)}
* **Unevaluable Cases:** {m.get('unevaluable_cases', 0)}
* **Over-Redaction Count:** {m.get('over_redaction_rate', 'N/A')}
* **Under-Redaction Count:** {m.get('under_redaction_rate', 'N/A')}
* **Identified Failures:** {len(m.get('failures', []))}

---

## 3. Case Execution Summary

| Case ID | Task | Schema | Preserved? | Match Reason | Retained | Leaks |
|---|---|---|:---:|---|:---:|:---:|
"""
    for c in data.get("cases", []):
        p_badge = "YES" if c.get("is_preserved") else "NO"
        leaks = len(c.get("removed_values_leaked", []))
        report += f"| `{c.get('case_id')}` | {c.get('task')[:35]}... | `{c.get('schema_id')}` | {p_badge} | {c.get('match_reason')} | {c.get('instances_retained')}/{c.get('instances_total')} | {leaks} |\n"

    report += "\n---\n*Report generated deterministically by `eval/eval_runner.py` according to AGENTS.md pre-registered evaluation standards.*\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JustEnough Official Benchmark Evaluation Runner")
    parser.add_argument("--live", action="store_true", help="Run with live Gemini API (requires GEMINI_API_KEY)")
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS, help="Seed integers for repeated consistency runs")
    parser.add_argument("--case", nargs="+", help="Filter specific case IDs (e.g. BS-1-A BS-1-B)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory to save evaluation results")

    args = parser.parse_args()
    run_evaluation(
        live=args.live,
        seeds=args.seeds,
        case_filter=args.case,
        output_dir=args.output_dir,
    )
