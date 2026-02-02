"""
Manual input interfaces for the student tracking system.

Supports:
- CLI-based data entry
- CSV import for bulk data
- JSON import for structured data
- Manual evaluation override
- Student note entry
"""

import os
import csv
import json
from datetime import datetime
from typing import Optional
from .models import (
    get_session, init_db, Student, Assignment, Submission,
    Evaluation, StudentNote, SubmissionStatus, EvaluationSource
)


# ============================================================================
# Student management
# ============================================================================

def add_student(
    name: str,
    email: Optional[str] = None,
    canvas_id: Optional[str] = None
) -> Student:
    """Add a student manually."""
    session = get_session()

    # Check if student already exists
    if canvas_id:
        existing = session.query(Student).filter_by(canvas_id=canvas_id).first()
        if existing:
            print(f"Student with Canvas ID {canvas_id} already exists: {existing.name}")
            session.close()
            return existing

    student = Student(
        name=name,
        email=email,
        canvas_id=canvas_id
    )
    session.add(student)
    session.commit()

    print(f"Added student: {name} (ID: {student.id})")
    result = student
    session.close()
    return result


def list_students(search: Optional[str] = None) -> list[dict]:
    """List all students, optionally filtered by search term."""
    session = get_session()

    query = session.query(Student)
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    students = query.order_by(Student.name).all()

    result = [{
        "id": s.id,
        "name": s.name,
        "email": s.email,
        "canvas_id": s.canvas_id,
        "submission_count": len(s.submissions)
    } for s in students]

    session.close()
    return result


def import_students_csv(filepath: str) -> int:
    """
    Import students from CSV file.

    Expected columns: name, email (optional), canvas_id (optional)
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    session = get_session()
    imported = 0

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue

            email = row.get("email", "").strip() or None
            canvas_id = row.get("canvas_id", "").strip() or None

            # Check for duplicates
            if canvas_id:
                existing = session.query(Student).filter_by(canvas_id=canvas_id).first()
                if existing:
                    continue

            student = Student(name=name, email=email, canvas_id=canvas_id)
            session.add(student)
            imported += 1

    session.commit()
    session.close()

    print(f"Imported {imported} students from {filepath}")
    return imported


# ============================================================================
# Assignment management
# ============================================================================

def add_assignment(
    name: str,
    points_possible: float,
    due_date: Optional[datetime] = None,
    assignment_type: Optional[str] = None,
    description: Optional[str] = None,
    rubric: Optional[dict] = None,
    skills_assessed: Optional[list[str]] = None
) -> Assignment:
    """Add an assignment manually."""
    session = get_session()

    assignment = Assignment(
        name=name,
        points_possible=points_possible,
        due_date=due_date,
        assignment_type=assignment_type,
        description=description,
        rubric=rubric,
        skills_assessed=skills_assessed
    )
    session.add(assignment)
    session.commit()

    print(f"Added assignment: {name} (ID: {assignment.id}, {points_possible} pts)")
    result = assignment
    session.close()
    return result


def list_assignments() -> list[dict]:
    """List all assignments."""
    session = get_session()

    assignments = session.query(Assignment).order_by(Assignment.due_date).all()

    result = [{
        "id": a.id,
        "name": a.name,
        "points_possible": a.points_possible,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "assignment_type": a.assignment_type,
        "submission_count": len(a.submissions),
        "canvas_id": a.canvas_id
    } for a in assignments]

    session.close()
    return result


def import_assignments_json(filepath: str) -> int:
    """
    Import assignments from JSON file.

    Expected format:
    [
        {
            "name": "Assignment Name",
            "points_possible": 100,
            "due_date": "2026-01-29T23:59:00",
            "assignment_type": "written",
            "description": "...",
            "skills_assessed": ["writing", "research"]
        }
    ]
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = get_session()
    imported = 0

    for item in data:
        name = item.get("name", "").strip()
        if not name:
            continue

        due_date = None
        if item.get("due_date"):
            try:
                due_date = datetime.fromisoformat(item["due_date"])
            except (ValueError, TypeError):
                pass

        assignment = Assignment(
            name=name,
            points_possible=item.get("points_possible", 0),
            due_date=due_date,
            assignment_type=item.get("assignment_type"),
            description=item.get("description"),
            rubric=item.get("rubric"),
            skills_assessed=item.get("skills_assessed")
        )
        session.add(assignment)
        imported += 1

    session.commit()
    session.close()

    print(f"Imported {imported} assignments from {filepath}")
    return imported


