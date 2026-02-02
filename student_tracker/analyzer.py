"""
Analysis and progression tracking module.

Provides:
- Individual student analysis
- Class-wide metrics
- Skill progression tracking
- Student clustering by performance
- Trend detection
"""

import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional
import anthropic
from .models import (
    get_session, Student, Assignment, Submission, Evaluation,
    SkillAssessment, ProgressSnapshot, SkillLevel
)

# Anthropic configuration for generating insights
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HAIKU_MODEL = "claude-3-5-haiku-20241022"

# Skill level ordering for comparisons
SKILL_LEVEL_ORDER = {
    "emerging": 1,
    "developing": 2,
    "proficient": 3,
    "advanced": 4
}


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ============================================================================
# Individual student analysis
# ============================================================================

def get_student_summary(student_id: int) -> dict:
    """Get a summary of a student's performance and progress."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        session.close()
        return {"error": f"Student {student_id} not found"}

    submissions = session.query(Submission).filter_by(student_id=student_id).all()
    assignments = session.query(Assignment).all()

    # Calculate metrics
    total_possible = sum(a.points_possible for a in assignments)
    total_earned = 0
    submission_count = 0
    on_time_count = 0
    evaluated_count = 0

    scores_by_type = defaultdict(list)
    skills = defaultdict(list)

    for submission in submissions:
        if submission.status in ["submitted", "late"]:
            submission_count += 1
            if submission.status == "submitted":
                on_time_count += 1

        # Get final evaluation
        final_eval = None
        for eval in submission.evaluations:
            if eval.is_final:
                final_eval = eval
                break

        if final_eval and final_eval.score is not None:
            evaluated_count += 1
            total_earned += final_eval.score

            # Track by assignment type
            assignment_type = submission.assignment.assignment_type or "general"
            percentage = (final_eval.score / submission.assignment.points_possible * 100
                         if submission.assignment.points_possible > 0 else 0)
            scores_by_type[assignment_type].append(percentage)

            # Collect skill ratings
            if final_eval.skill_ratings:
                for skill, level in final_eval.skill_ratings.items():
                    skills[skill].append(level)

    # Calculate averages
    average_by_type = {}
    for atype, scores in scores_by_type.items():
        average_by_type[atype] = sum(scores) / len(scores) if scores else 0

    # Determine current skill levels (most recent assessment for each skill)
    current_skills = {}
    for skill, levels in skills.items():
        # Use the most common level weighted toward recent submissions
        level_counts = defaultdict(int)
        for i, level in enumerate(levels):
            # More weight to recent submissions
            weight = 1 + (i / len(levels))
            level_counts[level] += weight

        if level_counts:
            current_skills[skill] = max(level_counts, key=level_counts.get)

    session.close()

    overall_percentage = (total_earned / total_possible * 100) if total_possible > 0 else 0

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "email": student.email
        },
        "metrics": {
            "total_assignments": len(assignments),
            "submissions": submission_count,
            "evaluated": evaluated_count,
            "on_time_rate": (on_time_count / submission_count * 100) if submission_count > 0 else 0,
            "total_earned": total_earned,
            "total_possible": total_possible,
            "overall_percentage": overall_percentage
        },
        "performance_by_type": average_by_type,
        "current_skills": current_skills
    }


def get_student_progression(student_id: int) -> dict:
    """Track a student's skill progression over time."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        session.close()
        return {"error": f"Student {student_id} not found"}

    # Get submissions ordered by date
    submissions = session.query(Submission).filter_by(
        student_id=student_id
    ).order_by(Submission.submitted_at).all()

    progression = {
        "student": {"id": student.id, "name": student.name},
        "timeline": [],
        "skill_trends": defaultdict(list)
    }

    for submission in submissions:
        if not submission.submitted_at:
            continue

        final_eval = None
        for eval in submission.evaluations:
            if eval.is_final:
                final_eval = eval
                break

        if not final_eval:
            continue

        entry = {
            "date": submission.submitted_at.isoformat(),
            "assignment": submission.assignment.name,
            "assignment_type": submission.assignment.assignment_type,
            "score": final_eval.score,
            "max_score": submission.assignment.points_possible,
            "percentage": (final_eval.score / submission.assignment.points_possible * 100
                         if submission.assignment.points_possible > 0 else 0),
            "skill_ratings": final_eval.skill_ratings or {}
        }
        progression["timeline"].append(entry)

        # Track skill trends
        if final_eval.skill_ratings:
            for skill, level in final_eval.skill_ratings.items():
                progression["skill_trends"][skill].append({
                    "date": submission.submitted_at.isoformat(),
                    "level": level,
                    "level_value": SKILL_LEVEL_ORDER.get(level, 0)
                })

    session.close()
    return progression


