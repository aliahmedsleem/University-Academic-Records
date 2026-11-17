"""Conservative student identity matching for an Excel preview.

No fuzzy name matching is auto-approved. No database changes.
"""
import re
from sqlalchemy import select
from .models import db, Student

def normalize_arabic_name(value):
    text = str(value or "").strip()
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    text = text.translate(str.maketrans({"أ":"ا","إ":"ا","آ":"ا","ٱ":"ا","ى":"ي"}))
    return " ".join(text.split())

def match_candidates(preview, department_id=None):
    if not isinstance(preview, dict) or not isinstance(preview.get("candidate_students"), list):
        raise ValueError("Invalid candidate preview")
    if len(preview["candidate_students"]) > 150:
        raise ValueError("Candidate limit exceeded")
    if department_id is not None and (type(department_id) is not int or department_id < 1):
        raise ValueError("Invalid department")
    query = select(Student)
    if department_id is not None:
        query = query.where(Student.department_id == department_id)
    students = db.session.execute(query).scalars().all()
    by_name = {}
    by_id = {}
    for student in students:
        by_name.setdefault(normalize_arabic_name(student.full_name_ar), []).append(student)
        by_id[student.university_id] = student
    results = []
    for candidate in preview["candidate_students"]:
        if not isinstance(candidate, dict):
            raise ValueError("Invalid candidate record")
        name = str(candidate.get("name_candidate", ""))
        uid = str(candidate.get("university_id_candidate") or "").strip()
        name_matches = by_name.get(normalize_arabic_name(name), [])
        id_match = by_id.get(uid) if uid else None
        if id_match and normalize_arabic_name(id_match.full_name_ar) == normalize_arabic_name(name):
            status, matches = "id_and_name_match", [id_match]
        elif id_match:
            status, matches = "identity_conflict", [id_match]
        elif len(name_matches) == 1:
            status, matches = "name_only_review", name_matches
        elif len(name_matches) > 1:
            status, matches = "ambiguous_name", name_matches
        else:
            status, matches = "unmatched", []
        results.append({
            "excel_row": candidate.get("excel_row"),
            "name_candidate": name,
            "status": status,
            "matches": [{"student_id": s.id, "university_id": s.university_id,
                         "full_name_ar": s.full_name_ar} for s in matches[:10]],
            "requires_manual_confirmation": True,
        })
    return {"results": results, "candidate_count": len(results),
            "review_required": True, "saved_to_database": False,
            "auto_approved": False}
