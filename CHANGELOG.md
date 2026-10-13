# JustEnough: File Change Log

All modifications to repository files are logged chronologically below, structured by file name with date and time in front of each individual change.

---

## [2026-10-13] - Gemini Planner Live Integration, Detector Improvements & Documentation

### `experiment/planner.py`
- `[2026-10-13 01:45:00 IST]` Updated default model identifier from deprecated `gemini-2.5-flash` to `gemini-flash-latest`.
- `[2026-10-13 01:45:00 IST]` Implemented live Gemini API execution path using `google-generativeai` with strict JSON output formatting.
- `[2026-10-13 01:45:00 IST]` Integrated temporary prompt debugging hook (`JUSTENOUGH_DEBUG_PROMPT=1`) with privacy safeguards (verifies no raw PII or API keys leak into prompt payloads).
- `[2026-10-13 01:45:00 IST]` Enforced canonical 16-category schema validation on model responses with one retry on schema failure.

### `experiment/detector.py`
- `[2026-10-13 01:45:00 IST]` Added custom Indian regex patterns for banking CIFs / Customer IDs (`CIF\d+`, `CUST\d+`, `SBICUST\d+`, `AXISCC\d+`, `ICICI\d+`) mapped to `internal_id`.
- `[2026-10-13 01:45:00 IST]` Added regex recognizers for account holder names in statement/bill headers (`Account Holder Name`, `Customer Name`, `Primary Cardholder`, etc.) mapped to `person_name`.
- `[2026-10-13 01:45:00 IST]` Added regex recognizers for counterparty transfer recipients in payment narration (`UPI-TRANSFER to`, `paid to`, `UPI payout to`) mapped to `counterparty_name`.
- `[2026-10-13 01:45:00 IST]` Added regex pattern for statement merchants (`Merchant:`, `POS/Merchant:`, `Vendor:`) and UPI narration merchants (`UPI/<merchant>/<tag>`) mapped to `merchant`.
- `[2026-10-13 01:45:00 IST]` Upgraded custom pattern matching loop to support multi-group extraction and whitespace stripping while ensuring `text[start:end] == val`.
- `[2026-10-13 01:45:00 IST]` Added false-positive filtering for SpaCy `PERSON` anomalies on bank statement headers (`Addr`, `Communication Addr`, `Flat 402`, tokens with `_`).
- `[2026-10-13 01:45:00 IST]` Added reclassification logic for known merchants (`Swiggy`, `Zomato`, `Flipkart`, etc.) misidentified by Presidio as `person_name`.

### `experiment/run_single_case.py`
- `[2026-10-13 01:45:00 IST]` Created single-case integration runner script supporting `--case-id`, `--live`, and `--no-debug-prompt`.
- `[2026-10-13 01:45:00 IST]` Validated end-to-end flow on `BS-1-A`: detection -> typed skeleton -> live Gemini planning -> policy floor enforcement -> deterministic transformation -> R1 invariant check.

### `eval/smoke_runner.py`
- `[2026-10-13 01:45:00 IST]` Updated smoke test runner to use enhanced detector and verified contract isolation under `results/smoke/`.

### `tests/test_detector.py`
- `[2026-10-13 01:45:00 IST]` Added `test_cif_and_enhanced_patterns()` covering CIFs, header names, counterparty transfers, merchants, and skeleton placeholder masking.
- `[2026-10-13 04:55:39 IST]` Added `test_repeated_name_both_occurrences_detected()` and `test_repeated_name_transformer_integration_with_actual_detector()` verifying end-to-end detection and minimization of repeated sensitive values.

### `tests/test_minimizer.py`
- `[2026-10-13 01:45:00 IST]` Updated default model test assertions to reflect `gemini-flash-latest`.
- `[2026-10-13 04:38:00 IST]` Added `test_repeated_sensitive_value_single_span_detection()` and `test_invalid_field_discarded_during_overlap_resolution()` to investigate transformer edge cases without modifying production code.

### `docs/images/justenough_overview.png`
- `[2026-10-13 01:45:00 IST]` Generated and saved 16:9 architecture and "Why JustEnough?" infographic banner illustrating blind redaction vs. unprotected upload vs. task-aware minimization.

### `README.md`
- `[2026-10-13 01:45:00 IST]` Created comprehensive project documentation with problem statement, comparison table, example walk-through, Mermaid pipeline flowchart, taxonomy table, and embedded architecture banner.
- `[2026-10-13 01:49:00 IST]` Streamlined document per instructions by staging out temporary sections for future release.

### `eval/metrics.py`
- `[2026-10-13 05:40:00 IST]` Built a reliable ground-truth loader (`load_ground_truth`) that correctly reads our full benchmark labels file (`cases -> case_id -> labels -> category`) and catches invalid or missing files early instead of failing silently.
- `[2026-10-13 05:40:00 IST]` Fixed answer preservation scoring to separate unstable AI baselines and unevaluable cases so they don't unfairly skew the accuracy score.
- `[2026-10-13 05:40:00 IST]` Replaced rough category counts with an instance-based privacy reduction score that measures actual sensitive values removed (accounting for partial masking, generalization, and pseudonymization) and penalizes data leaks.
- `[2026-10-13 05:40:00 IST]` Removed hardcoded 100% decision consistency and replaced it with real calculations across repeated AI runs (reporting "not measured" if repeated runs are not provided).
- `[2026-10-13 05:40:00 IST]` Updated ground-truth scoring (agreement, over-redaction, under-redaction) to ignore fields that do not exist in the document (`present: false`) and properly exclude ambiguous labels from agreement scoring.
- `[2026-10-13 05:40:00 IST]` Added pairwise trap checks to verify that identity is kept when genuinely needed (trap tasks) and minimized when not needed (standard tasks) for the same document.
- `[2026-10-13 05:40:00 IST]` Implemented clear failure attribution sorting failures into four clear causes: detection miss, planner error, ambiguous label, or comparison error.

### `eval/smoke_runner.py`
- `[2026-10-13 05:40:00 IST]` Updated smoke runner records to pass safe field detection tags (category and ID only, zero sensitive data) so the smoke test can calculate real instance-based data reduction.

### `tests/test_eval.py`
- `[2026-10-13 05:40:00 IST]` Added 9 comprehensive automated tests verifying ground-truth loading, error handling for bad label files, unstable baseline separation, multi-run consistency, instance reduction, pairwise trap checks, and failure attribution (all 11 tests passing).

### `docs/eval.md`
- `[2026-10-13 05:40:00 IST]` Documented the evaluation system architecture, explaining how answers are compared, how metrics are calculated, what limitations exist, and how to interpret scores.

---
