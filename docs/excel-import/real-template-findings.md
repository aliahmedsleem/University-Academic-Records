# Findings from six locally supplied workbooks (2026-11-17)

**Privacy:** This document intentionally contains no student names, grades, or original uploads. The originals must not be committed to this public repository.

- Inputs: three distinct legacy XLS files plus a duplicate of one of them, and two macro-enabled XLSM files.
- SHA-256 duplicate: 3(1).xls and 3-1.xls match exactly.
- 4.xlsm: nine worksheets. Primary grade sheet: `سجل الدرجات`. Carried: `سجل المحملين`. Derived: `السجل العام`, `النتائج`, `النتائج (2)`, `الاحصائيات`.
- 5.xlsm: ten worksheets. Primary grade sheet: `س درجات`. Carried: `س المحملين`. Derived: `س العام`, `نتائج`, `نتائج 2`, `احصائيات`.
- Both XLSM families include `المعلومات` metadata sheets and many cross-sheet formulas. Some sheets have thousands of formatted rows, so visible worksheet dimensions do not necessarily indicate student counts.
- The primary grade sheet in family A has header rows around 7–9, and family B around 7–9. These are *observations*, not approved import mappings.
- Some sheets refer to external workbooks. No external references or macros should be executed.
- Legacy XLS sheets require further inspection using xlrd in a configured environment.

## Rules
1. Identify format from file signature and extension.
2. Record SHA-256, reject repeated imports with same fingerprint once persistent import batches exist.
3. Classify worksheets by exact known names; never infer grades from statistics/results sheets.
4. Treat formulas and cached results as untrusted pending validation.
5. Require human-approved column mapping and student matching before import.
6. Never commit the supplied student workbooks to a public repository.
