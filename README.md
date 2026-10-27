# JointCheck — experimental solder-photo inspection prototype

JointCheck is an early, safety-first prototype for image-assisted solder-workmanship review. It accepts JPEG/PNG photos, computes basic OpenCV image-quality metrics, and proposes geometric contour regions. The geometry library can measure explicitly supplied masks, but the photo route does not yet segment pads or solder. An optional Nebius-compatible vision-model request can suggest candidate joint types and known condition codes—but only after explicit user opt-in. **Production grading remains disabled.**

> **Safety:** This prototype always reports `UNDETERMINED` for production grading. The checked-in workmanship thresholds are provisional and unreviewed; contour boxes are not confirmed joints, model suggestions are not verified evidence, and the project has no labelled image evaluation set. Do not use it to release or reject production assemblies. It is not affiliated with, endorsed by, or certified against IPC-A-610 or J-STD-001.

## Calibration status — no class-sensitivity proof yet

- **Labelled evaluation images checked in:** 0 (`data/testset/` is absent).
- **Human-reviewed numeric rules:** 0 (all checked-in rules remain provisional/unreviewed).
- **Validated class-sensitivity results:** not available. The requested 85° Class-2/Class-3 example is an unverified proposed threshold, not an observed evaluation result.

The current rule table, frozen measurement vocabulary, and inspection inputs do not yet agree on the requested metrics. These figures intentionally report the present evidence state rather than implying calibration.

## Current capabilities

| Component | What it does | What it does not do |
|---|---|---|
| Photo intake | Accepts JPEG/PNG up to 10 MiB, verifies basic signature/decode, hashes the original bytes | Persist uploads or perform calibrated image correction |
| OpenCV | Reports provisional blur/exposure checks and unclassified contour candidates; the geometry library accepts explicit masks and references for deterministic measurements | Segment pads/solder from uploaded photos, identify joints reliably, or produce production-validated measurements |
| Optional model assistance | On explicit opt-in, sends the photo to the configured vision endpoint; restricts responses to candidate IDs and known condition codes | Issue verdicts, create measurements, or bypass human review |
| Production grading | Always returns `UNDETERMINED` with reasons | Accept/reject production joints |
| API/UI | Exposes photo analysis plus runtime status and an upload/results UI | Claim validated or production-ready inspection |
| JSONL runner | Applies the fail-closed rule gate to caller-provided records | Trust caller-created measurements or return actionable grades |

The image-quality thresholds and contour filters are exploratory, not calibrated. The rule table has no production-reviewed rules. The gate's unit tests include a temporary reviewed rule only to test comparison logic; it is not shipped as an active rule.

## Quick start

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+ and npm. No API key is needed for local CV analysis.

```bash
# From the repository root
make sample    # offline gate/schema tests and synthetic JSONL example
make check     # Ruff, backend/API/schema tests, and frontend production build
make demo      # starts the API at http://localhost:8000
```

In a second terminal, run the upload UI while `make demo` is running:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies requests through relative `/health` and `/v1/*` paths to the backend. The photo-upload flow runs OpenCV locally in the backend. No photo is sent to a model unless the user checks **Request optional model suggestions**.

## Static GitHub Pages demo

The static demo is configured to deploy from `main` via `.github/workflows/deploy-pages.yml` to `https://knarayanareddy.github.io/jointcheck-solder-inspection/`. It has no backend: photo inspection is explicitly unavailable there. The three offline vector scenes are synthetic, their labels are illustrative scenario inputs, and they are never graded. The browser-generated HTML file is an illustrative report, not an inspection certificate; its SHA-256 is a byte checksum, not a digital signature or tamper-proof seal.

Build the static site locally with:

```bash
make build-pages
cd frontend
npm run preview -- --host 0.0.0.0 --port 4173
```

Open `http://localhost:4173/jointcheck-solder-inspection/`. The Pages workflow uploads `frontend/dist`; a deployment occurs only after the workflow runs on `main` or is manually dispatched.

## Demo recording

`scripts/record-demo.ts` uses Playwright to capture the seven-shot, 165-second screen demo and ffmpeg to encode `docs/media/jointcheck-demo.mp4`. In separate terminals, start the frontend preview above and run:

```bash
cd frontend && npx playwright install chromium
# Install ffmpeg/ffprobe using your operating system's package manager.
cd .. && make record-demo
```

The recording contains screen video only; narration must be recorded separately to `video/script.md`'s timing. Browser and ffmpeg were not included as part of the static build. Set `JOINTCHECK_DEMO_URL` only if previewing from a different URL.

## Photo-inspection API

`POST /v1/inspect?product_class=2&model_assist=false` accepts the raw bytes of a JPEG or PNG with the matching `Content-Type`. It returns the image hash/dimensions, provisional quality metrics, contour proposals and an always-abstaining grading object. Uploads are limited to 10 MiB and 40 megapixels.

Example:

```bash
curl -X POST 'http://localhost:8000/v1/inspect?product_class=2' \
  -H 'Content-Type: image/jpeg' --data-binary @macro-photo.jpg
```

Optional vision assistance requires `NEBIUS_API_KEY` and a configured `MODEL_VISION`/`NEBIUS_BASE_URL`. The caller must explicitly set `model_assist=true`; this sends the image to the configured service. Model output is advisory, allow-listed, and never used for grading. Provider credentials and API compatibility are not verified by the offline test suite.

## Gate API and JSONL runner

`POST /v1/gate/evaluate` and `jobs/run_gate_batch.py` accept measurement assertions, but treat caller-provided measurements as untrusted. They cannot emit an actionable verdict. Only a future internal, trusted measurement pipeline could call the pure gate with trusted provenance; even then it would require a reviewed rule and validation evidence.

```bash
make batch INPUT=data/sample-gate-request.jsonl
python jobs/run_gate_batch.py path/to/requests.jsonl --output results.jsonl
```

The included `jobs/Dockerfile` packages this local JSONL gate runner. It is not a Nebius Serverless Job deployment.

## Development checks

- `make sample` runs offline gate/schema tests and a synthetic assertion.
- `make check` runs Ruff and backend/API/CV/schema tests, then builds the React UI.
- `make test` runs the backend test suite.

The tests use synthetic images and a mocked model response. They do not validate real-world image detection, standards compliance, model-provider connectivity, or workmanship accuracy.

## Repository map

- `backend/app/vision/` — image-quality features, contour candidates, and mask-driven geometric measurement functions
- `backend/app/tf/vision.py` — explicit, optional vision-model suggestions
- `backend/app/gate/` — fail-closed numeric rule evaluator
- `backend/app/main.py` — FastAPI health, photo inspection, and gate routes
- `backend/tests/` — synthetic API, CV, model-contract, gate, telemetry, and schema tests
- `data/workmanship-rules.v0.json` — provisional, unreviewed seed rules
- `frontend/` — prototype photo upload and evidence display
- `jobs/run_gate_batch.py` — local JSONL gate runner
- `SPEC.md` — aspirational product specification; items described there are not necessarily implemented
- `LIMITATIONS.md` — current scope and safety boundaries
