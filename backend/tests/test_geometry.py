"""SYNTHETIC geometry fixtures; these are algorithm tests, not calibration data."""

import json

import cv2
import numpy as np
import pytest

from app.gate.gate import RULES_PATH, DeterministicGate
from app.vision.geometry import (
    measure_bridge_gap_mm,
    measure_fillet_concavity,
    measure_solder_coverage_pct,
    measure_wetting_angle_deg,
)


def _profile_mask(slope: float, quadratic: float) -> tuple[np.ndarray, tuple[int, int]]:
    """Render an analytic synthetic solder profile against a horizontal pad plane."""
    contact_x, contact_y = 20, 70
    max_u = 32
    top = []
    for u in range(max_u + 1):
        height = slope * u + quadratic * u * u
        top.append((contact_x + u, int(np.rint(contact_y - height))))
    polygon = np.asarray(
        top + [(contact_x + max_u, contact_y + 25), (contact_x, contact_y + 25)],
        dtype=np.int32,
    )
    mask = np.zeros((128, 128), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    return mask, (contact_x, contact_y)


def test_wetting_angle_recovers_synthetic_contact_angle_below_90():
    mask, contact = _profile_mask(slope=0.6, quadratic=0.0)
    result = measure_wetting_angle_deg(
        mask,
        ((0, contact[1]), (100, contact[1])),
        contact,
        inward_direction=1,
        normal_direction=-1,
    )
    assert result["computable"] is True
    assert result["value"] is not None and result["value"] < 90
    assert result["value"] == pytest.approx(np.degrees(np.arctan(0.6)), abs=4.5)
    assert len(result["pixel_evidence"]["mask_sha256"]) == 64


def test_sub_90_degree_synthetic_wetting_angle_passes_test_only_gate(tmp_path):
    mask, contact = _profile_mask(slope=0.6, quadratic=0.0)
    measurement = measure_wetting_angle_deg(
        mask,
        ((0, contact[1]), (100, contact[1])),
        contact,
        inward_direction=1,
        normal_direction=-1,
    )
    assert measurement["value"] < 90
    test_rule = {
        "rule_id": "JC-TEST-WET",
        "condition_code": "INSUFFICIENT_WETTING",
        "human_reviewed": True,
        "requires_calibration": True,
        "class_thresholds": {
            "2": {
                "metric": "wetting_angle_deg",
                "op": "<",
                "value": 90.0,
                "verdict_if_met": "ACCEPT",
            }
        },
        "verdict_if_not_met": "REJECT",
    }
    rules_path = tmp_path / "synthetic-wetting-rule.json"
    rules_path.write_text(json.dumps({"rules": [test_rule]}), encoding="utf-8")
    result = DeterministicGate.evaluate(
        "JC-TEST-WET",
        {
            "class": 2,
            "calibrated": True,
            "measurement": {**measurement, "roi_id": "j_synthetic_wet"},
        },
        rules_path,
        trusted_measurement=True,
    )
    assert result["verdict"] == "ACCEPT"


def test_synthetic_full_coverage_passes_all_class_thresholds_test_only(tmp_path):
    image = np.full((20, 20, 3), 180, dtype=np.uint8)
    pad = np.ones((20, 20), dtype=np.uint8) * 255
    measurement = measure_solder_coverage_pct(image, pad)
    assert measurement["value"] == 100.0

    document = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    wetting_rule = next(rule for rule in document["rules"] if rule["rule_id"] == "JC-WET-001")
    wetting_rule["human_reviewed"] = True  # test-only synthetic assertion
    rules_path = tmp_path / "synthetic-coverage-rules.json"
    rules_path.write_text(json.dumps({"rules": [wetting_rule]}), encoding="utf-8")
    for product_class in (1, 2, 3):
        result = DeterministicGate.evaluate(
            "JC-WET-001",
            {
                "class": product_class,
                "calibrated": True,
                "measurement": {**measurement, "roi_id": f"j_synthetic_class_{product_class}"},
            },
            rules_path,
            trusted_measurement=True,
        )
        assert result["verdict"] == "ACCEPT"


def test_coverage_uses_gray_alloy_and_specular_pixels_within_pad_only():
    image = np.full((20, 20, 3), 40, dtype=np.uint8)
    pad = np.ones((20, 20), dtype=np.uint8) * 255
    image[:5, :] = (180, 180, 180)  # synthetic gray alloy: 100 pixels
    image[5:10, :] = (255, 255, 255)  # synthetic specular area: 100 pixels
    pad[:, :10] = 0  # exclude half of the solder-colored region

    result = measure_solder_coverage_pct(image, pad)
    assert result["computable"] is True
    assert result["value"] == 50.0
    assert result["unit"] == "%"
    assert result["pixel_evidence"]["mask_sha256"]


def test_concavity_sign_distinguishes_synthetic_meniscus_from_convex_blob():
    concave_mask, contact = _profile_mask(slope=0.05, quadratic=0.008)
    convex_mask, _ = _profile_mask(slope=0.5, quadratic=-0.006)
    plane = ((0, contact[1]), (100, contact[1]))
    concave = measure_fillet_concavity(concave_mask, plane, contact)
    convex = measure_fillet_concavity(convex_mask, plane, contact)
    assert concave["computable"] is True
    assert convex["computable"] is True
    assert concave["value"] > 0
    assert convex["value"] < 0


def test_missing_pad_reference_and_blurry_quality_inputs_abstain():
    mask, contact = _profile_mask(slope=0.6, quadratic=0.0)
    no_plane = measure_wetting_angle_deg(mask, None, contact)
    assert no_plane["computable"] is False
    assert no_plane["value"] is None
    assert no_plane["not_computable_reason"] == "reference_not_visible"

    image = np.full((128, 128, 3), 90, dtype=np.uint8)
    empty_pad = np.zeros((128, 128), dtype=np.uint8)
    no_coverage = measure_solder_coverage_pct(image, empty_pad)
    assert no_coverage["computable"] is False
    assert no_coverage["not_computable_reason"] == "insufficient_resolution"


def test_synthetic_bridge_measurement_rejects_under_existing_rule_id(tmp_path):
    """SYNTHETIC geometry and a test-only reviewed rule; not calibration data."""
    solder = np.zeros((60, 120), dtype=np.uint8)
    pad_a = np.zeros_like(solder)
    pad_b = np.zeros_like(solder)
    pad_a[20:40, 10:40] = 255
    pad_b[20:40, 80:110] = 255
    solder[25:35, 20:100] = 255  # one connected feature bridges adjacent pads
    measurement = measure_bridge_gap_mm(
        solder, pad_a, pad_b, mm_per_px=0.05
    )
    assert measurement["computable"] is True
    assert measurement["value"] == 0.0

    document = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    bridge_rule = next(rule for rule in document["rules"] if rule["rule_id"] == "JC-BRD-001")
    bridge_rule["human_reviewed"] = True  # test-only; source rule remains unreviewed
    rules_path = tmp_path / "synthetic-rules.json"
    rules_path.write_text(json.dumps({"rules": [bridge_rule]}), encoding="utf-8")
    assertion = {
        "class": 2,
        "calibrated": True,
        "measurement": {
            **measurement,
            "roi_id": "j_synthetic_bridge",
        },
    }
    result = DeterministicGate.evaluate(
        "JC-BRD-001", assertion, rules_path, trusted_measurement=True
    )
    assert result["verdict"] == "REJECT"
    assert result["condition_code"] == "SOLDER_BRIDGE"


def test_bridge_measurement_abstains_without_calibration_or_both_pad_references():
    solder = np.zeros((32, 64), dtype=np.uint8)
    pad_a = np.zeros_like(solder)
    pad_b = np.zeros_like(solder)
    pad_a[10:20, 5:20] = 255
    pad_b[10:20, 40:55] = 255
    solder[12:18, 8:15] = 255
    solder[12:18, 43:50] = 255

    uncalibrated = measure_bridge_gap_mm(solder, pad_a, pad_b, mm_per_px=None)
    assert uncalibrated["computable"] is False
    assert uncalibrated["not_computable_reason"] == "uncalibrated"
    missing_second_pad = measure_bridge_gap_mm(
        solder, pad_a, np.zeros_like(pad_b), mm_per_px=0.05
    )
    assert missing_second_pad["computable"] is False
    assert missing_second_pad["not_computable_reason"] == "segmentation_ambiguous"


def test_wet_angle_uncomputable_measurements_have_evidence_field():
    result = measure_wetting_angle_deg(None, None, None)
    assert result["computable"] is False
    assert result["value"] is None
    assert isinstance(result["pixel_evidence"], dict)
