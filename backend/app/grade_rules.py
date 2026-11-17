"""Policy-based grade checks. Does not calculate a passing grade or write data.

Academic policy is supplied explicitly by an administrator for preview.
"""
from decimal import Decimal, InvalidOperation

FIELDS = ("annual", "final_exam", "total")
ATTEMPTS = ("د1", "د2", "ق")

def _number(value, field):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a finite non-negative number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a finite non-negative number") from None
    if not number.is_finite() or number < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return number

def validate_grade_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"maximums", "total_rule"}:
        raise ValueError("Policy requires maximums and total_rule")
    maximums = policy["maximums"]
    if not isinstance(maximums, dict) or set(maximums) != set(FIELDS):
        raise ValueError("Maximums must specify annual, final_exam and total")
    limits = {field: _number(maximums[field], field) for field in FIELDS}
    if any(value == 0 for value in limits.values()):
        raise ValueError("Maximums must be greater than zero")
    if policy["total_rule"] not in ("none", "sum"):
        raise ValueError("total_rule must be none or sum")
    if policy["total_rule"] == "sum" and limits["total"] != limits["annual"] + limits["final_exam"]:
        raise ValueError("Total maximum must equal component maximums for sum rule")
    return limits

def inspect_grade_rules(review, policy):
    limits = validate_grade_policy(policy)
    if not isinstance(review, dict) or not isinstance(review.get("candidate_students"), list):
        raise ValueError("Invalid register review")
    issues, inspected = [], 0
    for student in review["candidate_students"]:
        for attempt_name, attempt in student.get("attempts", {}).items():
            if attempt_name not in ATTEMPTS:
                issues.append({"code": "unknown_attempt", "row": attempt.get("excel_row"), "severity": "error"})
                continue
            for group in attempt.get("courses", []):
                values = {}
                for field in FIELDS:
                    cell = group.get("cells", {}).get(field, {})
                    raw = str(cell.get("raw") or "").strip()
                    if cell.get("formula"):
                        issues.append({"code": "unverified_formula", "row": attempt.get("excel_row"), "group": group.get("group"), "field": field, "severity": "error"})
                    elif raw:
                        try:
                            value = _number(raw, field)
                        except ValueError:
                            issues.append({"code": "invalid_score", "row": attempt.get("excel_row"), "group": group.get("group"), "field": field, "severity": "error"})
                            continue
                        inspected += 1
                        values[field] = value
                        if value > limits[field]:
                            issues.append({"code": "score_exceeds_maximum", "row": attempt.get("excel_row"), "group": group.get("group"), "field": field, "severity": "error"})
                if policy["total_rule"] == "sum" and all(field in values for field in FIELDS):
                    if values["total"] != values["annual"] + values["final_exam"]:
                        issues.append({"code": "total_mismatch", "row": attempt.get("excel_row"), "group": group.get("group"), "severity": "error"})
    return {"checked_cells": inspected, "issue_count": len(issues),
            "issues": issues[:1000], "issues_truncated": len(issues) > 1000,
            "policy": {"maximums": {k: str(v) for k,v in limits.items()}, "total_rule": policy["total_rule"]},
            "passing_grade_calculated": False, "approved": False,
            "saved_to_database": False, "preview_only": True}
