## 5. What should you read next?

Since you've completed `AGENTS.md`, follow this order. Don't jump into every Python file yet.

## 1

Read `GEMINI.md` next

Do this now

This should explain the operating rules for the main coding agent, its workflow, and how it coordinates work.

While reading, identify: what the agent may change, what it must not change, and when it must stop and ask you.

## 2

Read `DAY1_SPEC.md`

Focus on the purpose of the experiment, the corpus and tasks, the detector contract, planner, transformation, answer comparison, metrics, thresholds, and what is out of scope.

While reading, identify: what is frozen, what counts as success, and what the code must prove.

## 3

Trace `experiment/detector.py`

Now connect the specification to the real implementation: Presidio input, custom patterns, `DetectedField`, skeleton creation, and recall measurement.

## 4

Read the minimizer files

Start with `experiment/planner.py`, then `experiment/policy.py`, then `experiment/transform.py`.

Follow one example from Gemini's proposed plan to the actual transformed text.

## 5

Read the evaluation code

Read `eval/comparators.py`, `eval/metrics.py`, and `eval/smoke_runner.py`.

Your goal is to understand exactly how the 100% preservation and 82.8% reduction numbers were calculated, rather than just trusting the report.

Your next action: paste `GEMINI.md` here. We'll understand it section by section, just as we did with `AGENTS.md`. Then we'll tackle `DAY1_SPEC.md` before opening the code.







------------------------------------------------------------
## WHAT TO CHECK BEFORE FULL IMPLEMENTATION OF DAY 1
Let's do it now. I've read the `DAY1_SPEC.md` you shared. The central question is whether JustEnough can remove sensitive information while preserving the answer to the user's task.

We'll separate three layers as we go:

- Specification: What the experiment is supposed to do.
- Implementation: What the Python code actually does.
- Evidence: What the test results genuinely demonstrate.

## 1. Smoke test vs. full experiment

These are different stages, with different purposes.

## Smoke test

Infrastructure check

Section 14: Run 3 to 5 cases end to end.

Check that:

- The skeleton contains no raw detected values.
- Planner outputs validate against the schema.
- Answer comparators work.
- Logs don't contain sensitive values.
- API call counts match expectations.

Fix infrastructure issues, not labels or thresholds.

## Full experiment

Feasibility evaluation

Sections 7 to 13: Evaluate the task cases, measure the metrics, inspect failures, and make a GO / GO WITH CHANGES / NO-GO decision.

This requires approved ground-truth labels, completed sign-off, frozen thresholds, and a spend cap.

The existing implementation report mentions a four-case smoke test with 100% answer preservation and 82.8% sensitive-field reduction. Those are reported smoke-test results, not verified full-experiment results. Four cases cannot establish performance across all 30 cases or across the eventual B0–B3 comparison.

## 2. What the full experiment is intended to measure

The spec describes a pipeline that detects sensitive fields, creates a skeleton, asks the planner for a structured plan, transforms the document deterministically, and checks the answer against the original.&#x20;

Pasted markdown.md



The main metric is answer preservation, with secondary metrics assessing privacy reduction and decision quality.

| Metric                    | What it tells us                                                     |
| ------------------------- | -------------------------------------------------------------------- |
| Answer preservation       | Did the minimized data still produce an equivalent answer?           |
| Sensitive-field reduction | How much sensitive information was withheld?                         |
| Decision consistency      | Did the planner make the same decisions across three runs?           |
| Trap check                | Did decisions change appropriately when identity became necessary?   |
| Detection recall          | How many planted sensitive items did the detector find?              |
| Label agreement           | Did planner decisions fall within human-approved acceptable actions? |
| Over-redaction            | How often were required categories given unacceptable actions?       |
| Under-redaction           | How often were unnecessary sensitive categories kept?                |

The key is that these metrics cannot substitute for one another. High privacy reduction is not useful if the task answer breaks. Perfect answer preservation is also not enough if the system keeps everything.

## 3. B0–B3: an important specification mismatch

There is a discrepancy between the project rules and the Day 1 evaluation instructions.

| Arm | Intended comparison                               |
| --- | ------------------------------------------------- |
| B0  | Send everything, without minimization             |
| B1  | Redact everything flagged by the detector         |
| B2  | Use the planner's decisions, without the verifier |
| B3  | Use the planner plus verifier                     |

These arms appear in `AGENTS.md`, but the Day 1 evaluator instructions explicitly say not to implement or run B0–B3 on Day 1. `DAY1_SPEC.md` Sections 7–10 instead describe evaluating the original answer against the minimized answer.

That means we should distinguish two experiments:

- Day 1 feasibility test: Can the current pipeline minimize data and preserve answers?
- Later comparative experiment: Does the planner-plus-verifier approach outperform simpler baselines?

We shouldn't quietly add B0–B3 to Day 1. The later experiment needs its own agreed scope and protocol.

