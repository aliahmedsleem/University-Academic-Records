# Excel import — acceptance contract

## Supported inputs
- Legacy XLS via xlrd
- XLSX via openpyxl
- XLSM not supported in milestone 1; macro-enabled files require an explicit threat model

## Processing pipeline (planned)
1. Store original immutable file with SHA-256 and upload metadata
2. Validate actual container format, size and workbook structure
3. Detect template and header positions, including merged headers
4. Extract raw cells with worksheet coordinates and original data types
5. Map columns to canonical student/course/assessment fields
6. Validate ranges, required fields, duplicate students and inconsistent totals
7. Match students by authoritative university identifier
8. Show row-level errors and side-by-side changes for manual approval
9. Commit approved batch transactionally with immutable audit events

## Critical cases to test
- Arabic/English column names and reordered headers
- Multiple sheets, merged headers, hidden rows and columns
- Blank cells, duplicate identifiers, inconsistent totals
- Date and numeric formatting, Unicode digits, zero marks
- Formulas with missing/stale cached values and external links
- Protected worksheets, corrupt or renamed files
- Large sheets, oversized files, ZIP bombs and resource exhaustion

## Current status
Only structural preview exists. No template recognition, student matching, approval, grade persistence or automatic import has been implemented. Never treat preview output as verified academic results.
