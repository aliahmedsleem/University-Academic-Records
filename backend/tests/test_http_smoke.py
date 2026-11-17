"""HTTP smoke checks for the Flask application factory.

Uses an isolated in-memory database and synthetic requests only.
"""
from app import create_app


def test_health_endpoint():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-only-secret"})
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "uarms"}


def test_excel_preview_requires_authentication():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-only-secret"})
    response = app.test_client().post("/api/excel/preview")
    assert response.status_code in (401, 403)
