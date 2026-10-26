"""Image-quality metrics and uncalibrated contour proposals.

These heuristics are useful for demonstrating an image-to-report flow; they are
not a validated solder-joint detector and never produce solder measurements.
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.gate.gate import RULES_PATH

MAX_DECODED_PIXELS = 40_000_000
MAX_CANDIDATES = 50


def _quality_floors() -> dict[str, float]:
    with RULES_PATH.open(encoding="utf-8") as rules_file:
        rules = json.load(rules_file)
    floors = rules.get("image_quality_floors", {})
    return {
        "blur_laplacian_var_min": float(floors.get("blur_laplacian_var_min", 60)),
        "exposure_clipped_pct_max": float(floors.get("exposure_clipped_pct_max", 8)),
        "min_roi_px": float(floors.get("min_roi_px", 48)),
    }


def _intersection_over_union(
    first: tuple[int, int, int, int], second: tuple[int, int, int, int]
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[0] + first[2], second[0] + second[2])
    y2 = min(first[1] + first[3], second[1] + second[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = first[2] * first[3] + second[2] * second[3] - intersection
    return intersection / union if union else 0.0


def analyze_image(image_bytes: bytes) -> dict[str, Any]:
    """Decode an uploaded image and return conservative CV features and proposals."""
    if not image_bytes:
        raise ValueError("empty_image")
    try:
        # Read dimensions from headers before allocating the decoded pixel buffer;
        # compressed image bombs must be rejected before OpenCV expands them.
        with Image.open(BytesIO(image_bytes)) as header_image:
            if header_image.format not in {"JPEG", "PNG"}:
                raise ValueError("unsupported_or_corrupt_image")
            width, height = header_image.size
            if width * height > MAX_DECODED_PIXELS:
                raise ValueError("decoded_image_too_large")
            if width < 32 or height < 32:
                raise ValueError("image_dimensions_too_small")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("unsupported_or_corrupt_image") from exc

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("unsupported_or_corrupt_image")

    height, width = image.shape[:2]
    if width < 32 or height < 32:
        raise ValueError("image_dimensions_too_small")
    if width * height > MAX_DECODED_PIXELS:
        raise ValueError("decoded_image_too_large")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    clipped_pixels = int(np.count_nonzero((gray <= 2) | (gray >= 253)))
    clipped_pct = 100.0 * clipped_pixels / float(width * height)
    floors = _quality_floors()
    blur_ok = blur_variance >= floors["blur_laplacian_var_min"]
    exposure_ok = clipped_pct <= floors["exposure_clipped_pct_max"]

    # Contours propose regions only. The shape heuristics are intentionally not
    # interpreted as joint type or defect evidence.
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    minimum = int(floors["min_roi_px"])
    image_area = width * height
    proposals: list[tuple[float, tuple[int, int, int, int], Any]] = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if box_width < minimum or box_height < minimum:
            continue
        box_area = box_width * box_height
        if box_area > image_area * 0.20 or box_area < minimum * minimum:
            continue
        aspect = box_width / float(box_height)
        if not 0.25 <= aspect <= 4.0:
            continue
        contour_area = float(cv2.contourArea(contour))
        if contour_area < minimum * minimum * 0.25:
            continue
        proposals.append((contour_area, (x, y, box_width, box_height), contour))

    proposals.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[float, tuple[int, int, int, int], Any]] = []
    for proposal in proposals:
        if all(
            _intersection_over_union(proposal[1], accepted[1]) < 0.60
            for accepted in selected
        ):
            selected.append(proposal)
        if len(selected) >= MAX_CANDIDATES:
            break

    regions: list[dict[str, Any]] = []
    for index, (area, (x, y, box_width, box_height), contour) in enumerate(
        selected, start=1
    ):
        crop = image[y : y + box_height, x : x + box_width]
        perimeter = float(cv2.arcLength(contour, True))
        hull_area = float(cv2.contourArea(cv2.convexHull(contour)))
        hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        region_gray = gray[y : y + box_height, x : x + box_width]
        regions.append(
            {
                "region_id": f"cv_{index:03d}",
                "bbox_px": {"x": x, "y": y, "width": box_width, "height": box_height},
                "features": {
                    "contour_area_px": round(area, 2),
                    "perimeter_px": round(perimeter, 2),
                    "aspect_ratio": round(box_width / float(box_height), 4),
                    "solidity": round(area / hull_area, 4) if hull_area else 0.0,
                    "mean_gray": round(float(region_gray.mean()), 2),
                    "mean_saturation": round(float(hsv_crop[:, :, 1].mean()), 2),
                    "edge_density_pct": round(
                        100.0
                        * float(
                            np.count_nonzero(
                                edges[y : y + box_height, x : x + box_width]
                            )
                        )
                        / float(box_width * box_height),
                        2,
                    ),
                },
                "crop_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
                "interpretation": "unclassified_contour_candidate",
            }
        )

    return {
        "image": {
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "width": width,
            "height": height,
            "decoded_pixels": width * height,
            "calibrated": False,
        },
        "quality": {
            "blur_laplacian_var": round(blur_variance, 4),
            "blur_floor": floors["blur_laplacian_var_min"],
            "blur_check": "pass" if blur_ok else "fail",
            "exposure_clipped_pct": round(clipped_pct, 4),
            "exposure_floor_pct_max": floors["exposure_clipped_pct_max"],
            "exposure_check": "pass" if exposure_ok else "fail",
            "prototype_quality_checks_passed": blur_ok and exposure_ok,
            "thresholds_validated": False,
        },
        "candidate_regions": regions,
        "candidate_count": len(regions),
        "disclaimer": (
            "Contour candidates and image-quality thresholds are experimental. "
            "They are not validated joint detection or solder-quality measurements."
        ),
    }
