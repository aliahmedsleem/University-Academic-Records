import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from flask_migrate import Migrate

from .excel_engine.reader import inspect_workbook, WorkbookReadError
from .excel_engine.templates import enrich_preview
from .models import db
from .admin import admin_bp, require_auth
from .api_academic import academic_bp

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

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exc):
        return jsonify(error="File exceeds the 15 MB limit"), 413

    return app
