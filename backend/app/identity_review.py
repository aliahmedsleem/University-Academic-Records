"""Explicit review decisions for student identities; no persistent approval.

This module verifies selections against database records and the current
Excel preview. Decisions remain ephemeral until a secure approval workflow
and audit-backed storage are implemented.
"""
from sqlalchemy import select
from .models import db, Student
from .student_matching import normalize_arabic_name

def review_identity_decisions(preview, department_id, decisions):
    if type(department_id) is not int or department_id < 1:
        raise ValueError("Valid department_id required")
    if not isinstance(decisions, dict) or len(decisions) > 150:
        raise ValueError("Invalid identity decisions")
    candidates = preview.get("candidate_students", [])
    if not isinstance(candidates, list) or len(candidates) > 150:
        raise ValueError("Invalid preview")
    rows = {str(s["excel_row"]): s for s in candidates}
    if len(rows) != len(candidates):
        raise ValueError("Duplicate Excel row identifiers")
    if set(decisions) - set(rows):
        raise ValueError("Decision references unknown Excel row")
    if any(type(value) is not int or value < 1 for value in decisions.values()):
        raise ValueError("Student IDs must be positive integers")
    student_ids = list(decisions.values())
    if len(set(student_ids)) != len(student_ids):
        raise ValueError("One student cannot be assigned to multiple Excel rows")
    students = db.session.execute(select(Student).where(Student.id.in_(student_ids))).scalars().all() if student_ids else []
    by_id = {student.id: student for student in students}
    issues = []
    accepted = []
    for row, student_id in decisions.items():
        student = by_id.get(student_id)
        if student is None or student.department_id != department_id:
            issues.append({"row": int(row), "code": "student_missing_or_wrong_department"})
            continue
        candidate = rows[row]
        if normalize_arabic_name(candidate.get("name_candidate")) != normalize_arabic_name(student.full_name_ar):
            issues.append({"row": int(row), "code": "name_conflict_requires_offline_verification"})
            continue
        accepted.append({"excel_row": int(row), "student_id": student_id,
                         "status": "identity_review_proposed"})
    for row in rows:
        if row not in decisions:
            issues.append({"row": int(row), "code": "identity_not_selected"})
    return {"proposed": accepted, "issues": issues[:150],
            "proposed_count": len(accepted), "issue_count": len(issues),
            "persisted": False, "approved": False, "saved_to_database": False,
            "message": "Selections are preview-only and do not establish verified identity."}