## 4. What the smoke test proves, and what it doesn't

Based on the implementation report available in our project records:

## Reported smoke-test results

Cases tested

# 4

Answer preservation

# 100%

Sensitive-field reduction

# 82.8%

Detection recall

# 48.35%

These figures come from the saved implementation report, not an independently rerun experiment. The detection-recall figure covers the detector across the synthetic corpus, whereas the other two figures are from the four smoke cases.

The four smoke cases were:

- `BS-1-A`: Spending summary
- `BS-1-C`: Identity check
- `CC-1-B`: Outstanding balance
- `PS-1-B`: Salary summary

The smoke test gives us an early indication that the pipeline works end to end. It does not establish that all 30 cases will pass, that the planner is consistently correct, or that the proposed approach beats the baselines.

The detector's reported 48.35% recall is especially important: a minimizer cannot remove sensitive fields that the detector never identifies, unless another mechanism independently catches them.

## 5. Answer preservation: how the comparison should work

Section 8 defines this process:

### Original document

Run the task twice → R0a and R0b

### Check baseline stability

If answers disagree, mark the case unstable

### Minimized document

Run the same task → R1

Compare the answers

- Numbers: within 0.5% relative tolerance
- Lists: set equality
- Free text: all required facts in the human-written rubric

Why run the original task twice? Because an LLM may produce inconsistent answers even when its input has not changed. If the baseline is unstable, a difference between the original and minimized answers may not have been caused by minimization.

There is one detail the spec should clarify: when the two original answers disagree, exactly how do we select or construct the reference for comparing R1? It says to use the rubric and report unstable cases separately, but does not fully specify the comparison implementation.

## 6. Ground truth and readiness to run

The spec requires human-approved labels written or signed before model outputs are seen. It also requires human-written rubrics for free-text tasks.

The implementation report says these were still missing at the time of that report. It also identifies a placeholder commit hash and an unfilled spend cap in the specification.

So the project record does not support treating the full evaluation as ready or completed.

Before the full run, we need to verify:

- All 30 cases have human-approved ground-truth labels.
- The six free-text rubrics are complete and reviewed.
- The sign-off checklist is complete.
- The spend cap is filled in.
- The selected equivalence cases are specified.
- The baseline and minimized answer-comparison protocol is unambiguous.
- The actual code matches the frozen rules.

## 7. Code vs. specification: the first audit findings

I found the implementation reports and evaluator instructions in the project records, but not the actual Python source files themselves. So the following are reported implementation facts and specification issues, not a claim that I have independently inspected the code.

| Area        | What we know                                                                  | What still needs verification                                                         |
| ----------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Detector    | Presidio plus custom regex reportedly increased recall to 48.35%.             | How planted-item matching handles overlapping or duplicate detections.                |
| Planner     | Reportedly uses JSON Schema validation and one retry.                         | What happens if the response remains invalid after the retry.                         |
| Transformer | Reportedly implements all six actions deterministically.                      | Whether each action preserves the intended information and removes prohibited values. |
| Comparators | Reportedly implement numeric tolerance, list comparison and free-text checks. | How unstable baselines, missing fields and nested outputs are handled.                |
| Metrics     | Unit tests reportedly cover metric calculations.                              | Whether the denominators and ambiguous-label exclusions match the spec exactly.       |
| Full runner | Evaluator instructions reference `eval/runner.py`.                            | Whether the runner exists and executes the prescribed protocol correctly.             |

### Three specification issues I'd resolve before the full run

1\. How many cases require answer-equivalence evaluation?

Section 8 says at least 10 cases, with at least one per document type and two trap cases. The timeline refers to a 30-case full run. We need to clarify whether answer preservation is evaluated on all 30 cases or only the selected subset, and which metrics use each population.

2\. Do the API-call estimates add up?

Section 12 estimates \\(30 \times 3 \times 3 = 270\\) calls. But Section 8 also requires two original-answer runs to check stability. We need to specify whether those baseline calls are repeated for every run, cached per case, or handled separately. Otherwise, the budget estimate may be wrong.

3\. What exactly counts as a sensitive field retained?

The reduction metric needs a precise unit. Is it counting detected field instances, categories, or actual sensitive values sent to the model? The denominator must be defined consistently, particularly when the detector misses planted items.

These aren't reasons to abandon the design. They're the kinds of measurement details worth settling before the first official run, when the thresholds and labels are still protected from post-result changes.

## What I recommend next

Let's inspect the code in this order, starting with the evaluator rather than the planner:

1. `eval/comparators.py`
2. `eval/metrics.py`
3. `eval/smoke_runner.py`
4. `experiment/detector.py`
5. `experiment/planner.py` and `experiment/policy.py`
6. `experiment/transform.py`
7. The full evaluation runner, if present

Share the repository files or upload a ZIP of the project so we can trace actual inputs, outputs, and calculations. Then we'll make a concrete specification-versus-code table, mark each requirement as matched, mismatched, or not yet verifiable, and avoid changing any frozen thresholds or labels.



