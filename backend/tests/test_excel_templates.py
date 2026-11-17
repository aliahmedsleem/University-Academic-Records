from io import BytesIO
from zipfile import ZipFile
import openpyxl
from app.excel_engine.reader import inspect_workbook, WorkbookReadError
from app.excel_engine.templates import enrich_preview

def test_xlsm_preview():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "المعلومات"
    ws["A1"] = "السنة الدراسية"
    ws2 = wb.create_sheet("سجل الدرجات")
    ws2["B9"] = "اسم الطالب"
    data = BytesIO()
    wb.save(data)
    data.seek(0)
    preview = enrich_preview(inspect_workbook(data, "test.xlsm"))
    assert preview["template_family"] == "grade_register_family_a"
    assert preview["import_allowed"] is False
    assert preview["sha256"]
    assert preview["sheets"][1]["role"] == "primary_grades"

def test_invalid_xlsm():
    try:
        inspect_workbook(BytesIO(b"not a zip"), "bad.xlsm")
    except WorkbookReadError:
        pass
    else:
        raise AssertionError("Corrupt workbook must be rejected")

def test_candidate_extraction_never_saves():
    from app.excel_engine.extractor import extract_candidates
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "المعلومات"
    grades = wb.create_sheet("سجل الدرجات")
    grades["C9"] = "اسم الطالب"
    grades["E8"] = "الرياضيات"
    grades["C10"] = "احمد محمد علي حسين"
    grades["E10"] = 82
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    result = extract_candidates(output, "test.xlsx")
    assert result["saved_to_database"] is False
    assert result["review_required"] is True
    assert result["sheets"][0]["candidate_rows"][0]["excel_row"] == 10
    assert result["sheets"][0]["candidate_rows"][0]["cells"][0]["value"] == "82"

def test_formula_is_flagged_in_candidates():
    from app.excel_engine.extractor import extract_candidates
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الدرجات"
    ws["C10"] = "احمد محمد علي حسين"
    ws["E10"] = "=SUM(F10:G10)"
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    result = extract_candidates(output, "grades.xlsx")
    assert len(result["sha256"]) == 64
    cell = result["sheets"][0]["candidate_rows"][0]["cells"][0]
    assert cell["column"] == 5
    assert cell["formula"] is True
    assert result["saved_to_database"] is False
