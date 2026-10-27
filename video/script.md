# JointCheck demo video — 2:45

**Runtime:** exactly 165 seconds, seven shots. The timings are the edit and narration boundaries. `scripts/record-demo.ts` holds each corresponding screen for the same shot duration and normalizes its MP4 to 165 seconds; record narration to these boundaries in post. The capture is a silent screen recording, not evidence of a measured inspection.

## 1. Hook — show the boundary (00:00–00:20, 20s)
**Screen:** Open on the headline, “Explore the image. Withhold the verdict.” Hold long enough to read the prototype label.

**Voiceover:**
> In solder inspection, a confident label can be the riskiest output. JointCheck is an experiment in showing geometry while withholding a production verdict when the evidence is not there. Everything on screen is an explicitly synthetic schematic—not a board photo.

## 2. Three scenes — select a class example (00:20–00:45, 25s)
**Screen:** Scroll to the static canvas. Change the example selector to Class 1 and point to Joint A. Keep its “SIMULATED · NOT GRADED” label visible.

**Voiceover:**
> The offline canvas starts with three illustrative scenes. This selector changes the example class, not an inspection rule. Joint A is drawn as a shallow fillet, and its angle is entered scenario text; it was not measured from pixels or calibrated against a camera.

## 3. Joint C — geometry overlay, not a model output (00:45–01:10, 25s)
**Screen:** Move to Joint C and trace the cyan vector outline. Pause on the scenario input and neutral “NOT GRADED” label.

**Voiceover:**
> Joint C uses a cyan outline to make the geometry easy to discuss. The overlay is authored vector art, not segmentation output. A value above ninety degrees appears only as an illustrative input. The state remains simulated, not graded—so color or shape cannot be mistaken for ACCEPT or REJECT.

## 4. Local report — checksum, not a certificate (01:10–01:35, 25s)
**Screen:** Generate the illustrative HTML report. Show the resulting SHA-256 value. Do not edit the downloaded file or present a signature graphic.

**Voiceover:**
> Generate the local HTML report. It contains the three scenario descriptions and repeats that no inspection or IPC decision occurred. The browser computes a SHA-256 checksum over the exact bytes it downloads. That checksum can detect a changed file only when compared with a separately trusted copy; it is not a signature, provenance proof, or tamper-proof certificate.

## 5. Fail closed — missing evidence (01:35–02:00, 25s)
**Screen:** Scroll to “Not for production decisions.” Emphasize “UNDETERMINED” and the note that the static Pages demo has no backend.

**Voiceover:**
> Now the fail-closed boundary. The photo API has no trusted calibration source or pad-and-solder segmentation. Without trusted inputs, the correct state is undetermined. The static Pages build has no backend at all, so photo analysis is disabled here. There is no path from this demo to a production acceptance decision.

## 6. Limitations — name what is absent (02:00–02:25, 25s)
**Screen:** Hold on “Honest limitations.” Keep the data, rule, and edge-benchmark gaps readable.

**Voiceover:**
> This canvas is not a labelled dataset. No reviewed numeric rules, representative test set, measured accuracy, user study, or edge latency benchmark is available. We have not demonstrated standards compliance or validated against IPC-A-610. Those are evidence gaps, not implied results. Next comes controlled data collection, expert review, and independent validation.

## 7. Close — next milestone (02:25–02:45, 20s)
**Screen:** End on the JointCheck footer; leave the prototype scope visible.

**Voiceover:**
> JointCheck is a prototype for inspectable evidence and principled abstention. Try the offline scenes and inspect the HTML report, but do not use it to accept or reject hardware. The next milestone is trustworthy calibration and reviewed validation—not a stronger-sounding claim.

---

**Production note:** The current recorder does not synthesize or capture narration. No real joint photographs, user feedback, model calls, Sandbox runs, latency results, or standards validation are represented in this script. Add narration in an editor only if it can be timed to these boundaries without changing their total runtime.
