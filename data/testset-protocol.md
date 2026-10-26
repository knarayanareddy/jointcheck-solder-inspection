# Test-set protocol — JointCheck

**Tickets B-T04 (acquire), B-T15 (pass 1 labels), B-T30 (pass 2 + kappa), B-T24 (calibrate), B-T26 (batch eval).**

The test set is the product. Everything else — the CV pipeline, the rule table, the gate — is only as credible as
the data it is measured against. Budget a full day of a human's time here; do not delegate it entirely.

---

## 1. Targets

| Metric | Minimum | Target | Notes |
|---|---|---|---|
| Total joint images | **120** | **300** | Below 120, per-condition-code statistics are meaningless |
| Images with a calibration reference present | 60 | 180 | Required for any `requires_calibration: true` rule |
| Deliberately bad-quality images (blur / blown highlights / no scale) | **10** | 25 | These prove the abstention paths. Non-negotiable |
| Boards (multi-joint images) | 12 | 30 | Drives the golden-fixture tests |
| Condition codes with ≥5 examples | **8** | 16 | Any code below 5 is flagged `INSUFFICIENT` and gets **no** accuracy number |
| Independent labelers | **2** | 3 | Pass 1 and pass 2 must be blind to each other |
| Adjudicated disagreements with a written note | all | all | These notes become LIMITATIONS.md §human-ambiguity |

---

## 2. Acquisition — three sources, in priority order

### Source 1 (best): photograph your own boards
A team member, a phone in macro mode **or a €20–30 USB microscope**, a scrap PCB, a soldering iron, and one
afternoon produces ~100 images. This is the best source because:
- it is yours and unambiguously Apache-2.0 compatible,
- it is real (judges can smell stock imagery),
- it is **filmable** — the video can show the board being made and then graded,
- you can deliberately manufacture the failure modes you need.

**Deliberately produce, and label as such:**
| Condition | How to make it |
|---|---|
| Good joints (control) | Fresh tip, correct temp, flux-cored solder, clean pads |
| Insufficient wetting | Solder to an oxidised/unfluxed pad; too-cool iron |
| Cold / disturbed joint | Move the joint while it solidifies |
| Solder bridge | Bridge two adjacent 0805 pads deliberately |
| Icicle | Pull the iron away slowly from a through-hole joint |
| Excess solder | Feed too much solder |
| Insufficient volume | Starve the joint |
| Tombstoning | Uneven paste on a 0402/0603, reflow on a hot plate with a fast ramp |
| Solder balls / splash | Flick molten solder; use damp flux |
| Flux residue | Skip cleaning on a rosin-flux board |
| Component damage | Nip a capacitor body; over-torque a screw terminal |
| Lifted land | Overheat a pad and pull |
| Polarity mismatch | Fit a diode backwards |
| **Blurry** | Handheld, no brace, moving |
| **Blown highlights** | Ring light at full power, no diffuser |
| **No scale reference** | Nothing of known size in frame |
| **With calibration target** | The printed A4 target from B-T03 beside the board |
| **With coin reference** | A €0.05 coin (21.25 mm) in frame — the zero-cost calibration fallback |
| **With header-pitch reference** | A 0.1"/2.54 mm pin header in frame — the most natural fallback in a real shop |

**Photography protocol (write it into `data/testset/PHOTOGRAPHY.md`):**
- fixed working distance where possible; perpendicular to the board; diffuse light, no direct specular source
- save RAW or maximum-quality JPEG; **never** apply beautification, sharpening or HDR — it invalidates the blur metric
- record per image: camera, focal length, aperture, whether flash, whether target present, distance estimate
- include one image of the calibration target **alone** at every working distance used, so the mm/px curve can be
  validated

### Source 2: openly licensed public datasets
Search for PCB / solder-joint defect image datasets. **Check the licence of each before use:**
- `CC0` or `CC-BY` → fine to redistribute in an Apache-2.0 repo, with attribution
- `CC-BY-NC` / research-only → **do not redistribute.** Ship a `scripts/fetch_testset.py` that downloads it at
  build time plus a `.gitignore` entry, and state the licence position in `data/testset/SOURCES.md`
- unknown licence → do not use
Never upload a dataset you cannot licence into a public repo that a sponsor's judges will inspect.

### Source 3: a legally held copy of the standard
If a teammate's employer holds an IPC-A-610 licence, that person may **confirm clause numbers and threshold
direction** and set `verified_against_primary_source: true` with their name and edition. They may **not** copy
text or photographs into the repo. This is the single largest credibility upgrade available to this project —
ask your network on Sunday.

---

## 3. Labelling protocol (double-blind)

**Pass 1 — `data/testset/labels.pass1.csv`** (ticket B-T15)
**Pass 2 — `data/testset/labels.pass2.csv`** (ticket B-T30, a **different** labeler who has not seen pass 1)

| Column | Type | Notes |
|---|---|---|
| `image_id` | str | filename stem |
| `board_id` | str\|null | if the image is part of a multi-joint board |
| `roi_hint` | str\|null | rough location, e.g. "top-left 0805 cap" — helps pass 2 find the same joint |
| `joint_type` | enum | from `schemas/core-schemas.json` |
| `condition_code` | enum | from `data/condition-codes.json`; `NO_DEFECT_DETECTED` is a valid label |
| `expected_verdict_class1` | enum | ACCEPT / PROCESS_INDICATOR / REJECT / UNDETERMINED |
| `expected_verdict_class2` | enum | |
| `expected_verdict_class3` | enum | |
| `calibration_present` | bool | |
| `image_quality_usable` | bool | the labeler's judgement, independent of the CV blur metric |
| `labeler` | str | |
| `labeler_role` | str | e.g. "production lead, 12 yrs", "CS student, no electronics background" — **role matters**, see §5 |
| `labelled_at` | ISO-8601 | |
| `confidence` | 1–5 | self-rated |
| `notes` | str | free text |

