# JustEnough Evaluation: How It Works

## Purpose

JustEnough evaluates whether task-aware minimization can reduce
sensitive information in a document while preserving the answer to the
user's task.

The evaluation compares answers generated from: - **R0:** the original
document. - **R1:** the deterministically minimized document.

The goal is not merely to remove data. The system should retain enough
information to answer the task, follow the policy floor, and produce
measurable, reproducible results.

## End-to-end evaluation flow

1.  **Load a synthetic document and task.** The task defines what the
    user wants to know and identifies an answer schema.
2.  **Detect sensitive fields.** The detector finds candidate spans and
    their categories. `corpus/planted.json` provides the planted-span
    inventory used to measure detector performance.
3.  **Build a skeleton.** Detected values are replaced with typed
    placeholders. The planner receives the task and skeleton, not the
    original raw values.
4.  **Plan minimization.** The planner selects an action for each
    category, such as `KEEP`, `DROP`, `MASK_PARTIAL`, `GENERALIZE`,
    `PSEUDONYMIZE`, or `AGGREGATE`.
5.  **Enforce the policy floor.** Deterministic policy code overrides
    disallowed decisions where required.
6.  **Construct R1.** Python applies the approved actions to the
    original text using character spans. The LLM does not rewrite the
    document.
7.  **Check the R1 contract.** Before R1 is sent to the task-answering
    model, verify the applicable invariants, including that recorded
    removed values do not remain in R1 and that protected identifiers
    are not present in raw form.
8.  **Answer the task.** Run the task-answering model on the original
    document to produce R0 and on R1 to produce the minimized-document
    answer. Repeat runs as required by the experiment protocol.
9.  **Compare answers.** A comparator checks whether R0 and R1 are
    equivalent according to the answer schema or a human-authored
    rubric.
10. **Aggregate results.** The metrics layer calculates preservation,
    minimization, consistency, detection, label agreement,
    over/under-redaction, trap checks, and failures.
11. **Report limitations.** Unstable baselines, ambiguous labels,
    missing rubrics, detection misses, and comparison failures should be
    visible rather than hidden.

## What each evaluation component does

### Detector evaluation

The planted inventory records known sensitive spans. Detector evaluation
measures: - **Span recall:** fraction of planted spans matched by
detections. - **Category recall:** fraction of planted category-level
items correctly detected. - **Precision:** fraction of detections judged
valid against the reference inventory. - **False positives:** detections
not matched to the reference inventory.

**Important limitation:** the synthetic documents may contain real
sensitive-looking strings that were not planted. If those strings are
absent from the reference inventory, valid detections can be counted as
false positives. Precision therefore depends on reference-inventory
completeness.

### Answer comparison

The comparator determines whether R0 and R1 answers are equivalent: -
**Numbers:** compare within the configured relative tolerance (the
current comparator uses 0.5%). - **Lists:** compare as sets, ignoring
order and case. - **Structured objects:** compare keys and values
according to the schema/comparison rules. - **Free text:** use
human-authored required facts. If no rubric facts exist, the result
should be marked not evaluable pending human review, not treated as a
normal model failure.

Every answer schema used by a task needs an explicit, tested comparison
path. A schema file and comparator coverage must agree.

## Metrics and how to interpret them

### 1. Answer preservation (primary metric)

**Question:** Does minimization preserve the task answer?

Formula:

`equivalent eligible cases / eligible cases × 100`

The protocol should exclude unstable R0 baselines from the primary
denominator and report them separately. Missing or unevaluable
comparisons must not silently count as ordinary successes or failures.

### 2. Sensitive-field reduction

**Question:** How much sensitive information was actually reduced?

A meaningful instance-based measure is:

`(sensitive instances before − sensitive instances remaining) / sensitive instances before × 100`

This requires an explicit rule for how each action counts.
`MASK_PARTIAL`, `GENERALIZE`, `PSEUDONYMIZE`, and `AGGREGATE` do not
have the same privacy effect as `DROP`. Counting planner decisions or
category names is not a reliable substitute for measuring the sensitive
instances and exposure that remain.

### 3. Decision consistency

**Question:** Does the planner choose the same action for the same
case/category across repeated runs?

`case-category decisions that agree across runs / eligible case-category decisions × 100`

The metric must compare actual repeated plans. If repeated plans were
not supplied, consistency is **not measured**; it must not default to
100%.

