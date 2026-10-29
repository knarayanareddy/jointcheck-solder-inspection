# JointCheck demo video — 2:45

**Runtime:** exactly 165 seconds across seven shots. The recorder holds each corresponding screen for the listed duration and normalizes the MP4 to 165 seconds. Record narration to these boundaries in post. The MP4 is silent screen video; it is not a real inspection recording.

## 1. Hook — evidence before confidence (00:00–00:20, 20s)
**Screen:** Open on “Explore the image. Withhold the verdict.” Hold the prototype scope label.

**Voiceover:**
> Solder inspection tools should not sound more certain than their evidence. JointCheck is a prototype for making geometry visible while refusing production decisions when trusted measurements are absent. This walkthrough uses only authored vector fixtures—not board photos.

## 2. Joint A — scripted fixture expectation (00:20–00:45, 25s)
**Screen:** Scroll to Joint A, change the example selector to Class 1, and hold on its green `ACCEPT` expected UI label beside the in-card “SYNTHETIC FIXTURE · NOT AN INSPECTION RESULT” notice.

**Voiceover:**
> Joint A is an authored shallow-fillet schematic. Its green ACCEPT badge is a scripted expectation stored in the synthetic UI fixture profile. It is not computed from an image, a calibrated angle, or a workmanship rule. The profile explicitly says calibration is off and inspection grading is disabled.

## 3. Joint C — contrast without an inspection verdict (00:45–01:10, 25s)
**Screen:** Change the example selector to Class 3, move to Joint C, and trace its cyan vector outline. Keep the red `REJECT` expected UI label beside the in-card synthetic-fixture notice visible.

**Voiceover:**
> Joint C is a second authored vector, named for an excess-solder scenario. Its red REJECT badge is also fixture metadata only. The shape is not a captured joint, the outline is not segmentation, and there is no measurement behind the label. Color demonstrates the interface state; it does not certify a board.

## 4. HTML report — checksum, not a certificate (01:10–01:35, 25s)
**Screen:** Generate and download the self-contained HTML report. Show the checksum displayed in the page and the report’s fixture-only warning.

**Voiceover:**
> The browser exports a local HTML fixture report. It records the three scripted display labels and says clearly that no inspection or calibration occurred. SHA-256 is computed over the exact bytes downloaded. It can reveal a byte change when compared with a separately trusted checksum, but it is not a signature, proof of origin, or tamper-proof certificate.

## 5. Fail closed — static Pages has no backend (01:35–02:00, 25s)
**Screen:** Scroll to “Not for production decisions” and the service status. Emphasize that photo inspection is unavailable on the static Pages site.

**Voiceover:**
> The live static site has no analysis backend. Photo inspection is disabled here. In the separate experimental API, trusted calibration and pad-and-solder segmentation are absent, so this prototype does not issue production grades. The green and red words on the fixture cards never flow into that API or its rule gate.

## 6. Limits — identify the evidence gap (02:00–02:25, 25s)
**Screen:** Hold on “Honest limitations.” Keep the missing data, reviewed-rule, and edge-benchmark statements visible.

**Voiceover:**
> These vectors are software test fixtures, not an evaluation set. There are no labelled real-board images, reviewed numeric workmanship rules, measured accuracy results, user-study findings, or edge-latency benchmarks to report. The interface makes no IPC-A-610 compliance claim. Those are open validation tasks, not evidence we can infer from a demo.

## 7. Close — next milestone (02:25–02:45, 20s)
**Screen:** End on the JointCheck footer and keep prototype scope visible.

**Voiceover:**
> JointCheck demonstrates an interface pattern, not an inspection capability. Use the offline page to explore its synthetic fixtures and report. Do not use it to accept or reject hardware. The next milestone is trusted calibration and independent review of real labelled data.

---

**Production note:** This script represents no real board images, user feedback, model calls, Sandbox runs, performance numbers, or standards validation. Do not remove the fixture disclaimer or edit its expected labels into inspection outcomes.
