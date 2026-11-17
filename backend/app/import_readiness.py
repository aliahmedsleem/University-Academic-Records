"""Consolidated, conservative pre-import readiness report.

A report never authorizes persistence. Preview truncation and any unresolved
identity are blockers, even if individual checks find no score errors.
"""
from .grade_reconciliation import reconcile_register
from .grade_rules import inspect_grade_rules
from .identity_review import review_identity_decisions

def build_readiness_report(review, department_id, academic_year_id, course_mapping, policy, decisions):
    reconciliation = reconcile_register(review, department_id, academic_year_id, course_mapping)
    grades = inspect_grade_rules(review, policy)
    identities = review_identity_decisions(review, department_id, decisions)
    sections = {
        "reconciliation": reconciliation,
        "grade_rules": grades,
        "identity_review": identities,
    }
    blockers = []
    for section, result in sections.items():
        for issue in result["issues"]:
            blockers.append({"section": section, **issue})
    if review.get("issues"):
        for issue in review["issues"]:
            blockers.append({"section": "register_structure", "severity": "error", **issue})
    if len(review.get("candidate_students", [])) >= review.get("preview_limit", 150):
        blockers.append({"section": "register_structure", "code": "preview_may_be_truncated", "severity": "error"})
    if not review.get("candidate_students"):
        blockers.append({"section": "register_structure", "code": "no_candidates", "severity": "error"})
    if len(identities["proposed"]) != len(review.get("candidate_students", [])):
        blockers.append({"section": "identity_review", "code": "not_all_identities_selected", "severity": "error"})
    return {
        "filename": review.get("filename"),
        "sha256": review.get("sha256"),
        "candidate_count": len(review.get("candidate_students", [])),
        "checks": {
            "reconciliation": {"issue_count": reconciliation["issue_count"]},
            "grade_rules": {"issue_count": grades["issue_count"], "checked_cells": grades["checked_cells"]},
            "identity_review": {"issue_count": identities["issue_count"], "proposed_count": identities["proposed_count"]},
        },
        "blocker_count": len(blockers),
        "blockers": blockers[:200],
        "blockers_truncated": len(blockers) > 200,
        "preliminary_checks_clear": len(blockers) == 0,
        "ready_for_import": False,
        "approval_disabled": True,
        "saved_to_database": False,
        "warning": "A clean preview is not authorization to import or approve grades.",
    }
