"""
Feedback queue management for human-in-the-loop Canvas publishing.

This module handles:
- Adding AI-generated feedback to the review queue
- Instructor review and approval workflow
- Publishing approved feedback to Canvas
"""

from datetime import datetime
from typing import Optional
from .models import (
    get_session, FeedbackQueue, FeedbackQueueStatus, FeedbackType,
    Student, Submission, Assignment, Evaluation
)
from .canvas_fetcher import (
    post_submission_comment, create_discussion_topic,
    post_discussion_entry, create_announcement
)


def queue_submission_feedback(
    submission_id: int,
    content: str,
    generated_by: str = "haiku",
    context: dict = None
) -> FeedbackQueue:
    """
    Add feedback for a student submission to the review queue.

    Args:
        submission_id: ID of the submission to comment on
        content: The feedback text
        generated_by: Source of the feedback (haiku, manual, system)
        context: Optional context about how this was generated
    """
    session = get_session()

    submission = session.query(Submission).get(submission_id)
    if not submission:
        session.close()
        raise ValueError(f"Submission {submission_id} not found")

    feedback = FeedbackQueue(
        feedback_type=FeedbackType.SUBMISSION_COMMENT.value,
        student_id=submission.student_id,
        submission_id=submission_id,
        content=content,
        original_content=content,
        generated_by=generated_by,
        generation_context=context,
        status=FeedbackQueueStatus.PENDING.value
    )

    session.add(feedback)
    session.commit()

    feedback_id = feedback.id
    session.close()

    print(f"Queued submission feedback #{feedback_id} for review")
    return feedback


def queue_class_insight(
    title: str,
    content: str,
    feedback_type: str = "discussion_post",
    generated_by: str = "haiku",
    context: dict = None
) -> FeedbackQueue:
    """
    Add a class-wide insight to the review queue.

    Args:
        title: Title for the discussion/announcement
        content: The insight content
        feedback_type: "discussion_post" or "announcement"
        generated_by: Source of the insight
        context: Optional generation context
    """
    session = get_session()

    ft = FeedbackType.DISCUSSION_POST.value
    if feedback_type == "announcement":
        ft = FeedbackType.ANNOUNCEMENT.value

    feedback = FeedbackQueue(
        feedback_type=ft,
        title=title,
        content=content,
        original_content=content,
        generated_by=generated_by,
        generation_context=context,
        status=FeedbackQueueStatus.PENDING.value
    )

    session.add(feedback)
    session.commit()

    feedback_id = feedback.id
    session.close()

    print(f"Queued class insight #{feedback_id} for review")
    return feedback


def get_pending_feedback(limit: int = 50) -> list[dict]:
    """
    Get all pending feedback items awaiting review.

    Returns a list of dicts with feedback details and related info.
    """
    session = get_session()

    pending = session.query(FeedbackQueue).filter(
        FeedbackQueue.status == FeedbackQueueStatus.PENDING.value
    ).order_by(FeedbackQueue.created_at.desc()).limit(limit).all()

    results = []
    for fb in pending:
        item = {
            "id": fb.id,
            "type": fb.feedback_type,
            "title": fb.title,
            "content": fb.content,
            "original_content": fb.original_content,
            "generated_by": fb.generated_by,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
            "student_name": None,
            "assignment_name": None
        }

        if fb.student_id:
            student = session.query(Student).get(fb.student_id)
            if student:
                item["student_name"] = student.name

        if fb.submission_id:
            submission = session.query(Submission).get(fb.submission_id)
            if submission and submission.assignment:
                item["assignment_name"] = submission.assignment.name

        results.append(item)

    session.close()
    return results


