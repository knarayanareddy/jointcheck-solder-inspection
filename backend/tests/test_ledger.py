import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from app.tf import ledger

ROOT = Path(__file__).resolve().parents[2]


def test_record_telemetry_writes_a_schema_valid_line(tmp_path, monkeypatch):
    ledger_path = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(ledger, "LEDGER_PATH", ledger_path)
    recorded = ledger.record_telemetry(
        kind="chat.completions",
        stage="extract_fields",
        model="test/model",
        prompt_tokens=10,
        completion_tokens=4,
        cached_tokens=3,
        cost_usd=0.01,
        latency_ms=12.5,
    )

    schema = json.loads((ROOT / "schemas/core-schemas.json").read_text())
    line_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/LedgerLine",
    }
    Draft202012Validator(line_schema, format_checker=FormatChecker()).validate(recorded)
    assert json.loads(ledger_path.read_text().strip()) == recorded


def test_ledger_rejects_impossible_token_counts():
    with pytest.raises(ValueError, match="cached_tokens"):
        ledger.record_telemetry(
            kind="chat.completions",
            stage="test",
            model="test/model",
            prompt_tokens=2,
            completion_tokens=1,
            cached_tokens=3,
        )
