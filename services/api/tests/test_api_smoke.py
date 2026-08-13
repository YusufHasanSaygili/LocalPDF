from fastapi.testclient import TestClient

from app.main import app


def test_health_and_correlation_header() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "test-correlation"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Correlation-ID"] == "test-correlation"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_openapi_contains_core_local_workflows() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/documents" in paths
    assert "/api/v1/operations" in paths
    assert "/api/v1/sign/{token}/consent" in paths
    assert "/api/v1/documents/{document_id}/audit-export" in paths
    assert "/api/v1/maintenance/backups" in paths
