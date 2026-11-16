from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from .excel_engine.reader import inspect_workbook, WorkbookReadError


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="uarms")

    @app.post("/api/excel/preview")
    def excel_preview():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="A file is required"), 400
        try:
            preview = inspect_workbook(uploaded.stream, uploaded.filename)
        except WorkbookReadError as exc:
            return jsonify(error=str(exc)), 422
        return jsonify(preview)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exc):
        return jsonify(error="File exceeds the 15 MB limit"), 413

    return app
