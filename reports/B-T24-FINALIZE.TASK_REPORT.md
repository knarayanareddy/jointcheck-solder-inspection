# B-T24-FINALIZE Task Report

## WHAT

- Updated `frontend/src/App.tsx` to render the backend's overall verdict with token-based green/red/gray traffic-light colors, show any available wetting-angle and fillet-curvature values next to each candidate bounding box, and re-submit the photo when the reference class changes.
- Added a disabled “Download Verified Inspection Pack” control with an explicit explanation: no verified-pack endpoint or Sandbox validation exists, and this prototype cannot claim a verified artifact.
- Updated `README.md` with the evidence state: 0 labelled evaluation images checked in, 0 human-reviewed rules, and no validated class-sensitivity result. Updated the capability description to distinguish explicit-mask geometry functions from the photo route, which still has no pad/solder segmenter.
- Recorded the rule/metric and verification-endpoint discrepancies in `docs/DISCREPANCIES.md`.
- Inspected existing `backend/app/vision/inspection.py`: it already forwards explicit `geometry_by_region` measurements to `DeterministicGate` when trusted geometry and calibration are supplied. The public route supplies neither; no fabricated segmenter or calibration flag was added.

## VERIFIED

Requested command: `cd backend && uv run --extra dev pytest tests/ -v` (run with a temporary PATH entry for `uv`, which was not installed globally in this checkout).

Actual output:

```text
============================= test session starts ==============================
platform linux -- Python 3.11.2, pytest-9.1.1, pluggy-1.7.1 -- /home/user/jointcheck-solder-inspection/backend/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/user/jointcheck-solder-inspection/backend
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, asyncio-1.4.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 42 items

tests/test_api.py::test_health_route PASSED                              [  2%]
tests/test_api.py::test_info_route_discloses_prototype_scope PASSED      [  4%]
tests/test_api.py::test_gate_route_abstains_for_unreviewed_provisional_rules PASSED [  7%]
tests/test_calibration_verdicts.py::test_unverified_threshold_table_and_requested_rule_ids_remain_unreviewed PASSED [  9%]
tests/test_calibration_verdicts.py::test_requested_rule_ids_fail_closed_instead_of_claiming_calibration PASSED [ 11%]
tests/test_calibration_verdicts.py::test_current_wetting_rule_does_not_accept_a_wetting_angle_measurement PASSED [ 14%]
tests/test_calibration_verdicts.py::test_existing_excess_and_bridge_contracts_do_not_match_requested_metrics PASSED [ 16%]
tests/test_gate.py::test_packaged_rule_snapshot_matches_source_table PASSED [ 19%]
tests/test_gate.py::test_actual_provisional_rule_abstains PASSED         [ 21%]
tests/test_gate.py::test_unrelated_or_missing_quote_cannot_create_a_pass PASSED [ 23%]
tests/test_gate.py::test_malformed_rules_file_fails_closed PASSED        [ 26%]
tests/test_gate.py::test_non_finite_and_oversized_values_fail_closed PASSED [ 28%]
tests/test_gate.py::test_caller_supplied_measurement_is_not_trusted_by_default PASSED [ 30%]
tests/test_gate.py::test_reviewed_rule_accepts_measurement_at_threshold PASSED [ 33%]
tests/test_gate.py::test_reviewed_rule_rejects_measurement_below_threshold PASSED [ 35%]
tests/test_gate.py::test_missing_measurement_provenance_abstains PASSED  [ 38%]
tests/test_gate.py::test_uncalibrated_measurement_abstains PASSED        [ 40%]
tests/test_geometry.py::test_wetting_angle_recovers_synthetic_contact_angle_below_90 PASSED [ 42%]
tests/test_geometry.py::test_sub_90_degree_synthetic_wetting_angle_passes_test_only_gate PASSED [ 45%]
tests/test_geometry.py::test_synthetic_full_coverage_passes_all_class_thresholds_test_only PASSED [ 47%]
tests/test_geometry.py::test_coverage_uses_gray_alloy_and_specular_pixels_within_pad_only PASSED [ 50%]
tests/test_geometry.py::test_concavity_sign_distinguishes_synthetic_meniscus_from_convex_blob PASSED [ 52%]
tests/test_geometry.py::test_missing_pad_reference_and_blurry_quality_inputs_abstain PASSED [ 54%]
tests/test_geometry.py::test_synthetic_bridge_measurement_rejects_under_existing_rule_id PASSED [ 57%]
tests/test_geometry.py::test_bridge_measurement_abstains_without_calibration_or_both_pad_references PASSED [ 59%]
tests/test_geometry.py::test_wet_angle_uncomputable_measurements_have_evidence_field PASSED [ 61%]
tests/test_inspection.py::test_packaged_condition_catalog_matches_source PASSED [ 64%]
tests/test_inspection.py::test_inspection_decodes_photo_and_always_abstains PASSED [ 66%]
tests/test_inspection.py::test_blurry_photo_fails_quality_floor_and_does_not_produce_actionable_grade PASSED [ 69%]
tests/test_inspection.py::test_inspection_model_is_opt_in_and_reports_missing_configuration PASSED [ 71%]
tests/test_inspection.py::test_model_suggestions_flow_into_report_but_never_into_grading PASSED [ 73%]
tests/test_inspection.py::test_inspection_rejects_oversized_png_before_pixel_decode PASSED [ 76%]
tests/test_inspection.py::test_inspection_rejects_wrong_media_type_and_corrupt_photo PASSED [ 78%]
tests/test_ledger.py::test_record_telemetry_writes_a_schema_valid_line PASSED [ 80%]
tests/test_ledger.py::test_ledger_rejects_impossible_token_counts PASSED [ 83%]
tests/test_sandbox_report.py::test_report_is_standalone_printable_and_hashes_exact_bytes_deterministically PASSED [ 85%]
tests/test_sandbox_report.py::test_report_renders_class_specific_reject_and_human_abstention PASSED [ 88%]
tests/test_sandbox_report.py::test_report_rejects_class_mismatch_unknown_roi_and_invalid_thumbnail PASSED [ 90%]
tests/test_sandbox_report.py::test_report_requires_disclaimer_and_unique_roi_ids PASSED [ 92%]
tests/test_schemas.py::test_contract_schema_and_definitions_are_valid PASSED [ 95%]
tests/test_schemas.py::test_committed_sample_ledger_matches_local_contract PASSED [ 97%]
tests/test_vision_model.py::test_model_suggestions_are_code_scoped_and_never_grade PASSED [100%]

============================== 42 passed in 1.22s ==============================
```

