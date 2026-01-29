"""
Canvas LMS Integration for STCM140.

Syncs course content between this repo and Canvas at Montclair State University.

To get your Canvas API token:
1. Go to https://montclair.instructure.com/profile/settings
2. Scroll to "Approved Integrations"
3. Click "+ New Access Token"
4. Give it a name and expiration date
5. Copy the token (you won't see it again!)

Usage:
    python canvas_sync.py --list-courses
    python canvas_sync.py --list-assignments
    python canvas_sync.py --sync-schedule
    python canvas_sync.py --post-announcement "Title" "Message"
"""

import requests
import json
import os
import argparse
from datetime import datetime

# Configuration
CANVAS_BASE_URL = "https://montclair.instructure.com"
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "")

# Course ID for STCM140 - you'll need to find this
COURSE_ID = os.environ.get("CANVAS_COURSE_ID", "")


def get_headers():
    """Get authorization headers for Canvas API."""
    return {
        "Authorization": f"Bearer {CANVAS_API_TOKEN}",
        "Content-Type": "application/json",
    }


def api_get(endpoint, params=None):
    """Make a GET request to Canvas API."""
    url = f"{CANVAS_BASE_URL}/api/v1{endpoint}"
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()


def api_post(endpoint, data=None):
    """Make a POST request to Canvas API."""
    url = f"{CANVAS_BASE_URL}/api/v1{endpoint}"
    response = requests.post(url, headers=get_headers(), json=data)
    response.raise_for_status()
    return response.json()


def api_put(endpoint, data=None):
    """Make a PUT request to Canvas API."""
    url = f"{CANVAS_BASE_URL}/api/v1{endpoint}"
    response = requests.put(url, headers=get_headers(), json=data)
    response.raise_for_status()
    return response.json()


def list_courses():
    """List all courses you have access to."""
    print("Fetching your Canvas courses...\n")
    courses = api_get("/courses", params={"per_page": 100})

    print(f"{'ID':<10} {'Name':<50} {'Code':<20}")
    print("-" * 80)

    for course in courses:
        course_id = course.get("id", "")
        name = course.get("name", "Unknown")[:48]
        code = course.get("course_code", "")[:18]
        print(f"{course_id:<10} {name:<50} {code:<20}")

    print(f"\nTotal courses: {len(courses)}")
    print("\nTo use a course, set CANVAS_COURSE_ID environment variable or edit this script.")


def list_assignments():
    """List all assignments in the course."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    print(f"Fetching assignments for course {COURSE_ID}...\n")
    assignments = api_get(f"/courses/{COURSE_ID}/assignments", params={"per_page": 100})

    print(f"{'ID':<10} {'Name':<40} {'Due Date':<20} {'Points':<10}")
    print("-" * 80)

    for assignment in assignments:
        a_id = assignment.get("id", "")
        name = assignment.get("name", "Unknown")[:38]
        due = assignment.get("due_at", "No due date")
        if due and due != "No due date":
            due = due[:10]
        points = assignment.get("points_possible", "")
        print(f"{a_id:<10} {name:<40} {due:<20} {points:<10}")

    print(f"\nTotal assignments: {len(assignments)}")


def list_announcements():
    """List recent announcements in the course."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    print(f"Fetching announcements for course {COURSE_ID}...\n")
    announcements = api_get(
        "/announcements",
        params={
            "context_codes[]": f"course_{COURSE_ID}",
            "per_page": 20
        }
    )

    print(f"{'ID':<10} {'Title':<50} {'Posted':<20}")
    print("-" * 80)

    for ann in announcements:
        a_id = ann.get("id", "")
        title = ann.get("title", "Unknown")[:48]
        posted = ann.get("posted_at", "")[:10] if ann.get("posted_at") else "Draft"
        print(f"{a_id:<10} {title:<50} {posted:<20}")

    print(f"\nTotal announcements: {len(announcements)}")


