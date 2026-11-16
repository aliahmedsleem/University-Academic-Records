import pytest
from sqlalchemy.exc import IntegrityError
from app import create_app
from app.models import db, Department, AcademicYear, Stage, Student, Course

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_department_unique_code(app):
    with app.app_context():
        db.session.add(Department(code="CS", name_ar="علوم الحاسوب"))
        db.session.commit()
        db.session.add(Department(code="CS", name_ar="قسم مكرر"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_student_identity_unique(app):
    with app.app_context():
        d = Department(code="IT", name_ar="تقنية المعلومات")
        y = AcademicYear(label="2026-2027")
        db.session.add_all([d, y])
        db.session.flush()
        db.session.add(Student(university_id="U001", full_name_ar="طالب تجريبي", department_id=d.id, enrollment_year_id=y.id))
        db.session.commit()
        db.session.add(Student(university_id="U001", full_name_ar="طالب آخر", department_id=d.id, enrollment_year_id=y.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_read_only_endpoints(app):
    client = app.test_client()
    assert client.get("/api/academic/departments").json == []
    assert client.post("/api/academic/students", json={}).status_code == 405
