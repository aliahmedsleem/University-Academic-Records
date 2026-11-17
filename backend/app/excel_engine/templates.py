"""Conservative workbook layout classification from known grade-register families.

Classification never approves or imports student grades.
"""
from pathlib import Path

MASTER_SHEETS = {"سجل الدرجات", "س درجات"}
CARRIED_SHEETS = {"سجل المحملين", "س المحملين"}
RESULT_SHEETS = {"النتائج", "نتائج", "النتائج (2)", "نتائج 2"}
SUMMARY_SHEETS = {"السجل العام", "س العام"}
INFO_SHEETS = {"المعلومات"}

def classify_sheet(name):
    name = name.strip()
    if name in MASTER_SHEETS:
        return "primary_grades"
    if name in CARRIED_SHEETS:
        return "carried_subjects"
    if name in RESULT_SHEETS:
        return "derived_results"
    if name in SUMMARY_SHEETS:
        return "derived_summary"
    if name in INFO_SHEETS:
        return "metadata"
    return "other"

def classify_workbook(sheet_names):
    names = {name.strip() for name in sheet_names}
    if "سجل الدرجات" in names and "المعلومات" in names:
        return "grade_register_family_a"
    if "س درجات" in names and "المعلومات" in names:
        return "grade_register_family_b"
    return "unknown_manual_review"

def enrich_preview(preview):
    names = [s["name"] for s in preview["sheets"]]
    preview["template_family"] = classify_workbook(names)
    for sheet in preview["sheets"]:
        sheet["role"] = classify_sheet(sheet["name"])
    preview["import_allowed"] = False
    preview["requires_manual_review"] = True
    return preview
