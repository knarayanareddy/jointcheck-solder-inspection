# Devpost submission — JointCheck

## Project name

**JointCheck — Evidence-First Solder Inspection Prototype**

## Tagline

**Show the geometry. Keep synthetic fixture labels separate from real inspection results.**

## Project description

Visual inspection software can look more certain than its evidence supports. JointCheck is an experimental interface for exploring how inspection evidence and uncertainty might be presented without implying production readiness.

The static GitHub Pages demo offers three hand-authored SVG scenarios and an HTML report generated in the browser. Green `ACCEPT` and red `REJECT` strings on the cards are explicitly scripted expected labels in a synthetic UI test-fixture profile. They are not calculated from an image, measurements, calibrated thresholds, workmanship rules, or the separate photo-analysis API. The diagrams are not photographs, and the labels do not represent IPC-A-610 decisions or production verdicts.

The separate Python API prototype performs preliminary image-quality calculations and contour proposals. It does not have trusted camera calibration or pad-and-solder segmentation and does not issue production grades. The GitHub Pages frontend has no backend, so its photo-analysis controls are unavailable.

The browser-generated HTML report includes the fixture descriptions and repeats these limits. Its SHA-256 value is a checksum of the exact bytes downloaded; it is not a digital signature, proof of origin, or tamper-proof certificate.

## How it was built

- React and Vite for the browser UI and offline static site.
- Python and FastAPI for the separately run experimental API.
- Playwright for timed screen capture; ffmpeg/ffprobe encode and verify the 2:45 MP4.

No external model call, Nebius Sandbox run, performance benchmark, user study, or real-board evaluation is claimed for this submission.

## What we learned

A prototype can show geometry without presenting a vector overlay as a model detection. Explicitly calling green and red words “test fixture expectations” helps distinguish software test data from measured outcomes. The static site also makes the backend boundary visible instead of implying that photo analysis is hosted with the frontend.

## What comes next

A future inspection study would require appropriate data governance, representative labelled board images, trusted camera calibration, defined measurement uncertainty, qualified review of workmanship rules, an independent holdout evaluation, and a documented hardware assessment. Until then, JointCheck is not suitable for accepting or rejecting assemblies.

## Project links

- **Live static demo:** https://knarayanareddy.github.io/jointcheck-solder-inspection/
- **Source repository:** https://github.com/knarayanareddy/jointcheck-solder-inspection
- **Demo video (silent screen recording, 2:45):** [`docs/media/jointcheck-demo.mp4`](media/jointcheck-demo.mp4)
- **Narration script:** [`video/script.md`](../video/script.md) (voiceover is not included in the MP4).

Fill any event-specific track or team fields using verified details from the actual submission; none are assumed here.
