from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_info_route_discloses_prototype_scope():
    response = client.get("/v1/info")
    assert response.status_code == 200
    assert response.json()["inspection_available"] is True
    assert response.json()["production_grading_available"] is False


def test_gate_route_abstains_for_unreviewed_provisional_rules():
    response = client.post(
        "/v1/gate/evaluate",
        json={
            "rule_id": "JC-WET-001",
            "product_class": 3,
            "calibrated": True,
            "measurement": {
                "quantity": "solder_coverage_pct",
                "value": 90,
                "computable": True,
                "roi_id": "j_001",
                "derivation": "sample measurement",
                "pixel_evidence": {"mask_sha256": "a" * 64},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "UNDETERMINED"
    assert response.json()["reason"] == "rule_unreviewed"
