import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "core-schemas.json"


def test_contract_schema_and_definitions_are_valid():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema.get("$defs"), "core schema must define reusable contracts"

    for name in schema["$defs"]:
        scoped = {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{name}",
        }
        Draft202012Validator.check_schema(scoped)


def test_committed_sample_ledger_matches_local_contract():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    ledger_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/LedgerLine",
    }
    validator = Draft202012Validator(ledger_schema, format_checker=FormatChecker())
    sample_path = ROOT / "runs" / "sample_ledger.jsonl"
    lines = sample_path.read_text(encoding="utf-8").splitlines()
    assert lines, "sample ledger must not be empty"
    for line in lines:
        validator.validate(json.loads(line))
