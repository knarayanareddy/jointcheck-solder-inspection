# SPEC — "JointCheck": grade a solder joint against the real standard, and prove it

**Idea B · Track: Best Apps and Agents** (move to **Physical AI** if you add the microscope rig — see §14)
**Version:** 1.0 · 26 Oct 2026 · **Build window:** Sun 26 Oct → Thu 30 Oct 2026, 19:00 CEST
**Role in the portfolio:** the designated **pivot** for Idea A if Safety Gate ingestion fails by Sun 20:00.

> Read `_shared/agent-delegation-protocol.md` before dispatching any ticket.

---

## 1. Executive brief

### One-sentence pain
> *"I've got a 400-board run and one inspector. She's been at it since six, and by two o'clock she's passing
> joints she'd have rejected this morning. Nobody can tell me afterwards why board 217 was scrapped."*

### Persona
**Marc**, 51, production lead at a 12-person electronics contract manufacturer. Builds small runs of control
boards. Two trained inspectors, both nearing retirement. Scrap and rework are his margin. He has heard of
IPC-A-610 — his customers demand it — but he cannot put a trained inspector on every joint, and he cannot prove
*why* a board was accepted or rejected when a customer complains six months later.

Secondary persona: **an apprentice or hobbyist** who wants to know whether their hand-soldering is actually
acceptable, and against *which* class.

### The 30-second hook
> Drop a macro photo of a solder joint (or a phone video frame from a board).
> Two seconds later: a red box on the third joint, and above the fold —
> **"REJECT at Class 3 — insufficient solder wetting on J3. Fillet coverage 41% (Class 3 requires ≥75%).
> Class 2 would accept this joint."**
> A slider beneath: **Class 1 / Class 2 / Class 3** — and the verdict changes live as you drag it.
> Then: **"Download the inspection report"** — a printable per-joint record with citations.

### One takeaway
**A photograph can be graded against a written workmanship standard, with the measurement taken by code rather
than by the model's opinion — and the grade flips when the reliability class changes.**

### The named insider insight (say this in the video)
> **The same joint can be a pass and a fail.** Workmanship acceptance is not a property of the joint — it's a
> property of the joint *and the reliability class the product is built to*. Class 1 (general electronic
> products), Class 2 (dedicated service electronics) and Class 3 (high-reliability, medical/aerospace/military)
> accept different amounts of the same defect. Every "AI solder inspection" demo treats acceptability as
> binary. It isn't. **And a second, harder truth: you cannot measure a fillet without a scale.** Any system
> that reports a wetting percentage from an uncalibrated photo is reporting a hallucination with a decimal point.

Both halves are things an intelligent outsider would not guess, and both are demonstrable on camera.

### Why this wins against this specific field
- **Zero of 833 competitor repos** do workmanship inspection. `data/competitor-subset.csv` (41 rows) contains
  the nearest neighbours — `Wire-Harness-Robot-2` and `Harness-lab` (harness *assembly* and coding-agent
  *harnesses*, not inspection), `flawcheck` (ultrasonic NDT on thickness CSVs — closest cousin, different
  modality), `sieve` (biomedical equipment repair), `nationals` (VEX robotics control). Nobody grades a
  photograph against a written standard.
- It is **inherently filmable**: macro photography, red boxes on real defects, a slider that changes the verdict.
  Design is 25% and this idea scores it for free.
- The gate is **not a conceit** — measurements genuinely must come from pixels, and the class genuinely must come
  from the user. Abstention is genuinely the right answer on a blurry photo.
- **Manufacturing/industrial is the emptiest cluster in the entire hackathon** (1 of 833 repos).

### Legal / IP integrity note — read before anything else
`IPC-A-610` and `J-STD-001` are **trademarked standards owned by IPC and by IPC/WHMA**; the full text is paid.
You must **not**:
- reproduce substantial verbatim text or the official accept/reject photographs,
- imply endorsement or certification by IPC,
- claim your rule IDs are IPC clause numbers unless you have actually verified them from a legally held copy.

You **must**:
- use your own stable rule IDs (`JC-WET-001`), with a `source` field recording where the criterion came from
  (a publicly available training deck, a textbook, a standards body's free summary, your own validated
  measurement), a `source_url`, a `retrieved_at` and a `verbatim_quote` **only where the source is openly
  licensed**,
- state plainly in the README, the artifact footer and the video: *"an independent tool aligned to publicly
  documented electronics workmanship criteria. Not affiliated with, endorsed by, or certified against
  IPC-A-610 or J-STD-001."*
- if a teammate legally holds a copy of the standard (employer licence), they may confirm clause numbers — and
  then you record `verified_against_primary_source: true` with their name and the edition. **That is a huge
  credibility win and it is legal.** Ask your network on Sunday.

---

## 2. Success criteria mapped to the four judging criteria

| Criterion | How JointCheck earns it | Measurable target |
|---|---|---|
| **Technological Implementation (25%)** | Vision model + Nemotron tiers; a **classical CV measurement pipeline** (OpenCV) that produces the numbers the gate checks; **Sandbox branching** for the gate-on/gate-off experiment; **Sandbox network-off** validation of the generated PDF report; Serverless Job for the 300-joint eval batch; complete token/cost ledger | Ledger ≥95% coverage; A/B delta published; every reported measurement traceable to a pixel computation, never to prose |
| **Design (25%)** | The photo *is* the UI; verdict above the fold; the **Class slider** is the centrepiece interaction; overlay boxes with handles; annotated thumbnails in the report; custom "inspection bay" design system | Stranger reaches the verdict in ≤45 s; the class slider visibly changes the verdict |
| **Potential Impact (25%)** | Rework/scrap cost is a hard number; **≥3 real conversations** (a contract manufacturer, an inspector, an apprenticeship trainer); **300-joint eval with double labelling and Cohen's kappa**; a stated false-accept rate at Class 3 | n≥300 joints, kappa reported, per-class P/R/F1 published, INSUFFICIENT classes flagged |
| **Quality of the Idea (25%)** | The class-relativity insight + the calibration insight; abstention on uncalibrated/blurry input; **zero competitors** | Both insights stated in README and video; abstention demonstrated on camera |

---

## 3. Architecture

```
  drop a photo / video frame / pick a sample
        │
        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S1 ingest_image     normalise, EXIF, orientation, blur metric,              │
 │                     CALIBRATION CHECK  ◄── the make-or-break stage          │
 │                       • printed calibration target in frame? → mm/px        │
 │                       • known reference object (coin, 2.54mm header pitch)?  │
 │                       • user-supplied mm/px?                                │
 │                       • none of the above → calibrated=false                │
 │                     Output: ImageContext{pixels, mm_per_px|null, blur, dpi} │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S2 propose_rois     CLASSICAL CV FIRST (OpenCV, deterministic, free):       │
 │                     adaptive threshold → contours → pad/hole/paste geometry │
 │                     → candidate joint boxes with a shape prior              │
 │                     Vision model then CONFIRMS/REJECTS boxes and names the  │
 │                     joint type (through-hole, SMD gull-wing, BGA, wire,     │
 │                     terminal, hand-soldered pad)                            │
 │                     Output: [JointROI{id, bbox, type, confidence}]          │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S3 measure          PURE CV. No LLM. Per ROI compute:                       │
 │                     fillet_area_mm2, wetting_angle_deg, solder_coverage_pct,│
 │                     bridge_gap_mm, icicle_length_mm, ball_diameter_mm,      │
 │                     tombstone_lift_deg, insulation_clearance_mm,            │
 │                     flux_residue_area_pct, void_fraction,                   │
 │                     sharpness (Laplacian var), exposure (histogram)         │
 │                     EVERY number carries its pixel derivation + the         │
 │                     mm_per_px used. Unmeasurable → value=null + reason.     │
 │                     Output: Measurements[] (registered as citations,        │
 │                             kind=measurement, ttl=null)                     │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S4 classify         Nemotron NANO, JSON schema, one call per ROI batch:     │
 │                     given the joint type + the MEASURED numbers + a cropped │
 │                     image → candidate condition codes from the controlled   │
 │                     vocabulary (never free text). May add conditions the CV │
 │                     can't measure (disturbed joint, component damage,       │
 │                     lifted land) but MUST mark them measurement_basis=      │
 │                     "visual_only" with a confidence.                        │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S5 class_rule       DETERMINISTIC RULE LOOKUP (pure Python, no LLM):        │
 │                     (condition_code, joint_type, measurement, class)        │
 │                       → ACCEPT | PROCESS_INDICATOR | REJECT | UNDETERMINED  │
 │                     from data/rules/workmanship-rules.json                  │
 │                     This is where the Class 1/2/3 relativity lives.         │
 │                     Re-running this with a different class is O(1) and free │
 │                     → THAT is why the slider is instant.                    │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S6 gate             • every REJECT cites a rule_id that exists AND is       │
 │                       loaded (unverified rules excluded)                    │
 │                     • every numeric threshold comparison uses a value from  │
 │                       S3, never from model prose                            │
 │                     • if calibrated=false and the rule needs a measurement  │
 │                       → UNDETERMINED, reason="uncalibrated"                 │
 │                     • if blur < floor or exposure clipped → UNDETERMINED,   │
 │                       reason="image_quality_insufficient"                   │
 │                     • if class_rule returns UNDETERMINED → route to human   │
 │                     Determinism asserted by hash.                           │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ S7 report           TOKEN FACTORY SANDBOX:                                  │
 │                     image = rules table + validator + report template +     │
 │                             WeasyPrint + the annotated crops                │
 │                     generate a printable per-board inspection report (PDF): │
 │                       header (board id, inspector, class, timestamp, tool   │
 │                       version, rules-table version hash), per-joint rows    │
 │                       with thumbnail + overlay + measurement + rule +       │
 │                       verdict, a summary block, the abstentions listed       │
 │                       separately, and the disclaimer footer                 │
 │                     then run validate.py with the GUEST NETWORK DISABLED    │
 │                     download bytes, sha256 locally, compare                 │
 └─────────────────────────────────────────────────────────────────────────────┘

 CROSS-CUTTING: citation registry · ledger (runs/ledger.jsonl) · rules-table version hash

 A/B LANE (Sandbox branching):
   one immutable image(rules + 300-joint test set)
     ├─ branch gate_on  → false-accept rate at Class 3
     └─ branch gate_off → model verdict used directly → false-accept rate at Class 3
   publish the delta. THIS IS THE HEADLINE NUMBER.

 BATCH LANE (Nebius Serverless Job):
   300 labelled joints → S1..S6 → confusion matrix per class, kappa, latency, cost
```