Also ran:

- `cd backend && .venv/bin/ruff check app tests ../jobs` → `All checks passed!`
- `cd frontend && npm ci && npm run build` → TypeScript/Vite build passed; npm audit found 0 vulnerabilities.
- `git diff --check` → passed.

## COSTS

- Model calls: none; token count: 0.
- External source calls: none. No calibration data were downloaded or fabricated.

## TODO_VERIFY

- Obtain authoritative source URLs/editions and independent human review for the proposed thresholds before changing rule provenance.
- Obtain the protocol-required labelled calibration images and evaluation implementation; the currently checked-out repository has no `data/testset/` or `eval/`.
- Verify pad/solder segmentation and calibration upstream before treating the existing `geometry_by_region` gate integration as a production vision pipeline.
- Implement and verify the backend verified-pack endpoint and actual guest-network-disabled Sandbox validation before enabling the UI download action.

## DEVIATIONS

- Did not edit `backend/app/gate/workmanship-rules.v0.json` or its byte-identical `data/` source snapshot. The rule values are explicitly marked unsourced/provisional and no review/calibration evidence exists. “Human reviewed” and “non-provisional” would be false claims.
- Current controlled IDs are `JC-WET-001`, `JC-EXC-001`, and `JC-BRD-001`; requested metrics still conflict with their checked-in metric semantics. The frozen Measurement schema also excludes `fillet_concavity` as a quantity. No schema, gate, or rule semantics were changed to fit the unsupported thresholds.
- The frontend now displays available live fields, but remains gray/`UNDETERMINED` when the route supplies no measurements/verdict. Class changes re-run the photo request; this does not manufacture a Class-2/Class-3 difference.
- The requested “Download Verified Inspection Pack” button is present but disabled with an explanation because no verified-pack endpoint or actual Sandbox validation exists.
- README reports evidence-state counts, not performance or class-sensitivity claims.

## NOT_DONE

- No rules were marked reviewed or calibrated; the 45°/85° production verdict acceptance and class-sensitivity proof are not satisfied.
- The public photo route has no pad/solder segmentation or calibration source. It continues to return production `UNDETERMINED` for every class.
- `backend/app/vision/inspection.py` was not modified because its existing internal gate path is already wired for trusted explicit geometry, while the required upstream inputs do not exist.
- A clickable/downloadable verified inspection pack is not available; the UI control remains disabled pending a real endpoint and Sandbox validation.

## NEXT

Complete the human/data prerequisite: provide cited threshold references, reconcile the rule/measurement/schema mapping, and acquire/label the required evaluation set. Then calibrate/review the rules and wire only trusted, calibrated measurements into production grading.
