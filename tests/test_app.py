from fastapi.testclient import TestClient

from backend.app import app


def test_health_endpoint():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "volatility-api"}


def test_api_root_lists_endpoints():
    client = TestClient(app)

    response = client.get("/api")

    assert response.status_code == 200
    assert "/api/health" in response.json()["endpoints"]
