import json

import pytest

from app.config import settings
from app.tf import vision


@pytest.mark.asyncio
async def test_model_suggestions_are_code_scoped_and_never_grade(monkeypatch):
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "observations": [
                                {
                                    "region_id": "cv_001",
                                    "joint_type": "through_hole",
                                    "condition_codes": [
                                        "INSUFFICIENT_WETTING",
                                        "MADE_UP_CODE",
                                    ],
                                    "confidence": 0.72,
                                    "note": "Possible incomplete wetting; inspector review required.",
                                },
                                {
                                    "region_id": "not-a-candidate",
                                    "joint_type": "other",
                                    "condition_codes": ["EXCESS_SOLDER"],
                                    "confidence": 0.9,
                                    "note": "Must be discarded.",
                                },
                            ]
                        }
                    ),
                }
            }
        ],
        "usage": {"prompt_tokens": 300, "completion_tokens": 55},
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, headers, json):
            assert url.endswith("/chat/completions")
            assert headers["Authorization"].startswith("Bearer ")
            assert json["messages"][0]["content"][1]["image_url"]["url"].startswith(
                "data:image/jpeg;base64,"
            )
            return FakeResponse()

    monkeypatch.setattr(settings, "nebius_api_key", "test-key")
    monkeypatch.setattr(vision.httpx, "AsyncClient", FakeClient)
    result = await vision.request_visual_suggestions(
        b"synthetic-bytes",
        "image/jpeg",
        [
            {
                "region_id": "cv_001",
                "bbox_px": {"x": 10, "y": 20, "width": 40, "height": 50},
            }
        ],
    )
    assert result["status"] == "complete"
    assert result["review_required"] is True
    assert result["prompt_tokens"] == 300
    observations = result["observations"]
    assert len(observations) == 1
    assert observations[0]["condition_codes"] == ["INSUFFICIENT_WETTING"]
    assert observations[0]["review_required"] is True
    assert "verdict" not in observations[0]