# ============================================================================
# Submission management
# ============================================================================

def add_submission(
    student_id: int,
    assignment_id: int,
    content: str,
    submitted_at: Optional[datetime] = None,
    status: str = "submitted",
    file_path: Optional[str] = None
) -> Optional[Submission]:
    """Add a submission manually."""
    session = get_session()

    # Verify student and assignment exist
    student = session.query(Student).get(student_id)
    assignment = session.query(Assignment).get(assignment_id)

    if not student:
        print(f"Student {student_id} not found")
        session.close()
        return None

    if not assignment:
        print(f"Assignment {assignment_id} not found")
        session.close()
        return None

    # Check for existing submission
    existing = session.query(Submission).filter_by(
        student_id=student_id,
        assignment_id=assignment_id
    ).first()

    if existing:
        # Update existing submission
        existing.content = content
        existing.submitted_at = submitted_at or datetime.utcnow()
        existing.status = status
        existing.file_path = file_path
        existing.input_source = "manual"
        session.commit()
        print(f"Updated submission for {student.name} on {assignment.name}")
        result = existing
    else:
        # Create new submission
        submission = Submission(
            student_id=student_id,
            assignment_id=assignment_id,
            content=content,
            submitted_at=submitted_at or datetime.utcnow(),
            status=status,
            file_path=file_path,
            input_source="manual"
        )
        session.add(submission)
        session.commit()
        print(f"Added submission for {student.name} on {assignment.name}")
        result = submission

    session.close()
    return result


def add_submission_by_name(
    student_name: str,
    assignment_name: str,
    content: str,
    submitted_at: Optional[datetime] = None
) -> Optional[Submission]:
    """Add a submission using student and assignment names (fuzzy match)."""
    session = get_session()

    # Find student (partial match)
    student = session.query(Student).filter(
        Student.name.ilike(f"%{student_name}%")
    ).first()

    if not student:
        print(f"Student not found: {student_name}")
        session.close()
        return None

    # Find assignment (partial match)
    assignment = session.query(Assignment).filter(
        Assignment.name.ilike(f"%{assignment_name}%")
    ).first()

    if not assignment:
        print(f"Assignment not found: {assignment_name}")
        session.close()
        return None

    session.close()
    return add_submission(student.id, assignment.id, content, submitted_at)


