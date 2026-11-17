from io import BytesIO
import openpyxl
from app.excel_engine.annual_register import parse_annual_register
from app.excel_engine.reader import WorkbookReadError

def make_book():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "الدرجات السنوية"
    sheet["B8"] = 1
    sheet["C8"] = "طالب تجريبي"
    for row, label in [(8, "د1"), (9, "د2"), (10, "ق")]:
        sheet.cell(row, 4, label)
    stream = BytesIO()
    book.save(stream)
    stream.seek(0)
    return stream

def test_custom_sheet_selection():
    result = parse_annual_register(make_book(), "custom.xlsx", sheet_name="الدرجات السنوية")
    assert result["sheet"] == "الدرجات السنوية"
    assert result["candidate_count_preview"] == 1

def test_missing_sheet_reports_available_names():
    try:
        parse_annual_register(make_book(), "custom.xlsx", sheet_name="سجل الدرجات")
        assert False, "Expected workbook error"
    except WorkbookReadError as exc:
        assert "الدرجات السنوية" in str(exc)