def get_student_strengths_weaknesses(student_id: int) -> dict:
    """Analyze a student's strengths and areas needing improvement."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        session.close()
        return {"error": f"Student {student_id} not found"}

    all_strengths = []
    all_improvements = []
    skill_levels = defaultdict(list)

    submissions = session.query(Submission).filter_by(student_id=student_id).all()

    for submission in submissions:
        for eval in submission.evaluations:
            if eval.is_final:
                if eval.strengths:
                    all_strengths.extend(eval.strengths)
                if eval.areas_for_improvement:
                    all_improvements.extend(eval.areas_for_improvement)
                if eval.skill_ratings:
                    for skill, level in eval.skill_ratings.items():
                        skill_levels[skill].append(SKILL_LEVEL_ORDER.get(level, 0))

    # Count frequency of strengths and improvements
    strength_counts = defaultdict(int)
    for s in all_strengths:
        # Normalize and count
        s_lower = s.lower().strip()
        strength_counts[s_lower] += 1

    improvement_counts = defaultdict(int)
    for i in all_improvements:
        i_lower = i.lower().strip()
        improvement_counts[i_lower] += 1

    # Calculate average skill levels
    avg_skills = {}
    for skill, levels in skill_levels.items():
        avg_skills[skill] = sum(levels) / len(levels)

    # Sort and return top items
    top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_improvements = sorted(improvement_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    session.close()

    return {
        "student": {"id": student.id, "name": student.name},
        "recurring_strengths": [{"text": s, "count": c} for s, c in top_strengths],
        "recurring_improvements": [{"text": i, "count": c} for i, c in top_improvements],
        "average_skill_levels": avg_skills
    }


# ============================================================================
# Class-wide analysis
# ============================================================================

def get_class_overview() -> dict:
    """Get an overview of the entire class's performance."""
    session = get_session()

    students = session.query(Student).all()
    assignments = session.query(Assignment).all()

    total_students = len(students)
    total_assignments = len(assignments)

    # Submission statistics
    submissions = session.query(Submission).all()
    submission_rate_by_assignment = {}

    for assignment in assignments:
        assignment_submissions = [s for s in submissions if s.assignment_id == assignment.id]
        submitted = len([s for s in assignment_submissions if s.status in ["submitted", "late"]])
        submission_rate_by_assignment[assignment.name] = {
            "submitted": submitted,
            "total": total_students,
            "rate": (submitted / total_students * 100) if total_students > 0 else 0
        }

    # Score distribution
    all_scores = []
    scores_by_assignment = defaultdict(list)

    for submission in submissions:
        for eval in submission.evaluations:
            if eval.is_final and eval.score is not None:
                max_score = submission.assignment.points_possible
                if max_score > 0:
                    percentage = eval.score / max_score * 100
                    all_scores.append(percentage)
                    scores_by_assignment[submission.assignment.name].append(percentage)

    # Calculate distribution buckets
    def calculate_distribution(scores):
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for score in scores:
            if score >= 90:
                distribution["A"] += 1
            elif score >= 80:
                distribution["B"] += 1
            elif score >= 70:
                distribution["C"] += 1
            elif score >= 60:
                distribution["D"] += 1
            else:
                distribution["F"] += 1
        return distribution

    overall_distribution = calculate_distribution(all_scores)
    class_average = sum(all_scores) / len(all_scores) if all_scores else 0

    # Assignment averages
    assignment_averages = {}
    for name, scores in scores_by_assignment.items():
        assignment_averages[name] = sum(scores) / len(scores) if scores else 0

    # Skill distribution across class
    skill_distribution = defaultdict(lambda: defaultdict(int))
    for submission in submissions:
        for eval in submission.evaluations:
            if eval.is_final and eval.skill_ratings:
                for skill, level in eval.skill_ratings.items():
                    skill_distribution[skill][level] += 1

    session.close()

    return {
        "summary": {
            "total_students": total_students,
            "total_assignments": total_assignments,
            "class_average": class_average,
            "total_evaluated_submissions": len(all_scores)
        },
        "grade_distribution": overall_distribution,
        "submission_rates": submission_rate_by_assignment,
        "assignment_averages": assignment_averages,
        "skill_distribution": dict(skill_distribution)
    }


