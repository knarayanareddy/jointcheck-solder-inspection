from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.gate.gate import DeterministicGate
from app.tf.vision import request_visual_suggestions
from app.vision.inspection import analyze_image

app = FastAPI(
    title="JointCheck — Solder Joint Workmanship Inspection with Proof",
    description=(
        "Prototype API for image quality analysis, contour proposals, optional "
        "untrusted vision suggestions, and fail-closed grading."
    ),
    version="0.3.0",
)


class MeasurementInput(BaseModel):
    quantity: str
    value: float | None = None
    computable: bool = False
    roi_id: str | None = None
    derivation: str | None = None
    pixel_evidence: dict[str, Any] | None = None


class GateRequest(BaseModel):
    rule_id: str
    product_class: int = Field(ge=1, le=3)
    calibrated: bool = False
    measurement: MeasurementInput | None = None


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/v1/info")
def get_info() -> dict[str, Any]:
    return {
        "project": "JointCheck — Solder Joint Workmanship Inspection with Proof",
        "status": "prototype",
        "inspection_available": True,
        "inspection_scope": "experimental_photo_quality_and_contour_proposals",
        "production_grading_available": False,
        "capabilities": [
            "health",
            "runtime_info",
            "photo_quality",
            "contour_candidates",
            "fail_closed_grading",
        ],
        "model_assistance_configured": bool(settings.nebius_api_key),
        "vision_model": settings.model_vision,
        "configured_models": {
            "ultra": settings.model_ultra,
            "super": settings.model_super,
            "nano": settings.model_nano,
        },
    }


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_SUPPORTED_MEDIA_TYPES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


@app.post("/v1/inspect")
async def inspect_photo(
    request: Request,
    product_class: int = Query(default=2, ge=1, le=3),
    model_assist: bool = Query(default=False),
) -> dict[str, Any]:
    """Analyze one JPEG/PNG. Model sharing is opt-in; grading always abstains."""
    media_type = (
        request.headers.get("content-type", "")
        .split(";", maxsplit=1)[0]
        .strip()
        .lower()
    )
    signature = _SUPPORTED_MEDIA_TYPES.get(media_type)
    if signature is None:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG image body.")

    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > MAX_UPLOAD_BYTES
    ):
        raise HTTPException(
            status_code=413, detail="Image exceeds the 10 MiB upload limit."
        )
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413, detail="Image exceeds the 10 MiB upload limit."
            )
    image_bytes = bytes(body)
    if not image_bytes.startswith(signature):
        raise HTTPException(
            status_code=415, detail="Image bytes do not match the declared media type."
        )

    try:
        analysis = await run_in_threadpool(
            analyze_image, image_bytes, product_class=product_class
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "decoded_image_too_large":
            raise HTTPException(
                status_code=413, detail="Decoded image exceeds the pixel limit."
            ) from exc
        raise HTTPException(
            status_code=422, detail="Image could not be decoded or is too small."
        ) from exc

    if model_assist:
        model_result = await request_visual_suggestions(
            image_bytes, media_type, analysis["candidate_regions"]
        )
    else:
        model_result = {
            "status": "not_requested",
            "model": settings.model_vision,
            "observations": [],
        }

    reasons = [
        "pad_and_solder_segmentation_unavailable",
        "workmanship_thresholds_unreviewed",
        "no_double_labeled_validation_set",
    ]
    if not analysis["quality"]["prototype_quality_checks_passed"]:
        reasons.insert(0, "image_quality_below_provisional_floor")
    return {
        "status": "analysis_complete",
        "product_class": product_class,
        "image": analysis["image"],
        "quality": analysis["quality"],
        "candidate_regions": analysis["candidate_regions"],
        "candidate_count": analysis["candidate_count"],
        "model_assistance": model_result,
        "grading": {
            "verdict": "UNDETERMINED",
            "reason_codes": reasons,
            "actionable": False,
        },
        "disclaimer": analysis["disclaimer"],
    }


@app.post("/v1/gate/evaluate")
def evaluate_gate(request: GateRequest) -> dict[str, Any]:
    assertion = {
        "class": request.product_class,
        "calibrated": request.calibrated,
        "measurement": (
            request.measurement.model_dump()
            if request.measurement is not None
            else None
        ),
    }
    return DeterministicGate.evaluate(request.rule_id, assertion)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
