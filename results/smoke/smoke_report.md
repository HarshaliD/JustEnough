# Day 1 Infrastructure Smoke-Test Report

> **NOTICE**: This report was generated during preliminary infrastructure validation.
> It tests the end-to-end execution pipeline using mock executors and `dummy_labels.json`.
> It DOES NOT constitute official Day 1 experimental findings.

## Evaluated Smoke Cases
- BS-1-A | BS-1-C | CC-1-B | PS-1-B

## Smoke Metrics (Infrastructure Sanity Check)
- Total Cases: 4
- Preserved Cases: 4 (100.0%)
- Unstable Cases: 0
- Sensitive Field Reduction: 82.8%
- Trap Check Pass Rate: 100.0%
- Detection Mode: presidio+regex
- Detection Recall (on smoke docs): 32.1%

## Output Isolation
All smoke outputs are isolated under `results/smoke/`.
No files in `results/raw/` or `results/results.json` were created.

## Cleanup Instructions for Tomorrow's Full Run
Before executing tomorrow's real experiment with human-signed labels:
```powershell
Remove-Item -Recurse -Force results/smoke
```
