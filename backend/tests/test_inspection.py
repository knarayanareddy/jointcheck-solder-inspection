import json
import struct
import zlib
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient
from jsonschema import validate

from app import main
from app.config import settings
from app.main import app

client = TestClient(app)


def _synthetic_photo() -> bytes:
    image = np.full((480, 640, 3), 90, dtype=np.uint8)
    cv2.rectangle(image, (140, 130), (330, 250), (210, 210, 210), thickness=4)
    cv2.rectangle(image, (185, 170), (285, 215), (155, 155, 155), thickness=-1)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def test_packaged_condition_catalog_matches_source():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert (root / "backend/app/vision/condition-codes.json").read_bytes() == (
        root / "data/condition-codes.json"
    ).read_bytes()


def test_inspection_decodes_photo_and_always_abstains():
    response = client.post(
        "/v1/inspect?product_class=3",
        content=_synthetic_photo(),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "analysis_complete"
    assert result["product_class"] == 3
    assert result["image"]["width"] == 640
    assert result["image"]["height"] == 480
    assert result["image"]["calibrated"] is False
    assert result["candidate_count"] >= 1
    region = result["candidate_regions"][0]
    assert region["interpretation"] == "unclassified_contour_candidate"
    assert {item["quantity"] for item in region["measurements"]} == {
        "wetting_angle_deg",
        "solder_coverage_pct",
        "bridge_gap_mm",
    }
    assert all(item["computable"] is False for item in region["measurements"])
    schema_path = Path(__file__).resolve().parents[2] / "schemas/core-schemas.json"
    measurement_schema = json.loads(schema_path.read_text(encoding="utf-8"))["$defs"]["Measurement"]
    for measurement in region["measurements"]:
        validate(instance=measurement, schema=measurement_schema)
    assert region["geometry_diagnostics"][0]["name"] == "fillet_concavity"
    assert region["geometry_diagnostics"][0]["computable"] is False
    assert all(item["verdict"] == "UNDETERMINED" for item in region["rule_verdicts"])
    assert all(
        item["reason"] == "uncalibrated"
        for item in region["rule_verdicts"]
        if "rule_id" in item
    )
    assert result["grading"]["verdict"] == "UNDETERMINED"
    assert result["grading"]["actionable"] is False
    assert result["model_assistance"]["status"] == "not_requested"


def test_blurry_photo_fails_quality_floor_and_does_not_produce_actionable_grade():
    image = np.full((480, 640, 3), 90, dtype=np.uint8)
    cv2.rectangle(image, (140, 130), (330, 250), (210, 210, 210), thickness=4)
    image = cv2.GaussianBlur(image, (0, 0), sigmaX=20)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    response = client.post(
        "/v1/inspect",
        content=encoded.tobytes(),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["quality"]["blur_check"] == "fail"
    assert result["quality"]["usable"] is False
    assert result["grading"]["verdict"] == "UNDETERMINED"
    assert result["grading"]["actionable"] is False


def test_inspection_model_is_opt_in_and_reports_missing_configuration(monkeypatch):
    monkeypatch.setattr(settings, "nebius_api_key", "")
    response = client.post(
        "/v1/inspect?model_assist=true",
        content=_synthetic_photo(),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["model_assistance"]["status"] == "not_configured"
    assert result["grading"]["verdict"] == "UNDETERMINED"


def test_model_suggestions_flow_into_report_but_never_into_grading(monkeypatch):
    async def fake_model_assistance(image_bytes, media_type, candidate_regions):
        assert image_bytes.startswith(b"\xff\xd8\xff")
        assert media_type == "image/jpeg"
        assert candidate_regions
        return {
            "status": "complete",
            "model": "mock/vision",
            "observations": [
                {
                    "region_id": candidate_regions[0]["region_id"],
                    "joint_type": "through_hole",
                    "condition_codes": ["INSUFFICIENT_WETTING"],
                    "confidence": 0.75,
                    "note": "Synthetic advisory only.",
                    "review_required": True,
                }
            ],
            "review_required": True,
        }

    monkeypatch.setattr(settings, "nebius_api_key", "configured-for-test")
    monkeypatch.setattr(main, "request_visual_suggestions", fake_model_assistance)
    response = client.post(
        "/v1/inspect?model_assist=true",
        content=_synthetic_photo(),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 200
    report = response.json()
    assert report["model_assistance"]["status"] == "complete"
    assert report["model_assistance"]["observations"][0]["review_required"] is True
    assert report["grading"]["verdict"] == "UNDETERMINED"
    assert report["grading"]["actionable"] is False


def test_inspection_rejects_oversized_png_before_pixel_decode():
    width, height = 50_000, 1_000
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    def png_chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return (
            struct.pack(">I", len(data))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", b"")
        + png_chunk(b"IEND", b"")
    )
    response = client.post(
        "/v1/inspect", content=png, headers={"content-type": "image/png"}
    )
    assert response.status_code == 413


def test_inspection_rejects_wrong_media_type_and_corrupt_photo():
    wrong_type = client.post(
        "/v1/inspect", content=b"not image", headers={"content-type": "text/plain"}
    )
    assert wrong_type.status_code == 415

    corrupt = client.post(
        "/v1/inspect",
        content=b"\xff\xd8\xffnot a jpeg",
        headers={"content-type": "image/jpeg"},
    )
    assert corrupt.status_code == 422
