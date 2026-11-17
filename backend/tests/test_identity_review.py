import pytest
from app import create_app
from app.models import db, Department, AcademicYear, Student
from app.identity_review import review_identity_decisions

@pytest.fixture
def setup_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        department = Department(code="CS", name_ar="علوم الحاسوب")
        other = Department(code="IT", name_ar="تقنية المعلومات")
        year = AcademicYear(label="2026-2027")
        db.session.add_all([department, other, year])
        db.session.flush()
        first = Student(university_id="U1", full_name_ar="أحمد محمد علي", department_id=department.id, enrollment_year_id=year.id)
        second = Student(university_id="U2", full_name_ar="سارة حسن", department_id=other.id, enrollment_year_id=year.id)
        db.session.add_all([first, second])
        db.session.commit()
        yield department.id, first.id, second.id
        db.session.remove()
        db.drop_all()

def test_identity_review_does_not_persist(setup_app):
    dept, first, _ = setup_app
    review = {"candidate_students": [{"excel_row": 8, "name_candidate": "احمد محمد علي"}]}
    result = review_identity_decisions(review, dept, {"8": first})
    assert result["proposed_count"] == 1
    assert result["approved"] is False
    assert result["saved_to_database"] is False

def test_identity_review_rejects_wrong_department(setup_app):
    dept, _, other = setup_app
    review = {"candidate_students": [{"excel_row": 8, "name_candidate": "سارة حسن"}]}
    result = review_identity_decisions(review, dept, {"8": other})
    assert result["proposed_count"] == 0
    assert result["issues"][0]["code"] == "student_missing_or_wrong_department"

def test_identity_review_rejects_repeated_student(setup_app):
    dept, first, _ = setup_app
    review = {"candidate_students": [{"excel_row": 8, "name_candidate": "أحمد محمد علي"}, {"excel_row": 11, "name_candidate": "أحمد محمد علي"}]}
    with pytest.raises(ValueError, match="multiple"):
        review_identity_decisions(review, dept, {"8": first, "11": first})