**Rules for labelers:**
1. Label the **condition** first, then the verdict per class. Never look at the other pass.
2. If you cannot decide, label `UNDETERMINED`. Do not guess. An `UNDETERMINED` label is data, not failure.
3. Record your confidence. Low-confidence labels get adjudicated first.
4. Do **not** look at any model output while labelling. Contamination invalidates kappa.

**Adjudication:** for every disagreement, the two labelers discuss and record:
`adjudicated_condition_code`, `adjudicated_verdict_class{1,2,3}`, `agreement_reached (bool)`,
`disagreement_note` (why they differed), `ambiguity_class ∈ {visual_ambiguity, class_boundary_ambiguity,
standard_ambiguity, insufficient_image_quality}`.

> **The disagreement notes are one of the most valuable artifacts in this project.** They show, with evidence,
> *where the standard is ambiguous even to trained humans* — which is exactly the kind of insider finding
> Suchismita asked for ("what did you learn about the problem that someone outside it wouldn't know?") and
> exactly the "honesty about what hasn't been done" she said she looks for. Put a table of them in the README.

---

## 4. Agreement statistics

Compute and publish in `data/testset/kappa.json` and `docs/EVAL.md`:

| Statistic | Method | Interpret to publish |
|---|---|---|
| Cohen's kappa — `condition_code` | 2 raters, nominal | Report with the 95% CI if n allows |
| Cohen's kappa — verdict per class (1, 2, 3) | separate | **Expect kappa to fall as class rises.** If it does, that is a finding: higher classes are harder for humans too |
| Percent agreement | raw | Report alongside kappa; never instead |
| Krippendorff's alpha (optional) | if 3 raters | |
| Per-code agreement | breakdown | Which conditions do humans disagree about most? Publish the top 5 |

Report kappa honestly even if it is low (e.g. 0.55). A low kappa **with an explanation** ("class-3 boundaries on
insufficient-wetting are genuinely ambiguous; here are the 14 disagreement notes") is far stronger than a high
kappa with no analysis, because it demonstrates you understand where the problem is hard.

---

## 5. Why labeler role must be recorded

Include at least one labeler with **production experience** and one **without**. The gap between them is a
measurable, publishable result:

> "On the same 300 joints, an experienced inspector and a novice agreed on 62% of condition codes
> (κ = 0.48), but on 91% of *class-3 verdicts* once the borderline cases were excluded. The disagreement
> concentrated in four conditions: insufficient wetting, excess solder, flux residue, disturbed joint."

That sentence is an original empirical finding about the problem space, produced in one day, that no other
submission in this hackathon will have. It directly serves Potential Impact *and* Quality of the Idea.

---

## 6. Evaluation metrics (ticket B-T26)

Per class (1, 2, 3) and per condition code:

- Confusion matrix over `{ACCEPT, PROCESS_INDICATOR, REJECT, UNDETERMINED}`
- Precision / recall / F1 for REJECT specifically (the operationally important class)
- **False-accept rate at Class 3** — a labelled REJECT graded ACCEPT. This is *the* number for a
  high-reliability audience, and it is the headline of the A/B experiment (B-T23)
- False-reject rate (a labelled ACCEPT graded REJECT) — the cost of over-strictness, i.e. scrap
- Abstention rate, and abstention **appropriateness**: of the abstentions, how many were on images the humans
  also labelled `image_quality_usable=false` or `UNDETERMINED`? A high appropriateness rate proves the system
  abstains for the right reasons
- Mean and p95 latency per stage; tokens (text and **image** separately); cost per board
- Calibration recovery error: |measured mm/px − true mm/px| / true, distribution across the calibrated subset

**Flag any condition code with <5 examples as `INSUFFICIENT` and publish no accuracy number for it.** Publishing
a 100% accuracy on n=2 is the kind of thing that makes a judge distrust everything else you claim.

---

## 7. Acceptance test for B-T04

```bash
python scripts/check_testset.py \
  --min-images 120 --min-calibrated 60 --min-bad 10 \
  --min-boards 12 --min-codes-with-5 8 --require-sources-doc
```
Must exit 0 and print a composition table. Fails loudly if:
- fewer than the minimums
- any image lacks a `SOURCES.md` row with a licence
- fewer than 10 deliberately-bad images
- fewer than 8 condition codes with ≥5 examples

---

## 8. Storage & licensing hygiene

- Images >5 MB: use Git LFS **or** a `scripts/fetch_testset.py` + `.gitignore`. Do not bloat the repo — a judge
  cloning it has limited patience and the 128 MB snapshot cap matters.
- `data/testset/SOURCES.md` columns: `image_id | origin | url_or_method | licence | redistributable (bool) |
  appears_in_video (bool) | notes`
- **Any image that appears in the video must be `redistributable=true`.** Check this before editing, not after.
- No identifiable faces, no company logos, no customer board artwork, no serial numbers of real products in any
  published image. Crop or blur them. Video rules forbid unlicensed third-party marks and this is the easy place
  to violate them accidentally.
