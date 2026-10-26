"""Synthetic BoardReport inputs for the deterministic offline HTML renderer."""

import hashlib
import struct
import zlib
from html.parser import HTMLParser

import pytest

from app.sandbox.report import generate_report_html


def _png_1x1() -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        content = kind + payload
        return (
            struct.pack(">I", len(payload))
            + content
            + struct.pack(">I", zlib.crc32(content) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + chunk(b"IEND", b"")
    )


def _board_report(product_class: int = 2, verdict: str = "ACCEPT") -> dict:
    return {
        "report_id": "rep_synthetic_01",
        "board_id": "board <sample>",
        "class": product_class,
        "generated_at": "2026-10-26T12:00:00Z",
        "rules_table_version_hash": "a" * 64,
        "rois": [{"id": "j_001", "joint_type": "smd_gull_wing"}],
        "measurements": [
            {
                "id": "m_001",
                "roi_id": "j_001",
                "quantity": "wetting_angle_deg",
                "value": 45.0,
                "unit": "deg",
                "computable": True,
            }
        ],
        "condition_findings": [
            {"roi_id": "j_001", "condition_code": "INSUFFICIENT_WETTING"}
        ],
        "rule_verdicts": [
            {
                "id": "v_001",
                "roi_id": "j_001",
                "class": product_class,
                "verdict": verdict,
                "rule_id": "JC-WET-001",
            }
        ],
        "gate": {"abstentions": []},
        "summary": {"total_joints": 1, "accept": int(verdict == "ACCEPT")},
        "disclaimer": "Synthetic demonstration; not a certified inspection.",
    }


class _ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.image_sources = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "img":
            self.image_sources.append(dict(attrs).get("src", ""))


def test_report_is_standalone_printable_and_hashes_exact_bytes_deterministically():
    report = _board_report()
    thumbnails = {"j_001": _png_1x1()}
    instructions = {"j_001": "Follow the approved rework procedure."}

    first_bytes, first_hash = generate_report_html(report, thumbnails, instructions)
    second_bytes, second_hash = generate_report_html(report, thumbnails, instructions)

    assert first_bytes == second_bytes
    assert first_hash == second_hash == hashlib.sha256(first_bytes).hexdigest()
    assert first_bytes.startswith(b"<!doctype html>")
    text = first_bytes.decode("utf-8")
    assert "@media print" in text
    assert "Wetting angle" in text and "45.00 deg" in text
    assert "PASS" in text
    assert "Follow the approved rework procedure." in text
    assert "board &lt;sample&gt;" in text
    assert "https://" not in text and "http://" not in text

    parser = _ReportParser()
    parser.feed(text)
    parser.close()
    assert "html" in parser.tags and "article" in parser.tags and "table" in parser.tags
    assert len(parser.image_sources) == 1
    assert parser.image_sources[0].startswith("data:image/png;base64,")


def test_report_renders_class_specific_reject_and_human_abstention():
    report = _board_report(product_class=3, verdict="REJECT")
    report["gate"]["abstentions"] = [
        {
            "roi_id": "j_001",
            "reason": "image_quality_insufficient",
            "message": "The crop is too blurry.",
            "fix_instruction": "Capture a sharp, well-lit close-up.",
        }
    ]
    data, _ = generate_report_html(report)
    text = data.decode("utf-8")
    assert "Product class:</strong> 3" in text
    assert "REJECT" in text
    assert "Capture a sharp, well-lit close-up." in text
    assert "Follow the organization's approved rework procedure" not in text


def test_report_rejects_class_mismatch_unknown_roi_and_invalid_thumbnail():
    report = _board_report()
    report["rule_verdicts"][0]["class"] = 3
    with pytest.raises(ValueError, match="verdict_class_does_not_match_report"):
        generate_report_html(report)

    report = _board_report()
    report["rule_verdicts"][0]["roi_id"] = "j_missing"
    with pytest.raises(ValueError, match="verdict_references_unknown_roi"):
        generate_report_html(report)

    with pytest.raises(ValueError, match="thumbnail_must_be_png_or_jpeg"):
        generate_report_html(_board_report(), {"j_001": b"not an image"})


def test_report_requires_disclaimer_and_unique_roi_ids():
    report = _board_report()
    report["disclaimer"] = ""
    with pytest.raises(ValueError, match="invalid_or_missing_disclaimer"):
        generate_report_html(report)

    report = _board_report()
    report["rois"].append({"id": "j_001", "joint_type": "through_hole"})
    with pytest.raises(ValueError, match="duplicate_roi_id"):
        generate_report_html(report)
