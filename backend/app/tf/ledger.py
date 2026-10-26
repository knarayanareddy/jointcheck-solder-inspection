"""Append-only JSONL telemetry ledger for model-stage instrumentation."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

LEDGER_PATH = Path(__file__).resolve().parents[3] / "runs" / "ledger.jsonl"


def record_telemetry(
    kind: str,
    stage: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    status: str = "ok",
    notes: str | None = None,
) -> dict[str, Any]:
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (prompt_tokens, completion_tokens, cached_tokens)
    ):
        raise ValueError("token counts must be non-negative integers")
    if cached_tokens > prompt_tokens:
        raise ValueError("cached_tokens cannot exceed prompt_tokens")
    if any(not math.isfinite(value) or value < 0 for value in (cost_usd, latency_ms)):
        raise ValueError("cost and latency must be finite non-negative numbers")

    entry: dict[str, Any] = {
        "id": f"led_{uuid4().hex}",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "stage": stage,
        "model": model,
        "request": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_tokens": cached_tokens,
        },
        "cost_usd": round(cost_usd, 6),
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "notes": notes,
    }
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as ledger_file:
        ledger_file.write(json.dumps(entry, allow_nan=False) + "\n")
    return entry
