"""
Canvas API integration for fetching student submissions.

Extends the existing canvas_sync.py functionality to pull:
- Student roster
- Assignment submissions
- Submission content (text entries, file URLs)
- Grades (if available)
"""

import os
import requests
from datetime import datetime
from typing import Optional
from .models import (
    get_session, Student, Assignment, Submission,
    SubmissionStatus
)

# Configuration
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://montclair.instructure.com")
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "")
CANVAS_COURSE_ID = os.environ.get("CANVAS_COURSE_ID", "")


def get_headers():
    """Get authorization headers for Canvas API."""
    return {
        "Authorization": f"Bearer {CANVAS_API_TOKEN}",
        "Content-Type": "application/json",
    }


def api_get(endpoint: str, params: dict = None) -> dict:
    """Make a GET request to Canvas API with pagination support."""
    url = f"{CANVAS_BASE_URL}/api/v1{endpoint}"
    all_results = []

    while url:
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list):
            all_results.extend(data)
        else:
            return data

        # Handle pagination
        url = None
        if "next" in response.links:
            url = response.links["next"]["url"]
        params = None  # Only use params on first request

    return all_results


def check_configuration() -> bool:
    """Check if Canvas API is properly configured."""
    if not CANVAS_API_TOKEN:
        print("Error: CANVAS_API_TOKEN not set")
        print("Set this environment variable with your Canvas API token")
        return False
    if not CANVAS_COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set")
        print("Set this environment variable with your course ID")
        return False
    return True


def fetch_students() -> list[dict]:
    """Fetch all students enrolled in the course."""
    if not check_configuration():
        return []

    print("Fetching student roster from Canvas...")
    students = api_get(
        f"/courses/{CANVAS_COURSE_ID}/users",
        params={"enrollment_type[]": "student", "per_page": 100}
    )

    print(f"Found {len(students)} students")
    return students


def fetch_assignments() -> list[dict]:
    """Fetch all assignments in the course."""
    if not check_configuration():
        return []

    print("Fetching assignments from Canvas...")
    assignments = api_get(
        f"/courses/{CANVAS_COURSE_ID}/assignments",
        params={"per_page": 100}
    )

    print(f"Found {len(assignments)} assignments")
    return assignments


def fetch_submissions(assignment_id: str) -> list[dict]:
    """Fetch all submissions for a specific assignment."""
    if not check_configuration():
        return []

    submissions = api_get(
        f"/courses/{CANVAS_COURSE_ID}/assignments/{assignment_id}/submissions",
        params={
            "per_page": 100,
            "include[]": ["submission_comments", "user"]
        }
    )

    return submissions


def fetch_all_submissions() -> list[dict]:
    """Fetch all submissions for all assignments."""
    if not check_configuration():
        return []

    print("Fetching all submissions from Canvas...")
    submissions = api_get(
        f"/courses/{CANVAS_COURSE_ID}/students/submissions",
        params={
            "student_ids[]": "all",
            "per_page": 100,
            "include[]": ["assignment", "user"]
        }
    )

    print(f"Found {len(submissions)} total submissions")
    return submissions


def sync_students_to_db() -> int:
    """Sync Canvas students to local database."""
    if not check_configuration():
        return 0

    session = get_session()
    students_data = fetch_students()
    synced_count = 0

    for s in students_data:
        canvas_id = str(s.get("id"))
        name = s.get("name", s.get("sortable_name", "Unknown"))
        email = s.get("email")

        # Check if student exists
        student = session.query(Student).filter_by(canvas_id=canvas_id).first()

        if student:
            # Update existing
            student.name = name
            student.email = email
        else:
            # Create new
            student = Student(
                canvas_id=canvas_id,
                name=name,
                email=email
            )
            session.add(student)
            synced_count += 1

    session.commit()
    session.close()

    print(f"Synced {synced_count} new students ({len(students_data)} total)")
    return synced_count


