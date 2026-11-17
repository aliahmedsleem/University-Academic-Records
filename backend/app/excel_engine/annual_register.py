"""Read-only parser for the three-attempt annual grade register.

A candidate is a group of three rows (د1، د2، ق), not three students.
Course identities are deliberately not inferred from column positions.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import openpyxl
from .reader import WorkbookReadError, MAX_ROWS, MAX_COLUMNS, MAX_SHEETS

ATTEMPTS = ("د1", "د2", "ق")
FIELDS = ("annual", "final_exam", "total")
MAX_FILE = 15 * 1024 * 1024
MAX_PREVIEW_STUDENTS = 150

def _text(v):
    return "" if v is None else str(v).strip()

def parse_annual_register(stream, filename, sheet_name=None, max_students=MAX_PREVIEW_STUDENTS):
    if Path(filename).suffix.lower() not in (".xlsx", ".xlsm"):
        raise WorkbookReadError("Annual register parser supports XLSX and XLSM only")
    if type(max_students) is not int or not 1 <= max_students <= MAX_PREVIEW_STUDENTS:
        raise WorkbookReadError("Invalid preview limit")
    raw = stream.read(MAX_FILE + 1)
    if not raw or len(raw) > MAX_FILE:
        raise WorkbookReadError("Empty or oversized workbook")
    from zipfile import ZipFile, BadZipFile
    try:
        with ZipFile(BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > 20000 or sum(x.file_size for x in infos) > 250 * 1024 * 1024:
                raise WorkbookReadError("Workbook exceeds safe decompressed size")
        wb = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        try:
            if len(wb.worksheets) > MAX_SHEETS:
                raise WorkbookReadError("Workbook has too many sheets")
            if sheet_name:
                if sheet_name not in wb.sheetnames:
                    raise WorkbookReadError("Selected sheet not found. Available: " + ", ".join(wb.sheetnames[:10]))
            else:
                sheet_name = next((name for name in wb.sheetnames if "سجل" in name and "درج" in name), None)
                if sheet_name is None:
                    raise WorkbookReadError("Annual grade sheet not identified. Select one of: " + ", ".join(wb.sheetnames[:10]))
            ws = wb[sheet_name]
            if ws.max_row > MAX_ROWS or ws.max_column > MAX_COLUMNS:
                raise WorkbookReadError("Worksheet exceeds safe dimensions")
            groups = []
            for start in range(5, 41, 3):
                groups.append({
                    "group": len(groups) + 1,
                    "columns": {"annual": start, "final_exam": start + 1, "total": start + 2},
                    "credit_hours_raw": ws.cell(5, start).value,
                    "course_id": None,
                    "requires_course_mapping": True,
                })
            students, issues = [], []
            pending = None
            for row_number, row in enumerate(ws.iter_rows(min_row=8, max_col=47, values_only=True), 8):
                if len(students) >= max_students:
                    break
                name = _text(row[2]) if len(row) > 2 else ""
                attempt = _text(row[3]) if len(row) > 3 else ""
                if name:
                    if pending is not None:
                        issues.append({"row": pending["excel_row"], "code": "incomplete_attempt_group"})
                        students.append(pending)
                        if len(students) >= max_students:
                            break
                    pending = {"excel_row": row_number, "name_candidate": name,
                               "attempts": {}, "review_required": True}
                if pending is None:
                    continue
                if attempt not in ATTEMPTS:
                    if name:
                        issues.append({"row": row_number, "code": "unexpected_attempt_label"})
                    continue
                if attempt in pending["attempts"]:
                    issues.append({"row": row_number, "code": "duplicate_attempt_label"})
                    continue
                values = []
                for group in groups:
                    cells = {}
                    for field, col in group["columns"].items():
                        v = row[col - 1] if len(row) >= col else None
                        cells[field] = {"raw": _text(v)[:120], "formula": isinstance(v, str) and v.startswith("=")}
                    values.append({"group": group["group"], "cells": cells})
                pending["attempts"][attempt] = {
                    "excel_row": row_number, "courses": values,
                    "summary_raw": {
                        "sum": _text(row[40]) if len(row) > 40 else "",
                        "average": _text(row[41]) if len(row) > 41 else "",
                        "result": _text(row[42]) if len(row) > 42 else "",
                    }
                }
                if len(pending["attempts"]) == len(ATTEMPTS):
                    students.append(pending)
                    pending = None
            if pending is not None and len(students) < max_students:
                issues.append({"row": pending["excel_row"], "code": "incomplete_attempt_group"})
                students.append(pending)
            for student in students:
                missing = [a for a in ATTEMPTS if a not in student["attempts"]]
                if missing:
                    issues.append({"row": student["excel_row"], "code": "missing_attempts", "attempts": missing})
            return {
                "filename": Path(filename).name, "sha256": hashlib.sha256(raw).hexdigest(),
                "sheet": sheet_name, "layout": "annual_three_attempts",
                "attempt_labels": list(ATTEMPTS), "course_groups": groups,
                "candidate_students": students, "candidate_count_preview": len(students),
                "preview_limit": max_students, "issues": issues,
                "review_required": True, "saved_to_database": False,
                "warnings": ["Names are unverified candidates.",
                             "Course identities require explicit mapping.",
                             "Formula cells are not verified grades.",
                             "No student records or grades have been saved."]
            }
        finally:
            wb.close()
    except (BadZipFile, OSError, ValueError, TypeError, KeyError) as exc:
        raise WorkbookReadError("Could not read annual register") from exc
