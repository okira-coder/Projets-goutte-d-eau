"""Tests d'intégration de l'API FastAPI.

Les tests qui ont besoin de la DB sont skippés si MySQL n'est pas joignable.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_returns_metadata():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "goutte-d-eau-api"
    assert "docs" in body


def test_health_endpoint_exists():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "model_version" in body
    assert "db" in body


def test_predict_validation_far_future():
    r = client.post(
        "/predict",
        json={"station_id": 1, "target_date": "2099-01-01"},
    )
    assert r.status_code == 422
    assert "target_date" in r.text


def test_predict_validation_invalid_station_id():
    r = client.post(
        "/predict",
        json={"station_id": -1, "target_date": "2026-05-12"},
    )
    assert r.status_code == 422


def test_predict_missing_body():
    r = client.post("/predict", json={})
    assert r.status_code == 422


def test_docs_endpoint_available():
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower() or "openapi" in r.text.lower()


def test_openapi_schema():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"].startswith("Projet Goutte d'eau")
    paths = schema["paths"]
    assert "/predict" in paths
    assert "/health" in paths
    assert "/stations" in paths