def sync_assignments_to_db() -> int:
    """Sync Canvas assignments to local database."""
    if not check_configuration():
        return 0

    session = get_session()
    assignments_data = fetch_assignments()
    synced_count = 0

    # Map assignment types based on name patterns
    def detect_assignment_type(name: str) -> str:
        name_lower = name.lower()
        if any(x in name_lower for x in ["write", "copy", "analysis", "essay", "reflection"]):
            return "written"
        if any(x in name_lower for x in ["poster", "slide", "image", "graphic", "visual"]):
            return "visual"
        if any(x in name_lower for x in ["research", "dossier"]):
            return "research"
        if any(x in name_lower for x in ["strategy", "campaign", "persona"]):
            return "strategy"
        if "final" in name_lower:
            return "comprehensive"
        return "general"

    for a in assignments_data:
        canvas_id = str(a.get("id"))
        name = a.get("name", "Untitled")

        # Parse due date
        due_at = a.get("due_at")
        due_date = None
        if due_at:
            try:
                due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Check if assignment exists
        assignment = session.query(Assignment).filter_by(canvas_id=canvas_id).first()

        if assignment:
            # Update existing
            assignment.name = name
            assignment.description = a.get("description", "")
            assignment.points_possible = a.get("points_possible", 0)
            assignment.due_date = due_date
            assignment.assignment_type = detect_assignment_type(name)
        else:
            # Create new
            assignment = Assignment(
                canvas_id=canvas_id,
                name=name,
                description=a.get("description", ""),
                points_possible=a.get("points_possible", 0),
                due_date=due_date,
                assignment_type=detect_assignment_type(name)
            )
            session.add(assignment)
            synced_count += 1

    session.commit()
    session.close()

    print(f"Synced {synced_count} new assignments ({len(assignments_data)} total)")
    return synced_count


def sync_submissions_to_db(assignment_id: Optional[int] = None) -> int:
    """Sync Canvas submissions to local database."""
    if not check_configuration():
        return 0

    session = get_session()
    synced_count = 0

    if assignment_id:
        # Fetch for specific assignment
        assignment = session.query(Assignment).get(assignment_id)
        if not assignment or not assignment.canvas_id:
            print(f"Assignment {assignment_id} not found or missing Canvas ID")
            session.close()
            return 0
        submissions_data = fetch_submissions(assignment.canvas_id)
    else:
        # Fetch all submissions
        submissions_data = fetch_all_submissions()

    for s in submissions_data:
        canvas_submission_id = str(s.get("id"))
        canvas_user_id = str(s.get("user_id"))
        canvas_assignment_id = str(s.get("assignment_id"))

        # Find local student and assignment
        student = session.query(Student).filter_by(canvas_id=canvas_user_id).first()
        assignment = session.query(Assignment).filter_by(canvas_id=canvas_assignment_id).first()

        if not student or not assignment:
            continue  # Skip if student/assignment not synced yet

        # Determine submission status
        workflow_state = s.get("workflow_state", "")
        submitted_at = s.get("submitted_at")
        late = s.get("late", False)

        if workflow_state == "unsubmitted":
            status = SubmissionStatus.PENDING.value
        elif late:
            status = SubmissionStatus.LATE.value
        elif submitted_at:
            status = SubmissionStatus.SUBMITTED.value
        else:
            status = SubmissionStatus.MISSING.value

        # Parse submitted_at
        submission_time = None
        if submitted_at:
            try:
                submission_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Get submission content
        content = None
        submission_type = s.get("submission_type")
        if submission_type == "online_text_entry":
            content = s.get("body", "")
        elif submission_type == "online_url":
            content = s.get("url", "")
        elif submission_type == "online_upload":
            attachments = s.get("attachments", [])
            if attachments:
                # Store URLs to attachments
                content = "\n".join([att.get("url", "") for att in attachments])

        # Check if submission exists
        submission = session.query(Submission).filter_by(
            student_id=student.id,
            assignment_id=assignment.id
        ).first()

        if submission:
            # Update existing
            submission.canvas_submission_id = canvas_submission_id
            submission.content = content
            submission.submitted_at = submission_time
            submission.status = status
        else:
            # Create new
            submission = Submission(
                student_id=student.id,
                assignment_id=assignment.id,
                canvas_submission_id=canvas_submission_id,
                content=content,
                submitted_at=submission_time,
                status=status,
                input_source="canvas"
            )
            session.add(submission)
            synced_count += 1

    session.commit()
    session.close()

    print(f"Synced {synced_count} new submissions ({len(submissions_data)} total)")
    return synced_count


def full_sync() -> dict:
    """Perform a full sync of students, assignments, and submissions."""
    print("=" * 50)
    print("Starting full Canvas sync...")
    print("=" * 50)

    results = {
        "students": sync_students_to_db(),
        "assignments": sync_assignments_to_db(),
        "submissions": sync_submissions_to_db()
    }

    print("=" * 50)
    print("Sync complete!")
    print(f"  New students: {results['students']}")
    print(f"  New assignments: {results['assignments']}")
    print(f"  New submissions: {results['submissions']}")
    print("=" * 50)

    return results


if __name__ == "__main__":
    full_sync()
