from io import BytesIO
import pytest
import openpyxl
from app import create_app
from app.models import db, Grade, Student, GradeImportBatch

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["role"] = "admin"
            yield client
        db.session.remove()
        db.drop_all()

def workbook():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["C8"] = "طالب تجريبي محمد احمد"
    for row, label in [(8,"د1"), (9,"د2"), (10,"ق")]:
        ws.cell(row, 4, label)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def test_metadata_only_batch_and_duplicate_rejection(client):
    first = client.post("/api/grade-batches", data={"file": (workbook(), "sample.xlsx")})
    assert first.status_code == 201, first.json
    assert first.json["saved_grades"] == 0
    assert first.json["saved_students"] == 0
    assert first.json["workbook_stored"] is False
    duplicate = client.post("/api/grade-batches", data={"file": (workbook(), "sample.xlsx")})
    assert duplicate.status_code == 409
    batch_id = first.json["batch"]["id"]
    assert client.post(f"/api/grade-batches/{batch_id}/approve").status_code == 409
    assert client.post(f"/api/grade-batches/{batch_id}/reject").status_code == 200
    assert client.post(f"/api/grade-batches/{batch_id}/reject").status_code == 409
    with client.application.app_context():
        assert db.session.query(Grade).count() == 0
        assert db.session.query(Student).count() == 0
        assert db.session.query(GradeImportBatch).count() == 1

def test_unauthenticated_cannot_create_batch(client):
    client.post("/api/admin/logout")
    response = client.post("/api/grade-batches", data={"file": (workbook(), "sample.xlsx")})
    assert response.status_code == 401
