"""Deterministic geometric measurements from explicitly supplied pixel masks.

These functions do not discover pad or solder masks. Callers must provide
segmentation from an upstream stage; absent/ambiguous geometry is returned as
non-computable rather than inferred from a contour-box crop.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

import cv2
import numpy as np

# TODO_VERIFY(B-T24): tune these provisional pixel-screen cutoffs and minimum pad area against the double-labelled set.
GRAY_ALLOY_MAX_SATURATION = 70
GRAY_ALLOY_MIN_VALUE = 90
SPECULAR_MIN_VALUE = 220
SPECULAR_MAX_SATURATION = 100
MIN_PAD_PIXELS = 16


def _as_mask(mask: np.ndarray | None) -> np.ndarray | None:
    if mask is None:
        return None
    array = np.asarray(mask)
    if array.ndim != 2 or array.size == 0:
        return None
    return (array > 0).astype(np.uint8)


def _evidence(*masks: np.ndarray | None) -> dict[str, str]:
    digest = hashlib.sha256()
    found = False
    for mask in masks:
        normalized = _as_mask(mask)
        if normalized is None:
            continue
        found = True
        digest.update(np.asarray(normalized.shape, dtype=np.int64).tobytes())
        digest.update(normalized.tobytes())
    return {"mask_sha256": digest.hexdigest()} if found else {}


def _measurement(
    quantity: str,
    value: float | None,
    unit: str,
    reason: str | None,
    derivation: str,
    *masks: np.ndarray | None,
) -> dict[str, Any]:
    return {
        "quantity": quantity,
        "value": value,
        "unit": unit,
        "computable": reason is None and value is not None,
        "not_computable_reason": reason,
        "derivation": derivation,
        "pixel_evidence": _evidence(*masks),
    }


def _local_surface_fit(
    solder_mask: np.ndarray | None,
    pad_plane: tuple[tuple[float, float], tuple[float, float]] | None,
    contact_point: tuple[float, float] | None,
    inward_direction: int,
    normal_direction: int,
    fit_window_px: float,
) -> tuple[np.ndarray, float, float] | None:
    mask = _as_mask(solder_mask)
    if (
        mask is None
        or pad_plane is None
        or contact_point is None
        or inward_direction not in (-1, 1)
        or normal_direction not in (-1, 1)
        or not math.isfinite(fit_window_px)
        or fit_window_px < 5
    ):
        return None

    p1 = np.asarray(pad_plane[0], dtype=np.float64)
    p2 = np.asarray(pad_plane[1], dtype=np.float64)
    contact = np.asarray(contact_point, dtype=np.float64)
    if p1.shape != (2,) or p2.shape != (2,) or contact.shape != (2,):
        return None
    if not np.all(np.isfinite(np.concatenate((p1, p2, contact)))):
        return None
    plane_vector = p2 - p1
    plane_length = float(np.linalg.norm(plane_vector))
    if plane_length < 5:
        return None

    tangent = plane_vector / plane_length * inward_direction
    normal = np.asarray((-tangent[1], tangent[0])) * normal_direction
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    contour = min(
        contours,
        key=lambda item: float(
            np.min(np.linalg.norm(item.reshape(-1, 2).astype(np.float64) - contact, axis=1))
        ),
    )
    points = contour.reshape(-1, 2).astype(np.float64)
    if float(np.min(np.linalg.norm(points - contact, axis=1))) > 2.0:
        return None

    relative = points - contact
    u = relative @ tangent
    v = relative @ normal
    near_surface = (u >= -0.75) & (u <= fit_window_px) & (v >= -2.0) & (v <= fit_window_px)
    local_u = u[near_surface]
    local_v = v[near_surface]
    if local_u.size < 6 or np.unique(np.round(local_u, 1)).size < 4:
        return None

    try:
        quadratic, linear, _ = np.polyfit(local_u, local_v, deg=2)
    except (np.linalg.LinAlgError, ValueError, FloatingPointError):
        return None
    if not math.isfinite(float(quadratic)) or not math.isfinite(float(linear)):
        return None
    return mask, float(quadratic), float(linear)


def measure_wetting_angle_deg(
    solder_mask: np.ndarray | None,
    pad_plane: tuple[tuple[float, float], tuple[float, float]] | None,
    contact_point: tuple[float, float] | None,
    *,
    inward_direction: int = 1,
    normal_direction: int = -1,
    fit_window_px: float = 24.0,
) -> dict[str, Any]:
    """Fit a quadratic to the local free-surface contour and report its angle.

    ``pad_plane`` gives two pixel coordinates on the pad plane. ``contact_point``
    identifies the solder/pad contact. ``inward_direction`` chooses which way
    along that plane points into the joint; ``normal_direction`` selects the
    side of the plane occupied by the free solder surface. The returned angle
    is in degrees in [0, 180]. These conventions make the geometry explicit
    rather than guessing which edge is the pad from a generic contour.
    """
    fitted = _local_surface_fit(
        solder_mask,
        pad_plane,
        contact_point,
        inward_direction,
        normal_direction,
        fit_window_px,
    )
    if fitted is None:
        return _measurement(
            "wetting_angle_deg",
            None,
            "deg",
            "reference_not_visible" if solder_mask is not None else "segmentation_ambiguous",
            "Polynomial tangent fit requires a solder mask, a visible pad-plane line, and a contact point.",
            solder_mask,
        )

    mask, _, slope = fitted
    angle = math.degrees(math.atan2(slope, 1.0))
    if angle < 0:
        angle += 180.0
    return _measurement(
        "wetting_angle_deg",
        round(float(angle), 4),
        "deg",
        None,
        f"Quadratic contour fit at the supplied contact point; tangent slope={slope:.6f} px/px.",
        mask,
    )


def measure_solder_coverage_pct(
    image_bgr: np.ndarray | None,
    pad_mask: np.ndarray | None,
    *,
    solder_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Return solder-colour pixel coverage within an explicitly segmented pad.

    If no solder mask is supplied, an experimental HSV screen counts low-
    saturation gray alloy and low-saturation specular pixels. The caller still
    owns pad segmentation; this heuristic is not a calibrated classifier.
    """
    pad = _as_mask(pad_mask)
    image = None if image_bgr is None else np.asarray(image_bgr)
    provided_solder = _as_mask(solder_mask)
    if pad is None or image is None or image.ndim != 3 or image.shape[2] != 3:
        return _measurement(
            "solder_coverage_pct",
            None,
            "%",
            "segmentation_ambiguous",
            "Coverage requires a BGR image and a 2-D pad mask.",
            pad_mask,
            solder_mask,
        )
    if image.dtype != np.uint8 or image.shape[:2] != pad.shape:
        return _measurement(
            "solder_coverage_pct",
            None,
            "%",
            "segmentation_ambiguous",
            "Image and pad-mask dimensions or pixel type do not match.",
            pad,
            solder_mask,
        )
    pad_pixels = int(np.count_nonzero(pad))
    if pad_pixels < MIN_PAD_PIXELS:
        return _measurement(
            "solder_coverage_pct",
            None,
            "%",
            "insufficient_resolution",
            f"Pad mask contains {pad_pixels} pixels; at least {MIN_PAD_PIXELS} are required.",
            pad,
            solder_mask,
        )

    if provided_solder is not None:
        if provided_solder.shape != pad.shape:
            return _measurement(
                "solder_coverage_pct",
                None,
                "%",
                "segmentation_ambiguous",
                "Solder and pad masks have different dimensions.",
                pad,
                solder_mask,
            )
        solder_pixels = provided_solder
        derivation = "100 × (solder mask ∩ pad mask pixels) / pad-mask pixels."
    else:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        gray_alloy = (saturation <= GRAY_ALLOY_MAX_SATURATION) & (value >= GRAY_ALLOY_MIN_VALUE)
        specular = (saturation <= SPECULAR_MAX_SATURATION) & (value >= SPECULAR_MIN_VALUE)
        solder_pixels = (gray_alloy | specular).astype(np.uint8)
        derivation = (
            "100 × low-saturation gray/specular pixels intersecting the supplied pad mask "
            "/ pad-mask pixels; HSV screen is experimental."
        )

    intersection = int(np.count_nonzero((solder_pixels > 0) & (pad > 0)))
    coverage = 100.0 * intersection / pad_pixels
    evidence_mask = ((solder_pixels > 0) & (pad > 0)).astype(np.uint8)
    return _measurement(
        "solder_coverage_pct",
        round(float(coverage), 4),
        "%",
        None,
        derivation,
        pad,
        evidence_mask,
    )


