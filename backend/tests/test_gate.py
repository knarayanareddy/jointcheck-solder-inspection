import json
from pathlib import Path

from app.gate.gate import DeterministicGate


def _reviewed_rules_file(tmp_path, *, verdict_if_not_met="REJECT"):
    rule = {
        "rule_id": "TEST-RULE",
        "condition_code": "TEST_CONDITION",
        "human_reviewed": True,
        "requires_calibration": True,
        "class_thresholds": {
            "2": {
                "metric": "solder_coverage_pct",
                "op": ">=",
                "value": 65,
                "verdict_if_met": "ACCEPT",
            }
        },
        "verdict_if_not_met": verdict_if_not_met,
    }
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"rules": [rule]}), encoding="utf-8")
    return path


def _assertion(value=80):
    return {
        "class": 2,
        "calibrated": True,
        "measurement": {
            "quantity": "solder_coverage_pct",
            "value": value,
            "computable": True,
            "roi_id": "j_001",
            "derivation": "Pixel-mask coverage: 80 of 100 pixels.",
            "pixel_evidence": {"mask_sha256": "a" * 64},
        },
    }


def test_packaged_rule_snapshot_matches_source_table():
    root = Path(__file__).resolve().parents[2]
    source = (root / "data/workmanship-rules.v0.json").read_bytes()
    packaged = (root / "backend/app/gate/workmanship-rules.v0.json").read_bytes()
    assert packaged == source


def test_actual_provisional_rule_abstains():
    result = DeterministicGate.evaluate(
        "JC-WET-001",
        _assertion(),
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "rule_unreviewed"


def test_unrelated_or_missing_quote_cannot_create_a_pass(tmp_path):
    # Quotes are not accepted as evidence by this API; a measurement and its
    # traceable pixel evidence are required, and the rule must be reviewed.
    result = DeterministicGate.evaluate(
        "TEST-RULE",
        {"class": 2, "quote": "this happens to occur in the source"},
        _reviewed_rules_file(tmp_path),
        trusted_measurement=True,
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "measurement_missing"


def test_malformed_rules_file_fails_closed(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text("[]", encoding="utf-8")
    result = DeterministicGate.evaluate("JC-WET-001", _assertion(), path)
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "rules_table_unavailable_or_invalid"


def test_non_finite_and_oversized_values_fail_closed(tmp_path):
    rules_path = _reviewed_rules_file(tmp_path)
    for value in (float("nan"), 10**10000):
        result = DeterministicGate.evaluate(
            "TEST-RULE", _assertion(value), rules_path, trusted_measurement=True
        )
        assert result["verdict"] == "UNDETERMINED"


def test_caller_supplied_measurement_is_not_trusted_by_default(tmp_path):
    result = DeterministicGate.evaluate(
        "TEST-RULE", _assertion(), _reviewed_rules_file(tmp_path)
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "measurement_source_unverified"


def test_reviewed_rule_accepts_measurement_at_threshold(tmp_path):
    result = DeterministicGate.evaluate(
        "TEST-RULE",
        _assertion(65),
        _reviewed_rules_file(tmp_path),
        trusted_measurement=True,
    )
    assert result["verdict"] == "ACCEPT"
    assert result["measurement"]["value"] == 65
    assert result["evidence"]["mask_sha256"] == "a" * 64


def test_reviewed_rule_rejects_measurement_below_threshold(tmp_path):
    result = DeterministicGate.evaluate(
        "TEST-RULE",
        _assertion(64.99),
        _reviewed_rules_file(tmp_path),
        trusted_measurement=True,
    )
    assert result["verdict"] == "REJECT"


def test_missing_measurement_provenance_abstains(tmp_path):
    assertion = _assertion()
    assertion["measurement"]["pixel_evidence"]["mask_sha256"] = "not-a-hash"
    result = DeterministicGate.evaluate(
        "TEST-RULE", assertion, _reviewed_rules_file(tmp_path), trusted_measurement=True
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "measurement_provenance_invalid_or_incomplete"


def test_uncalibrated_measurement_abstains(tmp_path):
    assertion = _assertion()
    assertion["calibrated"] = False
    result = DeterministicGate.evaluate(
        "TEST-RULE", assertion, _reviewed_rules_file(tmp_path), trusted_measurement=True
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "measurement_requires_calibration"
