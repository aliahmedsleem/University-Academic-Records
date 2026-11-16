"""Read-only academic API. No public write endpoints until authentication exists."""
from flask import Blueprint, jsonify
from .models import Department, AcademicYear, Stage, Student, Course
from .admin import require_auth

academic_bp = Blueprint("academic", __name__, url_prefix="/api/academic")

def rows(model, fields):
    return [{field: getattr(obj, field) for field in fields} for obj in model.query.order_by(model.id).all()]

@academic_bp.get("/departments")
@require_auth
def departments():
    return jsonify(rows(Department, ("id", "code", "name_ar", "name_en", "active")))

@academic_bp.get("/academic-years")
@require_auth
def academic_years():
    return jsonify(rows(AcademicYear, ("id", "label", "active")))

@academic_bp.get("/stages")
@require_auth
def stages():
    return jsonify(rows(Stage, ("id", "department_id", "number", "name_ar")))

@academic_bp.get("/students")
@require_auth
def students():
    return jsonify(rows(Student, ("id", "university_id", "full_name_ar", "department_id", "enrollment_year_id", "status")))

@academic_bp.get("/courses")
@require_auth
def courses():
    return jsonify(rows(Course, ("id", "department_id", "stage_id", "code", "name_ar", "credits")))
