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

### `tests/test_minimizer.py`
- `[2026-10-13 01:45:00 IST]` Updated default model test assertions to reflect `gemini-flash-latest`.
- `[2026-10-13 04:38:00 IST]` Added `test_repeated_sensitive_value_single_span_detection()` and `test_invalid_field_discarded_during_overlap_resolution()` to investigate transformer edge cases without modifying production code.

### `docs/images/justenough_overview.png`
- `[2026-10-13 01:45:00 IST]` Generated and saved 16:9 architecture and "Why JustEnough?" infographic banner illustrating blind redaction vs. unprotected upload vs. task-aware minimization.

### `README.md`
- `[2026-10-13 01:45:00 IST]` Created comprehensive project documentation with problem statement, comparison table, example walk-through, Mermaid pipeline flowchart, taxonomy table, and embedded architecture banner.
- `[2026-10-13 01:49:00 IST]` Streamlined document per instructions by staging out temporary sections for future release.

---
