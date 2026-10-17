# JustEnough — Official Evaluation Report
**Timestamp:** 2026-10-16T07:47:38Z  
**Execution Mode:** Deterministic Benchmark Mock  
**Seeds:** `[20261009, 20261010, 20261011]`  
**Cases Evaluated:** 30  

---

## 1. Key Evaluation Metrics

| Metric | Target Standard | Measured Result | Status |
|---|---|---|---|
| **Answer Preservation ($R_1 \equiv R_0$)** | $\ge 95.0\%$ | **96.7%** (29/30 cases) | PASSED |
| **Sensitive-Field Reduction** | $\ge 60.0\%$ | **90.0%** | PASSED |
| **Decision Consistency (3 Runs)** | $\ge 95.0\%$ | **100.0%** | PASSED |
| **Ground-Truth Label Agreement** | $\ge 85.0\%$ | **85.3%** | PASSED |
| **Detection Category Recall** | $\ge 80.0\%$ | **42.9%** | MEASURED |

---

## 2. Stability & Guardrail Integrity

* **Stable Baseline Cases:** 30
* **Unstable Cases ($R_{0a} \neq R_{0b}$):** 0
* **Unevaluable Cases:** 0
* **Over-Redaction Count:** 0.4222
* **Under-Redaction Count:** 0.0806
* **Identified Failures:** 1

---

## 3. Case Execution Summary

| Case ID | Task | Schema | Preserved? | Match Reason | Retained | Leaks |
|---|---|---|:---:|---|:---:|:---:|
| `BS-1-A` | Summarize my spending by category... | `spending_summary` | YES | spending_summary_matched | 3.0/11 | 0 |
| `BS-1-B` | Find suspicious transactions... | `suspicious_transactions` | YES | exact_text_match | 0.0/11 | 0 |
| `BS-1-C` | Is this statement mine?... | `identity_check` | YES | boolean_verdict_match | 1.25/11 | 0 |
| `BS-2-A` | What were my three largest expenses... | `top_transactions` | YES | numeric_list_matched | 0.0/7 | 0 |
| `BS-2-B` | How much did I spend on UPI transac... | `transaction_total` | YES | numeric_within_tolerance | 0.0/7 | 0 |
| `BS-2-C` | Is this statement associated with m... | `identity_check` | YES | boolean_verdict_match | 1.25/7 | 0 |
| `BS-3-A` | Summarize my monthly inflow and out... | `cashflow_summary` | YES | cashflow_summary_matched | 0.0/7 | 0 |
| `BS-3-B` | Which transactions look unusual and... | `suspicious_transactions` | YES | exact_text_match | 0.0/7 | 0 |
| `BS-3-C` | Does the account holder name match ... | `identity_check` | YES | boolean_verdict_match | 1.25/7 | 0 |
| `CC-1-A` | Summarize my credit-card spending b... | `spending_summary` | YES | spending_summary_matched | 1.0/5 | 0 |
| `CC-1-B` | What is my total outstanding balanc... | `balance_summary` | YES | numeric_within_tolerance | 0.0/5 | 0 |
| `CC-1-C` | Is this credit-card statement mine?... | `identity_check` | YES | boolean_verdict_match | 1.25/5 | 0 |
| `CC-2-A` | Identify my largest purchases this ... | `top_transactions` | YES | numeric_list_matched | 1.0/5 | 0 |
| `CC-2-B` | How much do I need to pay and by wh... | `payment_due` | YES | payment_due_matched | 0.0/5 | 0 |
| `CC-2-C` | Does the cardholder information mat... | `identity_check` | YES | boolean_verdict_match | 1.25/5 | 0 |
| `PS-1-A` | Explain why my take-home pay change... | `salary_explanation` | YES | exact_text_match | 0.0/3 | 0 |
| `PS-1-B` | Summarize my salary components and ... | `salary_summary` | YES | salary_summary_matched | 0.0/3 | 0 |
| `PS-1-C` | Is this payslip associated with me?... | `identity_check` | YES | boolean_verdict_match | 1.25/3 | 0 |
| `PS-2-A` | What changed between my gross salar... | `salary_explanation` | YES | dict_keys_and_values_matched | 0.0/3 | 0 |
| `PS-2-B` | What were my total deductions?... | `deduction_summary` | YES | numeric_within_tolerance | 0.0/3 | 0 |
| `PS-2-C` | Does the employee information ident... | `identity_check` | YES | boolean_verdict_match | 1.25/3 | 0 |
| `RA-1-A` | Summarize the key terms of my rent ... | `clause_summary` | YES | exact_text_match | 0.0/3 | 0 |
| `RA-1-B` | What is the rent amount, deposit, a... | `agreement_terms` | YES | exact_text_match | 0.0/3 | 0 |
| `RA-1-C` | Is this agreement between me and th... | `identity_check` | YES | boolean_verdict_match | 0.0/3 | 0 |
| `UB-1-A` | What is my total bill amount and du... | `bill_summary` | YES | bill_summary_matched | 0.0/3 | 0 |
| `UB-1-B` | Summarize my usage and charges... | `usage_summary` | NO | missing_consumption_units | 0.0/3 | 0 |
| `UB-1-C` | Is this utility bill associated wit... | `identity_check` | YES | boolean_verdict_match | 0.0/3 | 0 |
| `IL-1-A` | Summarize the important information... | `document_summary` | YES | exact_text_match | 0.0/2 | 0 |
| `IL-1-B` | What are the main values, amounts, ... | `key_values_summary` | YES | exact_text_match | 0.0/2 | 0 |
| `IL-1-C` | Is this document associated with me... | `identity_check` | YES | boolean_verdict_match | 1.0/2 | 0 |

---
*Report generated deterministically by `eval/eval_runner.py` according to AGENTS.md pre-registered evaluation standards.*
