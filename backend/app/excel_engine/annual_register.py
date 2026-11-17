"""Read-only parser for the three-attempt annual grade register.

A candidate is a group of three rows (د1، د2، ق), not three students.
Course identities are deliberately not inferred from column positions.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import re
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
        cached_wb = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=True, keep_links=False)
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
            cached_ws = cached_wb[sheet_name]
            if ws.max_row > MAX_ROWS or ws.max_column > MAX_COLUMNS:
                raise WorkbookReadError("Worksheet exceeds safe dimensions")
            # Extract only metadata explicitly written in the workbook.
            header_cells = [_text(ws.cell(r, col).value) for r in range(1, 5) for col in range(1, min(ws.max_column, 62) + 1)]
            header_text = " | ".join(v for v in header_cells if v and not v.startswith("="))
            year_match = re.search(r"(?:العام\\s*الدراسي|السنة\\s*الدراسية)\\s*[:：]?\\s*(\\d{4}\\s*[-–/]\\s*\\d{4})", header_text)
            def labeled_value(label):
                match = re.search(label + r"\\s*[:：]\\s*([^|]+)", header_text)
                return match.group(1).strip() if match and match.group(1).strip() else None
            academic_metadata = {
                "academic_year": re.sub(r"\\s+", "", year_match.group(1)) if year_match else None,
                "department": labeled_value("القسم"),
                "stage": labeled_value("المرحلة"),
                "study": labeled_value("الدراسة"),
                "cohort": labeled_value("الدفعة"),
            }
            groups = []
            for start in range(5, 41, 3):
                groups.append({
                    "group": len(groups) + 1,
                    "columns": {"annual": start, "final_exam": start + 1, "total": start + 2},
                    "credit_hours_raw": ws.cell(5, start).value,
                    "course_name_raw": _text(ws.cell(6, start).value),
                    "course_id": None,
                    "requires_course_mapping": True,
                })
            students, issues = [], []
            pending = None
            # Stream both worksheets once. Reopening iter_rows for every row
            # rescans the XLSX XML from the beginning (quadratic slowdown).
            original_rows = ws.iter_rows(min_row=8, max_col=47, values_only=True)
            cached_rows = cached_ws.iter_rows(min_row=8, max_col=47, values_only=True)
            for row_number, (row, cached_row) in enumerate(zip(original_rows, cached_rows), 8):
                if len(students) >= max_students:
                    break
                name = _text(row[2]) if len(row) > 2 else ""
                attempt = _text(row[3]) if len(row) > 3 else ""
                # Student identity remains a candidate until manually reviewed.
                # No mandatory serial number: some legitimate registers omit it.
                valid_name = (
                    bool(name) and not name.startswith("=")
                    and len(name.split()) >= 2
                    and name.replace(" ", "").replace("ـ", "") not in
                    {"الاسم", "اسمالطالب", "اسمالطالبة", "اسماءالطلبة", "اسماءالطلاب"}
                )
                # Serial numbers are optional in legitimate register templates.
                # A plausible name on the first-attempt row is sufficient for
                # a *candidate*, never for automatic identity confirmation.
                starts_student = valid_name and attempt == ATTEMPTS[0]
                if name and not starts_student:
                    issues.append({"row": row_number, "code": "non_student_name_cell"})
                if starts_student:
                    if pending is not None:
                        issues.append({"row": pending["excel_row"], "code": "incomplete_attempt_group"})
                        students.append(pending)
                        if len(students) >= max_students:
                            break
                    pending = {"excel_row": row_number, "name_candidate": name,
                               "attempts": {}, "review_required": True}
                elif name:
                    # A heading or formula interrupts the current table.
                    if pending is not None:
                        issues.append({"row": pending["excel_row"], "code": "incomplete_attempt_group"})
                        students.append(pending)
                        pending = None
                    continue
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
                        is_formula = isinstance(v, str) and v.startswith("=")
                        cached = cached_row[col - 1] if len(cached_row) >= col else None
                        cached_number = isinstance(cached, (int, float)) and not isinstance(cached, bool)
                        cells[field] = {
                            "raw": _text(v)[:120],
                            "formula": is_formula,
                            "cached_value": cached if is_formula and cached_number else None,
                            "value_status": ("formula_cached_unverified" if cached_number else "formula_without_cached_value") if is_formula else "literal",
                        }
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
                "academic_metadata": academic_metadata,
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
            cached_wb.close()
    except WorkbookReadError:
        raise
    except (BadZipFile, OSError, ValueError, TypeError, KeyError) as exc:
        raise WorkbookReadError("Could not read annual register") from exc
