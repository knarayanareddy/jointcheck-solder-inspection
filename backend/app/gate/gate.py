"""Fail-closed rule evaluation for measurements produced by an upstream vision stage.

This module does not inspect images or establish that a measurement is physically
correct. It only validates the measurement's declared provenance and applies a
human-reviewed rule. Unreviewed or provisional rules always abstain.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_REPOSITORY_RULES_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "workmanship-rules.v0.json"
)
_PACKAGED_RULES_PATH = Path(__file__).with_name("workmanship-rules.v0.json")
RULES_PATH = (
    _REPOSITORY_RULES_PATH if _REPOSITORY_RULES_PATH.is_file() else _PACKAGED_RULES_PATH
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_VERDICTS = {"ACCEPT", "PROCESS_INDICATOR", "REJECT"}


def _undetermined(rule_id: str, reason: str) -> dict[str, Any]:
    return {"verdict": "UNDETERMINED", "reason": reason, "rule_id": rule_id}


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _load_rules(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as rules_file:
        document = json.load(rules_file)
    if not isinstance(document, dict):
        raise TypeError("workmanship rules file must contain a JSON object")
    entries = document.get("rules")
    if not isinstance(entries, list):
        raise TypeError("workmanship rules file must contain a 'rules' array")
    return {
        rule["rule_id"]: rule
        for rule in entries
        if isinstance(rule, dict) and isinstance(rule.get("rule_id"), str)
    }


class DeterministicGate:
    """Apply a reviewed numeric threshold to a traceable CV measurement.

    ``assertion`` must contain ``class`` (1–3), ``calibrated`` and a
    ``measurement`` with matching ``quantity``, finite numeric ``value``,
    ``computable: true``, non-empty derivation, ROI id, and a 64-character
    SHA-256 for the pixel mask. The caller must set ``trusted_measurement`` only
    for measurements produced by a trusted internal vision pipeline; the public
    API and JSONL runner deliberately leave it false. A text quote or caller-made
    hash by itself can never produce a pass.
    """

    @staticmethod
    def evaluate(
        rule_id: str,
        assertion: Mapping[str, Any],
        rules_path: Path = RULES_PATH,
        *,
        trusted_measurement: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(assertion, Mapping):
            return _undetermined(rule_id, "invalid_assertion")

        try:
            rule = _load_rules(Path(rules_path)).get(rule_id)
        except (OSError, json.JSONDecodeError, TypeError):
            return _undetermined(rule_id, "rules_table_unavailable_or_invalid")
        if rule is None:
            return _undetermined(rule_id, "unknown_rule")
        if rule.get("human_reviewed") is not True:
            return _undetermined(rule_id, "rule_unreviewed")
        if trusted_measurement is not True:
            return _undetermined(rule_id, "measurement_source_unverified")

        class_id = str(assertion.get("class", ""))
        if class_id not in {"1", "2", "3"}:
            return _undetermined(rule_id, "invalid_product_class")

        thresholds = rule.get("class_thresholds")
        threshold = thresholds.get(class_id) if isinstance(thresholds, dict) else None
        if not isinstance(threshold, dict):
            return _undetermined(rule_id, "rule_has_no_threshold_for_class")
        metric = threshold.get("metric")
        operator = threshold.get("op")
        limit = threshold.get("value")
        if (
            not isinstance(metric, str)
            or not isinstance(operator, str)
            or operator not in {">=", "<=", ">", "<", "=="}
            or not _is_finite_number(limit)
        ):
            return _undetermined(rule_id, "invalid_rule_threshold")

        measurement = assertion.get("measurement")
        if not isinstance(measurement, Mapping):
            return _undetermined(rule_id, "measurement_missing")
        value = measurement.get("value")
        pixel_evidence = measurement.get("pixel_evidence")
        mask_hash = (
            pixel_evidence.get("mask_sha256")
            if isinstance(pixel_evidence, Mapping)
            else None
        )
        if (
            measurement.get("quantity") != metric
            or measurement.get("computable") is not True
            or not _is_finite_number(value)
            or not isinstance(measurement.get("roi_id"), str)
            or not measurement["roi_id"]
            or not isinstance(measurement.get("derivation"), str)
            or not measurement["derivation"].strip()
            or not isinstance(mask_hash, str)
            or not _SHA256_RE.fullmatch(mask_hash)
        ):
            return _undetermined(
                rule_id, "measurement_provenance_invalid_or_incomplete"
            )
        if (
            rule.get("requires_calibration") is True
            and assertion.get("calibrated") is not True
        ):
            return _undetermined(rule_id, "measurement_requires_calibration")

        comparisons = {
            ">=": float(value) >= float(limit),
            "<=": float(value) <= float(limit),
            ">": float(value) > float(limit),
            "<": float(value) < float(limit),
            "==": float(value) == float(limit),
        }
        if comparisons[operator]:
            verdict = threshold.get("verdict_if_met", "ACCEPT")
        else:
            verdict = rule.get("verdict_if_not_met")
        if not isinstance(verdict, str) or verdict not in _ALLOWED_VERDICTS:
            return _undetermined(rule_id, "rule_contains_unsupported_verdict")

        return {
            "verdict": verdict,
            "rule_id": rule_id,
            "condition_code": rule.get("condition_code"),
            "measurement": {"quantity": metric, "value": value},
            "threshold": {"operator": operator, "value": limit},
            "evidence": {
                "roi_id": measurement["roi_id"],
                "mask_sha256": mask_hash,
                "derivation": measurement["derivation"],
            },
        }