### Component justification (Jackie's test — cut anything that fails)

| Component | Serves the 30-second hook? | Verdict |
|---|---|---|
| Calibration check | **Yes — it's half the insight** | Keep |
| Classical CV measurement | **Yes — it's why the numbers are trustworthy** | Keep |
| Class slider | **Yes — it's the centrepiece** | Keep |
| PDF report in Sandbox | Yes — "download the inspection report" is the action | Keep |
| Branch A/B | Yes — proves the gate | Keep |
| Live camera stream | No — a photo is enough | **CUT** (Next Steps) |
| ONNX edge deployment | Only if going Physical AI | Conditional (§14) |
| User accounts / board history DB | No | **CUT** |
| AOI hardware integration (Gerber, pick-and-place) | No | **CUT** (Next Steps) |
| Training/fine-tuning a custom detector | Only if time remains | **Optional stretch** (§14) |

---

## 4. Data model

Authoritative prose here; machine-checkable contract in `schemas/core-schemas.json`.

### 4.1 `ImageContext` (S1)
`id, source (upload|fixture|video_frame), sha256, width, height, dpi, orientation_corrected, blur_laplacian_var, exposure_clipped_pct, calibrated (bool), calibration_method ∈ {printed_target, reference_object, user_supplied, none}, mm_per_px (float|null), calibration_evidence (quote/path), notes`

### 4.2 `JointROI` (S2)
`id, bbox{x,y,w,h}, joint_type ∈ {through_hole, smd_gull_wing, smd_rectangular, bga, j_lead, wire_terminal, hand_pad, connector_pin, other}, detection_basis ∈ {cv_contour, vision_model, both}, confidence, crop_sha256, crop_path`

### 4.3 `Measurement` (S3) — the trust core
```
{ "id": "m_01J…", "roi_id": "j_03", "quantity": "solder_coverage_pct",
  "value": 41.3, "unit": "%", "mm_per_px_used": 0.0182,
  "derivation": "adaptive-threshold mask of solder region ∩ pad annulus / pad annulus area, from crop 412×388 px",
  "pixel_evidence": {"mask_sha256":"…","overlay_path":"runs/overlays/j_03_coverage.png"},
  "computable": true, "not_computable_reason": null }
```
Quantities: `fillet_area_mm2, wetting_angle_deg, solder_coverage_pct, solder_volume_ratio, bridge_gap_mm,
icicle_length_mm, solder_ball_diameter_mm, tombstone_lift_deg, insulation_clearance_mm, wire_strand_exposure_mm,
flux_residue_area_pct, void_fraction, joint_height_mm`.
**Rule:** `value=null` with a `not_computable_reason` is a valid, honest output. A guessed number is not.

### 4.4 `ConditionFinding` (S4)
`id, roi_id, condition_code (from the controlled vocabulary — never free text), measurement_basis ∈ {measured, visual_only}, supporting_measurement_ids[], confidence, model, ledger_id`

Controlled vocabulary (`data/condition-codes.json`): `INSUFFICIENT_WETTING, EXCESS_SOLDER, INSUFFICIENT_SOLDER_VOLUME,
EXCESSIVE_FILLET, SOLDER_BRIDGE, ICICLE, SOLDER_BALL_SPLASH, TOMBSTONING, HEAD_IN_PILLOW, DISTURBED_JOINT,
WICKING, LIFTED_LAND, PAD_DELAMINATION, COMPONENT_DAMAGE, INSULATION_CLEARANCE_VIOLATION, WIRE_STRAND_DAMAGE,
FLUX_RESIDUE_EXCESSIVE, VOIDING_EXCESSIVE, COLD_JOINT_APPEARANCE, NON_WETTING, WEBBING, SOLDER_MASK_VIOLATION,
POLARITY_MARKING_MISMATCH, NO_DEFECT_DETECTED, OTHER_UNCLASSIFIED`.

### 4.5 `RuleVerdict` (S5)
`id, roi_id, condition_code, class ∈ {1,2,3}, verdict ∈ {ACCEPT, PROCESS_INDICATOR, REJECT, UNDETERMINED}, rule_id, threshold_expression, measured_value, threshold_value, comparison, citation_ids[], rules_table_version_hash`

`PROCESS_INDICATOR` is the real-world middle grade (a condition that is not a defect but signals a process
problem). Including it is a credibility signal — an outsider would invent only pass/fail.

### 4.6 `BoardReport` (S6/S7)
`report_id, board_id, image_context, rois[], measurements[], condition_findings[], rule_verdicts[], class,
gate{checks_run, checks_passed, rejected_claims[], abstentions[], determinism_hash},
summary{total_joints, accept, process_indicator, reject, undetermined, reject_rate},
artifact{sha256, bytes, sandbox_image_uuid, sandbox_operation_id, network_disabled_during_validation:true},
cost, timings_ms, disclaimer, rules_table_version_hash`

### 4.7 `Rule` (`data/rules/workmanship-rules.json`)
```
{ "rule_id": "JC-WET-001",
  "condition_code": "INSUFFICIENT_WETTING",
  "applies_to_joint_types": ["smd_gull_wing","through_hole"],
  "title": "Solder must wet and flow over the pad and lead, with a concave fillet",
  "class_thresholds": {
     "1": {"metric":"solder_coverage_pct","op":">=","value":50,"verdict_if_met":"ACCEPT"},
     "2": {"metric":"solder_coverage_pct","op":">=","value":65,"verdict_if_met":"ACCEPT"},
     "3": {"metric":"solder_coverage_pct","op":">=","value":75,"verdict_if_met":"ACCEPT"}
  },
  "verdict_if_not_met": "REJECT",
  "requires_calibration": true,
  "image_quality_floor": {"blur_laplacian_var": 60, "exposure_clipped_pct_max": 8},
  "source": {"kind":"public_training_material|textbook|standards_summary|own_validated_measurement|primary_standard_copy",
             "reference":"…","url":"…","retrieved_at":"…","verbatim_quote_if_openly_licensed":null,
             "verified_against_primary_source": false, "verified_by": null, "verified_edition": null},
  "threshold_provenance": "SET BY US — must be calibrated against the labelled test set in B-T37 and adjusted;
                           record the before/after values in docs/DECISIONS.md",
  "human_reviewed": false }
```

> **Threshold honesty:** you do not have the standard's exact numbers. So: (1) set defensible initial thresholds
> from public sources, (2) **calibrate them against your own double-labelled test set**, (3) publish the
> resulting operating point and its precision/recall **per class**, (4) state in the README and on camera that
> the thresholds are *yours*, calibrated on *your* test set, and are not IPC's. Judges reward this far more than
> a fabricated clause number. Suchismita's *"honesty of what hasn't been done yet"* is literally a scored
> preference.

---

## 5. Model & platform usage matrix

| Model / feature | Stage | Job | Why this tier |
|---|---|---|---|
| **Vision model** (Token Factory) | S2, S4 | Confirm/reject CV boxes; name joint type; flag conditions CV cannot measure | Only a vision model sees "disturbed joint" |
| Nemotron 3 **Nano** | S4 | Map measured numbers + crop → condition codes from the controlled vocabulary | Cheap, high volume, constrained output |
| Nemotron 3 **Super** | S6 narrative, S7 | Write the plain-language rework instruction per rejected joint | Mid-tier suffices for instructional prose |
| Nemotron 3 **Ultra** | Escalation only | Adjudicate cases where Nano's confidence < 0.6 **and** the rule is class-sensitive **and** the measurement is near a threshold — i.e. exactly the cases that matter | Publish "Ultra invoked on N of 300 joints" |
| **OpenCV** (local, no API) | S1, S2, S3 | All measurement | The numbers must not come from a model |
| **Structured output / JSON** | S2, S4 | Condition codes from a fixed vocabulary | Prevents free-text drift |
| **Cached Tokens** | S4 | The condition vocabulary + rule preamble repeats on every call | Measure the saving |
| **Sandboxes** | S7 | Generate + validate the PDF **with networking disabled**; download and hash | Proves the report is self-consistent |
| **Sandboxes branching** | A/B | gate_on vs gate_off over the identical 300-joint set | The headline experiment |
| **Serverless Job** | Batch | 300-joint eval + confusion matrices overnight | Track text encourages it |
| **Serverless Endpoint** | Deploy | Host the API | Track text encourages it |
| **Tavily** *(optional)* | S6 | Look up the current public guidance / a component datasheet's solderability spec for a specific part | Only if load-bearing — otherwise skip; do not fake the $3k prize |

---

## 6. The deterministic gate — pseudocode

