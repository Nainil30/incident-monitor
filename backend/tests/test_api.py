import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from data import seed_incidents  # noqa: E402
from rca import suggest_root_causes  # noqa: E402

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_store():
    main.reset_store()


def test_list_incidents_returns_all_seeded():
    r = client.get("/api/incidents")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_list_sorted_active_first_by_severity():
    data = client.get("/api/incidents").json()
    assert data[0]["severity"] == "SEV1"
    assert data[-1]["status"] == "resolved"


def test_filter_by_status_and_severity():
    opened = client.get("/api/incidents", params={"status": "open"}).json()
    assert opened and all(i["status"] == "open" for i in opened)
    sev1 = client.get("/api/incidents", params={"severity": "SEV1"}).json()
    assert {i["id"] for i in sev1} == {"INC-1001", "INC-1004"}


def test_get_incident_detail_includes_logs_and_timeline():
    r = client.get("/api/incidents/INC-1002")
    assert r.status_code == 200
    body = r.json()
    assert body["logs"] and body["timeline"]
    assert body["services"] == ["search-indexer"]


def test_unknown_incident_returns_404():
    assert client.get("/api/incidents/INC-9999").status_code == 404
    assert client.post("/api/incidents/INC-9999/acknowledge").status_code == 404


def test_acknowledge_open_incident():
    r = client.post("/api/incidents/INC-1001/acknowledge")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "acknowledged"
    assert body["timeline"][-1]["type"] == "acknowledged"


def test_resolve_acknowledged_incident():
    r = client.post("/api/incidents/INC-1002/resolve")
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["timeline"][-1]["type"] == "resolved"


def test_resolve_directly_from_open():
    assert client.post("/api/incidents/INC-1003/resolve").json()["status"] == "resolved"


def test_invalid_transitions_return_409():
    assert client.post("/api/incidents/INC-1002/acknowledge").status_code == 409  # already acked
    assert client.post("/api/incidents/INC-1008/acknowledge").status_code == 409  # resolved
    assert client.post("/api/incidents/INC-1008/resolve").status_code == 409  # resolved twice


def test_stats_update_after_transition():
    before = client.get("/api/stats").json()
    client.post("/api/incidents/INC-1001/resolve")
    after = client.get("/api/stats").json()
    assert after["by_status"]["resolved"] == before["by_status"]["resolved"] + 1
    assert after["active_by_severity"]["SEV1"] == before["active_by_severity"]["SEV1"] - 1


@pytest.mark.parametrize(
    "incident_id,expected_top",
    [
        ("INC-1002", "Memory leak / insufficient memory limit"),
        ("INC-1004", "Expired TLS certificate"),
        ("INC-1003", "Database connection pool exhaustion"),
        ("INC-1006", "Disk space exhaustion"),
    ],
)
def test_suggestions_match_rules(incident_id, expected_top):
    r = client.get(f"/api/incidents/{incident_id}/suggestions")
    assert r.status_code == 200
    top = r.json()[0]
    assert top["cause"] == expected_top
    assert top["evidence"]
    assert 0 < top["confidence"] <= 0.95


def test_suggestions_are_deterministic():
    a = client.get("/api/incidents/INC-1001/suggestions").json()
    b = client.get("/api/incidents/INC-1001/suggestions").json()
    assert a == b
    assert "Faulty recent deployment" in [s["cause"] for s in a]


def test_fallback_suggestion_when_no_rule_matches():
    incident = seed_incidents()["INC-1007"].model_copy(deep=True)
    incident.title, incident.description = "Something odd", "Unclear"
    for log in incident.logs:
        log.message = "nothing interesting"
    result = suggest_root_causes(incident)
    assert len(result) == 1 and result[0].cause == "No known pattern matched"