-----------------------------------------------------
1. [ ] Create human ground truth (Critical)
   Create ground_truth/labels.json with human-reviewed, task-specific category labels and acceptable actions. Complete and sign the six required task rubrics independently of model output.

2. [ ] Integrate Gemini API (Critical)
   Configure the Gemini client using an environment variable for the API key and the existing JUSTENOUGH_MODEL setting. Handle missing credentials, API errors, timeouts and spend limits safely.

3. [ ] Complete experiment/planner.py (Critical)
   Replace the hardcoded planning path with a real Gemini request. Send the task and typed skeleton, parse structured JSON, validate against schemas/plan.schema.json, and allow at most one retry for schema failure.

4. [ ] Enforce planner contract (Critical)
   Validate required fields, action enums, reason, confidence bounds, case ID, decisions and task_output_schema. Enforce the frozen category taxonomy and policy floor without silently accepting malformed plans.

5. [ ] Fix answer-schema handling (High)
   Decide how answer_schema_id maps to actual answer-schema definitions. Ensure the task executor answers from the document and task, while the schema constrains output format rather than supplying the answer.

6. [ ] Audit policy and transformation (High)
   Verify policy enforcement and deterministic transformations, including that actions are applied to the correct detected fields and removed values do not leak.

7. [ ] Complete real evaluation pipeline (Critical)
   Replace mock task execution for official evaluation with actual task execution on original and minimized inputs. Check baseline stability, comparison rules, metric denominators and failure attribution.

8. [ ] Validate smoke tests and tests (High)
   Keep smoke tests isolated and mock-based where appropriate. Add tests for live-client behavior using mocks, schema failures, retry limits, policy restrictions and error handling.

9. [ ] Audit logs and spend controls (High)
   Prevent raw sensitive values and secrets from entering logs. Configure and verify the spend cap, call limits, timeouts and API usage before the full run.

10. [ ] Remove is_trap from planners input

11. [ ] Fix the answer-schema. The model should be given task_id to decide how to answer the question. Now the only way it can decide how to answer the question is to look at the answer_schema_id which might be non-determinstic.

12. [ ] planner should be able to detect is_trap.

13. [ ] Validate the plan before policy enforcement

Reject malformed decisions before calling .get('action'). Check required fields, valid actions, confidence range, and expected data types.
Also, the code currently checks only categories that are present in decisions. A missing government_id decision passes through unnoticed. Schema validation and completeness checks should catch that before transformation.

14. [ ] clarify confidence reporting

15. [ ] For example, a safe diagnostic summary might look like:
{
  "mode": "presidio+regex",
  "presidio_status": "success",
  "presidio_matches": 4,
  "custom_regex_matches": 2
}


These numbers are illustrative, not results from your actual run.
Also check whether en_core_web_sm is installed and whether AnalyzerEngine initializes. Your _init_presidio() method currently hides initialization errors by returning None, so a missing spaCy model could silently switch the system into regex-only mode.\

16. [ ]Yes. I would add this to our checklist. It would help us understand whether Presidio improves detection enough to justify including it.
However, there are three different experiments here.
A

Custom regex only
Tests the four custom Indian-format patterns without Presidio.



B

Presidio only
Tests Presidio by itself, without custom regex matches being added.



C

Presidio + regex
Tests the combined detector that JustEnough currently intends to use.



Measure each against the same planted ground truth.
Metric	What it tells you
Span recall	What fraction of planted sensitive values were found?
Category-correct recall	What fraction were found and assigned the correct category?
Precision	Of all detections, how many were genuinely intended sensitive fields?
False positives	How many ordinary values were incorrectly flagged?
Per-category recall	Which types of information does each detector miss?
One detail: your existing evaluate_detection_recall() can help with span recall, but it currently counts a match based on overlap and doesn't verify the detected category. It also uses the full planted dataset as its denominator. We'd need to address those limitations before comparing partial smoke runs or category correctness.
Keep this as a detector benchmark, separate from the end-to-end JustEnough evaluation. The first tells you which detector works best. The second tells you whether the whole system preserves task answers while reducing sensitive information.

17. [ ]
5. Three practical experiments I'd do next
Understanding becomes much stronger when you can observe the code yourself.
1. Prove which detector runs. Run one document with force_fallback=True, then with Presidio enabled. Compare the selected mode, analysis status, and detection counts.
2. Inspect a single detection. Print its category, start, end, line number, detector name, and placeholder. Do not print its raw value in persistent logs.
3. Test a deliberately difficult number. Put a 12-digit reference number in a synthetic document. Check whether the regex flags it, whether the category is appropriate, and how that affects recall and false positives.
For experiment 1, remember that enabling Presidio is not enough. You need evidence that analyze() completed successfully and that the combined run included its results.

18. [ ] 