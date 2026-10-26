# Limitations and safety boundaries

**Read before using this repository.** JointCheck is an experimental prototype, not a validated inspection instrument or certified compliance system. It must not be used to release, reject, or rework production assemblies.

## Current limitations

- **Image quality only:** The OpenCV path calculates Laplacian blur variance, clipped exposure percentage, dimensions, and geometric contour candidates. These thresholds are provisional; contour candidates are not confirmed solder joints.
- **No solder-specific measurement:** There is no validated segmentation or metric for solder coverage, fillet geometry, solder volume, wetting angle, or defect severity. Measurements are never inferred from contour area.
- **Model suggestions are untrusted:** Vision assistance is opt-in and sends the image to the configured provider. Suggestions are constrained to candidate IDs and known condition codes but may still be wrong. They are display-only and always require human review.
- **Production grading is disabled:** `/v1/inspect` always returns `UNDETERMINED`. Workmanship rules are provisional/unreviewed, and the repository has no labelled image set, inter-inspector agreement study, or measured false-accept rate.
- **Caller-supplied measurements are untrusted:** The rule gate checks structure, finite values, calibration flags, ROI IDs, derivation text, and mask-hash format. It cannot verify that those declarations came from a real image. The public API and JSONL runner cannot mark their measurements trusted.
- **No industrial image pipeline:** No camera calibration workflow, perspective correction, multi-joint tracking, board-level report, X-ray modality handling, or production storage is implemented.
- **No production deployment hardening:** Authentication, rate limiting, retention controls, service observability, and a provider SLA are not implemented. Do not expose this prototype as a public production service.

## Safety behavior

- Image quality checks report whether provisional thresholds were crossed, but do not certify an image as suitable for inspection.
- Model output is never converted into a numeric measurement or verdict.
- Grading remains `UNDETERMINED`, with explicit reason codes, until solder-specific measurements, human-reviewed thresholds, and independent validation exist.
- The model endpoint is called only when the user explicitly opts in. Otherwise the uploaded bytes are processed locally and are not persisted by the inspection route.

The project is not affiliated with, endorsed by, or certified against IPC-A-610 or J-STD-001. Any future rule or grade requires independent review and validation before operational use.
