import pytest
from app.grade_rules import inspect_grade_rules, validate_grade_policy

def policy():
    return {"maximums": {"annual": 40, "final_exam": 60, "total": 100}, "total_rule": "sum"}

def preview(annual, final, total, formula=False):
    return {"candidate_students": [{"attempts": {"د1": {"excel_row": 8, "courses": [
        {"group": 1, "cells": {"annual": {"raw": annual, "formula": formula},
                               "final_exam": {"raw": final, "formula": False},
                               "total": {"raw": total, "formula": False}}}
    ]}}}]}

def test_valid_policy_and_scores():
    result = inspect_grade_rules(preview("30", "50", "80"), policy())
    assert result["issue_count"] == 0
    assert result["checked_cells"] == 3
    assert result["approved"] is False

def test_over_maximum_and_incorrect_total():
    result = inspect_grade_rules(preview("45", "40", "90"), policy())
    assert {issue["code"] for issue in result["issues"]} == {"score_exceeds_maximum", "total_mismatch"}

def test_formula_never_accepted_as_numeric():
    result = inspect_grade_rules(preview("=20+10", "50", "80", True), policy())
    assert any(issue["code"] == "unverified_formula" for issue in result["issues"])

def test_policy_is_explicit():
    with pytest.raises(ValueError):
        validate_grade_policy({"maximums": {"annual": 40, "final_exam": 60, "total": 100}, "total_rule": "weighted"})
    with pytest.raises(ValueError):
        validate_grade_policy({"maximums": {"annual": 40, "final_exam": 60, "total": 90}, "total_rule": "sum"})