def get_feedback_by_id(feedback_id: int) -> Optional[dict]:
    """Get a single feedback item by ID."""
    session = get_session()

    fb = session.query(FeedbackQueue).get(feedback_id)
    if not fb:
        session.close()
        return None

    item = {
        "id": fb.id,
        "type": fb.feedback_type,
        "title": fb.title,
        "content": fb.content,
        "original_content": fb.original_content,
        "status": fb.status,
        "generated_by": fb.generated_by,
        "created_at": fb.created_at.isoformat() if fb.created_at else None,
        "student_id": fb.student_id,
        "submission_id": fb.submission_id,
        "student_name": None,
        "assignment_name": None,
        "student_canvas_id": None,
        "assignment_canvas_id": None
    }

    if fb.student_id:
        student = session.query(Student).get(fb.student_id)
        if student:
            item["student_name"] = student.name
            item["student_canvas_id"] = student.canvas_id

    if fb.submission_id:
        submission = session.query(Submission).get(fb.submission_id)
        if submission and submission.assignment:
            item["assignment_name"] = submission.assignment.name
            item["assignment_canvas_id"] = submission.assignment.canvas_id

    session.close()
    return item


def update_feedback_content(feedback_id: int, new_content: str, new_title: str = None) -> bool:
    """
    Update the content of a feedback item (instructor edit).

    Sets status to EDITED if content was changed.
    """
    session = get_session()

    fb = session.query(FeedbackQueue).get(feedback_id)
    if not fb:
        session.close()
        return False

    fb.content = new_content
    if new_title is not None:
        fb.title = new_title

    if fb.content != fb.original_content:
        fb.status = FeedbackQueueStatus.EDITED.value

    fb.updated_at = datetime.utcnow()
    session.commit()
    session.close()

    print(f"Updated feedback #{feedback_id}")
    return True


def approve_feedback(feedback_id: int) -> bool:
    """Mark feedback as approved (ready to publish)."""
    session = get_session()

    fb = session.query(FeedbackQueue).get(feedback_id)
    if not fb:
        session.close()
        return False

    fb.status = FeedbackQueueStatus.APPROVED.value
    fb.reviewed_at = datetime.utcnow()
    session.commit()
    session.close()

    print(f"Approved feedback #{feedback_id}")
    return True


def reject_feedback(feedback_id: int) -> bool:
    """Mark feedback as rejected."""
    session = get_session()

    fb = session.query(FeedbackQueue).get(feedback_id)
    if not fb:
        session.close()
        return False

    fb.status = FeedbackQueueStatus.REJECTED.value
    fb.reviewed_at = datetime.utcnow()
    session.commit()
    session.close()

    print(f"Rejected feedback #{feedback_id}")
    return True


def publish_feedback(feedback_id: int) -> dict:
    """
    Publish approved feedback to Canvas.

    Returns the Canvas API response or error details.
    """
    session = get_session()

    fb = session.query(FeedbackQueue).get(feedback_id)
    if not fb:
        session.close()
        return {"error": "Feedback not found"}

    if fb.status not in [FeedbackQueueStatus.APPROVED.value, FeedbackQueueStatus.EDITED.value]:
        session.close()
        return {"error": f"Feedback must be approved first (current status: {fb.status})"}

    result = {"error": "Unknown feedback type"}

    try:
        if fb.feedback_type == FeedbackType.SUBMISSION_COMMENT.value:
            # Get Canvas IDs
            submission = session.query(Submission).get(fb.submission_id)
            if not submission:
                session.close()
                return {"error": "Submission not found"}

            student = session.query(Student).get(fb.student_id)
            if not student or not student.canvas_id:
                session.close()
                return {"error": "Student Canvas ID not found"}

            if not submission.assignment or not submission.assignment.canvas_id:
                session.close()
                return {"error": "Assignment Canvas ID not found"}

            result = post_submission_comment(
                assignment_canvas_id=submission.assignment.canvas_id,
                student_canvas_id=student.canvas_id,
                comment_text=fb.content
            )

        elif fb.feedback_type == FeedbackType.DISCUSSION_POST.value:
            result = create_discussion_topic(
                title=fb.title or "Class Insight",
                message=fb.content
            )

        elif fb.feedback_type == FeedbackType.ANNOUNCEMENT.value:
            result = create_announcement(
                title=fb.title or "Course Announcement",
                message=fb.content
            )

        elif fb.feedback_type == FeedbackType.DISCUSSION_ENTRY.value:
            if not fb.discussion_topic_id:
                session.close()
                return {"error": "No discussion topic ID specified"}

            result = post_discussion_entry(
                topic_id=fb.discussion_topic_id,
                message=fb.content
            )

        # Mark as published
        if "error" not in result:
            fb.status = FeedbackQueueStatus.PUBLISHED.value
            fb.published_at = datetime.utcnow()
            fb.canvas_response_id = str(result.get("id", ""))
            session.commit()

    except Exception as e:
        result = {"error": str(e)}

    session.close()
    return result