def import_submissions_csv(filepath: str) -> int:
    """
    Import submissions from CSV file.

    Expected columns: student_name (or student_id), assignment_name (or assignment_id), content
    Optional columns: submitted_at, status
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    session = get_session()
    imported = 0
    errors = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            # Find student
            student = None
            if row.get("student_id"):
                student = session.query(Student).get(int(row["student_id"]))
            elif row.get("student_name"):
                student = session.query(Student).filter(
                    Student.name.ilike(f"%{row['student_name']}%")
                ).first()

            if not student:
                errors.append(f"Row {row_num}: Student not found")
                continue

            # Find assignment
            assignment = None
            if row.get("assignment_id"):
                assignment = session.query(Assignment).get(int(row["assignment_id"]))
            elif row.get("assignment_name"):
                assignment = session.query(Assignment).filter(
                    Assignment.name.ilike(f"%{row['assignment_name']}%")
                ).first()

            if not assignment:
                errors.append(f"Row {row_num}: Assignment not found")
                continue

            content = row.get("content", "").strip()
            if not content:
                errors.append(f"Row {row_num}: No content")
                continue

            # Parse submitted_at
            submitted_at = None
            if row.get("submitted_at"):
                try:
                    submitted_at = datetime.fromisoformat(row["submitted_at"])
                except (ValueError, TypeError):
                    pass

            status = row.get("status", "submitted")

            # Create or update submission
            existing = session.query(Submission).filter_by(
                student_id=student.id,
                assignment_id=assignment.id
            ).first()

            if existing:
                existing.content = content
                existing.submitted_at = submitted_at or datetime.utcnow()
                existing.status = status
                existing.input_source = "csv_import"
            else:
                submission = Submission(
                    student_id=student.id,
                    assignment_id=assignment.id,
                    content=content,
                    submitted_at=submitted_at or datetime.utcnow(),
                    status=status,
                    input_source="csv_import"
                )
                session.add(submission)

            imported += 1

    session.commit()
    session.close()

    print(f"Imported {imported} submissions from {filepath}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    return imported


def bulk_import_text_files(
    folder: str,
    assignment_id: int,
    filename_pattern: str = "{student_name}"
) -> int:
    """
    Import submissions from text files in a folder.

    Files should be named according to the pattern, e.g., "John Smith.txt"
    """
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        return 0

    session = get_session()
    assignment = session.query(Assignment).get(assignment_id)

    if not assignment:
        print(f"Assignment {assignment_id} not found")
        session.close()
        return 0

    imported = 0

    for filename in os.listdir(folder):
        if not filename.endswith((".txt", ".md")):
            continue

        # Extract student name from filename
        student_name = os.path.splitext(filename)[0]

        # Find student
        student = session.query(Student).filter(
            Student.name.ilike(f"%{student_name}%")
        ).first()

        if not student:
            print(f"Student not found for file: {filename}")
            continue

        # Read content
        filepath = os.path.join(folder, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Create or update submission
        existing = session.query(Submission).filter_by(
            student_id=student.id,
            assignment_id=assignment_id
        ).first()

        if existing:
            existing.content = content
            existing.file_path = filepath
            existing.input_source = "file_import"
        else:
            submission = Submission(
                student_id=student.id,
                assignment_id=assignment_id,
                content=content,
                submitted_at=datetime.utcnow(),
                status="submitted",
                file_path=filepath,
                input_source="file_import"
            )
            session.add(submission)

        imported += 1

    session.commit()
    session.close()

    print(f"Imported {imported} submissions from {folder}")
    return imported


# ============================================================================
# Evaluation override
# ============================================================================

def add_manual_evaluation(
    submission_id: int,
    score: float,
    feedback: str,
    strengths: Optional[list[str]] = None,
    areas_for_improvement: Optional[list[str]] = None,
    skill_ratings: Optional[dict] = None,
    override_haiku: bool = True
) -> Optional[Evaluation]:
    """
    Add a manual evaluation or override an existing Haiku evaluation.

    Args:
        submission_id: ID of the submission to evaluate
        score: Numeric score
        feedback: Overall feedback text
        strengths: List of identified strengths
        areas_for_improvement: List of areas to improve
        skill_ratings: Dict of skill -> level mappings
        override_haiku: If True, mark previous evaluations as non-final
    """
    session = get_session()

    submission = session.query(Submission).get(submission_id)
    if not submission:
        print(f"Submission {submission_id} not found")
        session.close()
        return None

    # If overriding, mark previous evaluations as non-final
    if override_haiku:
        previous = session.query(Evaluation).filter_by(
            submission_id=submission_id,
            is_final=True
        ).all()
        for prev in previous:
            prev.is_final = False

    evaluation = Evaluation(
        submission_id=submission_id,
        source=EvaluationSource.MANUAL.value,
        score=score,
        feedback=feedback,
        strengths=strengths or [],
        areas_for_improvement=areas_for_improvement or [],
        skill_ratings=skill_ratings or {},
        is_final=True
    )

    session.add(evaluation)
    session.commit()

    student = submission.student
    assignment = submission.assignment
    print(f"Added manual evaluation for {student.name} on {assignment.name}: {score}/{assignment.points_possible}")

    session.close()
    return evaluation


def confirm_haiku_evaluation(
    evaluation_id: int,
    adjustments: Optional[dict] = None
) -> Optional[Evaluation]:
    """
    Confirm a Haiku evaluation with optional adjustments.

    Creates a new 'haiku_assisted' evaluation with any adjustments.
    """
    session = get_session()

    haiku_eval = session.query(Evaluation).get(evaluation_id)
    if not haiku_eval:
        print(f"Evaluation {evaluation_id} not found")
        session.close()
        return None

    # Mark original as non-final
    haiku_eval.is_final = False

    # Create confirmed version
    adjustments = adjustments or {}

    confirmed = Evaluation(
        submission_id=haiku_eval.submission_id,
        source=EvaluationSource.HAIKU_ASSISTED.value,
        score=adjustments.get("score", haiku_eval.score),
        score_breakdown=adjustments.get("score_breakdown", haiku_eval.score_breakdown),
        feedback=adjustments.get("feedback", haiku_eval.feedback),
        strengths=adjustments.get("strengths", haiku_eval.strengths),
        areas_for_improvement=adjustments.get("areas_for_improvement", haiku_eval.areas_for_improvement),
        skill_ratings=adjustments.get("skill_ratings", haiku_eval.skill_ratings),
        overridden_by=haiku_eval.id,
        is_final=True
    )

    session.add(confirmed)
    session.commit()

    print(f"Confirmed evaluation {evaluation_id} with adjustments")
    session.close()
    return confirmed


# ============================================================================
# Student notes
# ============================================================================

def add_student_note(
    student_id: int,
    content: str,
    note_type: str = "general",
    assignment_id: Optional[int] = None
) -> Optional[StudentNote]:
    """Add a note about a student."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        print(f"Student {student_id} not found")
        session.close()
        return None

    note = StudentNote(
        student_id=student_id,
        content=content,
        note_type=note_type,
        assignment_id=assignment_id
    )

    session.add(note)
    session.commit()

    print(f"Added {note_type} note for {student.name}")
    session.close()
    return note


