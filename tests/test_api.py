"""
Deterministic unit tests for api/main.py (Phase 4 API, extended in
Phase 5 to the multi-hop chain path - docs/decisions/008). Uses
FastAPI's in-process TestClient, not a running server. No LLM call -
only exercises the facts-only path (no credentials assumed configured
in CI), so these never skip, same discipline as test_rag_guard.py.
"""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_reports_real_graph_counts():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["graph_nodes"] > 0
    assert body["graph_edges"] > 0


def test_techniques_lists_seed_set():
    r = client.get("/techniques")
    assert r.status_code == 200
    assert "T1059.001" in r.json()["techniques"]


def test_single_hop_query_returns_one_technique_id():
    r = client.post("/query", json={"question": "what happens after T1059.001 for APT29?"})
    assert r.status_code == 200
    body = r.json()
    assert body["technique_ids"] == ["T1059.001"]
    assert body["group"] == "APT29"
    assert "TECHNIQUE: T1059.001" in body["facts"]


def test_chain_query_routes_to_multi_hop_path():
    r = client.post(
        "/query",
        json={"question": "T1566.001 then T1204.002 then T1059.001 for APT29"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["technique_ids"] == ["T1566.001", "T1204.002", "T1059.001"]
    assert "CHAIN: T1566.001 -> T1204.002 -> T1059.001" in body["facts"]
    assert "Path T1566.001 -> T1204.002:" in body["facts"]
    assert "Path T1204.002 -> T1059.001:" in body["facts"]


def test_chain_query_with_no_path_reports_it_in_facts_not_an_error():
    r = client.post("/query", json={"question": "T1566.001 then T1560.001 for APT29"})
    assert r.status_code == 200
    assert "no single-group semantic-edge path found" in r.json()["facts"]


def test_no_technique_id_returns_400():
    r = client.post("/query", json={"question": "what should I watch for after a phishing email"})
    assert r.status_code == 400


def test_invalid_technique_id_returns_404():
    r = client.post("/query", json={"question": "what happens after T9999 for APT29?"})
    assert r.status_code == 404


def test_unknown_provider_returns_400():
    r = client.post(
        "/query",
        json={"question": "what happens after T1059.001 for APT29?", "provider": "not-a-real-provider"},
    )
    assert r.status_code == 400


def test_oversized_question_rejected_by_field_bound():
    r = client.post("/query", json={"question": "T1059.001 " + "x" * 2500})
    assert r.status_code == 422
