"""
tests/test_tasks.py: Validates tasks/tasks.json against Section 5 of DAY1_SPEC.md.
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = PROJECT_ROOT / "DAY1_SPEC.md"
TASKS_PATH = PROJECT_ROOT / "tasks" / "tasks.json"
CORPUS_DIR = PROJECT_ROOT / "corpus"


def parse_spec_tasks():
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Find Section 5 table
    sec5_match = re.search(r"## 5\. Tasks.*?\n(\|.*?\n)(?=## 6\.)", content, re.DOTALL)
    assert sec5_match, "Section 5 table not found in DAY1_SPEC.md"
    table_lines = [line.strip() for line in sec5_match.group(1).strip().splitlines() if line.strip()]

    rows = []
    # Skip header and divider
    for line in table_lines[2:]:
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) == 5:
            case_id = parts[0].replace("**", "").strip()
            doc_id = parts[1].strip()
            task = parts[2].strip()
            trap = parts[3].strip()
            schema_id = parts[4].replace("`", "").strip()
            rows.append({
                "case_id": case_id,
                "doc_id": doc_id,
                "task": task,
                "is_trap": (trap.lower() == "yes"),
                "answer_schema_id": schema_id
            })
    return rows


def test_tasks_json():
    spec_tasks = parse_spec_tasks()
    assert len(spec_tasks) == 30, f"Expected 30 tasks in Section 5, found {len(spec_tasks)}"

    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    assert len(tasks) == 30, f"Expected 30 tasks in tasks.json, found {len(tasks)}"

    for i, (spec_t, json_t) in enumerate(zip(spec_tasks, tasks)):
        assert json_t["case_id"] == spec_t["case_id"], f"Case ID mismatch at #{i}: {json_t['case_id']} != {spec_t['case_id']}"
        assert json_t["doc_id"] == spec_t["doc_id"], f"Doc ID mismatch in {spec_t['case_id']}: {json_t['doc_id']} != {spec_t['doc_id']}"
        assert json_t["task"] == spec_t["task"], f"Task mismatch in {spec_t['case_id']}: {json_t['task']} != {spec_t['task']}"
        assert json_t["is_trap"] == spec_t["is_trap"], f"Trap mismatch in {spec_t['case_id']}: {json_t['is_trap']} != {spec_t['is_trap']}"
        assert json_t["answer_schema_id"] == spec_t["answer_schema_id"], f"Schema ID mismatch in {spec_t['case_id']}: {json_t['answer_schema_id']} != {spec_t['answer_schema_id']}"

        # Verify referenced document exists in corpus
        doc_file = CORPUS_DIR / f"{json_t['doc_id']}.txt"
        assert doc_file.exists(), f"Referenced document {doc_file.name} does not exist in corpus"

    trap_count = sum(1 for t in tasks if t["is_trap"])
    assert trap_count == 10, f"Expected 10 trap tasks (1 per doc), got {trap_count}"
    print("Tasks validation passed: exactly 30 cases match DAY1_SPEC.md Section 5.")


if __name__ == "__main__":
    test_tasks_json()
