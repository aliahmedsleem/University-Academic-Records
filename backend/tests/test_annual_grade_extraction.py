"""Synthetic verification of course labels, literal scores and formula provenance."""
from io import BytesIO
import openpyxl
from app.excel_engine.annual_register import parse_annual_register


def test_grade_cells_and_subject_names_are_extracted_without_writing():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["E6"] = "اللغة الانكليزية"
    ws["B8"] = 1
    ws["C8"] = "طالب تجريبي"
    for row, attempt in ((8, "د1"), (9, "د2"), (10, "ق")):
        ws.cell(row, 4, attempt)
    ws["E8"] = 24
    ws["F8"] = 22
    ws["G8"] = "=E8+F8"
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    result = parse_annual_register(buffer, "synthetic.xlsx")
    assert result["course_groups"][0]["course_name_raw"] == "اللغة الانكليزية"
    cells = result["candidate_students"][0]["attempts"]["د1"]["courses"][0]["cells"]
    assert cells["annual"]["raw"] == "24"
    assert cells["final_exam"]["raw"] == "22"
    assert cells["total"]["formula"] is True
    assert cells["total"]["cached_value"] is None
    assert cells["total"]["value_status"] == "formula_without_cached_value"
    assert result["saved_to_database"] is False
