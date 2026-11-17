from app.import_readiness import build_readiness_report

def test_readiness_blocks_empty_register(monkeypatch):
    import app.import_readiness as module
    monkeypatch.setattr(module, "reconcile_register", lambda *args: {"issues": [], "issue_count": 0})
    monkeypatch.setattr(module, "inspect_grade_rules", lambda *args: {"issues": [], "issue_count": 0, "checked_cells": 0})
    monkeypatch.setattr(module, "review_identity_decisions", lambda *args: {"issues": [], "issue_count": 0, "proposed": [], "proposed_count": 0})
    result = build_readiness_report({"candidate_students": [], "issues": [], "preview_limit": 150}, 1, 1, {}, {}, {})
    assert result["ready_for_import"] is False
    assert any(i["code"] == "no_candidates" for i in result["blockers"])

def test_readiness_blocks_preview_limit(monkeypatch):
    import app.import_readiness as module
    monkeypatch.setattr(module, "reconcile_register", lambda *args: {"issues": [], "issue_count": 0})
    monkeypatch.setattr(module, "inspect_grade_rules", lambda *args: {"issues": [], "issue_count": 0, "checked_cells": 0})
    monkeypatch.setattr(module, "review_identity_decisions", lambda *args: {"issues": [], "issue_count": 0, "proposed": [{"excel_row": 8}], "proposed_count": 1})
    result = build_readiness_report({"candidate_students": [{"excel_row": 8}], "issues": [], "preview_limit": 1}, 1, 1, {}, {}, {})
    assert result["approval_disabled"] is True
    assert any(i["code"] == "preview_may_be_truncated" for i in result["blockers"])