```python
# backend/app/gate/gate.py — NO LLM CALLS. A test monkeypatches the TF client to raise and asserts this still runs.

def grade(board: BoardContext, class_: int, rules: RuleTable) -> BoardReport:
    rejected, abstentions, verdicts = [], [], []

    if not board.image.calibrated and any(r.requires_calibration for r in rules.applicable(board)):
        abstentions.append(Abstain("uncalibrated",
            "No scale reference in frame. Measurements that require millimetres cannot be trusted. "
            "Re-shoot with the printed calibration target, or enter mm/px manually, or accept a "
            "visual-only grade with reduced confidence."))

    if board.image.blur_laplacian_var < FLOOR or board.image.exposure_clipped_pct > CEIL:
        abstentions.append(Abstain("image_quality_insufficient",
            f"blur={board.image.blur_laplacian_var:.0f} floor={FLOOR}; clipped={board.image.exposure_clipped_pct:.1f}%"))

    for roi in board.rois:
        ms = {m.quantity: m for m in board.measurements if m.roi_id == roi.id}
        for cond in board.condition_findings_for(roi):
            rule = rules.find(cond.condition_code, roi.joint_type)
            if rule is None:
                rejected.append(Reject(cond, "no_rule_for_condition")); continue
            if not rule.human_reviewed and STRICT_MODE:
                rejected.append(Reject(cond, "rule_unverified")); continue

            th = rule.class_thresholds[str(class_)]
            m  = ms.get(th["metric"])
            if m is None or m.value is None:
                if rule.requires_calibration:
                    abstentions.append(Abstain("measurement_not_computable", roi.id, cond.condition_code)); continue
                if cond.measurement_basis == "visual_only" and cond.confidence < VISUAL_FLOOR:
                    abstentions.append(Abstain("visual_confidence_below_floor", roi.id, cond.condition_code)); continue

            # NUMBERS COME FROM S3 ONLY. Never from model prose.
            ok = compare(m.value, th["op"], th["value"]) if m else cond.confidence >= VISUAL_FLOOR
            verdicts.append(RuleVerdict(roi_id=roi.id, condition_code=cond.condition_code, **{"class": class_},
                verdict=("ACCEPT" if ok else rule.verdict_if_not_met),
                rule_id=rule.rule_id, threshold_expression=f'{th["metric"]} {th["op"]} {th["value"]}',
                measured_value=(m.value if m else None), threshold_value=th["value"],
                citation_ids=[c.id for c in [rule_citation(rule), measurement_citation(m)] if c],
                rules_table_version_hash=rules.version_hash))

    return BoardReport(
        rule_verdicts=verdicts, gate=Gate(checks_run=len(verdicts)+len(rejected)+len(abstentions),
            checks_passed=len(verdicts), rejected_claims=rejected, abstentions=abstentions,
            determinism_hash=sha256_canonical(verdicts)),
        summary=summarise(verdicts, abstentions), **{"class": class_})
```

**Why the class slider is instant:** S1–S4 are cached per image. Only S5–S6 re-run, and they are pure Python
over a small rule table. Dragging Class 1→3 re-grades in single-digit milliseconds. **That latency contrast is
worth showing on screen** — it demonstrates you understood where compute belongs.

---

## 7. Repository layout

As `_shared/platform-capabilities.md §7`, plus:
```
backend/app/cv/{calibration.py,roi_proposal.py,measure.py,annotate.py,quality.py}
backend/app/stages/{s1_ingest_image.py … s7_report.py}
backend/app/gate/{gate.py,rules_loader.py,compare.py}
backend/app/sandbox/{client.py,images.py,branching.py,report.py}
data/rules/workmanship-rules.json      data/condition-codes.json
data/calibration/target-a4.pdf         data/calibration/target-a4.png      ← printable target you author
data/testset/{images/,labels.csv,labels_pass2.csv,kappa.json}
data/fixtures/boards/*.json            eval/{run_eval.py,confusion.py}
sandbox/image/{Dockerfile,validate.py,templates/report.html.j2}
jobs/{Dockerfile,batch_eval.py}        frontend/src/{tokens.css,routes/,components/}
```

---

## 8. Phase plan & exit criteria

| Phase | Window | Exit criterion |
|---|---|---|
| **0** | Sun 26 Oct → 23:00 | Repo + licence + CI; credits confirmed; catalog snapshot; **≥30 real joint photographs acquired**; calibration target authored and printed; rules table v0 with ≥12 rules; condition vocabulary frozen; design tokens authored; hook doc |
| **1** | Sun 23:00 → Mon 09:00 | Schemas frozen; citation registry + ledger live; golden fixtures; `make check` green from clean clone; **CV measurement pipeline returns numbers on 3 real photos** |
| **2** | Mon → 23:00 | **One photo → annotated overlay + class-dependent verdict on screen.** Screen-record it |
| **3** | Tue 28 Oct | 300-joint double-labelled test set; kappa; confusion matrix per class; Sandbox PDF validated network-off; branch A/B numbers; 3 interviews; abstention paths proven |
| **4** | Wed 29 Oct 08:00–16:00 | **FEATURE FREEZE.** All UI states; slider smooth; accessibility; deployed; reachable from incognito + mobile; LIMITATIONS with real numbers |
| **5** | Wed 16:00 → Thu 30 Oct 18:00 | Video ≤2:50 public; README complete; Devpost copy + feedback; clean-clone test; **SUBMITTED** |

---

## 9. Task tickets

### Phase 0

```
ID: B-T01  TITLE: Bootstrap repo, licence, CI, Makefile
PHASE: 0   OWNER: devops-agent  DEPENDS_ON: —  BLOCKS: all
CONTEXT: _shared/platform-capabilities.md §7
DELIVERABLE: LICENSE (Apache-2.0) at root, README stub, .gitignore (exclude data/testset/images >5MB via LFS or
             a fetch script), .env.example, Makefile, .github/workflows/ci.yml, backend/pyproject.toml,
             frontend/package.json
SPEC: Identical to A-T01 plus: .env.example adds OPENCV_VERSION pin, SANDBOX_PROJECT_ID. CI runs ruff, pytest,
      tsc --noEmit, vite build. Add a `make sample` target that runs the pipeline on one committed fixture
      WITHOUT any API key (pure CV stages only) so a judge can try it instantly.
ACCEPTANCE: `make check` green on skeleton; `make sample` runs offline with no API key and prints CV measurements.
VERIFY: git clone <url> /tmp/t && cd /tmp/t && make check && make sample
```

```
ID: B-T02  TITLE: Credits + authenticated model catalog snapshot (vision model ID is critical here)
PHASE: 0   OWNER: backend-agent DEPENDS_ON: B-T01  BLOCKS: B-T06, B-T09
CONTEXT: _shared/platform-capabilities.md §1–2
DELIVERABLE: scripts/snapshot_catalog.py ; data/model-catalog.snapshot.json ; docs/MODEL-USAGE.md skeleton
SPEC: Dump /v1/models. Identify and RECORD the exact ID of: a vision-capable NVIDIA model, Nemotron 3 Ultra /
      Super / Nano. Send each one a trivial multimodal test (a 64×64 PNG of a solder blob) and confirm the vision
      model actually describes it. Log all calls.
ACCEPTANCE: snapshot committed; ≥1 vision model confirmed working with a real image; three ledger lines.
VERIFY: jq -r '.[] | select(.id|test("vision|vl|nemotron";"i")) | .id' data/model-catalog.snapshot.json
KILL CRITERION: if no vision-capable NVIDIA open model is available to your account by Sun 21:00, escalate —
                this idea depends on it. Pivot to Idea A or C.
```

```
ID: B-T03  TITLE: Author the calibration target (the half of the insight nobody else has)
PHASE: 0   OWNER: human + frontend-agent  DEPENDS_ON: B-T01  BLOCKS: B-T05
DELIVERABLE: data/calibration/target-a4.pdf ; data/calibration/target-a4.svg ; data/calibration/README.md
SPEC: Design a printable A4 target: a 20 mm × 20 mm black square with a white crosshair centre, a 10 mm grid,
      a 2.54 mm (0.1") header-pitch reference row of 10 dots, and a scale bar labelled in mm. High contrast,
      matte finish instruction, print at 100% scale with no fit-to-page. Include a QR/short URL back to the tool.
      README explains how to use it: place beside the board, same focal plane, perpendicular to the lens.
      ALSO document the two zero-cost fallbacks: (a) a coin of known diameter, (b) a 2.54 mm IC/pin-header pitch
      visible in frame — both let a user calibrate without printing anything.
ACCEPTANCE: PDF prints at exactly 20 mm (measure with a ruler — record the measurement in the ticket report);
            automatic target detection finds it in ≥9 of 10 test photos at varying distances.
VERIFY: python -c "from app.cv.calibration import detect_target; print(detect_target('data/fixtures/calib/*.jpg'))"
```

```
ID: B-T04  TITLE: Acquire the image corpus (HUMAN + agent, the real bottleneck)
PHASE: 0   OWNER: human (photography) + data-agent (sourcing)  DEPENDS_ON: B-T01  BLOCKS: B-T14, B-T15, B-T37
DELIVERABLE: data/testset/images/ (target 300, minimum 120) ; data/testset/SOURCES.md
SPEC: Three sources, in priority order:
      (1) **Photograph your own boards.** A team member with a phone (macro mode) or a €25 USB microscope, a
          scrap PCB, and a soldering iron can produce 100 images in an afternoon — deliberately including good
          joints, cold joints, bridges, icicles, insufficient solder, tombstoned parts, and 10 deliberately
          blurry/uncalibrated ones for the abstention tests. THIS IS THE BEST SOURCE: it's yours, it's real,
          it's licensable, and it's filmable.
      (2) **Public/openly-licensed PCB and solder-defect image datasets.** Search for openly licensed sets
          (check the licence for each — many are research-only or CC-BY-NC, which is a problem for an
          Apache-2.0 repo; NC-licensed images may still be used for *evaluation* if you do not redistribute
          them, in which case ship a fetch script + .gitignore instead of the files, and say so).
      (3) **A legally held copy of the standard, if a teammate's employer has one** — for threshold confirmation
          only, never for redistribution.
      SOURCES.md records for every image: origin, licence, whether it may be redistributed in the repo, and
      whether it appears in the video.
ACCEPTANCE: ≥120 images committed or fetch-scripted; ≥10 deliberately bad-quality images for abstention;
            ≥60 with a calibration reference present; SOURCES.md complete with a licence column.
VERIFY: python scripts/check_testset.py --min-images 120 --min-calibrated 60 --min-bad 10
```

```
ID: B-T05  TITLE: CV foundation — calibration + image quality
PHASE: 0   OWNER: backend-agent DEPENDS_ON: B-T03, B-T04  BLOCKS: B-T11
DELIVERABLE: backend/app/cv/{calibration.py,quality.py} ; backend/tests/test_cv_calibration.py
SPEC: detect_target(img) → {found, mm_per_px, corners, warp_error} via contour + known 20 mm square.
      detect_reference_object(img, kind) → mm_per_px for coin/header-pitch fallbacks.
      quality(img) → {blur_laplacian_var, exposure_clipped_pct, white_balance_offset, sharp_enough, usable}.
      Pure OpenCV, deterministic, no network, no model. Unit-test against the fixtures with known geometry:
      a synthetic render at a known mm/px must be recovered within ±3%.
ACCEPTANCE: mm_per_px recovered within ±3% on ≥9/10 calibrated fixtures; blur floor separates the 10 deliberately
            bad images from the good ones with zero overlap (report the two distributions).
VERIFY: cd backend && uv run pytest tests/test_cv_calibration.py tests/test_cv_quality.py -q
```