def identify_student_groups() -> dict:
    """Cluster students based on performance patterns."""
    session = get_session()

    students = session.query(Student).all()

    # Categorize students
    groups = {
        "high_performers": [],      # Consistently scoring 90%+
        "solid_performers": [],     # Consistently scoring 80-90%
        "improving": [],            # Showing upward trend
        "struggling": [],           # Consistently below 70%
        "inconsistent": [],         # High variance in scores
        "at_risk": []              # Missing submissions or declining
    }

    for student in students:
        summary = get_student_summary(student.id)

        if "error" in summary:
            continue

        metrics = summary["metrics"]
        overall = metrics["overall_percentage"]
        submissions = metrics["submissions"]
        total = metrics["total_assignments"]

        # Get progression for trend analysis
        progression = get_student_progression(student.id)
        timeline = progression.get("timeline", [])

        # Calculate trend
        trend = 0
        if len(timeline) >= 3:
            recent_avg = sum(t["percentage"] for t in timeline[-3:]) / 3
            earlier_avg = sum(t["percentage"] for t in timeline[:3]) / 3
            trend = recent_avg - earlier_avg

        # Calculate variance
        percentages = [t["percentage"] for t in timeline]
        variance = 0
        if len(percentages) >= 2:
            mean = sum(percentages) / len(percentages)
            variance = sum((p - mean) ** 2 for p in percentages) / len(percentages)

        student_info = {
            "id": student.id,
            "name": student.name,
            "average": overall,
            "trend": trend,
            "submission_rate": (submissions / total * 100) if total > 0 else 0
        }

        # Categorize
        submission_rate = (submissions / total) if total > 0 else 0

        if submission_rate < 0.5:
            groups["at_risk"].append(student_info)
        elif trend < -10:
            groups["at_risk"].append(student_info)
        elif overall >= 90:
            groups["high_performers"].append(student_info)
        elif overall >= 80:
            groups["solid_performers"].append(student_info)
        elif trend > 10:
            groups["improving"].append(student_info)
        elif overall < 70:
            groups["struggling"].append(student_info)
        elif variance > 200:  # High variance
            groups["inconsistent"].append(student_info)
        else:
            groups["solid_performers"].append(student_info)

    session.close()
    return groups


# ============================================================================
# AI-powered insights
# ============================================================================

def generate_student_insights(student_id: int) -> dict:
    """Generate AI-powered insights for a student."""
    summary = get_student_summary(student_id)
    progression = get_student_progression(student_id)
    strengths_weaknesses = get_student_strengths_weaknesses(student_id)

    if "error" in summary:
        return summary

    prompt = f"""Analyze this student's performance data and provide actionable insights.

STUDENT: {summary['student']['name']}

PERFORMANCE METRICS:
- Overall grade: {summary['metrics']['overall_percentage']:.1f}%
- Submissions: {summary['metrics']['submissions']}/{summary['metrics']['total_assignments']}
- On-time rate: {summary['metrics']['on_time_rate']:.1f}%

PERFORMANCE BY ASSIGNMENT TYPE:
{json.dumps(summary['performance_by_type'], indent=2)}

CURRENT SKILL LEVELS:
{json.dumps(summary['current_skills'], indent=2)}

RECURRING STRENGTHS:
{json.dumps(strengths_weaknesses['recurring_strengths'], indent=2)}

RECURRING AREAS FOR IMPROVEMENT:
{json.dumps(strengths_weaknesses['recurring_improvements'], indent=2)}

SKILL PROGRESSION:
{json.dumps(dict(progression.get('skill_trends', {})), indent=2)}

Based on this data, provide:
1. A brief overall assessment (2-3 sentences)
2. Two specific, actionable recommendations for this student
3. Teaching strategies that might help this student
4. Any concerns that warrant instructor attention

Respond in JSON format:
{{
    "overall_assessment": "...",
    "recommendations": ["...", "..."],
    "teaching_strategies": ["...", "..."],
    "concerns": ["..."] or null if no concerns
}}

Be specific and reference actual data patterns. Focus on actionable insights."""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        result["student"] = summary["student"]
        result["data_summary"] = summary["metrics"]
        return result

    except Exception as e:
        return {"error": str(e), "student": summary["student"]}


def generate_class_insights() -> dict:
    """Generate AI-powered insights for the entire class."""
    overview = get_class_overview()
    groups = identify_student_groups()

    prompt = f"""Analyze this class performance data and provide insights for the instructor.

CLASS SUMMARY:
- Students: {overview['summary']['total_students']}
- Class average: {overview['summary']['class_average']:.1f}%

GRADE DISTRIBUTION:
{json.dumps(overview['grade_distribution'], indent=2)}

ASSIGNMENT AVERAGES:
{json.dumps(overview['assignment_averages'], indent=2)}

SKILL DISTRIBUTION:
{json.dumps(overview['skill_distribution'], indent=2)}

STUDENT GROUPINGS:
- High performers: {len(groups['high_performers'])}
- Solid performers: {len(groups['solid_performers'])}
- Improving: {len(groups['improving'])}
- Struggling: {len(groups['struggling'])}
- Inconsistent: {len(groups['inconsistent'])}
- At risk: {len(groups['at_risk'])}

Based on this data, provide:
1. Overall class health assessment (2-3 sentences)
2. Which skills need more class-wide instruction
3. Specific recommendations for different student groups
4. Any patterns or concerns the instructor should address

Respond in JSON format:
{{
    "class_health": "...",
    "skills_needing_attention": ["...", "..."],
    "group_recommendations": {{
        "struggling": "...",
        "at_risk": "...",
        "high_performers": "..."
    }},
    "patterns_and_concerns": ["...", "..."],
    "suggested_interventions": ["...", "..."]
}}

Be specific and actionable."""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        result["data"] = overview
        result["groups"] = {k: len(v) for k, v in groups.items()}
        return result

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# Progress snapshots
# ============================================================================

