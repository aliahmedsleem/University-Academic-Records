"""Validate an annual register review without importing or changing grades."""
from collections import Counter
import re

def _normalize_name(value):
    return " ".join(str(value or "").strip().split())

def validate_annual_review(review, course_mapping=None):
    if not isinstance(review, dict) or review.get("layout") != "annual_three_attempts":
        raise ValueError("Invalid annual register review")
    students = review.get("candidate_students")
    groups = review.get("course_groups")
    if not isinstance(students, list) or not isinstance(groups, list):
        raise ValueError("Invalid review structure")
    if len(students) > 150 or len(groups) > 60:
        raise ValueError("Review exceeds configured limits")
    mapping = course_mapping or {}
    if not isinstance(mapping, dict) or len(mapping) > 60:
        raise ValueError("Invalid course mapping")
    if any(not re.fullmatch(r"[1-9][0-9]?", str(k)) or not isinstance(v, str) or len(v) > 100 for k,v in mapping.items()):
        raise ValueError("Invalid course mapping entries")
    issues = []
    names = Counter(_normalize_name(s.get("name_candidate")) for s in students if isinstance(s, dict))
    for s in students:
        if not isinstance(s, dict):
            raise ValueError("Invalid student record")
        name = _normalize_name(s.get("name_candidate"))
        row = s.get("excel_row")
        if not name:
            issues.append({"row": row, "code": "missing_student_name", "severity": "error"})
        elif names[name] > 1:
            issues.append({"row": row, "code": "duplicate_name_candidate", "severity": "warning"})
        attempts = s.get("attempts", {})
        if not isinstance(attempts, dict):
            raise ValueError("Invalid attempts")
        for label in ("د1", "د2", "ق"):
            if label not in attempts:
                issues.append({"row": row, "code": "missing_attempt", "attempt": label, "severity": "warning"})
        for label, attempt in attempts.items():
            if label not in ("د1", "د2", "ق") or not isinstance(attempt, dict):
                issues.append({"row": row, "code": "unknown_attempt", "severity": "warning"})
                continue
            for group in attempt.get("courses", []):
                if not isinstance(group, dict):
                    raise ValueError("Invalid course group")
                for field, cell in group.get("cells", {}).items():
                    if not isinstance(cell, dict):
                        raise ValueError("Invalid score cell")
                    raw = str(cell.get("raw", "")).strip()
                    if cell.get("formula"):
                        issues.append({"row": attempt.get("excel_row"), "code": "unverified_formula",
                                       "group": group.get("group"), "field": field, "severity": "warning"})
                    elif raw and not raw.replace(".", "", 1).isdigit():
                        issues.append({"row": attempt.get("excel_row"), "code": "non_numeric_score",
                                       "group": group.get("group"), "field": field, "severity": "warning"})
    mapped = [str(v).strip() for v in mapping.values() if str(v).strip()]
    if len(mapped) != len(set(mapped)):
        issues.append({"code": "duplicate_course_mapping", "severity": "error"})
    for group in groups:
        if str(group.get("group")) not in mapping or not str(mapping.get(str(group.get("group")), "")).strip():
            issues.append({"code": "unmapped_course_group", "group": group.get("group"), "severity": "warning"})
    return {"candidate_count": len(students), "issues": issues[:1000],
            "issues_truncated": len(issues) > 1000, "issue_count": len(issues),
            "course_mapping": mapping, "ready_for_import": False,
            "review_required": True, "saved_to_database": False}
