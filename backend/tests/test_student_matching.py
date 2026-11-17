import pytest
from app import create_app
from app.student_matching import normalize_arabic_name, match_candidates
from app.models import db, Department, AcademicYear, Student

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_arabic_name_normalization():
    assert normalize_arabic_name("أحمد  مُحَمَّد علي") == "احمد محمد علي"

def test_matching_is_read_only_and_name_only_never_approved(app):
    with app.app_context():
        dept = Department(code="CS", name_ar="علوم الحاسوب")
        year = AcademicYear(label="2025-2026")
        db.session.add_all([dept, year])
        db.session.flush()
        student = Student(university_id="U-001", full_name_ar="أحمد محمد علي",
                          department_id=dept.id, enrollment_year_id=year.id)
        db.session.add(student)
        db.session.commit()
        result = match_candidates({"candidate_students": [
            {"excel_row": 8, "name_candidate": "احمد محمد علي"},
            {"excel_row": 11, "name_candidate": "شخص غير مسجل"},
        ]}, dept.id)
        assert result["results"][0]["status"] == "name_only_review"
        assert result["results"][1]["status"] == "unmatched"
        assert result["auto_approved"] is False
        assert result["saved_to_database"] is False
