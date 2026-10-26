"""Create deterministic, standalone HTML inspection reports without networking.

The renderer uses only the Python standard library. Thumbnail bytes are embedded
as data URIs, styles are inline, and it performs no file, URL, or SDK access, so
it can be run in a sandbox with guest networking disabled. This module does not
validate calibration or create/upgrade inspection verdicts.
"""

from __future__ import annotations

import base64
import hashlib
import html
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

_VERDICT_LABELS = {
    "ACCEPT": "PASS",
    "REJECT": "REJECT",
    "UNDETERMINED": "UNDETERMINED",
    "PROCESS_INDICATOR": "PROCESS INDICATOR",
}
_VERDICT_CLASSES = {
    "ACCEPT": "pass",
    "REJECT": "reject",
    "UNDETERMINED": "undetermined",
    "PROCESS_INDICATOR": "process-indicator",
}
_DEFAULT_ACTIONS = {
    "ACCEPT": "No rework is indicated by this verdict. Follow approved work instructions if other evidence requires action.",
    "REJECT": "Have an authorized inspector follow the organization's approved rework procedure, then re-inspect this joint.",
    "UNDETERMINED": "Hold for human inspection. Do not accept or rework solely on the basis of this undetermined result.",
    "PROCESS_INDICATOR": "Review the process condition and follow the organization's approved corrective-action procedure.",
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_or_missing_{field}")
    return html.escape(value, quote=True)


def _items(value: Any, field: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ValueError(f"invalid_{field}")
    return value


def _format_number(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if not math.isfinite(float(value)):
        return "—"
    return f"{float(value):.2f}"


def _thumbnail_uri(image_bytes: bytes) -> str:
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("thumbnail_must_be_nonempty_bytes")
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    else:
        raise ValueError("thumbnail_must_be_png_or_jpeg")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def generate_report_html(
    board_report: Mapping[str, Any],
    thumbnails: Mapping[str, bytes] | None = None,
    rework_instructions: Mapping[str, str] | None = None,
) -> tuple[bytes, str]:
    """Render a BoardReport mapping and return `(UTF-8 HTML bytes, SHA-256 hex)`.

    ``thumbnails`` maps ROI ids to PNG/JPEG bytes; bytes are embedded in the
    report, so no relative paths or network requests are needed. Optional
    ``rework_instructions`` maps ROI ids to human-approved instructions. When
    absent, the report displays a conservative routing instruction rather than
    inventing repair parameters. Input order and supplied timestamps are kept,
    and no current time or randomness is introduced, making output reproducible.
    """
    if not isinstance(board_report, Mapping):
        raise TypeError("board_report_must_be_a_mapping")
    board_id = _text(board_report.get("board_id"), "board_id")
    product_class = board_report.get("class")
    if isinstance(product_class, bool) or product_class not in (1, 2, 3):
        raise ValueError("invalid_product_class")
    generated_at = _text(board_report.get("generated_at"), "generated_at")
    rules_hash = _text(board_report.get("rules_table_version_hash"), "rules_table_version_hash")
    disclaimer = _text(board_report.get("disclaimer"), "disclaimer")
    rois = _items(board_report.get("rois"), "rois")
    measurements = _items(board_report.get("measurements"), "measurements")
    verdicts = _items(board_report.get("rule_verdicts"), "rule_verdicts")
    findings = _items(board_report.get("condition_findings", []), "condition_findings")
    gate = board_report.get("gate", {})
    if not isinstance(gate, Mapping):
        raise TypeError("invalid_gate")
    abstentions = _items(gate.get("abstentions", []), "abstentions")
    summary = board_report.get("summary", {})
    if not isinstance(summary, Mapping):
        raise TypeError("invalid_summary")
    if thumbnails is not None and not isinstance(thumbnails, Mapping):
        raise TypeError("thumbnails_must_be_a_mapping")
    if rework_instructions is not None and not isinstance(rework_instructions, Mapping):
        raise TypeError("rework_instructions_must_be_a_mapping")
    if rework_instructions is not None and any(
        not isinstance(instruction, str) or not instruction.strip()
        for instruction in rework_instructions.values()
    ):
        raise ValueError("invalid_rework_instruction")

    roi_ids: set[str] = set()
    for roi in rois:
        roi_id = roi.get("id")
        if not isinstance(roi_id, str) or not roi_id:
            raise ValueError("roi_missing_id")
        if roi_id in roi_ids:
            raise ValueError("duplicate_roi_id")
        roi_ids.add(roi_id)
    for verdict in verdicts:
        if verdict.get("roi_id") not in roi_ids:
            raise ValueError("verdict_references_unknown_roi")
        if verdict.get("class") != product_class:
            raise ValueError("verdict_class_does_not_match_report")
        if verdict.get("verdict") not in _VERDICT_LABELS:
            raise ValueError("unsupported_verdict")
    if thumbnails and set(thumbnails) - roi_ids:
        raise ValueError("thumbnail_references_unknown_roi")
    if rework_instructions and set(rework_instructions) - roi_ids:
        raise ValueError("rework_instruction_references_unknown_roi")

    measures_by_roi: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    verdicts_by_roi: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    findings_by_roi: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    abstentions_by_roi: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for measurement in measurements:
        roi_id = measurement.get("roi_id")
        if roi_id not in roi_ids:
            raise ValueError("measurement_references_unknown_roi")
        measures_by_roi[roi_id].append(measurement)
    for verdict in verdicts:
        verdicts_by_roi[verdict["roi_id"]].append(verdict)
    for finding in findings:
        roi_id = finding.get("roi_id")
        if roi_id not in roi_ids:
            raise ValueError("finding_references_unknown_roi")
        findings_by_roi[roi_id].append(finding)
    for abstention in abstentions:
        roi_id = abstention.get("roi_id")
        if roi_id in roi_ids:
            abstentions_by_roi[roi_id].append(abstention)

    sections: list[str] = []
    for roi in rois:
        roi_id = roi["id"]
        roi_id_html = _text(roi_id, "roi_id")
        joint_type = html.escape(str(roi.get("joint_type", "Not specified")), quote=True)
        thumbnail = (thumbnails or {}).get(roi_id)
        if thumbnail is None:
            image_html = '<div class="thumbnail missing" role="img" aria-label="Thumbnail unavailable">Thumbnail unavailable</div>'
        else:
            uri = _thumbnail_uri(thumbnail)
            image_html = f'<img class="thumbnail" src="{uri}" alt="Joint {roi_id_html} thumbnail">'

        roi_verdicts = verdicts_by_roi.get(roi_id, [])
        if roi_verdicts:
            chips = " ".join(
                f'<span class="chip {_VERDICT_CLASSES[v["verdict"]]}" aria-label="{_VERDICT_LABELS[v["verdict"]]}">{_VERDICT_LABELS[v["verdict"]]}</span>'
                for v in roi_verdicts
            )
        else:
            chips = '<span class="chip undetermined">UNDETERMINED</span>'

        measure_rows: list[str] = []
        for measurement in measures_by_roi.get(roi_id, []):
            quantity = measurement.get("quantity")
            value = measurement.get("value")
            unit = html.escape(str(measurement.get("unit") or ""), quote=True)
            computable = measurement.get("computable") is True
            if quantity == "wetting_angle_deg":
                name = "Wetting angle"
                display = f'{_format_number(value)} {unit}'.strip() if computable else "UNDETERMINED"
            else:
                name = str(quantity or "Measurement")
                display = f'{_format_number(value)} {unit}'.strip() if computable else "UNDETERMINED"
            reason = measurement.get("not_computable_reason")
            reason_html = f'<small>{html.escape(str(reason), quote=True)}</small>' if reason else ""
            measure_rows.append(
                f"<tr><th scope=\"row\">{html.escape(name, quote=True)}</th><td>{html.escape(display, quote=True)}{reason_html}</td></tr>"
            )
        if not measure_rows:
            measure_rows.append('<tr><th scope="row">Measurements</th><td>UNDETERMINED</td></tr>')
        measurement_table = "".join(measure_rows)

        conditions = ", ".join(
            html.escape(str(finding.get("condition_code", "")), quote=True)
            for finding in findings_by_roi.get(roi_id, [])
        ) or "No condition recorded"
        instruction = (rework_instructions or {}).get(roi_id)
        if instruction is None:
            instructions = [
                str(item.get("fix_instruction"))
                for item in abstentions_by_roi.get(roi_id, [])
                if item.get("fix_instruction")
            ]
            instruction = " ".join(instructions) if instructions else _DEFAULT_ACTIONS[
                roi_verdicts[0]["verdict"] if roi_verdicts else "UNDETERMINED"
            ]
        instruction_html = html.escape(instruction, quote=True)
        sections.append(
            f"""<article class="joint" id="{roi_id_html}">
<header><h2>Joint {roi_id_html}</h2><p>Type: {joint_type}</p><div class="chips">{chips}</div></header>
<div class="joint-body">{image_html}<div class="details"><h3>Measurements</h3>
<table><tbody>{measurement_table}</tbody></table>
<h3>Recorded conditions</h3><p>{conditions}</p>
<h3>Rework / next action</h3><p>{instruction_html}</p></div></div>
</article>"""
        )

    summary_rows = "".join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title(), quote=True)}:</strong> {html.escape(str(value), quote=True)}</li>"
        for key, value in summary.items()
    )
    abstention_html = "".join(
        f'<li><strong>{html.escape(str(item.get("reason", "abstention")), quote=True)}:</strong> '
        f'{html.escape(str(item.get("message", "Human review required.")), quote=True)} '
        f'<span>{html.escape(str(item.get("fix_instruction", "Follow approved work instructions.")), quote=True)}</span></li>'
        for item in abstentions
    )
    if not abstention_html:
        abstention_html = "<li>None recorded.</li>"

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inspection report — {board_id}</title>
<style>
:root {{ color-scheme: light; font: 15px/1.45 system-ui, sans-serif; color: #17202a; background: #fff; }}
body {{ max-width: 980px; margin: 0 auto; padding: 28px; }}
h1, h2, h3 {{ line-height: 1.2; }}
.meta, .summary {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; }}
.joint {{ border: 1px solid #aab4bf; border-radius: 8px; margin: 20px 0; padding: 16px; break-inside: avoid; }}
.joint-body {{ display: grid; grid-template-columns: minmax(150px, 260px) 1fr; gap: 20px; align-items: start; }}
.thumbnail {{ display: block; max-width: 100%; max-height: 220px; object-fit: contain; border: 1px solid #ccd2d8; }}
.thumbnail.missing {{ min-height: 100px; padding: 12px; color: #4d5966; }}
.chip {{ display: inline-block; border-radius: 999px; padding: 3px 10px; margin: 3px; font-weight: 700; border: 1px solid currentColor; }}
.pass {{ color: #176b3a; }} .reject {{ color: #a32020; }} .undetermined {{ color: #654b00; }} .process-indicator {{ color: #7049a0; }}
table {{ border-collapse: collapse; width: 100%; }} th, td {{ text-align: left; border-bottom: 1px solid #d7dce1; padding: 7px; }}
small {{ display: block; color: #5b6570; }} .abstentions {{ border-left: 5px solid #b17a00; padding: 8px 16px; background: #fff8e6; }}
footer {{ border-top: 1px solid #aab4bf; margin-top: 28px; padding-top: 12px; font-size: 0.9rem; }}
@page {{ size: A4; margin: 14mm; }}
@media print {{ body {{ max-width: none; padding: 0; }} .joint {{ break-inside: avoid; }} a {{ color: inherit; text-decoration: none; }} }}
@media (max-width: 620px) {{ body {{ padding: 14px; }} .joint-body, .meta, .summary {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header><h1>Inspection report</h1><div class="meta">
<p><strong>Board:</strong> {board_id}</p>
<p><strong>Product class:</strong> {product_class}</p><p><strong>Generated:</strong> {generated_at}</p>
<p><strong>Rules table SHA-256:</strong> <code>{rules_hash}</code></p>
</div></header>
<section aria-labelledby="summary-title"><h2 id="summary-title">Summary</h2><ul class="summary">{summary_rows or '<li>No summary supplied.</li>'}</ul></section>
<section aria-labelledby="joints-title"><h2 id="joints-title">Joint findings</h2>{''.join(sections) or '<p>No joint regions were supplied.</p>'}</section>
<section class="abstentions" aria-labelledby="abstentions-title"><h2 id="abstentions-title">Abstentions and human review</h2><ul>{abstention_html}</ul></section>
<footer><strong>Disclaimer</strong><p>{disclaimer}</p><p>Standalone report; thumbnails are embedded. No network resources are referenced.</p></footer>
</body>
</html>
"""
    report_bytes = document.encode("utf-8")
    return report_bytes, hashlib.sha256(report_bytes).hexdigest()
