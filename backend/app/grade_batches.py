"""Metadata-only import batch workflow.

No student identities, workbook contents or grades are persisted.
Approval and grade import intentionally remain unavailable.
"""
from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from .admin import require_auth
from .models import db, GradeImportBatch, GradeBatchAuditEvent
from .excel_engine.annual_register import parse_annual_register
from .excel_engine.reader import WorkbookReadError

batch_bp = Blueprint("grade_batches", __name__, url_prefix="/api/grade-batches")

def _admin_only():
    return session.get("role") == "admin"

def _event(batch, action, old_status, new_status):
    return GradeBatchAuditEvent(
        batch_id=batch.id, action=action,
        actor_username=str(session.get("username") or "unknown")[:150],
        actor_role=str(session.get("role") or "unknown")[:30],
        previous_status=old_status, new_status=new_status,
    )

def _serialize_event(event):
    return {"id": event.id, "batch_id": event.batch_id,
            "action": event.action, "actor_username": event.actor_username,
            "actor_role": event.actor_role,
            "previous_status": event.previous_status, "new_status": event.new_status,
            "created_at": event.created_at.isoformat() if event.created_at else None}

def _serialize(batch):
    return {"id": batch.id, "original_filename": batch.original_filename,
            "sha256": batch.sha256, "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None}

@batch_bp.get("")
@require_auth
def list_batches():
    if not _admin_only():
        return jsonify(error="Forbidden"), 403
    batches = db.session.execute(db.select(GradeImportBatch).order_by(GradeImportBatch.id.desc()).limit(100)).scalars().all()
    return jsonify([_serialize(batch) for batch in batches])

@batch_bp.post("")
@require_auth
def create_batch():
    if not _admin_only():
        return jsonify(error="Forbidden"), 403
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="A file is required"), 400
    try:
        preview = parse_annual_register(uploaded.stream, uploaded.filename, sheet_name=request.form.get('sheet_name') or None)
    except WorkbookReadError as exc:
        return jsonify(error=str(exc)), 422
    if not preview["candidate_students"]:
        return jsonify(error="No student candidates found; batch not created"), 422
    existing = db.session.execute(
        db.select(GradeImportBatch).where(GradeImportBatch.sha256 == preview["sha256"])
        .order_by(GradeImportBatch.id.desc()).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return jsonify(error="This exact workbook already has a review batch", batch=_serialize(existing)), 409
    batch = GradeImportBatch(original_filename=preview["filename"][:255],
                             sha256=preview["sha256"], status="pending_review")
    try:
        db.session.add(batch)
        db.session.flush()
        db.session.add(_event(batch, 'created', None, 'pending_review'))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Could not create batch"), 409
    return jsonify(batch=_serialize(batch), saved_grades=0,
                   saved_students=0, workbook_stored=False,
                   message="Metadata saved for review only; grade import disabled"), 201

@batch_bp.post("/<int:batch_id>/reject")
@require_auth
def reject_batch(batch_id):
    if not _admin_only():
        return jsonify(error="Forbidden"), 403
    batch = db.session.get(GradeImportBatch, batch_id)
    if batch is None:
        return jsonify(error="Batch not found"), 404
    if batch.status != "pending_review":
        return jsonify(error="Only pending batches can be rejected"), 409
    old_status = batch.status
    batch.status = "rejected"
    db.session.add(_event(batch, 'rejected', old_status, 'rejected'))
    db.session.commit()
    return jsonify(batch=_serialize(batch))

@batch_bp.post("/<int:batch_id>/approve")
@require_auth
def approval_disabled(batch_id):
    if not _admin_only():
        return jsonify(error="Forbidden"), 403
    return jsonify(error="Grade approval is disabled until verified identities, course mappings, grade rules and audit trail are implemented"), 409

@batch_bp.get("/<int:batch_id>/audit")
@require_auth
def batch_audit(batch_id):
    if not _admin_only():
        return jsonify(error="Forbidden"), 403
    if db.session.get(GradeImportBatch, batch_id) is None:
        return jsonify(error="Batch not found"), 404
    events = db.session.execute(
        db.select(GradeBatchAuditEvent)
        .where(GradeBatchAuditEvent.batch_id == batch_id)
        .order_by(GradeBatchAuditEvent.id.asc()).limit(500)
    ).scalars().all()
    return jsonify([_serialize_event(event) for event in events])