def publish_all_approved() -> dict:
    """Publish all approved feedback items to Canvas."""
    session = get_session()

    approved = session.query(FeedbackQueue).filter(
        FeedbackQueue.status.in_([
            FeedbackQueueStatus.APPROVED.value,
            FeedbackQueueStatus.EDITED.value
        ])
    ).all()

    session.close()

    results = {
        "success": 0,
        "failed": 0,
        "errors": []
    }

    for fb in approved:
        result = publish_feedback(fb.id)
        if "error" in result:
            results["failed"] += 1
            results["errors"].append({
                "id": fb.id,
                "error": result["error"]
            })
        else:
            results["success"] += 1

    return results


def get_feedback_stats() -> dict:
    """Get statistics about the feedback queue."""
    session = get_session()

    stats = {
        "pending": session.query(FeedbackQueue).filter(
            FeedbackQueue.status == FeedbackQueueStatus.PENDING.value
        ).count(),
        "approved": session.query(FeedbackQueue).filter(
            FeedbackQueue.status == FeedbackQueueStatus.APPROVED.value
        ).count(),
        "edited": session.query(FeedbackQueue).filter(
            FeedbackQueue.status == FeedbackQueueStatus.EDITED.value
        ).count(),
        "published": session.query(FeedbackQueue).filter(
            FeedbackQueue.status == FeedbackQueueStatus.PUBLISHED.value
        ).count(),
        "rejected": session.query(FeedbackQueue).filter(
            FeedbackQueue.status == FeedbackQueueStatus.REJECTED.value
        ).count()
    }

    session.close()
    return stats


def generate_submission_feedback_for_queue(submission_id: int) -> Optional[FeedbackQueue]:
    """
    Generate AI feedback for a submission and add to queue.

    Uses existing evaluation if available, otherwise generates new feedback.
    """
    session = get_session()

    submission = session.query(Submission).get(submission_id)
    if not submission:
        session.close()
        return None

    # Check for existing evaluation
    final_eval = None
    for e in submission.evaluations:
        if e.is_final:
            final_eval = e
            break

    if not final_eval:
        session.close()
        print(f"No evaluation found for submission {submission_id}")
        return None

    # Build feedback content from evaluation
    content_parts = []

    if final_eval.feedback:
        content_parts.append(final_eval.feedback)

    if final_eval.strengths:
        strengths = final_eval.strengths if isinstance(final_eval.strengths, list) else [final_eval.strengths]
        if strengths:
            content_parts.append("\n**Strengths:**")
            for s in strengths[:3]:
                content_parts.append(f"- {s}")

    if final_eval.areas_for_improvement:
        areas = final_eval.areas_for_improvement if isinstance(final_eval.areas_for_improvement, list) else [final_eval.areas_for_improvement]
        if areas:
            content_parts.append("\n**Areas for growth:**")
            for a in areas[:3]:
                content_parts.append(f"- {a}")

    if final_eval.score is not None:
        content_parts.append(f"\n**Score:** {final_eval.score}/{submission.assignment.points_possible}")

    content = "\n".join(content_parts)

    session.close()

    # Queue the feedback
    return queue_submission_feedback(
        submission_id=submission_id,
        content=content,
        generated_by=final_eval.source or "haiku",
        context={
            "evaluation_id": final_eval.id,
            "generated_from": "existing_evaluation"
        }
    )
