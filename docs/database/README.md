# Academic data model — milestone 2

- Department (college has many departments)
- AcademicYear (year label)
- Stage (department-specific stage)
- Student (globally unique university identifier)
- Course (belongs to department and stage)
- CourseOffering (course, year, section)
- GradeImportBatch (source checksum and approval status)
- Grade (student, offering, assessment, attempt, decimal score)

The initial model intentionally does **not** determine passing thresholds or assessment maximums: these depend on real college regulations and templates.

Important pending safeguards: course/stage/department cross-reference validation, enrollment history, assessment definitions and maximum scores, import staging rows, reviewer identities, audit events, authorization and transaction-safe approval. No grade import writes are exposed.

Use Alembic migrations, not create_all, for deployment.
