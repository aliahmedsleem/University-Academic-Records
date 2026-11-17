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
