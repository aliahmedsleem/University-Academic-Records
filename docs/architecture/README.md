# Architecture — target design

One college has many departments. Each department has programs, academic years, stages, courses, sections and students.

## Planned modules
- Identity and role-based access (administrator, registrar, department operator, instructor, auditor)
- Students and academic profiles
- Academic structure and course catalog
- Assessment components and grading rules per academic year
- Import batches, raw source provenance, validation findings and approval workflow
- Immutable grade change history and reconciliation reports

## Data integrity
A grade must be traceable to the original upload, worksheet, row, column, assessment definition and approver. Imports are staged first and never overwrite approved records. Student IDs are primary matching keys; name matching alone never auto-approves.

## Production baseline
PostgreSQL, SQLAlchemy/Alembic, object storage, Celery/Redis, authentication, CSRF protection, malware scanning, upload quotas, backup/restore and audit logs. These are planned, not yet implemented.
