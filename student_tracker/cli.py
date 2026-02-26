#!/usr/bin/env python3
"""
Command-line interface for the student tracking system.

Usage:
    python -m student_tracker.cli [command] [options]

Commands:
    init          Initialize the database
    sync          Sync data from Canvas
    evaluate      Run evaluations on pending submissions
    dashboard     Start the web dashboard
    export        Export data (grades, reports)
    import        Import data from files
    student       Student management commands
    analyze       Run analysis and generate insights
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from student_tracker.models import init_db, get_session, Student, Assignment, Submission
from student_tracker.canvas_fetcher import full_sync as canvas_sync
from student_tracker.evaluator import evaluate_submission, evaluate_all_pending
from student_tracker.manual_input import (
    add_student, list_students, import_students_csv,
    add_submission, import_submissions_csv,
    add_manual_evaluation, export_grades_csv, export_student_report
)
from student_tracker.analyzer import (
    get_student_summary, get_class_overview, identify_student_groups,
    generate_student_insights, generate_class_insights, create_progress_snapshot
)
from student_tracker.recommendations import (
    generate_student_recommendations, generate_class_recommendations
)


def cmd_init(args):
    """Initialize the database."""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")


def cmd_sync(args):
    """Sync data from Canvas."""
    print("Syncing from Canvas...")
    results = canvas_sync()
    print(f"\nSync complete:")
    print(f"  Students: {results['students']} new")
    print(f"  Assignments: {results['assignments']} new")
    print(f"  Submissions: {results['submissions']} new")


def cmd_evaluate(args):
    """Run evaluations on submissions."""
    if args.submission_id:
        print(f"Evaluating submission {args.submission_id}...")
        result = evaluate_submission(args.submission_id, force=args.force)
        if result:
            print(f"Evaluation complete: {result.score}")
        else:
            print("Evaluation failed.")
    else:
        print(f"Evaluating up to {args.limit} pending submissions...")
        results = evaluate_all_pending(
            assignment_id=args.assignment_id,
            limit=args.limit
        )
        print(f"Completed {len(results)} evaluations.")


def cmd_dashboard(args):
    """Start the web dashboard."""
    from student_tracker.dashboard import run_dashboard
    run_dashboard(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


def cmd_export(args):
    """Export data."""
    if args.type == "grades":
        filepath = args.output or "grades.csv"
        export_grades_csv(filepath)
        print(f"Grades exported to {filepath}")
    elif args.type == "student":
        if not args.student_id:
            print("Error: --student-id required for student export")
            return
        filepath = args.output or f"student_{args.student_id}_report.json"
        export_student_report(args.student_id, filepath)
        print(f"Student report exported to {filepath}")


def cmd_import(args):
    """Import data from files."""
    if args.type == "students":
        count = import_students_csv(args.file)
        print(f"Imported {count} students.")
    elif args.type == "submissions":
        count = import_submissions_csv(args.file)
        print(f"Imported {count} submissions.")


def cmd_student(args):
    """Student management commands."""
    if args.action == "list":
        students = list_students(args.search)
        print(f"\n{'ID':<6} {'Name':<30} {'Email':<30} {'Submissions':<12}")
        print("-" * 80)
        for s in students:
            print(f"{s['id']:<6} {s['name']:<30} {s['email'] or '-':<30} {s['submission_count']:<12}")
        print(f"\nTotal: {len(students)} students")

    elif args.action == "add":
        student = add_student(args.name, args.email)
        print(f"Added student: {student.name} (ID: {student.id})")

    elif args.action == "summary":
        if not args.student_id:
            print("Error: --student-id required")
            return
        summary = get_student_summary(args.student_id)
        if "error" in summary:
            print(f"Error: {summary['error']}")
            return

        print(f"\n=== {summary['student']['name']} ===")
        print(f"Overall: {summary['metrics']['overall_percentage']:.1f}%")
        print(f"Submissions: {summary['metrics']['submissions']}/{summary['metrics']['total_assignments']}")
        print(f"On-time rate: {summary['metrics']['on_time_rate']:.1f}%")

        if summary['current_skills']:
            print("\nSkill levels:")
            for skill, level in summary['current_skills'].items():
                print(f"  {skill}: {level}")

    elif args.action == "insights":
        if not args.student_id:
            print("Error: --student-id required")
            return
        print("Generating insights...")
        insights = generate_student_insights(args.student_id)
        if "error" in insights:
            print(f"Error: {insights['error']}")
            return

        print(f"\n=== Insights for {insights['student']['name']} ===")
        print(f"\n{insights.get('overall_assessment', 'No assessment available')}")

        if insights.get('recommendations'):
            print("\nRecommendations:")
            for i, rec in enumerate(insights['recommendations'], 1):
                print(f"  {i}. {rec}")

        if insights.get('concerns'):
            print("\nConcerns:")
            for concern in insights['concerns']:
                print(f"  - {concern}")

    elif args.action == "recommendations":
        if not args.student_id:
            print("Error: --student-id required")
            return
        print("Generating recommendations...")
        recs = generate_student_recommendations(args.student_id)
        if "error" in recs:
            print(f"Error: {recs['error']}")
            return

        print(f"\n=== Recommendations for {recs['student']['name']} ===")

        if recs.get('priority_skills'):
            print(f"\nPriority skills to develop: {', '.join(recs['priority_skills'])}")

        for skill, data in recs.get('skill_recommendations', {}).items():
            print(f"\n{skill.upper()} ({data['current_level']}):")
            for rec in data['recommendations'][:2]:
                print(f"  - {rec}")


def cmd_analyze(args):
    """Run analysis and generate insights."""
    if args.type == "overview":
        overview = get_class_overview()
        print("\n=== Class overview ===")
        print(f"Students: {overview['summary']['total_students']}")
        print(f"Class average: {overview['summary']['class_average']:.1f}%")
        print(f"Evaluated submissions: {overview['summary']['total_evaluated_submissions']}")

        print("\nGrade distribution:")
        for grade, count in overview['grade_distribution'].items():
            print(f"  {grade}: {count}")

    elif args.type == "groups":
        groups = identify_student_groups()
        print("\n=== Student groups ===")
        for group, students in groups.items():
            print(f"\n{group.upper()} ({len(students)}):")
            for s in students[:5]:
                print(f"  - {s['name']}: {s['average']:.1f}%")
            if len(students) > 5:
                print(f"  ... and {len(students) - 5} more")

    elif args.type == "insights":
        print("Generating class insights...")
        insights = generate_class_insights()
        if "error" in insights:
            print(f"Error: {insights['error']}")
            return

        print(f"\n=== Class insights ===")
        print(f"\n{insights.get('class_health', 'No assessment available')}")

        if insights.get('skills_needing_attention'):
            print(f"\nSkills needing attention: {', '.join(insights['skills_needing_attention'])}")

        if insights.get('suggested_interventions'):
            print("\nSuggested interventions:")
            for i, intervention in enumerate(insights['suggested_interventions'], 1):
                print(f"  {i}. {intervention}")

    elif args.type == "recommendations":
        print("Generating class recommendations...")
        recs = generate_class_recommendations()

        print("\n=== Class recommendations ===")
        class_recs = recs.get('class_recommendations', {})

        if class_recs.get('class_health_assessment'):
            print(f"\n{class_recs['class_health_assessment']}")

        if class_recs.get('immediate_priorities'):
            print("\nImmediate priorities:")
            for priority in class_recs['immediate_priorities']:
                print(f"  - {priority}")

        if class_recs.get('teaching_adjustments'):
            print("\nTeaching adjustments:")
            for adj in class_recs['teaching_adjustments']:
                print(f"  - {adj}")

    elif args.type == "snapshot":
        print("Creating progress snapshot...")
        snapshot = create_progress_snapshot()
        print(f"Snapshot created at {snapshot.snapshot_date}")


def main():
    parser = argparse.ArgumentParser(
        description="STCM140 Student Tracking System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize the database")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync data from Canvas")

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Run evaluations")
    eval_parser.add_argument("--submission-id", type=int, help="Specific submission to evaluate")
    eval_parser.add_argument("--assignment-id", type=int, help="Filter by assignment")
    eval_parser.add_argument("--limit", type=int, default=10, help="Max submissions to evaluate")
    eval_parser.add_argument("--force", action="store_true", help="Re-evaluate even if already evaluated")

    # Dashboard command
    dash_parser = subparsers.add_parser("dashboard", help="Start web dashboard")
    dash_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    dash_parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    dash_parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("type", choices=["grades", "student"], help="Export type")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.add_argument("--student-id", type=int, help="Student ID for student export")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data from files")
    import_parser.add_argument("type", choices=["students", "submissions"], help="Import type")
    import_parser.add_argument("file", help="File to import")

    # Student command
    student_parser = subparsers.add_parser("student", help="Student management")
    student_parser.add_argument("action",
        choices=["list", "add", "summary", "insights", "recommendations"],
        help="Action to perform")
    student_parser.add_argument("--name", help="Student name (for add)")
    student_parser.add_argument("--email", help="Student email (for add)")
    student_parser.add_argument("--student-id", type=int, help="Student ID")
    student_parser.add_argument("--search", help="Search term (for list)")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run analysis")
    analyze_parser.add_argument("type",
        choices=["overview", "groups", "insights", "recommendations", "snapshot"],
        help="Analysis type")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route to appropriate command
    commands = {
        "init": cmd_init,
        "sync": cmd_sync,
        "evaluate": cmd_evaluate,
        "dashboard": cmd_dashboard,
        "export": cmd_export,
        "import": cmd_import,
        "student": cmd_student,
        "analyze": cmd_analyze
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