```
ID: B-T06  TITLE: Token Factory client wrapper + ledger + cached-token accounting
PHASE: 0   OWNER: backend-agent DEPENDS_ON: B-T02  BLOCKS: all model stages
CONTEXT: _shared/platform-capabilities.md §2, §7 (ledger contract)
SPEC: Same contract as A-T06, plus multimodal support (image_url or base64 image parts) and a per-call image
      token estimate in the ledger so you can report image-token cost separately — nobody in the field does this.
ACCEPTANCE: multimodal call works; ledger records image tokens; aggregates() includes the all-Ultra counterfactual.
VERIFY: cd backend && uv run pytest tests/test_ledger.py -q
```

```
ID: B-T07  TITLE: Freeze the condition vocabulary
PHASE: 0   OWNER: data-agent    DEPENDS_ON: B-T04  BLOCKS: B-T08, B-T17
DELIVERABLE: data/condition-codes.json
SPEC: The 24-code vocabulary from SPEC §4.4, each with: code, plain-English definition (one sentence, written for
      an apprentice, not for an engineer), measurable (bool), the quantity that measures it if measurable,
      typical_class_sensitivity (does the accept threshold differ across classes?), and example image ids from
      the test set. Codes the CV cannot measure get measurable=false and must be handled by the visual_only path.
ACCEPTANCE: ≥20 codes; every code has a one-sentence definition a non-expert understands; every measurable code
            names its quantity; ≥3 test-set images linked per code where available (flag INSUFFICIENT otherwise).
VERIFY: jq '[.codes[] | select(.example_image_ids|length<3)] | length' data/condition-codes.json
```

```
ID: B-T08  TITLE: Rules table v0 with honest provenance
PHASE: 0   OWNER: data-agent + human  DEPENDS_ON: B-T07  BLOCKS: B-T18
DELIVERABLE: data/rules/workmanship-rules.json ; docs/STANDARDS-POSITION.md
SPEC: ≥12 rules covering: insufficient wetting, insufficient solder volume, excess solder, excessive fillet,
      solder bridge, icicle, solder ball/splash, tombstoning, insulation clearance, wire strand damage, flux
      residue, voiding. Each with class_thresholds for classes 1/2/3, requires_calibration, image_quality_floor,
      and a fully populated source block.
      ⚠️ NO INVENTED CLAUSE NUMBERS. Use JC-* IDs. Where you cannot cite an openly licensed source, set
      source.kind="own_validated_measurement" and threshold_provenance explaining that the threshold will be
      calibrated against the labelled test set in B-T37, and human_reviewed=false.
      docs/STANDARDS-POSITION.md states the IP position from SPEC §1 verbatim, in plain language.
ACCEPTANCE: ≥12 rules; zero invented IPC clause numbers (grep for "IPC-A-610" must appear ONLY in
            STANDARDS-POSITION.md and the disclaimer, never as a rule_id or a claimed clause);
            every rule has a populated source block; rules_table_version_hash computable.
VERIFY: jq '.rules | length' data/rules/workmanship-rules.json && ! jq -e '.rules[].rule_id | select(test("IPC"))' data/rules/workmanship-rules.json
```

```
ID: B-T09  TITLE: Design system — "inspection bay", not "SaaS dashboard"
PHASE: 0   OWNER: frontend-agent DEPENDS_ON: B-T01  BLOCKS: B-T13, B-T20
CONTEXT: _shared/judging-rubric.md §3 ; _shared/agent-delegation-protocol.md §6
DELIVERABLE: frontend/src/tokens.css ; frontend/src/components/primitives.tsx ; docs/DESIGN.md
SPEC: Metaphor = an electronics inspection bench under a magnifier lamp. Palette: near-black bench #0E1113,
      warm lamp white #FDF6E3 for the image surface, solder-silver #C7CDD1 for structure,
      ACCEPT green #2FA36B, PROCESS_INDICATOR amber #E8A33D, REJECT red #D6453D, UNDETERMINED slate #7A858C,
      and a single annotation cyan #35C4D7 for overlay boxes (must not collide with the verdict colours).
      Type: a technical grotesque for verdicts; **monospace for every measurement, threshold and rule ID** —
      numbers in mono is the whole aesthetic. Hairline 1px rules, no drop shadows, no rounded-pill buttons.
      Primitives: VerdictBanner, ClassSlider (the hero control — 3 detents, tactile, keyboard-operable),
      ImageCanvas (zoom/pan, overlay boxes with labels, hover-to-highlight the matching finding row),
      FindingRow, MeasurementCell (mono, shows value + unit + threshold + comparison glyph),
      CitationPill, AbstentionNotice, ProgressRail, StopButton, ReportDownloadCard.
      FORBIDDEN: purple→pink gradients; glassmorphism; emoji iconography; centred hero + 3 cards; raw Tailwind
      colour classes in components; any stock chart library default styling.
ACCEPTANCE: docs/DESIGN.md explains the metaphor in 5 sentences; ClassSlider is operable by keyboard alone;
            a screenshot of ImageCanvas with 3 overlay boxes is committed; annotation cyan is distinguishable
            from all four verdict colours for deuteranopia (check with a simulator, record the result).
VERIFY: cd frontend && npm run build && npx tsc --noEmit
```

```
ID: B-T10  TITLE: Hook doc + persona doc + the two insights (CONTENT)
PHASE: 0   OWNER: content-agent DEPENDS_ON: —  BLOCKS: B-T20, B-T41, B-T44
DELIVERABLE: docs/HOOK.md
SPEC: One page: the 30-second hook with exact on-screen strings; Marc in his own words; **both** insights
      (class relativity, calibration necessity) as single sentences; the one takeaway; the cut list.
ACCEPTANCE: ≤1 page; reads aloud in ≤45 s; both insight sentences contain no hedge words.
```

### Phase 1 — Contracts

```
ID: B-T11  TITLE: Freeze core schemas
PHASE: 1  OWNER: backend-agent DEPENDS_ON: B-T05, B-T07, B-T08  BLOCKS: all
DELIVERABLE: schemas/core-schemas.json ; backend/app/models.py ; backend/tests/test_schemas.py
SPEC: Transcribe SPEC §4 into JSON Schema + Pydantic v2 with a schema_version. Round-trip test every fixture.
      Schemas FROZEN afterwards.
ACCEPTANCE: all fixtures validate; a Measurement with computable=true and value=null fails validation
            (that combination is a lie); a ConditionFinding with a code outside the vocabulary fails validation.
VERIFY: cd backend && uv run pytest tests/test_schemas.py -q
```

```
ID: B-T12  TITLE: Citation registry (measurement + rule + image citations)
PHASE: 1  OWNER: backend-agent DEPENDS_ON: B-T11  BLOCKS: B-T18
DELIVERABLE: backend/app/citations.py ; tests/test_citations.py
SPEC: As A-T10, with two project-specific kinds: kind="measurement" (locator = measurement id + pixel derivation,
      ttl=null, trust=primary) and kind="rule" (locator = rule_id + rules_table_version_hash, ttl=null,
      trust=primary). A RuleVerdict must cite BOTH a rule and (where a threshold comparison happened) a
      measurement. trust="model_derived" must be rejected by register().
ACCEPTANCE: a verdict citing only a rule but not its measurement fails the gate; model_derived registration raises.
VERIFY: cd backend && uv run pytest tests/test_citations.py -q
```

```
ID: B-T13  TITLE: Backend skeleton + frontend skeleton + offline sample route
PHASE: 1  OWNER: backend-agent + frontend-agent  DEPENDS_ON: B-T09, B-T11  BLOCKS: B-T20
DELIVERABLE: backend/app/{main.py,config.py} ; frontend/src/{App.tsx,routes/,lib/api.ts} ; frontend/vite.config.ts
SPEC: Backend: GET /healthz (pinned model IDs, rules_table_version_hash, credits flag); POST /api/inspect
      (multipart image + class); GET /api/report/{id}; GET /api/report/{id}/events (SSE);
      GET /api/regrade/{id}?class=N (re-runs S5–S6 only, from cache — must return in <200 ms);
      GET /api/ledger/summary. CORS for the deployed origin + localhost.
      Frontend routes: / (inspect), /report/:id, /eval, /dev/tokens. Vite proxy /api → :8000.
      `make sample` route renders a committed fixture's CV-only result with no API key.
ACCEPTANCE: /api/regrade on a cached board returns in <200 ms (assert in a test); frontend builds with zero
            external network references.
VERIFY: cd backend && uv run pytest tests/test_api.py -q && cd ../frontend && npm run build
```

```
ID: B-T14  TITLE: CV measurement pipeline (S3) — the trust core
PHASE: 1→2  OWNER: backend-agent DEPENDS_ON: B-T05  BLOCKS: B-T16, B-T17
DELIVERABLE: backend/app/cv/{measure.py,annotate.py} ; tests/test_cv_measure.py
SPEC: Implement every quantity in SPEC §4.3 with OpenCV. Each returns value|null + a derivation string + a
      pixel-evidence overlay PNG (so a human can see exactly what was measured — this overlay is also your
      video B-roll). Unmeasurable must return null with a reason, never a guess.
      Key algorithms: solder mask region via adaptive threshold + morphological cleanup; pad annulus from the
      detected geometry; coverage = intersection area / annulus area; wetting angle via contour tangent fit at
      the fillet edge; bridge gap = min distance between adjacent solder masks; icicle length = longest
      protrusion beyond the pad boundary; tombstone lift = component body angle vs board plane (needs the
      component contour; return null if not visible); flux residue = colour-space region outside the solder mask.
      Write a synthetic-image test: render a known geometry (a circle of known radius on a known grid), assert
      the measurement recovers it within ±5%.
ACCEPTANCE: synthetic recovery within ±5% on ≥6 quantities; every null return carries a reason; overlay PNGs
            written for every measurement; determinism (same image → identical values) asserted.
VERIFY: cd backend && uv run pytest tests/test_cv_measure.py -q
```

