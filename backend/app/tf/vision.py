"""Optional, explicitly requested visual suggestions from a compatible API.

Model output is advisory only. It is constrained to known codes and candidate
region IDs and is never passed to the grading gate.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

ROOT = Path(__file__).resolve().parents[3]
CONDITION_CODES_PATH = ROOT / "data" / "condition-codes.json"
PACKAGED_CODES_PATH = (
    Path(__file__).resolve().parents[1] / "vision" / "condition-codes.json"
)
MAX_OUTPUT_TOKENS = 900


def _load_code_catalog() -> list[dict[str, str]]:
    path = (
        CONDITION_CODES_PATH if CONDITION_CODES_PATH.is_file() else PACKAGED_CODES_PATH
    )
    catalog = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"code": row["code"], "title": row["title"]}
        for row in catalog["codes"]
        if isinstance(row, dict) and isinstance(row.get("code"), str)
    ]


def _content_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part.get("text", "") for part in content if isinstance(part, dict)
        ]
        return "\n".join(part for part in text_parts if isinstance(part, str)) or None
    return None


def _normalise_observations(
    payload: Any, region_ids: set[str], codes: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(
        payload.get("observations"), list
    ):
        raise TypeError("missing observations array")
    observations = []
    for item in payload["observations"]:
        if not isinstance(item, dict):
            continue
        region_id = item.get("region_id")
        joint_type = item.get("joint_type")
        confidence = item.get("confidence")
        if region_id not in region_ids or joint_type not in {
            "through_hole",
            "smd_gull_wing",
            "smd_rectangular",
            "bga",
            "j_lead",
            "wire_terminal",
            "hand_pad",
            "connector_pin",
            "other",
        }:
            continue
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            continue
        suggested_codes = item.get("condition_codes", [])
        if not isinstance(suggested_codes, list):
            suggested_codes = []
        known_codes = [
            code for code in suggested_codes if isinstance(code, str) and code in codes
        ]
        note = item.get("note", "")
        observations.append(
            {
                "region_id": region_id,
                "joint_type": joint_type,
                "condition_codes": known_codes,
                "confidence": float(confidence),
                "note": note[:400] if isinstance(note, str) else "",
                "review_required": True,
            }
        )
    return observations


async def request_visual_suggestions(
    image_bytes: bytes,
    media_type: str,
    candidate_regions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Request non-grading observations; errors return a safe unavailable state."""
    if not settings.nebius_api_key:
        return {
            "status": "not_configured",
            "model": settings.model_vision,
            "observations": [],
        }

    try:
        catalog = _load_code_catalog()
        region_ids = {region["region_id"] for region in candidate_regions}
        if not region_ids:
            return {
                "status": "skipped_no_regions",
                "model": settings.model_vision,
                "observations": [],
            }
        region_context = [
            {"region_id": region["region_id"], "bbox_px": region["bbox_px"]}
            for region in candidate_regions
        ]
        prompt = (
            "Inspect this electronics assembly macro photo only for visible, tentative "
            "joint observations. Candidate regions use pixel boxes from the image's "
            "upper-left origin: " + json.dumps(region_context) + ".\n"
            "Allowed condition codes: "
            + json.dumps(catalog, ensure_ascii=False)
            + ".\n"
            'Return only JSON: {"observations":[{"region_id":string,"joint_type":string,'
            '"condition_codes":[string],"confidence":number,"note":string}]}. '
            "Use only listed region IDs and codes. Do not grade, accept, reject, infer a class, "
            "invent measurements, or claim compliance. If uncertain, return an empty observations array."
        )
        image_url = (
            f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        )
        endpoint = settings.nebius_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=8.0)
        ) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {settings.nebius_api_key}"},
                json={
                    "model": settings.model_vision,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                },
            )
            response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        text = _content_text(content)
        if not text:
            raise ValueError("empty model response")
        parsed = json.loads(text)
        observations = _normalise_observations(
            parsed, region_ids, {row["code"] for row in catalog}
        )
        usage = result.get("usage", {})
        return {
            "status": "complete",
            "model": settings.model_vision,
            "observations": observations,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "review_required": True,
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "model": settings.model_vision,
            "observations": [],
            "message": "Visual assistance could not be completed; CV-only results are retained.",
        }