def post_announcement(title, message):
    """Post a new announcement to the course."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    print(f"Posting announcement: {title}")

    data = {
        "title": title,
        "message": message,
        "is_announcement": True,
        "published": True,
    }

    result = api_post(f"/courses/{COURSE_ID}/discussion_topics", data)

    print(f"Announcement posted successfully!")
    print(f"ID: {result.get('id')}")
    print(f"URL: {result.get('html_url')}")


def create_assignment(name, description, due_at, points_possible):
    """Create a new assignment in the course."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    print(f"Creating assignment: {name}")

    data = {
        "assignment": {
            "name": name,
            "description": description,
            "due_at": due_at,  # ISO 8601 format: 2026-01-29T23:59:00Z
            "points_possible": points_possible,
            "submission_types": ["online_upload", "online_text_entry"],
            "published": False,  # Set to True to publish immediately
        }
    }

    result = api_post(f"/courses/{COURSE_ID}/assignments", data)

    print(f"Assignment created successfully!")
    print(f"ID: {result.get('id')}")
    print(f"URL: {result.get('html_url')}")
    return result


def update_assignment(assignment_id, **kwargs):
    """Update an existing assignment."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set.")
        return

    print(f"Updating assignment {assignment_id}...")

    data = {"assignment": kwargs}
    result = api_put(f"/courses/{COURSE_ID}/assignments/{assignment_id}", data)

    print(f"Assignment updated successfully!")
    return result


def sync_schedule_to_calendar():
    """Sync the course schedule to Canvas calendar events."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    # Course schedule from the syllabus
    schedule = [
        {"date": "2026-01-29", "title": "Due: Read the Cluetrain Manifesto", "points": 25},
        {"date": "2026-02-12", "title": "Due: Media markets & information needs", "points": 20},
        {"date": "2026-02-26", "title": "Due: Enshittification & file organization", "points": 25},
        {"date": "2026-03-05", "title": "Due: Slide deck that doesn't suck", "points": 50},
        {"date": "2026-03-05", "title": "Due: Alien planet travel poster", "points": 50},
        {"date": "2026-03-26", "title": "Due: Research dossier", "points": 50},
        {"date": "2026-04-02", "title": "Due: User/customer persona", "points": 75},
        {"date": "2026-04-09", "title": "Due: Critical copywriting", "points": 100},
        {"date": "2026-04-23", "title": "Due: Featured images + social graphics", "points": 75},
        {"date": "2026-04-30", "title": "Due: Campaign strategy", "points": 75},
        {"date": "2026-05-04", "title": "Due: Final project", "points": None},
    ]

    print("This would sync the following assignments to Canvas:")
    print("-" * 60)
    for item in schedule:
        print(f"{item['date']}: {item['title']} ({item['points']} pts)")

    print("\nTo actually create these assignments, use the --create-assignments flag.")


def get_course_info():
    """Get detailed information about the course."""
    if not COURSE_ID:
        print("Error: CANVAS_COURSE_ID not set. Run --list-courses first.")
        return

    print(f"Fetching course info for {COURSE_ID}...\n")
    course = api_get(f"/courses/{COURSE_ID}")

    print(f"Course Name: {course.get('name')}")
    print(f"Course Code: {course.get('course_code')}")
    print(f"Start Date: {course.get('start_at', 'Not set')}")
    print(f"End Date: {course.get('end_at', 'Not set')}")
    print(f"Time Zone: {course.get('time_zone', 'Not set')}")
    print(f"Enrollment Count: {course.get('total_students', 'Unknown')}")

    return course


def main():
    parser = argparse.ArgumentParser(description="Canvas LMS Integration for STCM140")
    parser.add_argument("--list-courses", action="store_true", help="List all your Canvas courses")
    parser.add_argument("--list-assignments", action="store_true", help="List assignments in the course")
    parser.add_argument("--list-announcements", action="store_true", help="List announcements in the course")
    parser.add_argument("--course-info", action="store_true", help="Get course information")
    parser.add_argument("--sync-schedule", action="store_true", help="Preview schedule sync")
    parser.add_argument("--post-announcement", nargs=2, metavar=("TITLE", "MESSAGE"),
                        help="Post a new announcement")

    args = parser.parse_args()

    if not CANVAS_API_TOKEN:
        print("Error: CANVAS_API_TOKEN environment variable not set.")
        print("\nTo get your token:")
        print("1. Go to https://montclair.instructure.com/profile/settings")
        print("2. Scroll to 'Approved Integrations'")
        print("3. Click '+ New Access Token'")
        print("4. Set: CANVAS_API_TOKEN=your_token_here")
        return

    if args.list_courses:
        list_courses()
    elif args.list_assignments:
        list_assignments()
    elif args.list_announcements:
        list_announcements()
    elif args.course_info:
        get_course_info()
    elif args.sync_schedule:
        sync_schedule_to_calendar()
    elif args.post_announcement:
        title, message = args.post_announcement
        post_announcement(title, message)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