```
ID: B-T15  TITLE: Golden-fixture harness + offline replay
PHASE: 1  OWNER: eval-agent    DEPENDS_ON: B-T04, B-T11  BLOCKS: B-T37
DELIVERABLE: backend/tests/golden/ ; backend/tests/conftest.py ; eval/labels.pass1.csv
SPEC: VCR-style recorded model responses so `pytest --offline` costs nothing and never flakes. 12 golden boards
      with hand-labelled expected verdicts at all three classes. labels.pass1.csv = one row per joint image:
      image_id, roi_hint, expected_condition_code, expected_verdict_class1/2/3, labelled_by, labelled_at,
      notes. **Pass 2 is done separately by a different labeler in B-T37 — keep them blind to each other.**
ACCEPTANCE: `pytest -q --offline` green with zero network; golden verdicts differ across at least 4 of the 12
            boards between Class 1 and Class 3 (proving class relativity is real in your data).
VERIFY: cd backend && uv run pytest -q --offline
```

### Phase 2 — Spine (Mon 27 Oct)

```
ID: B-T16  TITLE: S1 ingest_image + S2 propose_rois
PHASE: 2  OWNER: backend-agent DEPENDS_ON: B-T05, B-T13  BLOCKS: B-T19
DELIVERABLE: backend/app/stages/{s1_ingest_image.py,s2_propose_rois.py} ; backend/app/cv/roi_proposal.py ; tests
SPEC: S1 = decode, EXIF-orient, compute quality, attempt calibration (target → reference object → user-supplied
      → none), emit ImageContext. S2 = CV contour proposal first (adaptive threshold → contours → filter by area,
      aspect, solidity, and a shape prior per joint type) producing candidate boxes; then ONE vision-model call
      with the full image and the candidate boxes asking it to confirm/reject each and name the joint_type from
      the controlled list. detection_basis records which source produced the box. If the vision call fails, fall
      back to CV-only boxes with reduced confidence and set a flag the UI must show.
ACCEPTANCE: on 12 golden boards, ≥85% of hand-marked joints are proposed with IoU ≥0.5; a vision-model outage
            still yields CV boxes and a visible degraded-mode notice; no box is invented by the model that CV
            did not propose (assert this — it is the "model may not create evidence" law).
VERIFY: cd backend && uv run pytest tests/test_s1_s2.py -q
```

```
ID: B-T17  TITLE: S4 classify (Nemotron Nano + vision, controlled vocabulary)
PHASE: 2  OWNER: backend-agent DEPENDS_ON: B-T14, B-T15  BLOCKS: B-T18
DELIVERABLE: backend/app/stages/s4_classify.py ; backend/app/prompts/classify.md ; tests/test_s4.py
SPEC: One Nano call per batch of ROIs. Input per ROI: joint_type, the MEASURED numbers (labelled as measurements,
      with units), the crop image. Output: condition codes from data/condition-codes.json ONLY, each with
      measurement_basis (measured if it cites a supplied number, visual_only otherwise) and confidence.
      Enforce in code: any code outside the vocabulary → drop and record a rejection. Any
      measurement_basis="measured" claim whose supporting_measurement_ids are absent or null-valued → downgrade
      to visual_only. The model may NOT introduce a number; it may only reference one you gave it.
ACCEPTANCE: vocabulary violations are caught by a mocked-response test; a claim citing a null measurement is
            downgraded; on 12 golden boards, condition-code accuracy ≥0.70 offline-replayed.
VERIFY: cd backend && uv run pytest tests/test_s4.py -q
```

```
ID: B-T18  TITLE: S5 class_rule + S6 gate
PHASE: 2  OWNER: backend-agent DEPENDS_ON: B-T08, B-T12, B-T17  BLOCKS: B-T19
DELIVERABLE: backend/app/gate/{gate.py,rules_loader.py,compare.py} ; tests/test_gate.py
SPEC: Implement SPEC §6 exactly. rules_loader excludes rules with human_reviewed=false when STRICT_MODE and
      records the exclusion. compare() implements >=, >, <=, <, between. Determinism asserted by hashing the
      canonical verdict list. All four abstention reasons implemented: uncalibrated, image_quality_insufficient,
      measurement_not_computable, visual_confidence_below_floor. NO LLM imports in this module — enforce with a
      test that monkeypatches the TF client to raise.
ACCEPTANCE: 12/12 golden boards produce the hand-labelled verdict at Class 3; ≥4 boards change verdict between
            Class 1 and Class 3; determinism hash stable across 3 runs; gate module imports no LLM client;
            all four abstention paths covered by tests.
VERIFY: cd backend && uv run pytest tests/test_gate.py -q
```

```
ID: B-T19  TITLE: POST /api/inspect + GET /api/regrade end to end
PHASE: 2  OWNER: backend-agent DEPENDS_ON: B-T16, B-T17, B-T18  BLOCKS: B-T20, G2
DELIVERABLE: backend/app/pipeline.py ; backend/app/main.py ; tests/test_api_inspect.py
SPEC: S1→S6 with SSE stage events, an abort Event, and a per-run budget guard. Cache S1–S4 results keyed by
      image sha256 so /api/regrade?class=N re-runs only S5–S6. Concurrent-safe: 6 parallel uploads must not
      interfere. Store BoardReport at runs/reports/{id}.json.
ACCEPTANCE: a 12-joint photo completes in <30 s; /api/regrade returns in <200 ms from cache; 6 concurrent
            uploads all succeed with distinct report ids.
VERIFY: for i in 1 2 3 4 5 6; do curl -sF "image=@data/fixtures/boards/b01.jpg" -F "class=3" localhost:8000/api/inspect & done; wait
```

```
ID: B-T20  TITLE: Frontend — the inspection view (photo is the UI)
PHASE: 2  OWNER: frontend-agent DEPENDS_ON: B-T09, B-T19  BLOCKS: G2
DELIVERABLE: frontend/src/routes/InspectRoute.tsx + components
SPEC: Above the fold, in order: (1) drop zone + 6 one-click sample boards with thumbnails; (2) VerdictBanner —
      board-level summary "3 REJECT · 1 PROCESS INDICATOR · 8 ACCEPT — at Class 3"; (3) **ClassSlider**;
      (4) ImageCanvas with overlay boxes colour-coded by verdict, hover-synced to the finding list;
      (5) the finding list, each row = joint id, condition code in plain English, MeasurementCell
      (mono: `coverage 41.3% ≥ 75%? ✗`), rule_id CitationPill, verdict chip.
      BELOW the fold: AbstentionNotice block (why, and how to fix the photo), the Run cost panel (tokens by
      model, image tokens separately, cost, latency), and Download the report.
      Dragging ClassSlider must re-grade in <200 ms with a visible, immediate change — this is the demo's
      signature moment. Do not show a spinner for it.
ACCEPTANCE: a teammate who has never seen it grades a board and flips the class without being spoken to, in ≤45 s
            (timed, recorded in the ticket report); overlay hover syncs both directions; works at 360 px.
VERIFY: cd frontend && npm run build && timed manual test logged
```

### Phase 3 — Proof (Tue 28 Oct)

```
ID: B-T21  TITLE: S7 report generation in a Token Factory Sandbox
PHASE: 3  OWNER: sandbox-agent DEPENDS_ON: B-T19  BLOCKS: B-T22
DELIVERABLE: sandbox/image/{Dockerfile,validate.py,templates/report.html.j2} ; backend/app/sandbox/* ;
             backend/app/stages/s7_report.py ; tests/test_s7.py
SPEC: One reusable image containing the frozen rules table (by version hash), validate.py, the Jinja template and
      WeasyPrint. Resolve and pin the immutable image UUID in docs/MODEL-USAGE.md. Per report: inject the
      BoardReport JSON + annotated crop PNGs; render an A4 PDF with header (board id, inspector, class, timestamp,
      tool version, **rules_table_version_hash**), per-joint rows (thumbnail with overlay, plain-English condition,
      measurement vs threshold in mono, rule id, verdict), a summary block, **abstentions listed separately and
      prominently**, and the disclaimer footer. Retain, download bytes, sha256 locally, compare with the
      Sandbox-reported hash.
ACCEPTANCE: PDFs render for all 12 golden boards; local hash == sandbox hash; image UUID reused across runs;
            abstentions appear in the PDF even when there are zero rejects.
VERIFY: cd backend && uv run pytest tests/test_s7.py -q && ls runs/artifacts | wc -l
```

```
ID: B-T22  TITLE: Sandbox validator with the guest network DISABLED  ← showpiece
PHASE: 3  OWNER: sandbox-agent DEPENDS_ON: B-T21  BLOCKS: B-T41
DELIVERABLE: sandbox/image/validate.py ; backend/app/sandbox/network_off.py ; tests/test_sandbox_network_off.py
SPEC: Re-validate the finished PDF inside the Sandbox with networking disabled: every REJECT cites a rule_id that
      exists in the embedded rules table at the embedded version hash; every numeric comparison in the report
      re-computes from the embedded measurements; no placeholder text; every abstention has a reason code; the
      disclaimer is present; the class in the header matches the class in every verdict row; the PDF opens and
      has the expected page count. Emit a signed validation report.
      The point: **the report is provably internally consistent with no ability to phone home.** Show
      `network: disabled` in the UI and the video.
ACCEPTANCE: validator passes on 12/12; a deliberately corrupted report (test flips one threshold) FAILS and the
            verdict is withheld; UI shows "validated offline · sha256 …".
VERIFY: cd backend && uv run pytest tests/test_sandbox_network_off.py -q
```

```
ID: B-T23  TITLE: Sandbox branch A/B — gate ON vs gate OFF  ← the headline experiment
PHASE: 3  OWNER: sandbox-agent DEPENDS_ON: B-T18, B-T21, B-T37  BLOCKS: B-T41, B-T44
DELIVERABLE: scripts/ab_gate.py ; runs/reports/ab-gate.json ; docs/img/ab-gate-chart.svg ; tests/test_ab.py
SPEC: Save ONE immutable image containing the rules table and the full labelled test set (≥120, ideally 300).
      Branch twice: `gate_on` (S5+S6 rule lookup) vs `gate_off` (the model's own accept/reject used directly as
      the verdict). Run the identical set down both arms at **Class 3** — the class where a false accept is most
      dangerous. Compute false-accept rate (REJECT/PROCESS_INDICATOR labelled, but graded ACCEPT), false-reject
      rate, UNDETERMINED rate, mean cost, mean latency. Publish the delta as a bar chart and one sentence.
      Recover from the known-good branch afterwards.
ACCEPTANCE: both arms n≥120; the chart renders; the README's first screen states the delta in one sentence with
            real numbers; the Class-3 false-accept rate is stated for both arms.
VERIFY: python scripts/ab_gate.py --class 3 --report && jq '.arms[] | {arm,n,false_accept_rate}' runs/reports/ab-gate.json
```

