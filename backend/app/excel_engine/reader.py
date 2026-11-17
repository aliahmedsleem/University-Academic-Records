"""Conservative Excel workbook inspection, without grade import or execution.

No macros are executed. Formula cells are flagged, not silently accepted.
"""
from io import BytesIO
from pathlib import Path
from zipfile import is_zipfile, BadZipFile, ZipFile
import hashlib

import openpyxl
import xlrd


class WorkbookReadError(ValueError):
    pass


OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
MAX_SHEETS = 100
MAX_ROWS = 100_000
MAX_COLUMNS = 300
PREVIEW_ROWS = 12
PREVIEW_COLUMNS = 25


def _safe_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def inspect_workbook(stream, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xls", ".xlsx", ".xlsm"}:
        raise WorkbookReadError("Only .xls, .xlsx and .xlsm files are supported")
    raw = stream.read(15 * 1024 * 1024 + 1)
    if len(raw) > 15 * 1024 * 1024:
        raise WorkbookReadError("File exceeds the 15 MB limit")
    if not raw:
        raise WorkbookReadError("File is empty")

    if suffix in {".xlsx", ".xlsm"}:
        if not is_zipfile(BytesIO(raw)):
            raise WorkbookReadError("Invalid XLSX container")
        try:
            with ZipFile(BytesIO(raw)) as archive:
                infos = archive.infolist()
                if len(infos) > 20000 or sum(item.file_size for item in infos) > 250 * 1024 * 1024:
                    raise WorkbookReadError("Workbook exceeds safe decompressed size")
                contains_macros = any(item.filename.lower().endswith("vbaproject.bin") for item in infos)
            wb = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
            try:
                if len(wb.worksheets) > MAX_SHEETS:
                    raise WorkbookReadError("Too many worksheets")
                sheets = []
                for ws in wb.worksheets:
                    if ws.max_row > MAX_ROWS or ws.max_column > MAX_COLUMNS:
                        raise WorkbookReadError("Worksheet exceeds configured dimensions")
                    preview = [
                        [_safe_value(ws.cell(r, c).value) for c in range(1, min(ws.max_column, PREVIEW_COLUMNS) + 1)]
                        for r in range(1, min(ws.max_row, PREVIEW_ROWS) + 1)
                    ]
                    formulas = sum(1 for row in ws for cell in row if cell.data_type == "f")
                    sheets.append({
                        "name": ws.title, "rows": ws.max_row, "columns": ws.max_column,
                        "merged_ranges": [], "merged_ranges_inspected": False,
                        "formula_count": formulas, "preview": preview,
                    })
                return {"filename": Path(filename).name, "format": suffix[1:],
                        "status": "preview_only_unverified", "sha256": hashlib.sha256(raw).hexdigest(), "contains_macros": contains_macros, "sheets": sheets,
                        "warnings": ["Formula results are not verified; never approve grades from preview alone.", "Merged cells are not inspected in streaming preview.", "Macros are never executed."]}
            finally:
                wb.close()
        except (BadZipFile, KeyError, ValueError, TypeError, OSError) as exc:
            if isinstance(exc, WorkbookReadError):
                raise
            raise WorkbookReadError("Could not parse OOXML workbook") from exc

    if not raw.startswith(OLE_SIGNATURE):
        raise WorkbookReadError("Invalid XLS container")
    try:
        wb = xlrd.open_workbook(file_contents=raw, on_demand=True)
        try:
            if wb.nsheets > MAX_SHEETS:
                raise WorkbookReadError("Too many worksheets")
            sheets = []
            for ws in wb.sheets():
                if ws.nrows > MAX_ROWS or ws.ncols > MAX_COLUMNS:
                    raise WorkbookReadError("Worksheet exceeds configured dimensions")
                preview = [
                    [_safe_value(ws.cell_value(r, c)) for c in range(min(ws.ncols, PREVIEW_COLUMNS))]
                    for r in range(min(ws.nrows, PREVIEW_ROWS))
                ]
                sheets.append({"name": ws.name, "rows": ws.nrows, "columns": ws.ncols,
                               "preview": preview, "formula_count": None,
                               "merged_ranges": []})
            return {"filename": Path(filename).name, "format": "xls",
                    "status": "preview_only_unverified", "sha256": hashlib.sha256(raw).hexdigest(), "contains_macros": False, "sheets": sheets,
                    "warnings": ["XLS formulas and merged ranges are not validated by this preview."]}
        finally:
            wb.release_resources()
    except (xlrd.XLRDError, ValueError, TypeError, OSError) as exc:
        if isinstance(exc, WorkbookReadError):
            raise
        raise WorkbookReadError("Could not parse XLS workbook") from exc