def get_student_notes(student_id: int) -> list[dict]:
    """Get all notes for a student."""
    session = get_session()

    notes = session.query(StudentNote).filter_by(
        student_id=student_id
    ).order_by(StudentNote.created_at.desc()).all()

    result = [{
        "id": n.id,
        "type": n.note_type,
        "content": n.content,
        "assignment_id": n.assignment_id,
        "created_at": n.created_at.isoformat()
    } for n in notes]

    session.close()
    return result


# ============================================================================
# Export functions
# ============================================================================

def export_grades_csv(filepath: str) -> int:
    """Export all final grades to CSV."""
    session = get_session()

    students = session.query(Student).order_by(Student.name).all()
    assignments = session.query(Assignment).order_by(Assignment.due_date).all()

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header row
        header = ["Student Name", "Email"] + [a.name for a in assignments] + ["Total", "Percentage"]
        writer.writerow(header)

        total_possible = sum(a.points_possible for a in assignments)

        for student in students:
            row = [student.name, student.email or ""]
            total_earned = 0

            for assignment in assignments:
                # Find submission and final evaluation
                submission = session.query(Submission).filter_by(
                    student_id=student.id,
                    assignment_id=assignment.id
                ).first()

                if submission:
                    evaluation = session.query(Evaluation).filter_by(
                        submission_id=submission.id,
                        is_final=True
                    ).first()

                    if evaluation and evaluation.score is not None:
                        row.append(evaluation.score)
                        total_earned += evaluation.score
                    else:
                        row.append("")
                else:
                    row.append("Missing")

            percentage = (total_earned / total_possible * 100) if total_possible > 0 else 0
            row.extend([total_earned, f"{percentage:.1f}%"])
            writer.writerow(row)

    session.close()
    print(f"Exported grades to {filepath}")
    return len(students)


def export_student_report(student_id: int, filepath: str) -> bool:
    """Export a detailed report for a single student."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        print(f"Student {student_id} not found")
        session.close()
        return False

    report = {
        "student": {
            "id": student.id,
            "name": student.name,
            "email": student.email
        },
        "submissions": [],
        "skill_assessments": [],
        "notes": [],
        "generated_at": datetime.utcnow().isoformat()
    }

    # Submissions and evaluations
    for submission in student.submissions:
        sub_data = {
            "assignment": submission.assignment.name,
            "assignment_type": submission.assignment.assignment_type,
            "points_possible": submission.assignment.points_possible,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "status": submission.status,
            "evaluations": []
        }

        for evaluation in submission.evaluations:
            sub_data["evaluations"].append({
                "source": evaluation.source,
                "score": evaluation.score,
                "feedback": evaluation.feedback,
                "strengths": evaluation.strengths,
                "areas_for_improvement": evaluation.areas_for_improvement,
                "skill_ratings": evaluation.skill_ratings,
                "is_final": evaluation.is_final
            })

        report["submissions"].append(sub_data)

    # Skill assessments
    for assessment in student.skill_assessments:
        report["skill_assessments"].append({
            "skill": assessment.skill_name,
            "level": assessment.skill_level,
            "confidence": assessment.confidence,
            "assessed_at": assessment.assessed_at.isoformat()
        })

    # Notes
    for note in student.notes:
        report["notes"].append({
            "type": note.note_type,
            "content": note.content,
            "created_at": note.created_at.isoformat()
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, indent=2, fp=f)

    session.close()
    print(f"Exported report for {student.name} to {filepath}")
    return True


if __name__ == "__main__":
    # Initialize database if needed
    init_db()

    # Example usage
    print("\n=== Student Tracker Manual Input ===")
    print("\nExample commands:")
    print("  add_student('John Doe', 'jdoe@montclair.edu')")
    print("  import_students_csv('students.csv')")
    print("  add_submission_by_name('John', 'Cluetrain', 'My analysis...')")
    print("  import_submissions_csv('submissions.csv')")
    print("  add_manual_evaluation(1, 22, 'Good work overall')")
    print("  export_grades_csv('grades.csv')")