```
ID: B-T24  TITLE: Threshold calibration against the labelled test set
PHASE: 3  OWNER: eval-agent    DEPENDS_ON: B-T08, B-T15, B-T37  BLOCKS: B-T41
DELIVERABLE: eval/calibrate.py ; runs/reports/threshold-calibration.json ; docs/DECISIONS.md entries
SPEC: You set the initial thresholds from public sources. Now CALIBRATE them: for each rule and each class, sweep
      the threshold across its plausible range and pick the operating point that maximises F1 against the
      double-labelled ground truth, subject to a **minimum precision floor at Class 3 of 0.90** — because at
      Class 3 a false accept is the expensive error, and saying so is the insider move. Record before/after
      values, the chosen operating point, and the resulting per-class P/R/F1 in docs/DECISIONS.md.
      Publish the calibration curve for at least the two most important rules.
ACCEPTANCE: every rule with a measurable threshold has a recorded before/after; Class 3 precision ≥0.90 on the
            calibration set (or an honest report of what it actually is and why); ≥2 calibration curves committed.
VERIFY: python eval/calibrate.py --report && jq '.rules[] | {rule_id,class,threshold_before,threshold_after,f1}' runs/reports/threshold-calibration.json
```

```
ID: B-T25  TITLE: Escalation to Ultra — and instrument it
PHASE: 3  OWNER: backend-agent DEPENDS_ON: B-T17, B-T18  BLOCKS: B-T33
SPEC: Invoke Ultra only when: Nano confidence <0.6 AND the applicable rule is class-sensitive AND the measured
      value is within 15% of the threshold. Log the escalation reason in the ledger note. Publish
      "Ultra invoked on N of M joints (X%)" and the cost saved versus grading every joint with Ultra.
ACCEPTANCE: escalation fires on the near-threshold fixtures and not on the obvious ones; ledger notes record the
            reason; the N-of-M number is in docs/MODEL-USAGE.md.
VERIFY: jq -s 'map(select(.notes|test("escalat";"i"))) | length' runs/ledger.jsonl
```

```
ID: B-T26  TITLE: Batch eval as a Nebius Serverless Job
PHASE: 3  OWNER: devops-agent  DEPENDS_ON: B-T19, B-T24  BLOCKS: B-T27
DELIVERABLE: jobs/Dockerfile ; jobs/batch_eval.py ; docs/EVAL.md
SPEC: Package the pipeline; submit as a Serverless Job that runs S1–S6 over the full test set and emits the
      confusion matrix per class, per-condition-code P/R/F1, abstention rate, mean/p95 latency, total tokens
      (text and image separately) and total cost. Handle partial failure honestly — report n_completed and
      n_failed separately, never pad.
ACCEPTANCE: job completes; confusion matrices for all three classes; per-code F1 with INSUFFICIENT flags where
            a code has <5 examples; total cost logged.
VERIFY: jq '.per_class' runs/reports/eval.json
FALLBACK: run the identical script locally as a long process and record runner="local_process" honestly.
```

```
ID: B-T27  TITLE: /eval page — the results, in public
PHASE: 3  OWNER: frontend-agent DEPENDS_ON: B-T26, B-T23  BLOCKS: B-T41
SPEC: A public page showing: the test set composition (n, sources, licence position), inter-annotator kappa,
      the three confusion matrices, per-code F1 with INSUFFICIENT flags, the A/B gate chart, the threshold
      calibration curves, the cost ledger summary and the all-Ultra counterfactual, and a methodology box with
      known biases. Judges can check your numbers without opening the repo — and a sceptical judge who can
      verify your claims is a judge who scores you high on Potential Impact.
ACCEPTANCE: every number on the page matches runs/reports/*.json (scripted diff); methodology box present;
            INSUFFICIENT classes visibly flagged rather than hidden.
VERIFY: python scripts/check_eval_page_matches_reports.py
```

```
ID: B-T28  TITLE: Abstention paths + the "bad photo" demo
PHASE: 3  OWNER: eval-agent    DEPENDS_ON: B-T18  BLOCKS: B-T44
DELIVERABLE: data/testset/images/bad/ (≥10) ; tests/test_abstention.py
SPEC: Prove all four abstention reasons on real bad inputs: no calibration reference; motion blur; blown
      highlights; a joint type with no rule; a measurement CV cannot compute (tombstone lift with no visible
      component contour). Each must produce a calm, useful UNDETERMINED state that says **how to fix the photo**,
      not just "failed". This is the on-camera answer to *"what happens when the evidence is thin?"*
ACCEPTANCE: 10/10 abstain correctly with distinct reason codes; each abstention notice contains a concrete
            re-shoot instruction; the UI state is visually distinct from REJECT (never alarm the user for a
            photo problem).
VERIFY: cd backend && uv run pytest tests/test_abstention.py -q
```

```
ID: B-T29  TITLE: Talk to 3 real people (HUMAN TASK — highest ROI per hour)
PHASE: 3  OWNER: human         DEPENDS_ON: B-T20  BLOCKS: B-T41, B-T44
SPEC: Find 3 people: a contract manufacturer or production lead, a working inspector or quality engineer, and an
      electronics apprenticeship trainer / maker-space mentor. Eindhoven/Brainport is dense with all three —
      this is your location advantage. Show them the running demo. Ask:
        1. What does rework and scrap actually cost you per board / per month?
        2. How do you decide Class 1 vs 2 vs 3 today, and who decides?
        3. What happens when two inspectors disagree? How is it resolved? Is it recorded?
        4. Would a tool that grades a photo and produces a citable record be useful? Where would it break?
        5. What is wrong with it?
      Record one 20-second clip OR one quotable sentence + first name and role, with permission. Write
      reports/B-T29.INTERVIEWS.md. Feed at least one finding back into the UI copy within the hour.
ACCEPTANCE: 3 conversations documented; ≥1 usable quote with permission; ≥1 product change logged in DECISIONS.md;
            **≥1 real rework-cost number** you can cite in the video (this is your Potential Impact figure).
NOTE: Ricky, verbatim: *"even if you're not a subject matter expert… you should be going out and talking to
      potential customers before you build any features."*
```

```
ID: B-T30  TITLE: Double-blind labelling + Cohen's kappa
PHASE: 3  OWNER: eval-agent + human  DEPENDS_ON: B-T04, B-T15  BLOCKS: B-T24, B-T26
DELIVERABLE: data/testset/labels.pass2.csv ; data/testset/kappa.json ; docs/EVAL.md §labelling
SPEC: Pass 2 labelled by a **different** labeler who has not seen pass 1. Compute Cohen's kappa for the
      condition code and for the verdict at each class. Where the two disagree, adjudicate by discussion and
      record the adjudicated label plus a note on why they disagreed — **the disagreement notes are gold for
      LIMITATIONS.md**, because they show where the standard itself is ambiguous to humans.
ACCEPTANCE: kappa computed for condition code and for each class verdict; ≥20 disagreement notes written;
            adjudicated labels committed.
VERIFY: jq '.' data/testset/kappa.json
```

### Phase 4 — Polish (Wed 29 Oct) — FEATURE FREEZE

```
ID: B-T31  TITLE: Onboarding — samples, first-run explainer, tooltips everywhere
PHASE: 4  OWNER: frontend-agent DEPENDS_ON: B-T20  BLOCKS: G4
SPEC: Assay lost points for having no onboarding. Ship: 6 one-click sample boards with a 4-word label each
      ("good joints", "solder bridge", "tombstoned 0805", "cold joint", "blurry — will abstain", "no scale —
      will abstain"); a dismissible 2-sentence first-run overlay; a tooltip on EVERY control, especially the
      ClassSlider (explain Class 1/2/3 in one line each) and the mm/px manual entry; an inline "what is a process
      indicator?" explainer. Including two samples that deliberately abstain is a trust signal, not a weakness.
ACCEPTANCE: a first-time user completes an inspection with zero instruction (3 people, timed, median ≤45 s);
            every control has a tooltip.
```

```
ID: B-T32  TITLE: Empty / loading / error / degraded states
PHASE: 4  OWNER: frontend-agent DEPENDS_ON: B-T31  BLOCKS: G4
SPEC: Seven designed states: empty; uploading/analysing (ProgressRail with the real stage + elapsed + StopButton);
      vision-model-degraded (CV-only boxes, visible notice); gate-abstained; full error (with retry and reason);
      budget exhausted; rate limited. Never show a raw stack trace — Assay showed a `standard error` live to the
      judges and it cost them.
ACCEPTANCE: 7 states each with a designed component and a screenshot in docs/img/states/.
```

```
ID: B-T33  TITLE: Ledger aggregates + cost report
PHASE: 4  OWNER: backend-agent DEPENDS_ON: B-T06, B-T26  BLOCKS: B-T41
DELIVERABLE: scripts/ledger_report.py ; docs/MODEL-USAGE.md complete
SPEC: Totals; per-model and per-stage cost; **image tokens reported separately from text tokens**; cache-hit rate
      and $ saved; p50/p95 latency; failure counts by class; Ultra escalation rate (N of M); and the
      **counterfactual cost of grading every joint with Ultra**. Publish the table with a one-sentence
      interpretation. This is the exact comparison the judges asked slash-agent for and it did not have.
ACCEPTANCE: docs/MODEL-USAGE.md has real numbers including the counterfactual and the escalation rate;
            GET /api/ledger/summary returns the same JSON.
VERIFY: python scripts/ledger_report.py --markdown > docs/MODEL-USAGE.md && grep -c "US\$" docs/MODEL-USAGE.md
```

