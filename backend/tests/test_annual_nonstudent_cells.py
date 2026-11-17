"""Synthetic regression checks: headings and formula references are not students."""
from io import BytesIO
import openpyxl
from app.excel_engine.annual_register import parse_annual_register


def test_formula_and_heading_are_not_student_candidates():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "سجل الدرجات"
    sheet["C8"] = "=C5"
    sheet["D8"] = "د1"
    sheet["C11"] = "الاسم"
    sheet["D11"] = "د1"
    sheet["C14"] = "طالب تجريبي"
    for row, attempt in [(14, "د1"), (15, "د2"), (16, "ق")]:
        sheet.cell(row, 4, attempt)
    buffer = BytesIO()
    book.save(buffer)
    buffer.seek(0)
    result = parse_annual_register(buffer, "synthetic.xlsx")
    assert [student["name_candidate"] for student in result["candidate_students"]] == ["طالب تجريبي"]
    assert sum(issue["code"] == "non_student_name_cell" for issue in result["issues"]) == 2
