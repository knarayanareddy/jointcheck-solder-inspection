"""Fail-closed regression tests; proposed thresholds are not approved calibration."""

import json
from pathlib import Path

from app.gate.gate import RULES_PATH, DeterministicGate

_REQUESTED_RULE_IDS = {
    "RULE-WETTING-01",
    "RULE-SOLDER-01",
    "RULE-BRIDGE-01",
}


def _trusted_measurement(quantity: str, value) -> dict:
    return {
        "quantity": quantity,
        "value": value,
        "computable": True,
        "roi_id": "j_synthetic",
        "derivation": "Synthetic test value; no physical inspection performed.",
        "pixel_evidence": {"mask_sha256": "a" * 64},
    }


def _rule(rule_id: str) -> dict:
    with RULES_PATH.open(encoding="utf-8") as handle:
        document = json.load(handle)
    return next(item for item in document["rules"] if item["rule_id"] == rule_id)


def test_unverified_threshold_table_and_requested_rule_ids_remain_unreviewed():
    with RULES_PATH.open(encoding="utf-8") as handle:
        document = json.load(handle)
    rules = {rule["rule_id"]: rule for rule in document["rules"]}

    assert "PROVISIONAL" in document["_meta"]["status"]
    assert _REQUESTED_RULE_IDS.isdisjoint(rules)
    assert all(rule.get("human_reviewed") is False for rule in rules.values())
    assert all("provisional" not in rule for rule in rules.values())


def test_requested_rule_ids_fail_closed_instead_of_claiming_calibration():
    values = {
        "RULE-WETTING-01": ("wetting_angle_deg", 45.0),
        "RULE-SOLDER-01": ("solder_coverage_pct", 100.0),
        "RULE-BRIDGE-01": ("bridge_detected", False),
    }
    for rule_id, (quantity, value) in values.items():
        result = DeterministicGate.evaluate(
            rule_id,
            {
                "class": 2,
                "calibrated": True,
                "measurement": _trusted_measurement(quantity, value),
            },
            trusted_measurement=True,
        )
        assert result["verdict"] == "UNDETERMINED"
        assert result["reason"] == "unknown_rule"


def test_current_wetting_rule_does_not_accept_a_wetting_angle_measurement(tmp_path):
    """Temporary review flag only probes metric compatibility; no source rule is changed."""
    rule = _rule("JC-WET-001")
    rule["human_reviewed"] = True
    rules_path = tmp_path / "test-only-reviewed-rule.json"
    rules_path.write_text(json.dumps({"rules": [rule]}), encoding="utf-8")

    result = DeterministicGate.evaluate(
        "JC-WET-001",
        {
            "class": 1,
            "calibrated": True,
            "measurement": _trusted_measurement("wetting_angle_deg", 45.0),
        },
        rules_path,
        trusted_measurement=True,
    )
    assert result["verdict"] == "UNDETERMINED"
    assert result["reason"] == "measurement_provenance_invalid_or_incomplete"


def test_existing_excess_and_bridge_contracts_do_not_match_requested_metrics():
    excess = _rule("JC-EXC-001")
    bridge = _rule("JC-BRD-001")
    assert {
        threshold["metric"]
        for threshold in excess["class_thresholds"].values()
        if isinstance(threshold, dict)
    } == {"solder_volume_ratio"}
    assert {
        threshold["metric"]
        for threshold in bridge["class_thresholds"].values()
        if isinstance(threshold, dict)
    } == {"bridge_gap_mm"}

    schema_path = Path(__file__).resolve().parents[2] / "schemas/core-schemas.json"
    schemas = json.loads(schema_path.read_text(encoding="utf-8"))["$defs"]
    allowed_quantities = set(schemas["Measurement"]["properties"]["quantity"]["enum"])
    assert "fillet_concavity" not in allowed_quantities
    assert "bridge_detected" not in allowed_quantities