```
ID: B-T34  TITLE: Accessibility pass (and make it visible)
PHASE: 4  OWNER: frontend-agent DEPENDS_ON: B-T32  BLOCKS: G4
SPEC: ClassSlider fully keyboard-operable with aria-valuetext announcing "Class 2 — dedicated service
      electronics"; ImageCanvas has a text alternative — the finding list IS the accessible equivalent, and it
      must be complete without the image; overlay boxes have aria-labels; colour never the only signal (every
      verdict chip carries a glyph: ✓ / △ / ✗ / ?); contrast ≥4.5:1 verified, not assumed; the four verdict
      colours checked against a deuteranopia simulator; prefers-reduced-motion; visible focus ring; skip link;
      the PDF report is tagged and screen-reader navigable (WeasyPrint supports structure — verify).
      Then add an accessibility line to the video script and a paragraph to README + Next Steps.
ACCEPTANCE: axe-core reports 0 critical/serious violations; a keyboard-only inspection completes; a screen reader
            announces the verdict and the class correctly; colour-blind simulation screenshots committed.
VERIFY: cd frontend && npx @axe-core/cli http://localhost:5173 --exit
```

```
ID: B-T35  TITLE: Responsive + deploy (Serverless Endpoint + static host)
PHASE: 4  OWNER: devops-agent  DEPENDS_ON: B-T19, B-T34  BLOCKS: G4, G5
SPEC: 360/768/1280/1920 px; ImageCanvas pinch-zoom on touch. Containerise the backend, deploy as a **Nebius
      Serverless Endpoint** (named in the track text → free points), expose the public URL, point
      VITE_API_BASE at it, configure CORS for the exact frontend origin. Frontend to Cloudflare Pages / Vercel /
      Netlify free tier.
ACCEPTANCE: works from a fresh incognito window AND a phone on cellular; no localhost reference in the built
            bundle; uploads up to 12 MB succeed through the endpoint.
VERIFY: grep -rn "localhost\|127.0.0.1" frontend/dist || echo clean; curl -s $DEMO/healthz
FALLBACK: any always-free host; document the deviation in docs/DISCREPANCIES.md.
```

```
ID: B-T36  TITLE: Durability hardening + judge runbook
PHASE: 4  OWNER: devops-agent  DEPENDS_ON: B-T35  BLOCKS: G5
SPEC: No login; fixtures served from cache so the demo works even if the vision model is unreachable (degraded
      mode); ≥$10 credits unspent for judge-time runs; all dependency versions pinned; docs/JUDGE-RUNBOOK.md
      with exact steps and expected results, including how to run `make sample` offline with no API key; an
      hourly uptime ping to a Discord webhook; video public; repo public.
ACCEPTANCE: a non-teammate follows the runbook successfully; `make sample` works with no API key at all;
            uptime check running; ≥$10 credits confirmed.
```

```
ID: B-T37  TITLE: LIMITATIONS.md with real failure cases
PHASE: 4  OWNER: content-agent DEPENDS_ON: B-T24, B-T26, B-T28, B-T30  BLOCKS: G5
CONTEXT: _shared/templates/LIMITATIONS.template.md
SPEC: Real numbers and ≥4 concrete failure cases with screenshots. Must cover: per-class precision/recall and
      what the system is bad at; **the fact that the thresholds are ours, calibrated on our test set, and are
      not IPC's** — say this plainly and early; condition codes with INSUFFICIENT examples; the 20 labelling
      disagreements and what they reveal about human ambiguity; which joint types are unsupported (BGA,
      press-fit, large transformers); why uncalibrated photos abstain; the IP/affiliation disclaimer; the
      accessibility gaps and the plan; that this is not a certified inspection system and must not be used as
      the sole acceptance authority.
      Ricky + Suchismita + Aditya all said publishing failure cases reads as **rigor**.
ACCEPTANCE: every claim backed by a number, citation or screenshot; a sceptical read finds no unbacked sentence;
            the threshold-provenance statement appears in the first third of the document.
```

```
ID: B-T38  TITLE: README.md complete
PHASE: 4  OWNER: content-agent DEPENDS_ON: B-T27, B-T33, B-T23  BLOCKS: G5
CONTEXT: _shared/templates/README.template.md
SPEC: In order: the one-sentence problem; a 10-second gif of the class slider flipping a verdict; **both insider
      insights**; how NVIDIA Nemotron models are used (tiering table with real costs, incl. image tokens);
      **where Token Factory accelerated the workflow** (Sandboxes network-off validation, branching A/B, cached
      tokens, Serverless Job batch, structured output — named explicitly); other Nebius services used
      (Serverless Endpoint, Serverless Job); the A/B chart; the eval summary with kappa; a 5-minute quickstart
      **including `make sample` with no API key**; architecture diagram; the standards/IP position; data
      licences and attribution; LIMITATIONS.md and JUDGE-RUNBOOK.md links; licence.
ACCEPTANCE: clean clone + quickstart works; `make sample` runs offline; all required highlight areas present
            with real numbers; the IP disclaimer appears in the first screen.
VERIFY: git clone <url> /tmp/r && cd /tmp/r && make sample && make check
```

```
ID: B-T39  TITLE: docs/ — DECISIONS, DISCREPANCIES, DESIGN, STANDARDS-POSITION, EVAL, DATA-SOURCES
PHASE: 4  OWNER: content-agent DEPENDS_ON: B-T33  BLOCKS: G5
SPEC: DECISIONS.md = one line per decision + rejected alternative + why, including every threshold calibration
      before/after. DISCREPANCIES.md = everywhere docs or reality disagreed with assumptions (raw material for
      the Devpost feedback prize). EVAL.md = the full method.
ACCEPTANCE: ≥15 decisions; ≥3 discrepancies; EVAL.md reproducible from the committed scripts.
```

### Phase 5 — Package (Wed 16:00 → Thu 30 Oct 18:00)

```
ID: B-T40  TITLE: Video script + shot list (≤2:50)
PHASE: 5  OWNER: content-agent + human  DEPENDS_ON: G4  BLOCKS: B-T41a
CONTEXT: _shared/templates/video-script.template.md ; docs/HOOK.md
SPEC:
  0:00–0:15  the problem, in Marc's words, with the rework-cost number from B-T29 on screen and its source.
  0:15–0:35  THE CLASS INSIGHT, shown not told: one joint on screen. Drag Class 1 → ACCEPT (green).
             Drag Class 3 → REJECT (red). Same joint. Same photo. Two seconds. No narration needed.
             Caption: "Acceptability is a property of the product's reliability class, not of the joint."
  0:35–1:05  a real board: 12 joints graded, overlay boxes, a bridge caught, a measurement cell showing
             `coverage 41.3% ≥ 75%? ✗` in mono. Download the PDF report.
  1:05–1:35  THE CALIBRATION INSIGHT: show a photo with no scale → the tool ABSTAINS and says why, with a
             re-shoot instruction. Then show the printed target → it measures. Caption: "A wetting percentage
             from an uncalibrated photo is a hallucination with a decimal point."
  1:35–2:05  how it works: architecture; name the model tiers; show the Sandbox validating the PDF with the
             **network disabled**; show the sha256 match.
  2:05–2:30  the proof: the gate-on vs gate-off A/B chart at Class 3; kappa; per-class P/R/F1; the ledger incl.
             image tokens and the all-Ultra counterfactual; Ultra escalation rate.
  2:30–2:45  LIMITATIONS out loud: "these thresholds are ours, calibrated on our 300-joint set — they are not
             IPC's. Here is a joint we got wrong." Next steps incl. the accessibility plan and live camera input.
  2:45–2:50  the insight restated. Standards/IP disclaimer card.
  RULES: no copyrighted music; **no IPC material on screen**; no third-party trademarks; public YouTube;
         captions on; macro shots must be genuinely in focus (this audience will notice).
ACCEPTANCE: script reads aloud in ≤2:50; every shot numbered with an owner; the class-slider shot is unbroken.
```

```
ID: B-T41a TITLE: Shoot and edit the video
PHASE: 5  OWNER: human  DEPENDS_ON: B-T40  BLOCKS: G5
SPEC: Shoot the macro B-roll first (it needs the most light and steadiness). One pass per shot, no live editing.
      Upload PUBLIC. Verify ≤2:59 and that the link works logged-out.
ACCEPTANCE: public URL; ≤3:00; the class-slider shot is one unbroken take; captions present; macro shots in focus.
KILL CRITERION: not shot by Wed 20:00 → cut to 90 s: problem → class slider → abstention → architecture → insight.
```

```
ID: B-T41  TITLE: Devpost submission copy
PHASE: 5  OWNER: content-agent DEPENDS_ON: B-T38  BLOCKS: G5
SPEC: Title; tagline ≤80 chars; Inspiration (Marc + the rework number, sourced); What it does; How we built it
      (tiers, CV-vs-model division of labour, Sandbox network-off, branching A/B, Serverless Job/Endpoint, cached
      tokens — real numbers); Challenges (≥3, specific: calibration, near-threshold adjudication, labelling
      disagreement, image token cost); Accomplishments (the A/B delta, kappa, the escalation rate); What we
      learned (both insights + one platform learning); What's next; the required Nebius/Nemotron highlight;
      built-with tags. Every number must match the README — judges cross-check.
ACCEPTANCE: all sections present; no number disagrees with the README; the IP disclaimer appears.
```

```
ID: B-T42  TITLE: Devpost feedback section (10 × $100 + swag)
PHASE: 5  OWNER: human  DEPENDS_ON: docs/DISCREPANCIES.md  BLOCKS: G5
CONTEXT: _shared/templates/devpost-feedback.template.md
SPEC: ≥400 words, ≥6 specific points, ≥4 with numbers or quoted doc URLs, ≥1 concrete feature request.
      Strong material unique to this project: **image-token cost observability** (the ledger reports image tokens
      separately — does Token Factory expose this natively?); vision-model availability and pricing
      discoverability in the catalog; Sandboxes with large image payloads (injecting annotated crops); whether
      Sandbox image size limits affected the WeasyPrint install; rate-limit behaviour on 300 multimodal calls;
      what a branch-diff view would have saved you.
ACCEPTANCE: specific, technical, constructive; includes numbers; includes at least one thing that would help
            another builder.
```

