"""Conservative candidate extraction for grade-register spreadsheets.

Never writes to the database. Column mapping and grade interpretation require review.
"""
from io import BytesIO
from pathlib import Path
import openpyxl
import xlrd
import hashlib
from .reader import WorkbookReadError, OLE_SIGNATURE, MAX_ROWS, MAX_COLUMNS, MAX_SHEETS
from .templates import classify_sheet, classify_workbook

MAX_CANDIDATES = 300
MAX_COURSES = 60
HEADER_ROWS = (7, 8, 9)
MAX_UPLOAD = 15 * 1024 * 1024

def _clean(value):
    if value is None:
        return ""
    return str(value).strip()

def _candidate_name(value):
    s = _clean(value)
    if not (7 <= len(s) <= 150) or not any("\u0621" <= c <= "\u064a" for c in s):
        return False
    return 3 <= len(s.split()) <= 7 and not any(ch.isdigit() for ch in s) and not s.startswith("=")

def _scan(get_value, max_row, max_col, sheet_name, name_column=3, start_row=10):
    # Name column and first data row can be configured by a reviewer.
    header = []
    for col in range(1, min(max_col, MAX_COLUMNS) + 1):
        parts = [_clean(get_value(row, col)) for row in HEADER_ROWS]
        if any(parts):
            header.append({"column": col, "header": parts})
    candidates = []
    for row in range(start_row, min(max_row, MAX_ROWS) + 1):
        name = _clean(get_value(row, name_column))
        if not _candidate_name(name):
            continue
        cells = []
        for col in range(1, min(max_col, 28) + 1):
            if col == name_column:\n                continue\n            value = get_value(row, col)
            if value is not None and _clean(value):
                cells.append({"column": col, "value": _clean(value)[:120], "formula": False})
        candidates.append({"excel_row": row, "name_candidate": name, "cells": cells})
        if len(candidates) >= MAX_CANDIDATES:
            break
    return {"sheet": sheet_name, "header_cells": header[:MAX_COURSES * 4],
            "candidate_rows": candidates, "candidate_count_preview": len(candidates),
            "truncated": len(candidates) == MAX_CANDIDATES,
            "review_required": True}

def extract_candidates(stream, filename, sheet_name=None, name_column=3, start_row=10):
    if type(name_column) is not int or not 1 <= name_column <= MAX_COLUMNS:
        raise WorkbookReadError("Invalid name column")
    if type(start_row) is not int or not 1 <= start_row <= MAX_ROWS:
        raise WorkbookReadError("Invalid starting row")
    if sheet_name is not None and (not isinstance(sheet_name, str) or not sheet_name.strip() or len(sheet_name) > 100):
        raise WorkbookReadError("Invalid sheet name")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xls", ".xlsx", ".xlsm"}:
        raise WorkbookReadError("Unsupported Excel format")
    raw = stream.read(MAX_UPLOAD + 1)
    if not raw or len(raw) > MAX_UPLOAD:
        raise WorkbookReadError("Empty or oversized file")
    digest = hashlib.sha256(raw).hexdigest()
    if suffix == ".xls":
        if not raw.startswith(OLE_SIGNATURE):
            raise WorkbookReadError("Invalid XLS signature")
        try:
            book = xlrd.open_workbook(file_contents=raw, on_demand=True)
            try:
                if book.nsheets > MAX_SHEETS:
                    raise WorkbookReadError("Too many worksheets")
                names = book.sheet_names()
                sheets = []
                for sheet in book.sheets():
                    if (sheet.name != sheet_name if sheet_name else classify_sheet(sheet.name) != "primary_grades"):
                        continue
                    if sheet.nrows > MAX_ROWS or sheet.ncols > MAX_COLUMNS:
                        raise WorkbookReadError("Worksheet exceeds limits")
                    def value(r,c):
                        return sheet.cell_value(r-1,c-1) if r <= sheet.nrows and c <= sheet.ncols else None
                    sheets.append(_scan(value,sheet.nrows,sheet.ncols,sheet.name,name_column,start_row))
            finally:
                book.release_resources()
        except xlrd.XLRDError as exc:
            raise WorkbookReadError("Could not read XLS workbook") from exc
    else:
        from zipfile import ZipFile, BadZipFile
        try:
            with ZipFile(BytesIO(raw)) as archive:
                infos = archive.infolist()
                if len(infos) > 20000 or sum(i.file_size for i in infos) > 250*1024*1024:
                    raise WorkbookReadError("Workbook exceeds safe decompressed size")
            book = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
            try:
                if len(book.worksheets) > MAX_SHEETS:
                    raise WorkbookReadError("Too many worksheets")
                names = book.sheetnames
                sheets = []
                for sheet in book.worksheets:
                    if (sheet.title != sheet_name if sheet_name else classify_sheet(sheet.title) != "primary_grades"):
                        continue
                    if sheet.max_row > MAX_ROWS or sheet.max_column > MAX_COLUMNS:
                        raise WorkbookReadError("Worksheet exceeds limits")
                    # Avoid repeatedly accessing random rows in read-only worksheets.
                    rows = sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, MAX_ROWS),
                                           max_col=min(sheet.max_column, MAX_COLUMNS), values_only=True)
                    headers = {}
                    candidates = []
                    for row_num, values in enumerate(rows, 1):
                        if row_num in HEADER_ROWS:
                            headers[row_num] = values
                        if row_num < start_row:
                            continue
                        name = _clean(values[name_column-1] if len(values) >= name_column else None)
                        if not _candidate_name(name):
                            continue
                        cells = [{"column": j+1, "value": _clean(v)[:120], "formula": isinstance(v,str) and v.startswith("=")}
                                 for j,v in enumerate(values[:28]) if j+1 != name_column and v is not None and _clean(v)]
                        candidates.append({"excel_row": row_num, "name_candidate": name, "cells": cells})
                        if len(candidates) >= MAX_CANDIDATES:
                            break
                    header_cells = []
                    for col in range(1,min(sheet.max_column,MAX_COLUMNS)+1):
                        parts = [_clean(headers.get(r,())[col-1]) if len(headers.get(r,())) >= col else "" for r in HEADER_ROWS]
                        if any(parts):
                            header_cells.append({"column":col,"header":parts})
                    sheets.append({"sheet":sheet.title,"header_cells":header_cells[:MAX_COURSES*4],
                                   "candidate_rows":candidates,"candidate_count_preview":len(candidates),
                                   "truncated":len(candidates)==MAX_CANDIDATES,"review_required":True})
            finally:
                book.close()
        except (BadZipFile, ValueError, TypeError, OSError) as exc:
            if isinstance(exc, WorkbookReadError):
                raise
            raise WorkbookReadError("Could not read OOXML workbook") from exc
    return {"filename":Path(filename).name,"sha256":digest,"template_family":classify_workbook(names),
            "sheets":sheets,"mapping":{"sheet_name":sheet_name,"name_column":name_column,"start_row":start_row},"review_required":True,"saved_to_database":False,
            "warnings":["Student names are candidates, not verified identities.",
                        "Assessment columns are raw values, not interpreted grades.",
                        "Cells marked formula=true must not be treated as verified scores.",
                        "No student records or grades have been saved."]}
