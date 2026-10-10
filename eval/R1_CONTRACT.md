# R1 Input Contract: Minimized Document Representation

## Definition
The **R1 input** is the structured minimum document representation supplied to the task answering model (executor). It is constructed by applying the planner's action decisions (after strict policy floor enforcement) to the original document via deterministic code.

## Invariant Guarantees
1. **Zero LLM Rewriting**: The minimized document is produced 100% deterministically by `experiment/transform.py` using character slice replacements. No LLM rewriting or rephrasing occurs.
2. **Absence of Removed Sensitive Values**: Any field assigned `DROP`, `MASK_PARTIAL`, `GENERALIZE`, `PSEUDONYMIZE`, or `AGGREGATE` has its exact raw sensitive value completely removed from the text:
   - `DROP`: The raw substring is removed and replaced by `[REDACTED:<CATEGORY>]`.
   - `MASK_PARTIAL`: Full raw value is removed; only trailing verification digits (e.g. `XXXX-XXXX-1234`) are retained.
   - `GENERALIZE`: Exact raw string is removed and replaced with coarsened granularity (e.g. `YYYY-MM` or region code).
   - `PSEUDONYMIZE`: Raw name or identifier is removed and replaced with a document-local alias (e.g. `Counterparty_1`).
   - `AGGREGATE`: Raw item value is removed and replaced by `[AGGREGATED:<CATEGORY>]`.
3. **Verification Check**: Before any R1 execution, the harness verifies that:
   `for val in removed_values: assert val not in r1_text`
4. **Policy Floor Compliance**: Full account/card numbers and government IDs are never present in raw form in R1.
