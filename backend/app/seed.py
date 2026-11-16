"""Seed data for QAAI.

Sets up the institution structure, the Year 3 course units a student walks
through in one evaluation session, the evaluation template shared across
every course, and the reviewer account used to sign in to the dashboard.
No fabricated evaluation responses are generated here — all evaluation
data comes from real students using the app.
"""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .db import SessionLocal
from .security import hash_password

CRITERIA = [
    {
        "key": "teaching_clarity",
        "label": "Teaching clarity",
        "question": "Let's start with how the lecturer explains things — how clear have the lectures been for this course?",
        "requires_rating": False,
    },
    {
        "key": "lecturer_preparedness",
        "label": "Lecturer preparedness",
        "question": "How prepared did the lecturer seem for each session — were materials and examples ready to go?",
        "requires_rating": False,
    },
    {
        "key": "learning_materials",
        "label": "Learning materials",
        "question": "What did you think of the materials — slides, notes, readings, or anything shared online?",
        "requires_rating": False,
    },
    {
        "key": "practical_learning",
        "label": "Practical learning opportunities",
        "question": "How were the practical side of things — labs, exercises, or hands-on work? Enough practice, or not quite?",
        "requires_rating": False,
    },
    {
        "key": "student_engagement",
        "label": "Student engagement",
        "question": "How engaged did you feel in class — discussions, questions, activities, that kind of thing?",
        "requires_rating": False,
    },
    {
        "key": "lecturer_accessibility",
        "label": "Lecturer accessibility",
        "question": "Could you actually reach the lecturer when you needed help — in class, office hours, or online?",
        "requires_rating": False,
    },
    {
        "key": "assessment_feedback",
        "label": "Assessment and feedback",
        "question": "How were assessments and feedback for this course — fair, and actually useful for improving?",
        "requires_rating": False,
    },
    {
        "key": "overall_experience",
        "label": "Overall course experience",
        "question": "Last one for this course — overall, how was your experience of it?",
        "requires_rating": True,
    },
]

# (name, code, lecturer name, lecturer title)
YEAR3_COURSE_UNITS = [
    ("Embedded Systems", "CSC3101", "David", "Mr"),
    ("Data Mining and Business Intelligence", "CSC3102", "Mukyaake", "Mr"),
    ("Logic Programming", "CSC3103", "Fred", "Mr"),
    ("Business English", "LAN3101", "Otaala", "Prof"),
    ("Remote Sensing", "CSC3104", "Luwaga", "Mr"),
    ("Computability and Complexity", "CSC3105", "Byron", "Mr"),
]


def _get_or_create(db: Session, model, defaults: dict | None = None, **filters):
    instance = db.scalar(select(model).filter_by(**filters))
    if instance is not None:
        return instance
    values = dict(filters)
    if defaults:
        values.update(defaults)
    instance = model(**values)
    db.add(instance)
    db.flush()
    return instance


def seed_structure(db: Session):
    institution = _get_or_create(
        db, models.Institution, {"name": "Uganda Martyrs University"}, code="UMU"
    )
    faculty = _get_or_create(
        db,
        models.Faculty,
        {"name": "Faculty of Science", "code": "SCI"},
        institution_id=institution.id,
        code="SCI",
    )
    department = _get_or_create(
        db,
        models.Department,
        {"name": "Department of Computing", "code": "COMP"},
        faculty_id=faculty.id,
        code="COMP",
    )
    course = _get_or_create(
        db,
        models.Course,
        {"name": "Bachelor of Science in Computer Science", "code": "BSCS"},
        department_id=department.id,
        code="BSCS",
    )

    course_units: list[models.CourseUnit] = []
    for position, (name, code, lecturer_name, lecturer_title) in enumerate(
        YEAR3_COURSE_UNITS
    ):
        course_unit = _get_or_create(
            db,
            models.CourseUnit,
            {
                "name": name,
                "code": code,
                "semester": "Year 3",
                "credits": 3,
                "year": 3,
                "position": position,
            },
            course_id=course.id,
            code=code,
        )
        if course_unit.year != 3 or course_unit.position != position:
            course_unit.year = 3
            course_unit.position = position

        lecturer = db.scalar(
            select(models.Lecturer).where(
                models.Lecturer.course_unit_id == course_unit.id,
                models.Lecturer.name == lecturer_name,
            )
        )
        if lecturer is None:
            lecturer = models.Lecturer(
                course_unit_id=course_unit.id,
                name=lecturer_name,
                title=lecturer_title,
            )
            db.add(lecturer)
            db.flush()
        course_units.append(course_unit)

    template = db.scalar(
        select(models.EvaluationTemplate).where(
            models.EvaluationTemplate.key == "umu-year3-review"
        )
    )
    if template is None:
        template = models.EvaluationTemplate(
            institution_id=institution.id,
            key="umu-year3-review",
            name="Year 3 course review",
            version="1.0",
            description=(
                "A single conversation covering every Year 3 course unit, one at "
                "a time, with the same core questions for each."
            ),
            is_active=True,
        )
        db.add(template)
        db.flush()

    existing = {
        criterion.key
        for criterion in db.scalars(
            select(models.EvaluationCriterion).where(
                models.EvaluationCriterion.template_id == template.id
            )
        )
    }
    for position, item in enumerate(CRITERIA):
        if item["key"] in existing:
            continue
        db.add(
            models.EvaluationCriterion(
                template_id=template.id,
                key=item["key"],
                label=item["label"],
                description=None,
                question=item["question"],
                position=position,
                is_mandatory=True,
                requires_rating=item["requires_rating"],
            )
        )
    db.flush()
    return institution, faculty, department, course, course_units, template


def seed_reviewer(db: Session, email: str, password: str, name: str):
    reviewer = db.scalar(
        select(models.ReviewerAccount).where(models.ReviewerAccount.email == email.lower())
    )
    if reviewer is None:
        reviewer = models.ReviewerAccount(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
            role="reviewer",
            is_active=True,
        )
        db.add(reviewer)
        db.flush()
    return reviewer


def run_seed(reset_demo: bool = False) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        institution, faculty, department, course, course_units, template = seed_structure(db)
        reviewer = seed_reviewer(
            db,
            settings.seed_reviewer_email,
            settings.seed_reviewer_password,
            settings.seed_reviewer_name,
        )

        if reset_demo:
            demo_sessions = list(
                db.scalars(
                    select(models.EvaluationSession).where(
                        models.EvaluationSession.is_demo.is_(True)
                    )
                )
            )
            for session in demo_sessions:
                db.delete(session)
            db.flush()

        db.commit()

        print("QAAI seed complete")
        print(f"  Institution: {institution.name}")
        print(f"  Template: {template.name} [{template.key}]")
        print(f"  Year 3 course units ({len(course_units)}):")
        for course_unit in course_units:
            lecturer = course_unit.lecturers[0] if course_unit.lecturers else None
            lecturer_label = f" — {lecturer.title} {lecturer.name}" if lecturer else ""
            print(f"    {course_unit.code}: {course_unit.name}{lecturer_label}")
        print(f"  Reviewer email: {reviewer.email}")
        print("  Reviewer password: set via SEED_REVIEWER_PASSWORD (change in production)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed QAAI data")
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Delete any pre-existing demo-flagged sessions",
    )
    args = parser.parse_args()
    run_seed(reset_demo=args.reset_demo)


if __name__ == "__main__":
    main()