### 4. Detection recall and precision

Recall measures how much of the known planted inventory was found.
Precision measures how many detections match valid reference items.
Report span and category recall separately, and state the
reference-inventory limitation when applicable.

### 5. Over-redaction rate

**Question:** How often was information required for the task minimized
with an action not accepted by the ground truth?

`required labels with unacceptable actions / eligible required labels × 100`

Lower is better. It depends on the quality of the task labels and their
acceptable-action sets.

### 6. Under-redaction rate

**Question:** How often was information not required for the task kept?

`non-required labels incorrectly kept / eligible non-required labels × 100`

Lower is better. Only categories actually present in the document should
contribute, and ambiguity should be handled according to the evaluation
rules.

### 7. Label agreement

**Question:** How often did the selected action belong to the
human-approved acceptable-action set?

`eligible non-ambiguous labels with acceptable selected actions / eligible non-ambiguous labels × 100`

This is a planner-decision diagnostic, not the same as answer
preservation.

### 8. Trap check

Trap cases test whether identity information is retained when needed for
a task such as ownership verification, while corresponding non-trap
tasks minimize identity information when it is unnecessary. The check
must cover the relevant identity categories and both sides of the
trap/non-trap comparison, not just one hardcoded category.

### 9. Baseline stability

The original-document answer is run repeatedly (for example, R0a and
R0b). If those answers differ, the baseline is unstable. Report the
number of unstable cases and exclude them from the primary
answer-preservation denominator when required by the protocol.

### 10. Failure attribution

Each failed or unevaluable case should have evidence supporting one of
the defined categories: - `detection miss` - `planner error` -
`ambiguous label` - `comparison error`

Do not assign every failure to `comparison error` by default. The runner
should capture which stage failed and provide supporting evidence.

## Smoke test versus the real evaluation

The smoke runner is an infrastructure check, not a final experiment. It
uses four fixed cases and a deterministic mock task executor. This
verifies that the detector/planner/transformer/comparator/metrics
pipeline can run without live task-answering API calls.

A mock can return an answer based on simple string checks. It does not
establish that a real model will answer correctly after minimization.
Therefore, smoke-test scores must not be presented as evidence of
real-world answer preservation or privacy performance.

The full evaluation needs a real R0/R1 task executor, defined answer
schemas, tested comparators, a valid ground-truth loader, repeated-run
handling, run metadata, and a finalized budget/protocol. Use mocks to
test the harness before authorizing live calls.

## Known audit findings to address

The read-only audit reported the following: - Ground truth covers all 30
cases and 16 categories, but is explicitly **not human-approved**. Its
contents and status are left unchanged until a human review is
requested. - `eval/metrics.py` expects a different label structure from
the actual `ground_truth/labels.json`, so label metrics can silently
read no labels. - `schemas/answer_schemas.json` is missing, and
comparator handling does not explicitly cover all 17 task schema IDs. -
Six free-text cases have empty required-fact rubrics and are not yet
evaluable by the current free-text comparator. - `decision_consistency`
is hardcoded to 1.0. - Sensitive-field reduction counts planner category
decisions rather than actual sensitive instances. - Trap checks do not
cover all relevant identity categories and matching non-trap cases. -
Unstable baseline cases are still included in the answer-preservation
denominator. - Failure attribution defaults to `comparison_error`. - The
run protocol has unresolved case-selection and spend-cap placeholders,
and seed/run telemetry needs review. - The audited detector results were
63.74% span recall and 51.65% category recall against the current
planted inventory, below the specified 80% recall target.

These are audit findings, not claims that fixes have already been made.

## Safe order of work

1.  Fix metric calculations and the ground-truth loader, with regression
    tests.
2.  Define answer schemas and align/test every comparator.
3.  Build the full evaluation runner and live R0/R1 executor.
4.  Test the runner end-to-end using mocks.
5.  Resolve protocol choices and set a spend cap before any live API
    experiment.
6.  Review/approve ground truth and free-text rubrics before treating
    the results as an official evaluation.

## Interpretation rule

A high answer-preservation score alone is not sufficient. It must be
interpreted alongside sensitive-field reduction, detector recall,
consistency, policy-floor compliance, failure attribution, and the
limitations of the reference labels. No metric should be reported as
measured when its required evidence was not collected.
