# Devpost submission draft — JointCheck

> Draft only. Verify the event's rules, track, team details, and deployment status before submitting. This text intentionally makes no field-test, benchmark, customer, or standards-compliance claims.

## Project name

**JointCheck — evidence-first solder inspection prototype**

## One-line summary

An experimental solder-workmanship interface that makes geometric evidence inspectable and abstains from production grades when trusted measurements are missing.

## Inspiration

Visual inspection software can look more certain than its inputs justify. JointCheck explores the opposite design choice: expose what the prototype can show, label illustrative material honestly, and make missing calibration or validation a visible limitation rather than an implied pass/fail result.

## What it does

The repository contains a React/Vite interface and a Python API prototype. The interface includes an offline static canvas with three synthetic, hand-authored vector schematics. Their angle and clearance annotations are scenario inputs, not measurements. A browser-only action downloads a self-contained HTML explainer and displays a SHA-256 checksum of its exact bytes. The checksum is useful for byte comparison against a separately trusted copy; it is not a digital signature, proof of origin, or tamper-proof certificate.

The separate photo-analysis path is experimental contour and image-quality tooling. It is not a trained joint detector, has no trusted camera calibration or pad/solder segmentation source, and does not make a production ACCEPT/REJECT decision. The static GitHub Pages build contains no backend, so live photo analysis is unavailable there.

## How it was built

- React and Vite provide the browser UI and static Pages build.
- Python and FastAPI provide a separately run experimental API.
- The Pages demo works without a network service: its diagrams and report are generated in the browser.
- Playwright automation is provided to capture the timed demonstration; Chromium and ffmpeg are required to produce the MP4.

No external model call or Nebius Sandbox run is claimed for this demo. Do not add those claims unless independently performed and documented.

## What is different

The prototype emphasizes the boundary between a visible contour and a trusted measurement. Its demonstration scenes are explicitly synthetic, its report is described as illustrative, and its UI surfaces the absence of calibration and validation. It is a workflow and safety-prototyping exercise—not a validated inspection product.

## Challenges and learnings

The main challenge is preserving uncertainty across the interface: a schematic must not resemble a captured inspection, a geometric overlay must not imply a model detection, and a checksum must not be marketed as a signature. A static frontend also cannot silently imply that the backend is hosted alongside it.

## What is next

With appropriate data governance and qualified reviewers: collect representative, consented and traceable images; establish camera calibration and measurement uncertainty; define and independently review any workmanship rules; evaluate against an expert-labelled holdout set; and run a documented hardware and security assessment. Until those steps are complete, the prototype should not be used to accept or reject assemblies.

## Evidence and links to add before submission

- Source repository: `https://github.com/knarayanareddy/jointcheck-solder-inspection`
- Demo URL: `https://knarayanareddy.github.io/jointcheck-solder-inspection/` (confirm that Pages deployment has completed before describing it as live)
- Video: `docs/media/jointcheck-demo.mp4` (generated only after running the recorder with Chromium and ffmpeg; do not link a missing file)
- Team, event track, screenshots, and any real feedback: fill in only with verified details.
