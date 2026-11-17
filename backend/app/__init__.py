import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from flask_migrate import Migrate

from .excel_engine.reader import inspect_workbook, WorkbookReadError
from .excel_engine.templates import enrich_preview
from .excel_engine.extractor import extract_candidates
from .excel_engine.annual_register import parse_annual_register
from .excel_engine.validation import validate_annual_review
from .student_matching import match_candidates
from .models import db
from .admin import admin_bp, require_auth
from .api_academic import academic_bp
from .grade_batches import batch_bp
from .grade_reconciliation import reconcile_register

migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=15 * 1024 * 1024,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///uarms-dev.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("UARMS_SECRET_KEY", "development-only-insecure-key"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["TESTING"] and app.config["SECRET_KEY"] == "development-only-insecure-key" and not app.debug:
        app.logger.warning("Set UARMS_SECRET_KEY before deployment")
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(admin_bp)
    app.register_blueprint(academic_bp)
    app.register_blueprint(batch_bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="uarms")

    @app.post("/api/excel/preview")
    @require_auth
    def excel_preview():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            preview = enrich_preview(inspect_workbook(uploaded.stream, uploaded.filename))
        except WorkbookReadError as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(preview)

    @app.post("/api/excel/candidates")
    @require_auth
    def excel_candidates():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            try:
                name_column = int(request.form.get("name_column", "3"))
                start_row = int(request.form.get("start_row", "10"))
            except (TypeError, ValueError):
                return jsonify(error="Column and row must be integers"), 400
            result = extract_candidates(
                uploaded.stream, uploaded.filename,
                sheet_name=request.form.get("sheet_name") or None,
                name_column=name_column, start_row=start_row,
            )
        except WorkbookReadError as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(result)

    @app.post("/api/excel/annual-register")
    @require_auth
    def annual_register_preview():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            result = parse_annual_register(uploaded.stream, uploaded.filename)
        except WorkbookReadError as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(result)

    @app.post("/api/excel/annual-register/validate")
    @require_auth
    def annual_register_validate():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        import json
        try:
            mapping = json.loads(request.form.get("course_mapping", "{}"))
            review = parse_annual_register(uploaded.stream, uploaded.filename)
            result = validate_annual_review(review, mapping)
        except (ValueError, TypeError, WorkbookReadError) as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(result)

    @app.post("/api/excel/annual-register/match-students")
    @require_auth
    def annual_register_match_students():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            department_raw = request.form.get("department_id", "").strip()
            department_id = int(department_raw) if department_raw else None
            review = parse_annual_register(uploaded.stream, uploaded.filename)
            result = match_candidates(review, department_id)
        except (ValueError, TypeError, WorkbookReadError) as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(result)

    @app.post("/api/excel/annual-register/reconcile")
    @require_auth
    def annual_register_reconcile():
        import json
        from flask import session
        if session.get("role") != "admin":
            return jsonify(error="Forbidden"), 403
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            department_id = int(request.form["department_id"])
            academic_year_id = int(request.form["academic_year_id"])
            course_mapping = json.loads(request.form.get("course_mapping", "{}"))
            review = parse_annual_register(uploaded.stream, uploaded.filename)
            result = reconcile_register(review, department_id, academic_year_id, course_mapping)
        except (KeyError, ValueError, TypeError, WorkbookReadError) as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(result)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exc):
        return jsonify(error="File exceeds the 15 MB limit"), 413

    return app
