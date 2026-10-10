# Antigravity operating rules for JustEnough

Read AGENTS.md first. It holds the project facts and constraints. This file only says HOW to work in Antigravity.
Do not restate or override AGENTS.md. If they conflict, AGENTS.md wins and you tell me.

## Working style
- For any change touching more than one file, produce a short plan first (/plan) and wait for my approval.
- One module per task. Keep tasks small and independently testable.
- After each task report: what changed, which tests you ran WITH real output, assumptions made, open issues.
- Never say tests passed unless you ran them and have the output. Never fabricate results.

## Subagents
- Custom agents live in .agents/agents/: synthetic-data, detector, minimizer, evaluator.
- Delegate only independent work. Two agents never edit the same file at the same time.
- The evaluator must not edit planner, transformer or ground-truth files. It only measures and reports.
- Subagents inherit sandbox command policy. Keep it on `sandbox`.

## Multi-agent modes
- Do NOT start /teamwork-preview or /boost unless I explicitly ask.
- If I do use Teamwork: integrity mode `development`, project directory = this repo, never for ground truth,
  labels or the final evaluation. (Stricter modes can forbid libraries and external APIs we depend on.)

## Commands, cost and safety
- Prefer sandboxed execution. Never run a command that prints environment variables, keys or raw document values.
- Before any long or repeated model run, check usage/credits and tell me the expected number of calls.
- Stop and report if the run would exceed the spend cap in DAY1_SPEC.md.

## End of day
Append to docs/DAYLOG.md: Done | Learned | Decisions | Tomorrow | Blockers. Do not edit old entries.
