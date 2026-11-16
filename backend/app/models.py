"""Relational academic foundation. No grade imports are committed in milestone 2."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, CheckConstraint

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name_ar = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200))
    active = db.Column(db.Boolean, nullable=False, default=True)

class AcademicYear(db.Model):
    __tablename__ = "academic_years"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(20), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=False)

class Stage(db.Model):
    __tablename__ = "stages"
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    __table_args__ = (UniqueConstraint("department_id", "number"), CheckConstraint("number >= 1"),)

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.String(64), nullable=False, unique=True)
    full_name_ar = db.Column(db.String(250), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    enrollment_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="active")
    __table_args__ = (CheckConstraint("status IN ('active','graduated','suspended','withdrawn')"),)

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey("stages.id"), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    name_ar = db.Column(db.String(250), nullable=False)
    credits = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("department_id", "code"), CheckConstraint("credits >= 0"),)

class CourseOffering(db.Model):
    __tablename__ = "course_offerings"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    section = db.Column(db.String(30), nullable=False, default="A")
    __table_args__ = (UniqueConstraint("course_id", "academic_year_id", "section"),)

class GradeImportBatch(db.Model):
    __tablename__ = "grade_import_batches"
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending_review")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    __table_args__ = (CheckConstraint("status IN ('pending_review','rejected','approved')"),)

class Grade(db.Model):
    __tablename__ = "grades"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    offering_id = db.Column(db.Integer, db.ForeignKey("course_offerings.id"), nullable=False)
    assessment_code = db.Column(db.String(40), nullable=False)
    attempt = db.Column(db.Integer, nullable=False, default=1)
    score = db.Column(db.Numeric(8, 3), nullable=False)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("grade_import_batches.id"))
    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", "assessment_code", "attempt"),
        CheckConstraint("score >= 0"),
        CheckConstraint("attempt >= 1"),
    )