def measure_bridge_gap_mm(
    solder_mask: np.ndarray | None,
    pad_mask_a: np.ndarray | None,
    pad_mask_b: np.ndarray | None,
    *,
    mm_per_px: float | None,
) -> dict[str, Any]:
    """Measure the closest solder-component clearance between two pad masks.

    A connected solder component touching both pad masks is a bridge and has
    zero gap. Separate components report their nearest-pixel distance, scaled
    by the supplied calibration. This requires caller-provided pad and solder
    segmentations; the generic contour proposal stage does not create them.
    """
    solder = _as_mask(solder_mask)
    pad_a = _as_mask(pad_mask_a)
    pad_b = _as_mask(pad_mask_b)
    evidence_masks = (solder, pad_a, pad_b)
    if (
        solder is None
        or pad_a is None
        or pad_b is None
        or solder.shape != pad_a.shape
        or solder.shape != pad_b.shape
    ):
        return _measurement(
            "bridge_gap_mm",
            None,
            "mm",
            "segmentation_ambiguous",
            "Bridge gap requires same-sized solder and two pad masks.",
            *evidence_masks,
        )
    if (
        isinstance(mm_per_px, bool)
        or not isinstance(mm_per_px, (int, float))
        or not math.isfinite(float(mm_per_px))
        or mm_per_px <= 0
    ):
        return _measurement(
            "bridge_gap_mm",
            None,
            "mm",
            "uncalibrated",
            "A positive finite mm_per_px calibration is required for a millimetre gap.",
            *evidence_masks,
        )

    component_count, labels = cv2.connectedComponents(solder, connectivity=8)
    if component_count <= 1:
        return _measurement(
            "bridge_gap_mm",
            None,
            "mm",
            "segmentation_ambiguous",
            "No solder components were found in the supplied solder mask.",
            *evidence_masks,
        )
    components_a, counts_a = np.unique(labels[pad_a > 0], return_counts=True)
    components_b, counts_b = np.unique(labels[pad_b > 0], return_counts=True)
    components_a = {int(label) for label, count in zip(components_a, counts_a) if label > 0 and count > 0}
    components_b = {int(label) for label, count in zip(components_b, counts_b) if label > 0 and count > 0}
    if not components_a or not components_b:
        return _measurement(
            "bridge_gap_mm",
            None,
            "mm",
            "segmentation_ambiguous",
            "Solder must be visible on both supplied pad masks.",
            *evidence_masks,
        )

    touching = components_a & components_b
    if touching:
        gap_px = 0.0
        derivation = "A single 8-connected solder component intersects both pad masks; bridge gap = 0 px."
    else:
        solder_a = np.isin(labels, tuple(components_a)).astype(np.uint8)
        solder_b = np.isin(labels, tuple(components_b)).astype(np.uint8)
        distance = cv2.distanceTransform(1 - solder_b, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        gap_px = float(distance[solder_a > 0].min())
        derivation = f"Nearest distance between distinct pad-associated solder masks: {gap_px:.4f} px × {float(mm_per_px):.8f} mm/px."

    return _measurement(
        "bridge_gap_mm",
        round(gap_px * float(mm_per_px), 6),
        "mm",
        None,
        derivation,
        *evidence_masks,
    )


def measure_fillet_concavity(
    solder_mask: np.ndarray | None,
    pad_plane: tuple[tuple[float, float], tuple[float, float]] | None,
    contact_point: tuple[float, float] | None,
    *,
    inward_direction: int = 1,
    normal_direction: int = -1,
    fit_window_px: float = 24.0,
) -> dict[str, Any]:
    """Return signed local curvature in px⁻¹ (positive = concave fillet).

    Curvature is computed from the same local quadratic contour fit used for
    wetting angle: k = 2a / (1 + b²)^(3/2), where a and b are the quadratic and
    linear coefficients in coordinates oriented inward along the pad plane and
    outward into the solder surface. This is a geometric descriptor, not a
    workmanship threshold.
    """
    fitted = _local_surface_fit(
        solder_mask,
        pad_plane,
        contact_point,
        inward_direction,
        normal_direction,
        fit_window_px,
    )
    if fitted is None:
        return _measurement(
            "fillet_concavity",
            None,
            "px^-1",
            "reference_not_visible" if solder_mask is not None else "segmentation_ambiguous",
            "Signed curvature requires a resolvable solder contour and pad-plane contact.",
            solder_mask,
        )

    mask, quadratic, linear = fitted
    curvature = 2.0 * quadratic / ((1.0 + linear * linear) ** 1.5)
    return _measurement(
        "fillet_concavity",
        round(float(curvature), 8),
        "px^-1",
        None,
        "Signed second derivative of the quadratic contour fit; positive values indicate concavity under the documented coordinate convention.",
        mask,
    )
