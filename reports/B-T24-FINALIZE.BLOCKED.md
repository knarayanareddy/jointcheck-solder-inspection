# B-T24-FINALIZE Blocker — rule provenance, metric mapping, and live grading

## Precise question

May the provided threshold numbers be marked `human_reviewed: true` and used for production verdicts despite the rule table declaring its thresholds unsourced/provisional, no labelled calibration set being present, and the requested rule metrics not matching the frozen schema and gate?

**Decision:** no. Keep the production rules unchanged and retain fail-closed `UNDETERMINED` behavior until evidence and contracts are reconciled.

## What was tried and observed

- Confirmed the active work branch is `arena/9cc7794e-jointcheck-solder-inspection`, based on the merge of PR #3; worktree was clean before this task.
- Inspected both rule snapshots: they are byte-identical; `JC-WET-001`, `JC-EXC-001`, and `JC-BRD-001` are all unreviewed and carry provisional provenance. No `provisional: false` metadata is present.
- Inspected `schemas/core-schemas.json`: `fillet_concavity` is not a `Measurement.quantity`. The gate evaluates a single numeric metric; the request's bridge mapping and excess-solder metric combination do not match this contract.
- Checked the data tree and calibration assets. Actual command output:

  ```text
  find: 'data/testset': No such file or directory
  find: 'eval': No such file or directory
  ```

- Inspected `backend/app/vision/inspection.py`: the public photo route supplies no pad/solder masks or calibration. Existing internal geometry-to-gate wiring only operates with explicit trusted geometry and `calibrated=True`; those inputs are not established by the route.
- Updated the UI to display available measurements/verdicts, rerun when class changes, and show the verified-pack control disabled rather than claim unsupported grades/artifacts.
- Added factual README calibration status and logged the discrepancies. The full 42-test backend suite, Ruff, frontend build, and diff checks pass.

## Two options

1. **Recommended:** obtain and record authoritative threshold references; have a qualified reviewer approve the criteria; reconcile the rule IDs/metrics/schema in an authorized contract change; acquire and independently label the calibration set; then enable the per-class production verdict tests and verified-pack endpoint.
2. Keep the rules and gate fail-closed, present available geometry only as non-actionable evidence, and leave the verified-pack control disabled until those prerequisites are complete.

## Run-limit note

This is a missing-evidence and frozen-contract blocker, not a claim that three agent runs were exhausted. Further coding-only iterations cannot create review provenance, calibration labels, or trusted segmentation.
