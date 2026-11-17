from io import BytesIO
import openpyxl
import pytest
from app import create_app
from app.models import db, Department, AcademicYear, Stage, Course, CourseOffering, Grade

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        department = Department(code="CS", name_ar="علوم الحاسوب")
        year = AcademicYear(label="2026-2027")
        db.session.add_all([department, year])
        db.session.flush()
        stage = Stage(department_id=department.id, number=1, name_ar="الأولى")
        db.session.add(stage)
        db.session.flush()
        course = Course(department_id=department.id, stage_id=stage.id, code="CS101", name_ar="برمجة", credits=3)
        db.session.add(course)
        db.session.flush()
        db.session.add(CourseOffering(course_id=course.id, academic_year_id=year.id))
        db.session.commit()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["role"] = "admin"
            yield client, department.id, year.id, course.id
        db.session.remove()
        db.drop_all()

def workbook():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["C8"] = "طالب اختبار"
    for row, attempt in [(8, "د1"), (9, "د2"), (10, "ق")]:
        ws.cell(row, 4, attempt)
        ws.cell(row, 5, 30)
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream

def test_reconciliation_never_writes_grades(client):
    import json
    http, department_id, year_id, course_id = client
    response = http.post("/api/excel/annual-register/reconcile", data={
        "file": (workbook(), "sample.xlsx"),
        "department_id": str(department_id),
        "academic_year_id": str(year_id),
        "course_mapping": json.dumps({"1": course_id}),
    })
    assert response.status_code == 200, response.json
    assert response.json["approval_disabled"] is True
    assert response.json["ready_for_import"] is False
    assert response.json["saved_to_database"] is False
    assert any(i["code"] == "student_identity_needs_confirmation" for i in response.json["issues"])
    with http.application.app_context():
        assert db.session.query(Grade).count() == 0

def test_reconciliation_rejects_bad_course_id(client):
    import json
    http, department_id, year_id, _ = client
    response = http.post("/api/excel/annual-register/reconcile", data={
        "file": (workbook(), "sample.xlsx"),
        "department_id": str(department_id),
        "academic_year_id": str(year_id),
        "course_mapping": json.dumps({"1": 999999}),
    })
    assert response.status_code == 422
