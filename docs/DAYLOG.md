# JustEnough: Daily Engineering Log

## Day 1 — 2026-10-09

- **Done**:
  - Replaced SDP stub in `experiment/detector.py` with Microsoft Presidio (`presidio-analyzer` + `spacy` with `en_core_web_sm`).
  - Implemented contextual `ORGANIZATION` mapping to `employer`, `merchant`, or `counterparty_name` based on local window context and document prefix.
  - Implemented ambiguous organization tracking without recording raw sensitive values.
  - Preserved the four custom Indian patterns (UPI handle, IFSC, Indian phone, masked account); ensured custom patterns bypass Presidio confidence threshold filtering.
  - Preserved frozen 16-category taxonomy and frozen detector output contract (`DetectedField`).
  - Updated `eval/smoke_runner.py` and `tests/test_detector.py`.
  - Updated `.agents/agents/detector.md`.
  - Ran all 10 unit tests across test suites: 100% passed.
  - Ran smoke test on 4 fixed cases: 100% answer preservation, outputs isolated strictly under `results/smoke/`.

- **Learned**:
  - Presidio default configuration attempts to pull `en_core_web_lg` unless an explicit `NlpEngineProvider` configuration specifying `en_core_web_sm` is provided. Explicit configuration avoids ~580MB downloads and runs efficiently offline.
  - Detection recall with Presidio + custom patterns on corpus documents increased to 48.35% (compared to 19.78% in regex-only mode), successfully detecting names, locations, and contractual parties while maintaining the frozen 4 government_id misses.

- **Decisions**:
  - Retained strict 16-category taxonomy. Contextual organization disambiguation applies heuristic cues without guessing; unmapped organizations are logged as `organization_ambiguous` (id and location only) rather than guessing categories.
  - Confidence threshold set to 0.5 via `JUSTENOUGH_PRESIDIO_MIN_SCORE`; custom Indian regex recognizers remain exempt.

- **Tomorrow**:
  - Review human ground-truth labels and signed rubrics before proceeding to the full Day 1 evaluation run.

- **Blockers**:
  - None for infrastructure. Awaiting human-signed ground truth before executing full Day 1 experiment.

## Day 1 — Phase 1 Update (2026-10-10)

- **Done**:
  - Implemented Phase 1 (Detector and Transformer Reliability).
  - Added detector observability tracking: initialization telemetry (`init_telemetry`) and per-document safe execution counts by source (`custom_regex`, `presidio`, `ambiguous_orgs`) without logging raw sensitive values.
  - Added diagnostic detection benchmarks (`regex-only`, `presidio-only`, `combined`) and exact evaluation metrics: span recall, category-correct recall, precision, false positives, and corrected subset denominators.
  - Hardened transformer safety: pre-validates coordinates and text slices, raises `ValueError` on any offset mismatch (no silent skips), deterministically resolves span overlaps, and updates `removed_values` only after verified slice substitution.
  - Added comprehensive test coverage for all 6 actions (`KEEP`, `DROP`, `MASK_PARTIAL`, `GENERALIZE`, `PSEUDONYMIZE`, `AGGREGATE`), invalid offset errors, overlap resolution, and benchmark evaluation.
  - Executed full test suite: 17/17 pytest tests passed in 36.63s; smoke runner passed with 100% answer preservation.

- **Learned**:
  - Distinguishing span recall from category-correct recall is crucial: on the synthetic corpus, combined detector achieves 48.35% span recall and 32.97% category-correct recall (with 15.38% due to category disambiguation or non-matching entity types like organizations/names in tables).
  - Subsetting documents in detection evaluation requires filtering `corpus/planted.json` to the evaluated document set to prevent denominator inflation.

- **Decisions**:
  - Strict pre-validation in `apply_minimization` rejects slice mismatches with explicit errors rather than silently skipping them, ensuring unminimized sensitive text is never returned.
  - Detector benchmarking remains strictly diagnostic via `mode_override` and helper function, keeping official pipeline execution mode intact.

- **Tomorrow**:
  - Proceed with Phase 2: Schema definition (`schemas/answer_schemas.json`, `schemas/field.schema.json`) and task executor implementation.

- **Blockers**:
  - Official Day 1 evaluation still requires human-authored `ground_truth/labels.json` and human rubrics in `rubrics/rubric_template.json`.