```
ID: B-T43  TITLE: Final verification sweep + SUBMIT
PHASE: 5  OWNER: human + eval-agent  DEPENDS_ON: all  BLOCKS: —
SPEC: (1) clean clone → `make sample` offline → works, then README quickstart with a key → works;
      (2) fresh incognito → demo → verdict in ≤45 s; (3) phone on cellular; (4) class slider works on the
      deployed build; (5) video public ≤3:00; (6) LICENSE at repo root visible on the repo page;
      (7) every number identical across README / Devpost / video; (8) ≥$10 credits left; (9) uptime ping running;
      (10) LIMITATIONS present with real numbers; (11) feedback written; (12) **no IPC material anywhere**.
      Then submit. Screenshot the confirmation. Email every teammate.
ACCEPTANCE: all 12 checked in reports/B-T43.FINAL.md with evidence; submitted by Thu 29 Oct 18:00 CEST.
```

---

## 10. Test & verification plan

| Layer | What |
|---|---|
| CV unit | synthetic geometry recovery within ±5%; determinism; every null has a reason |
| Calibration | ±3% mm/px recovery on ≥9/10 fixtures; blur floor separates good from bad with zero overlap |
| Contract | every fixture validates; computable+null is a validation error; out-of-vocabulary code is an error |
| Golden | 12 boards → expected verdicts at all three classes, offline-replayed |
| Adversarial | model invents a number → rejected; model cites a null measurement → downgraded; out-of-vocabulary code → dropped; corrupted PDF → validation fails |
| Abstention | 10 bad images → 4 distinct reason codes |
| Determinism | same image + same class → identical determinism_hash across 3 runs |
| Integration | 6 concurrent uploads; regrade <200 ms |
| Eval | ≥120 (target 300) joints, double-labelled, kappa, confusion matrix per class, per-code F1, INSUFFICIENT flags |
| Calibration study | threshold sweep, Class-3 precision floor 0.90, before/after recorded |
| Experiment | Sandbox branch A/B at Class 3, n≥120 per arm |
| Load | 6 parallel users on the deployed demo |
| CI | ruff + pytest + tsc + build; `make sample` must work with NO API key |

---

## 11. Design system summary (full brief in B-T09)

**Metaphor:** an electronics inspection bench under a magnifier lamp. Dark bench, warm lamp-lit image surface,
solder-silver structure, **every number in monospace**. Hairline rules, no shadows, no pill buttons. One
annotation cyan for overlay boxes that must not collide with any verdict colour, verified against a deuteranopia
simulator.

The **ClassSlider is the hero control** — three detents, tactile, keyboard-operable, with `aria-valuetext`.
Everything else is secondary to it, because it is the thing that visually proves the insight.

---

## 12. Risk register & pivots

| # | Risk | Likelihood | Detection | Mitigation | Pivot |
|---|---|---|---|---|---|
| R1 | **No vision-capable NVIDIA open model in your catalog** | Low–Med | **B-T02, Sun 21:00** | Snapshot first; test a real image | **Fatal → switch to Idea A or C** |
| R2 | Cannot acquire enough labelled images | **High** | B-T04, Sun 22:00 | Photograph your own boards (best source); ≥120 minimum; a 60-image honest study beats a 300-image promised one | Shrink to n=60 and publish it honestly |
| R3 | CV measurements too noisy on phone photos | Med | B-T14 | Require the calibration target for measurement claims; abstain otherwise — **this is a feature, not a failure** | Fall back to CV-assisted visual grading with measurement_basis="visual_only" everywhere and say so |
| R4 | IPC IP problem | Med | B-T08, B-T43 | Own rule IDs; STANDARDS-POSITION.md; disclaimer everywhere; no IPC material in the video | Reframe as "an independent workmanship grader with published, calibrated thresholds" |
| R5 | Thresholds indefensible | Med | B-T24 | Calibrate against the double-labelled set; publish the operating point and the provenance | Report the honest precision/recall even if unflattering |
| R6 | Class relativity doesn't show in your data | Low | B-T15 (assert ≥4/12 differ) | Choose test joints near thresholds deliberately | The insight survives as an explanation even if the demo is subtler |
| R7 | Credits exhausted by 300 multimodal calls | **Med** | Ledger budget guard | Image tokens are expensive — downscale crops to ≤512 px, batch ROIs per call, Nano-first, offline test mode | Reduce to n=120 |
| R8 | Design ships generic | Med | B-T09 review | Own tokens first; forbidden list enforced; human eyeballs every screen | Cut a feature, spend the hours on UI |
| R9 | Demo dies before 15 Dec | Med | B-T36 | Offline `make sample`; degraded CV-only mode; reserved credits; judge runbook; uptime ping | Ship a downloadable build + recorded walkthrough |
| R10 | Scope creep (live camera, ONNX, fine-tuning) | **High** | Every phase gate | Component table in §3; feature freeze at Phase 4 | Cut to the hook |

---

## 13. Team allocation

| Person | Lanes | P0 | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|---|
| **P1 — CV/backend** | cv, gate | B-T01, B-T05 | B-T11, B-T12, B-T14 | B-T16, B-T18, B-T19 | B-T25 | B-T33 | B-T43 |
| **P2 — data/sandbox** | data, sandbox, jobs | B-T02, B-T04, B-T07, B-T08 | B-T15 | B-T17 | B-T21, B-T22, B-T23, B-T26 | B-T35, B-T36 | B-T41a (edit) |
| **P3 — frontend/design** | frontend | B-T03, B-T09 | B-T13 | B-T20 | B-T27 | B-T31, B-T32, B-T34 | B-T41a (shoot) |
| **P4 — eval/content/human** | eval, content | B-T06, B-T10 | — | — | B-T24, B-T28, B-T29, B-T30 | B-T37, B-T38, B-T39 | B-T40, B-T41, B-T42 |

**Critical path:** B-T04 → B-T05 → B-T14 → B-T17 → B-T18 → B-T19 → B-T20 → **G2** → B-T21 → B-T22/B-T23 →
B-T30 → B-T24 → B-T38 → B-T40 → B-T41a → submit.
**B-T04 (images) is the real bottleneck — start photographing today, in parallel with everything else.**

---

## 14. Physical AI variant (only if you have hardware and want the weaker field)

Move to the Physical AI track if you can field **any** of: a USB microscope on a stand, a Jetson, a Raspberry Pi
with a camera, a small 3-axis stage, or a relay-driven reject arm.

| Tier | Hardware | What changes | Film strength |
|---|---|---|---|
| **1 — full** | Jetson Orin Nano + USB microscope + a small reject/pick-and-place actuator | A **local small model on-device** does first-pass screening; Token Factory Ultra adjudicates near-threshold cases in the cloud; the actuator physically sorts pass/reject boards into two bins | ★★★★★ |
| **2 — camera + stage** | USB microscope on a motorised XY stage (or a cheap camera slider) | The rig auto-rasters across a board, grades each joint, and produces a full-board report — the physical part is the scanning motion | ★★★★ |
| **3 — minimum viable** | USB microscope + a relay + a red/green lamp tower | The lamp tower physically shows ACCEPT / PROCESS INDICATOR / REJECT and the relay locks a gate when a reject is found. **~€40 and one afternoon.** This satisfies "physical hardware actually operating" | ★★★ |
| **4 — no hardware** | none | Rules allow it: *"if your project has no physical hardware component — the key application modules in action."* Weakest film; you compete against 34 simulation-only entries | ★★ |

If you take Tier 1–3, add these tickets:
```
B-P1  On-device small model: run a quantised open model locally for first-pass screening; measure and publish
      local-vs-cloud latency and the accuracy delta. Johnny, verbatim: "I hope to see some project related with
      local models running to apply on physical AI." This ticket IS the track win.
B-P2  Reflex loop: the deterministic envelope (CV measurements + rule lookup) has veto authority over the
      actuator and never consults the network. Show the veto firing physically.
B-P3  Serverless Jobs for the counterfactual replay of every veto, and the veto ledger.
B-P4  ≥1 minute of continuous, well-lit footage of the hardware actually operating (rules requirement).
      Film it twice: once wide, once macro. Good audio or none.
```

**Optional stretch (only if everything else is done by Tue night):** a **LoRA fine-tune of Nemotron Nano** on
your labelled joints via Token Factory post-training (`post-training/how-to-fine-tune`, then
`merge-moe-lora-weights`). Report the before/after F1. This is exactly what won NVIDIA's Seoul Nemotron
hackathon (a synthetic-data pipeline for MoE quantization on Nemotron 3 Super) and almost nobody in this field
will have done it. High reward, real time cost — treat it as a bonus, never as a dependency.

---

## 15. Definition of Done — project level

- [ ] All tickets DONE or explicitly parked with a reason in `docs/DECISIONS.md`
- [ ] `make check` green from a clean clone; **`make sample` works with no API key**
- [ ] ≥120 (target 300) labelled joints, double-labelled, kappa published
- [ ] Per-class confusion matrices + per-code F1 published, INSUFFICIENT classes flagged
- [ ] Thresholds calibrated, before/after recorded, Class-3 precision floor addressed honestly
- [ ] A/B gate experiment published at Class 3 with n≥120 per arm
- [ ] Sandbox PDF validated **with networking disabled** and hash-verified
- [ ] All four abstention paths proven and shown on camera
- [ ] ClassSlider re-grades in <200 ms and is keyboard-operable
- [ ] Ledger covers ≥95% of calls, **image tokens reported separately**, all-Ultra counterfactual published
- [ ] ≥3 real interviews, ≥1 quote with permission, ≥1 real rework-cost number, ≥1 resulting product change
- [ ] `LIMITATIONS.md` with real failure cases and the threshold-provenance statement in its first third
- [ ] Standards/IP position stated in README, artifact footer, video and Devpost copy; **no IPC material anywhere**
- [ ] Accessibility audited, colour-blind checked, and called out in the video
- [ ] `LICENSE` at repo root; repo public; video public ≤3:00
- [ ] `docs/JUDGE-RUNBOOK.md` followed successfully by a non-teammate; ≥$10 credits reserved
- [ ] Devpost feedback written with ≥4 numbers
- [ ] **Submitted by Thu 29 Oct 18:00 CEST**
