"""Authenticated administration endpoints for departments, stages and courses."""
import os
from functools import wraps
from flask import Blueprint, request, jsonify, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from .models import db, Department, Stage, Course, Student, CourseOffering, Grade

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
CONFIG = {
    "departments": (Department, ("code", "name_ar", "name_en", "active")),
    "stages": (Stage, ("department_id", "number", "name_ar")),
    "courses": (Course, ("department_id", "stage_id", "code", "name_ar", "credits")),
}
ROLES = {"admin": {"departments", "stages", "courses"}, "registrar": {"departments", "stages", "courses"}, "viewer": set()}

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("role"):
            return jsonify(error="Authentication required"), 401
        return fn(*args, **kwargs)
    return wrapper

def serialize(obj, fields):
    return {"id": obj.id, **{key: getattr(obj, key) for key in fields}}

@admin_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    expected = os.getenv("UARMS_ADMIN_PASSWORD_HASH")
    if not expected:
        return jsonify(error="Administrator account not configured"), 503
    if data.get("username") != os.getenv("UARMS_ADMIN_USERNAME", "admin") or not check_password_hash(expected, str(data.get("password", ""))):
        return jsonify(error="Invalid credentials"), 401
    session.clear()
    session["role"] = "admin"
    session["username"] = os.getenv("UARMS_ADMIN_USERNAME", "admin")
    return jsonify(role="admin", username=session["username"])

@admin_bp.post("/logout")
@require_auth
def logout():
    session.clear()
    return jsonify(ok=True)

@admin_bp.get("/me")
@require_auth
def me():
    return jsonify(role=session["role"], username=session.get("username"))

@admin_bp.route("/<resource>", methods=["GET", "POST"])
@admin_bp.route("/<resource>/<int:record_id>", methods=["PUT", "DELETE"])
@require_auth
def records(resource, record_id=None):
    if resource not in CONFIG:
        return jsonify(error="Unknown resource"), 404
    model, fields = CONFIG[resource]
    if request.method == "GET":
        return jsonify([serialize(obj, fields) for obj in db.session.execute(db.select(model).order_by(model.id)).scalars()])
    if resource not in ROLES.get(session["role"], set()):
        return jsonify(error="Forbidden"), 403
    obj = db.session.get(model, record_id) if record_id is not None else None
    if record_id is not None and obj is None:
        return jsonify(error="Not found"), 404
    if request.method == "DELETE":
        # Check dependencies explicitly: SQLite may not enforce foreign keys
        # in every environment, and academic records must never be orphaned.
        dependencies = {
            "departments": (
                (Stage, "department_id"),
                (Course, "department_id"),
                (Student, "department_id"),
            ),
            "stages": ((Course, "stage_id"),),
            "courses": ((CourseOffering, "course_id"),),
        }
        for related_model, foreign_key in dependencies[resource]:
            exists = db.session.execute(
                db.select(related_model.id)
                .where(getattr(related_model, foreign_key) == record_id)
                .limit(1)
            ).first()
            if exists:
                return jsonify(error="Record is referenced by other academic records"), 409
        try:
            db.session.delete(obj)
            db.session.commit()
            return jsonify(ok=True)
        except IntegrityError:
            db.session.rollback()
            return jsonify(error="Record is referenced by other academic records"), 409
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON object required"), 400
    if set(payload) - set(fields):
        return jsonify(error="Unknown fields"), 400
    if request.method == "POST":
        obj = model()
    required = {"departments": ("code", "name_ar"), "stages": ("department_id", "number", "name_ar"), "courses": ("department_id", "stage_id", "code", "name_ar")}
    if request.method == "POST" and any(payload.get(key) in (None, "") for key in required[resource]):
        return jsonify(error="Required fields missing"), 400
    for key, value in payload.items():
        if key in ("department_id", "stage_id", "number", "credits"):
            if type(value) is not int or (key in ("number", "department_id", "stage_id") and value < 1) or (key == "credits" and value < 0):
                return jsonify(error="Invalid numeric field: " + key), 400
        elif key == "active":
            if type(value) is not bool:
                return jsonify(error="active must be boolean"), 400
        elif not isinstance(value, str) or len(value) > (250 if key == "name_ar" else 200):
            return jsonify(error="Invalid text field: " + key), 400
        setattr(obj, key, value)
    if resource == "courses":
        stage = db.session.get(Stage, obj.stage_id)
        if stage is None or stage.department_id != obj.department_id:
            return jsonify(error="Stage must belong to selected department"), 400
    try:
        db.session.add(obj)
        db.session.commit()
        return jsonify(serialize(obj, fields)), 201 if request.method == "POST" else 200
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Duplicate or invalid referenced record"), 409
