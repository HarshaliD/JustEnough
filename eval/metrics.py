"""
eval/metrics.py: Metric calculation, ground-truth loading, and failure attribution for JustEnough Day 1.

Calculates:
- Answer preservation (primary): preserved cases / eligible stable cases (unstable reported separately)
- Baseline stability: total, stable, unstable, unevaluable case tracking
- Sensitive-field reduction: instance-based calculation using detected field instances
- Decision consistency: across 3 repeated runs of identical (case, category) decisions
- Trap check: pairwise check across document families (identity kept in trap, minimized in non-trap)
- Detection metrics: span recall, category recall, precision, false positives
- Ground-truth metrics: label agreement, over-redaction, under-redaction (skipping present: false, handling ambiguous)
- Failure attribution: detection miss | planner error | ambiguous label | comparison error | unattributed
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

FROZEN_ACTIONS: Set[str] = {
    "KEEP",
    "DROP",
    "MASK_PARTIAL",
    "GENERALIZE",
    "PSEUDONYMIZE",
    "AGGREGATE",
}

CANONICAL_CATEGORIES: Set[str] = {
    "account_identifier",
    "government_id",
    "person_name",
    "counterparty_name",
    "address",
    "contact",
    "date_of_birth",
    "internal_id",
    "employer",
    "merchant",
    "amount",
    "balance",
    "transaction_date",
    "salary_component",
    "medical_value",
    "clause_text",
}

IDENTITY_CATEGORIES: Set[str] = {
    "person_name",
    "account_identifier",
    "counterparty_name",
    "address",
    "contact",
    "internal_id",
    "government_id",
}

# Explicit instance-level retention weights per action
# Reflects post-transform sensitive information exposure
ACTION_RETENTION_WEIGHTS: Dict[str, float] = {
    "KEEP": 1.0,          # 100% retained: exact raw sensitive value remains
    "DROP": 0.0,          # 0% retained: completely removed
    "MASK_PARTIAL": 0.25, # 25% retained: trailing digits / partial token remains
    "GENERALIZE": 0.25,   # 25% retained: coarse granularity remains
    "PSEUDONYMIZE": 0.50, # 50% retained: consistent local alias / linkage remains
    "AGGREGATE": 0.25,    # 25% retained: grouped / summary value remains
}

VALID_FAILURE_TYPES: Set[str] = {
    "detection miss",
    "planner error",
    "ambiguous label",
    "comparison error",
    "unattributed",
}


def load_ground_truth(source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Loads and strictly validates privacy ground-truth labels.

    Supports:
    1. Canonical ground_truth/labels.json format:
       {"cases": {"<case_id>": {"labels": {"<category>": {"present": bool, "required": bool, "acceptable_actions": list, "ambiguous": bool}}}}}
    2. Normalized dictionary format or legacy fixture format:
       {"labels": {"<case_id>": {"categories": {...}}}} or {"<case_id>": {"categories": {...}}}

    Raises:
    - ValueError for missing, invalid, or malformed structure. Never silently interprets missing labels as an empty dictionary.

    Returns:
    - Dict mapping case_id -> {category -> label_info_dict}
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise ValueError(f"Ground-truth file does not exist: {path}")
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid ground-truth JSON in {path}: {str(e)}") from e
    elif isinstance(source, dict):
        data = source
    else:
        raise ValueError("Invalid ground-truth source: must be a file path or dictionary.")

    if not isinstance(data, dict) or not data:
        raise ValueError("Invalid ground-truth structure: root must be a non-empty mapping.")

    # Determine cases mapping
    cases_raw: Optional[Dict[str, Any]] = None
    if "cases" in data and isinstance(data["cases"], dict):
        cases_raw = data["cases"]
    elif "labels" in data and isinstance(data["labels"], dict):
        # Support legacy fixture format if it maps cases
        sample_val = next(iter(data["labels"].values()), None)
        if isinstance(sample_val, dict) and ("categories" in sample_val or "labels" in sample_val or "acceptable_actions" in sample_val):
            cases_raw = data["labels"]
    elif any(isinstance(v, dict) and ("labels" in v or "categories" in v) for v in data.values()):
        cases_raw = data

    if cases_raw is None or not isinstance(cases_raw, dict) or not cases_raw:
        raise ValueError(
            "Malformed ground-truth structure: missing 'cases' mapping. "
            "Expected structure 'cases -> case_id -> labels -> category'."
        )

    normalized: Dict[str, Dict[str, Any]] = {}

    for case_id, case_obj in cases_raw.items():
        if not isinstance(case_obj, dict):
            raise ValueError(f"Malformed ground-truth for case '{case_id}': case entry must be an object.")

        if "labels" in case_obj and isinstance(case_obj["labels"], dict):
            cat_dict = case_obj["labels"]
        elif "categories" in case_obj and isinstance(case_obj["categories"], dict):
            cat_dict = case_obj["categories"]
        elif any(isinstance(v, dict) and "acceptable_actions" in v for v in case_obj.values()):
            # Flat category mapping directly under case
            cat_dict = case_obj
        else:
            raise ValueError(
                f"Malformed ground-truth for case '{case_id}': missing 'labels' or 'categories' mapping."
            )

        if not cat_dict:
            raise ValueError(f"Malformed ground-truth for case '{case_id}': category labels dictionary is empty.")

        case_normalized: Dict[str, Any] = {}
        for cat, info in cat_dict.items():
            if not isinstance(info, dict):
                raise ValueError(
                    f"Malformed category label for case '{case_id}', category '{cat}': entry must be an object."
                )

            for req_field in ("acceptable_actions", "required", "ambiguous"):
                if req_field not in info:
                    raise ValueError(
                        f"Malformed label for case '{case_id}', category '{cat}': missing required field '{req_field}'."
                    )

            actions = info["acceptable_actions"]
            if not isinstance(actions, list) or not actions:
                raise ValueError(
                    f"Malformed acceptable_actions for case '{case_id}', category '{cat}': must be a non-empty list."
                )

            invalid_actions = set(actions) - FROZEN_ACTIONS
            if invalid_actions:
                raise ValueError(
                    f"Invalid action(s) {invalid_actions} in ground truth for case '{case_id}', category '{cat}'."
                )

            present = info.get("present", True)
            if not isinstance(present, bool):
                raise ValueError(
                    f"Invalid 'present' flag for case '{case_id}', category '{cat}': must be a boolean."
                )

            case_normalized[cat] = {
                "present": present,
                "required": bool(info["required"]),
                "acceptable_actions": list(actions),
                "ambiguous": bool(info["ambiguous"]),
                "reason": str(info.get("reason", "")),
            }

        normalized[case_id] = case_normalized

    return normalized


def compute_metrics(
    eval_cases: List[Dict[str, Any]],
    ground_truth_labels: Optional[Union[Dict[str, Any], Path, str]] = None,
    detection_metrics: Optional[Union[float, Dict[str, Any]]] = None,
    repeated_plans: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    matching_non_trap_cases: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Computes all Day 1 metrics across evaluated cases according to DAY1_SPEC.md and docs/eval.md.
    """
    total_cases = len(eval_cases)
    if total_cases == 0:
        return {
            "total_cases_evaluated": 0,
            "stable_cases": 0,
            "unstable_cases": 0,
            "unevaluable_cases": 0,
            "preserved_cases": 0,
            "answer_preservation": None,
            "sensitive_field_reduction": None,
            "sensitive_field_reduction_status": "zero_cases_evaluated",
            "decision_consistency": None,
            "decision_consistency_status": "zero_cases_evaluated",
            "trap_check_rate": None,
            "trap_check_mode": "no_cases_evaluated",
            "label_agreement_rate": None,
            "over_redaction_rate": None,
            "under_redaction_rate": None,
            "failures": [],
        }

    # 1. Answer Preservation & Baseline Stability Tracking
    preserved_cases = 0
    stable_cases = 0
    unstable_cases = 0
    unevaluable_cases = 0
    unstable_cases_list: List[str] = []
    unevaluable_cases_list: List[Dict[str, Any]] = []

    # 2. Sensitive Field Reduction (Instance-Based)
    has_instance_artifacts = False
    total_sensitive_instances = 0
    retained_sensitive_instances = 0.0

    # 3. Ground-Truth Tracking
    gt_map: Optional[Dict[str, Dict[str, Any]]] = None
    if ground_truth_labels is not None:
        gt_map = load_ground_truth(ground_truth_labels)

    label_agreements = 0
    total_non_ambiguous = 0
    over_redactions = 0
    total_required = 0
    under_redactions = 0
    total_non_required = 0
    ambiguous_count = 0

    failures: List[Dict[str, Any]] = []

    # 4. Grouping for Pairwise Trap Check
    # doc_id -> {"trap": [case_records], "non_trap": [case_records]}
    doc_families: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for case in eval_cases:
        case_id = case["case_id"]
        doc_id = case.get("doc_id") or case_id.split("-")[0]
        is_trap = bool(case.get("is_trap", False))
        is_unstable = bool(case.get("is_unstable", False))
        is_preserved = bool(case.get("is_preserved", False))
        match_reason = str(case.get("match_reason", ""))
        is_unevaluable = bool(case.get("is_unevaluable", False)) or match_reason in (
            "human_rubric_required",
            "null_response",
            "unevaluable",
        )

        # Document family tracking for trap check
        if doc_id not in doc_families:
            doc_families[doc_id] = {"trap": [], "non_trap": []}
        if is_trap:
            doc_families[doc_id]["trap"].append(case)
        else:
            doc_families[doc_id]["non_trap"].append(case)

        # Baseline stability & preservation accounting
        if is_unstable:
            unstable_cases += 1
            unstable_cases_list.append(case_id)
        elif is_unevaluable:
            unevaluable_cases += 1
            unevaluable_cases_list.append({
                "case_id": case_id,
                "reason": match_reason or "unevaluable_comparison",
            })
            # Unevaluable cases count as comparison errors
            failures.append({
                "case_id": case_id,
                "failure_type": "comparison error",
                "evidence": f"Comparison unevaluable: {match_reason or 'human rubric or valid comparison required'}",
            })
        else:
            stable_cases += 1
            if is_preserved:
                preserved_cases += 1
            else:
                # Failure attribution for unpreserved stable cases
                raw_ftype = case.get("failure_type")
                failure_stage = case.get("failure_stage")
                evidence = str(case.get("failure_evidence") or match_reason or "R1 answer differed from R0")

                attributed_type = "unattributed"
                if raw_ftype and raw_ftype in VALID_FAILURE_TYPES:
                    attributed_type = raw_ftype
                elif failure_stage == "detection" or "detector" in evidence.lower() or "detection miss" in evidence.lower():
                    attributed_type = "detection miss"
                elif failure_stage in ("planner", "policy") or "policy" in evidence.lower() or "over-redaction" in evidence.lower() or "planner" in evidence.lower():
                    attributed_type = "planner error"
                elif failure_stage == "ground_truth" or "ambiguous" in evidence.lower():
                    attributed_type = "ambiguous label"
                elif failure_stage == "comparator" or any(kw in evidence.lower() for kw in ("tolerance", "mismatch", "comparator")):
                    attributed_type = "comparison error"
                elif not case.get("failure_evidence") and not failure_stage:
                    attributed_type = "unattributed"

                failures.append({
                    "case_id": case_id,
                    "failure_type": attributed_type,
                    "evidence": evidence,
                })

        # Instance-Based Sensitive-Field Reduction Accounting
        decisions = case.get("plan_decisions", {})
        leaked_values = set(case.get("removed_values_leaked", []))

        if "detected_fields" in case and isinstance(case["detected_fields"], list):
            has_instance_artifacts = True
            for field in case["detected_fields"]:
                total_sensitive_instances += 1
                cat = getattr(field, "category", None) or (field.get("category") if isinstance(field, dict) else None)
                val = getattr(field, "value", None) or (field.get("value") if isinstance(field, dict) else None)
                action = decisions.get(cat, {}).get("action", "DROP") if cat else "DROP"

                # If non-KEEP value was leaked into R1, it is 100% retained
                if action != "KEEP" and val and val in leaked_values:
                    retained_sensitive_instances += 1.0
                else:
                    retained_sensitive_instances += ACTION_RETENTION_WEIGHTS.get(action, 0.0)
        elif "instances_total" in case and "instances_retained" in case:
            has_instance_artifacts = True
            total_sensitive_instances += int(case["instances_total"])
            retained_sensitive_instances += float(case["instances_retained"])

        # Ground-Truth Label Metrics Accounting
        if gt_map and case_id in gt_map:
            case_labels = gt_map[case_id]
            for cat, label_info in case_labels.items():
                # Skip absent categories per ground_truth/labels.json line 14
                if not label_info.get("present", True):
                    continue

                is_ambiguous = label_info.get("ambiguous", False)
                is_req = label_info.get("required", False)
                acceptable = label_info.get("acceptable_actions", [])
                chosen_action = decisions.get(cat, {}).get("action", "DROP")

                # Ambiguous categories excluded from agreement scoring per DAY1_SPEC Section 6
                if is_ambiguous:
                    ambiguous_count += 1
                    continue

                total_non_ambiguous += 1
                if chosen_action in acceptable:
                    label_agreements += 1

                if is_req:
                    total_required += 1
                    if chosen_action not in acceptable:
                        over_redactions += 1
                else:
                    total_non_required += 1
                    if chosen_action == "KEEP" and "KEEP" not in acceptable:
                        under_redactions += 1

    # Primary metric: Answer preservation over eligible stable cases
    answer_preservation = round(preserved_cases / stable_cases, 4) if stable_cases > 0 else None

    # Instance-Based Sensitive-Field Reduction
    if has_instance_artifacts and total_sensitive_instances > 0:
        reduction = (total_sensitive_instances - retained_sensitive_instances) / total_sensitive_instances
        sensitive_field_reduction: Optional[float] = round(reduction, 4)
        reduction_status = "measured"
    elif has_instance_artifacts and total_sensitive_instances == 0:
        sensitive_field_reduction = None
        reduction_status = "zero_eligible_instances"
    else:
        sensitive_field_reduction = None
        reduction_status = (
            "unavailable: instance-level field artifacts (detected_fields / field_instances) "
            "not provided in eval_cases"
        )

    # Decision Consistency (Across 3 repeated runs)
    consistency_rate: Optional[float] = None
    consistency_status = "not_measured: repeated plans across 3 runs not provided"
    consistent_decisions = 0
    total_consistency_decisions = 0

    # Aggregate repeated plans from argument or per-case artifacts
    all_repeated_plans: Dict[str, List[Dict[str, Any]]] = {}
    if repeated_plans:
        all_repeated_plans.update(repeated_plans)
    for c in eval_cases:
        cid = c["case_id"]
        if cid not in all_repeated_plans and "repeated_plans" in c and isinstance(c["repeated_plans"], list):
            all_repeated_plans[cid] = c["repeated_plans"]

    if all_repeated_plans:
        for cid, plan_list in all_repeated_plans.items():
            if len(plan_list) >= 2:
                all_cats = set().union(*(p.keys() for p in plan_list if isinstance(p, dict)))
                for cat in all_cats:
                    actions = [p.get(cat, {}).get("action") for p in plan_list if isinstance(p, dict)]
                    if len(actions) == len(plan_list) and all(a is not None for a in actions):
                        total_consistency_decisions += 1
                        if len(set(actions)) == 1:
                            consistent_decisions += 1

        if total_consistency_decisions > 0:
            consistency_rate = round(consistent_decisions / total_consistency_decisions, 4)
            consistency_status = "measured"
        else:
            consistency_status = "insufficient_repeated_runs_for_consistency"

    # Trap Check: Pairwise Check across Document Families
    trap_cases_evaluated = 0
    trap_cases_passed = 0
    trap_pairs_evaluated = 0
    trap_pairs_passed = 0

    for doc_id, fam in doc_families.items():
        trap_list = fam["trap"]
        non_trap_list = fam["non_trap"]

        if not trap_list:
            continue

        for t_case in trap_list:
            trap_cases_evaluated += 1
            t_decisions = t_case.get("plan_decisions", {})

            # Check if identity was retained in trap case adhering to policy floor
            has_identity_retained = False
            for id_cat in IDENTITY_CATEGORIES:
                act = t_decisions.get(id_cat, {}).get("action")
                if act == "KEEP":
                    has_identity_retained = True
                    break
                if id_cat == "account_identifier" and act in ("MASK_PARTIAL",):
                    has_identity_retained = True
                    break

            t_preserved = bool(t_case.get("is_preserved", False))
            if has_identity_retained and t_preserved:
                trap_cases_passed += 1

            # Pairwise evaluation if matching non-trap cases are present
            if non_trap_list:
                trap_pairs_evaluated += 1
                non_trap_minimized = True
                for nt_case in non_trap_list:
                    nt_decisions = nt_case.get("plan_decisions", {})
                    for id_cat in IDENTITY_CATEGORIES:
                        if nt_decisions.get(id_cat, {}).get("action") == "KEEP":
                            non_trap_minimized = False
                            break
                    if not non_trap_minimized:
                        break

                if has_identity_retained and t_preserved and non_trap_minimized:
                    trap_pairs_passed += 1

    if trap_pairs_evaluated > 0:
        trap_check_rate: Optional[float] = round(trap_pairs_passed / trap_pairs_evaluated, 4)
        trap_check_mode = "pairwise"
    elif trap_cases_evaluated > 0:
        trap_check_rate = round(trap_cases_passed / trap_cases_evaluated, 4)
        trap_check_mode = "individual_trap_only (matching non-trap cases not evaluated)"
    else:
        trap_check_rate = None
        trap_check_mode = "no_trap_cases_evaluated"

    # Ground-truth rates (distinguishing zero eligible from 0.0)
    over_redaction_rate = round(over_redactions / total_required, 4) if total_required > 0 else None
    under_redaction_rate = round(under_redactions / total_non_required, 4) if total_non_required > 0 else None
    label_agreement_rate = round(label_agreements / total_non_ambiguous, 4) if total_non_ambiguous > 0 else None

    # Detection Metrics Integration
    det_recall: Optional[float] = None
    det_span_recall: Optional[float] = None
    det_precision: Optional[float] = None
    det_false_positives: Optional[int] = None

    if isinstance(detection_metrics, dict):
        det_recall = detection_metrics.get("category_recall") or detection_metrics.get("recall")
        det_span_recall = detection_metrics.get("span_recall")
        det_precision = detection_metrics.get("precision")
        det_false_positives = detection_metrics.get("false_positives")
    elif isinstance(detection_metrics, (int, float)):
        det_recall = float(detection_metrics)

    # Count failures by type
    failure_counts = {ft: 0 for ft in VALID_FAILURE_TYPES}
    for f in failures:
        ft = f.get("failure_type", "unattributed")
        failure_counts[ft] = failure_counts.get(ft, 0) + 1

    return {
        "total_cases_evaluated": total_cases,
        "stable_cases": stable_cases,
        "unstable_cases": unstable_cases,
        "unstable_cases_list": unstable_cases_list,
        "unevaluable_cases": unevaluable_cases,
        "unevaluable_cases_list": unevaluable_cases_list,
        "preserved_cases": preserved_cases,
        "answer_preservation": answer_preservation,
        "sensitive_field_reduction": sensitive_field_reduction,
        "sensitive_field_reduction_status": reduction_status,
        "total_sensitive_instances": total_sensitive_instances,
        "retained_sensitive_instances": round(retained_sensitive_instances, 2),
        "decision_consistency": consistency_rate,
        "decision_consistency_status": consistency_status,
        "consistent_decisions_count": consistent_decisions,
        "consistency_eligible_decisions": total_consistency_decisions,
        "trap_cases_evaluated": trap_cases_evaluated,
        "trap_cases_passed": trap_cases_passed,
        "trap_pairs_evaluated": trap_pairs_evaluated,
        "trap_pairs_passed": trap_pairs_passed,
        "trap_check_rate": trap_check_rate,
        "trap_check_mode": trap_check_mode,
        "label_agreement_rate": label_agreement_rate,
        "label_agreements_count": label_agreements,
        "label_agreement_eligible": total_non_ambiguous,
        "over_redaction_rate": over_redaction_rate,
        "over_redactions_count": over_redactions,
        "over_redaction_eligible": total_required,
        "under_redaction_rate": under_redaction_rate,
        "under_redactions_count": under_redactions,
        "under_redaction_eligible": total_non_required,
        "ambiguous_labels_count": ambiguous_count,
        "detection_recall": round(det_recall, 4) if det_recall is not None else None,
        "detection_span_recall": round(det_span_recall, 4) if det_span_recall is not None else None,
        "detection_precision": round(det_precision, 4) if det_precision is not None else None,
        "detection_false_positives": det_false_positives,
        "failure_counts": failure_counts,
        "failures": failures,
    }
