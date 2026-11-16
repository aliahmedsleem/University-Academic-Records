# University Academic Records Management System (UARMS)

Arabic-first academic records system for **one college with multiple departments**.

## Scope
- Departments, students, courses, academic years and grades
- Auditable, review-before-commit Excel imports (.xls/.xlsx)
- Multiple grade-sheet layouts through explicit template mappings
- No automatic overwriting of approved grades

## Initial implementation
The first milestone provides a Flask API with a **read-only Excel preview** endpoint. It does not import or modify academic records.

### Run locally (Python 3.11+)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```
Test:
```bash
curl http://127.0.0.1:5000/api/health
curl -F "file=@grades.xlsx" http://127.0.0.1:5000/api/excel/preview
pytest
```

## Security notes
Never upload real student information to public issues, commits or sample fixtures. Restrict access to academic records; encryption, authentication, role-based access and audit trails are required before production use. Treat preview results as **unverified**. Formula cached results can be missing or stale.

See [architecture](docs/architecture/README.md) and [Excel import specification](docs/excel-import/README.md).