def create_progress_snapshot() -> ProgressSnapshot:
    """Create a point-in-time snapshot of class progress."""
    session = get_session()

    overview = get_class_overview()
    groups = identify_student_groups()

    # Generate insights
    try:
        insights_data = generate_class_insights()
        insights = insights_data.get("patterns_and_concerns", [])
        recommendations = insights_data.get("suggested_interventions", [])
    except Exception:
        insights = []
        recommendations = []

    snapshot = ProgressSnapshot(
        class_average_score=overview["summary"]["class_average"],
        submission_rate=sum(
            r["rate"] for r in overview["submission_rates"].values()
        ) / len(overview["submission_rates"]) if overview["submission_rates"] else 0,
        skill_distribution=overview["skill_distribution"],
        student_clusters={k: len(v) for k, v in groups.items()},
        insights=insights,
        recommendations=recommendations
    )

    session.add(snapshot)
    session.commit()

    print(f"Created progress snapshot at {snapshot.snapshot_date}")
    session.close()
    return snapshot


def get_progress_history(days: int = 30) -> list[dict]:
    """Get historical progress snapshots."""
    session = get_session()

    cutoff = datetime.utcnow() - timedelta(days=days)
    snapshots = session.query(ProgressSnapshot).filter(
        ProgressSnapshot.snapshot_date >= cutoff
    ).order_by(ProgressSnapshot.snapshot_date).all()

    result = [{
        "id": s.id,
        "date": s.snapshot_date.isoformat(),
        "class_average": s.class_average_score,
        "submission_rate": s.submission_rate,
        "skill_distribution": s.skill_distribution,
        "student_clusters": s.student_clusters,
        "insights": s.insights,
        "recommendations": s.recommendations
    } for s in snapshots]

    session.close()
    return result


# ============================================================================
# Skill assessment updates
# ============================================================================

def update_student_skill_assessments(student_id: int) -> list[SkillAssessment]:
    """Update cumulative skill assessments for a student based on all evaluations."""
    session = get_session()

    student = session.query(Student).get(student_id)
    if not student:
        session.close()
        return []

    # Collect all skill ratings from evaluations
    skill_data = defaultdict(list)

    for submission in student.submissions:
        for eval in submission.evaluations:
            if eval.is_final and eval.skill_ratings:
                for skill, level in eval.skill_ratings.items():
                    skill_data[skill].append({
                        "level": level,
                        "date": eval.created_at
                    })

    # Create/update skill assessments
    assessments = []
    for skill, ratings in skill_data.items():
        # Weight recent ratings more heavily
        level_scores = defaultdict(float)
        for i, r in enumerate(sorted(ratings, key=lambda x: x["date"])):
            weight = 1 + (i / len(ratings))  # Later = higher weight
            level_scores[r["level"]] += weight

        # Determine current level
        current_level = max(level_scores, key=level_scores.get)

        # Calculate confidence based on number of data points
        confidence = min(1.0, len(ratings) / 5)  # Max confidence at 5+ ratings

        # Update or create assessment
        existing = session.query(SkillAssessment).filter_by(
            student_id=student_id,
            skill_name=skill
        ).first()

        if existing:
            existing.skill_level = current_level
            existing.confidence = confidence
            existing.evidence_count = len(ratings)
            existing.assessed_at = datetime.utcnow()
            assessments.append(existing)
        else:
            assessment = SkillAssessment(
                student_id=student_id,
                skill_name=skill,
                skill_level=current_level,
                confidence=confidence,
                evidence_count=len(ratings)
            )
            session.add(assessment)
            assessments.append(assessment)

    session.commit()
    session.close()

    return assessments


def update_all_skill_assessments() -> int:
    """Update skill assessments for all students."""
    session = get_session()
    students = session.query(Student).all()
    student_ids = [s.id for s in students]
    session.close()

    count = 0
    for student_id in student_ids:
        update_student_skill_assessments(student_id)
        count += 1

    print(f"Updated skill assessments for {count} students")
    return count


if __name__ == "__main__":
    # Example usage
    print("=== Student Tracker Analysis ===")

    overview = get_class_overview()
    print(f"\nClass Overview:")
    print(f"  Students: {overview['summary']['total_students']}")
    print(f"  Average: {overview['summary']['class_average']:.1f}%")

    groups = identify_student_groups()
    print(f"\nStudent Groups:")
    for group, students in groups.items():
        print(f"  {group}: {len(students)}")
