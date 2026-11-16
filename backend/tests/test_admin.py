import os
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("UARMS_ADMIN_PASSWORD_HASH", generate_password_hash("example-strong-password"))
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def test_auth_required(client):
    assert client.get("/api/admin/departments").status_code == 401
    assert client.get("/api/academic/students").status_code == 401
    assert client.post("/api/excel/preview").status_code == 401

def test_admin_crud(client):
    assert client.post("/api/admin/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "admin", "password": "example-strong-password"}).status_code == 200
    d = client.post("/api/admin/departments", json={"code": "CS", "name_ar": "علوم الحاسوب"})
    assert d.status_code == 201
    dept = d.json["id"]
    s = client.post("/api/admin/stages", json={"department_id": dept, "number": 1, "name_ar": "الأولى"})
    assert s.status_code == 201
    stage = s.json["id"]
    c = client.post("/api/admin/courses", json={"department_id": dept, "stage_id": stage, "code": "CS101", "name_ar": "برمجة", "credits": 3})
    assert c.status_code == 201
    assert len(client.get("/api/admin/courses").json) == 1
    assert client.delete("/api/admin/departments/"+str(dept)).status_code == 409
    assert client.post("/api/admin/logout").status_code == 200
    assert client.get("/api/admin/departments").status_code == 401
