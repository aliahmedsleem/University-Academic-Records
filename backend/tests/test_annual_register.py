from io import BytesIO
import openpyxl
from app.excel_engine.annual_register import parse_annual_register

def test_three_rows_are_one_student_and_no_database_write():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["E5"] = 2
    ws["C8"] = "طالب تجريبي محمد احمد"
    for row, label in ((8, "د1"), (9, "د2"), (10, "ق")):
        ws.cell(row, 4, label)
    ws["E8"] = 24
    ws["F8"] = 22
    ws["G8"] = "=E8+F8"
    ws["G9"] = 50
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    result = parse_annual_register(output, "synthetic.xlsx")
    assert result["candidate_count_preview"] == 1
    assert list(result["candidate_students"][0]["attempts"]) == ["د1", "د2", "ق"]
    assert result["candidate_students"][0]["attempts"]["د1"]["courses"][0]["cells"]["total"]["formula"] is True
    assert len(result["course_groups"]) == 12
    assert result["course_groups"][0]["course_id"] is None
    assert result["saved_to_database"] is False

def test_missing_attempt_is_flagged():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["C8"] = "طالب تجريبي محمد احمد"
    ws["D8"] = "د1"
    ws["C11"] = "طالب تجريبي اخر محمد"
    ws["D11"] = "د1"
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    result = parse_annual_register(out, "synthetic.xlsx")
    assert any(i["code"] == "missing_attempts" for i in result["issues"])
