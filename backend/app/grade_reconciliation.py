"""Pre-import reconciliation. Always read-only; never auto-approve grades."""
from collections import Counter
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from .models import db, Course, CourseOffering
from .student_matching import match_candidates
from .excel_engine.validation import validate_annual_review

ATTEMPT_CODES = {"د1": 1, "د2": 2, "ق": 3}

def reconcile_register(review, department_id, academic_year_id, course_mapping):
    if type(department_id) is not int or department_id < 1:
        raise ValueError("A valid department_id is required")
    if type(academic_year_id) is not int or academic_year_id < 1:
        raise ValueError("A valid academic_year_id is required")
    if not isinstance(course_mapping, dict):
        raise ValueError("course_mapping must be an object")
    valid_groups = {str(g["group"]) for g in review.get("course_groups", [])}
    if set(course_mapping) - valid_groups:
        raise ValueError("Unknown course group")
    mapping_ids = {}
    for key, value in course_mapping.items():
        if type(value) is not int or value < 1:
            raise ValueError("Course mapping values must be positive integer course IDs")
        mapping_ids[key] = value
    if len(set(mapping_ids.values())) != len(mapping_ids):
        raise ValueError("One course cannot be assigned to multiple groups")
    courses = db.session.execute(select(Course).where(Course.id.in_(mapping_ids.values()))).scalars().all() if mapping_ids else []
    course_by_id = {course.id: course for course in courses}
    for course_id in mapping_ids.values():
        course = course_by_id.get(course_id)
        if course is None or course.department_id != department_id:
            raise ValueError("Mapped course does not belong to selected department")
    offerings = db.session.execute(
        select(CourseOffering).where(
            CourseOffering.course_id.in_(mapping_ids.values()),
            CourseOffering.academic_year_id == academic_year_id,
        )
    ).scalars().all() if mapping_ids else []
    offering_count = Counter(o.course_id for o in offerings)
    issues = []
    for key, course_id in mapping_ids.items():
        if offering_count[course_id] != 1:
            issues.append({"code": "course_offering_not_unique", "group": int(key), "severity": "error"})
    for group in valid_groups - set(mapping_ids):
        issues.append({"code": "unmapped_course_group", "group": int(group), "severity": "error"})
    matched = match_candidates(review, department_id)
    for candidate in matched["results"]:
        if candidate["status"] != "id_and_name_match":
            issues.append({"code": "student_identity_needs_confirmation",
                           "row": candidate["excel_row"], "severity": "error"})
    score_cells = 0
    for student in review["candidate_students"]:
        for label, attempt in student.get("attempts", {}).items():
            if label not in ATTEMPT_CODES:
                issues.append({"code": "unknown_attempt", "row": student["excel_row"], "severity": "error"})
                continue
            for group in attempt.get("courses", []):
                for field, cell in group.get("cells", {}).items():
                    raw = str(cell.get("raw") or "").strip()
                    if cell.get("formula"):
                        issues.append({"code": "unverified_formula", "row": attempt["excel_row"], "group": group["group"], "field": field, "severity": "error"})
                    elif raw:
                        try:
                            score = Decimal(raw)
                            if not score.is_finite() or score < 0:
                                raise InvalidOperation
                            score_cells += 1
                        except InvalidOperation:
                            issues.append({"code": "invalid_score", "row": attempt["excel_row"], "group": group["group"], "field": field, "severity": "error"})
    basic = validate_annual_review(review)
    return {
        "candidate_count": len(review["candidate_students"]),
        "numeric_cells_preview": score_cells,
        "student_matches": matched["results"],
        "course_mapping": mapping_ids,
        "issues": (issues + [i for i in basic["issues"] if i["code"] in ("missing_attempt", "duplicate_name_candidate")])[:1000],
        "issue_count": len(issues) + sum(i["code"] in ("missing_attempt", "duplicate_name_candidate") for i in basic["issues"]),
        "preview_limited": len(review["candidate_students"]) >= review.get("preview_limit", 150),
        "ready_for_import": False,
        "approval_disabled": True,
        "saved_to_database": False,
    }
