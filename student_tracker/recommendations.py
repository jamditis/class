"""
Recommendation engine for skill-based insights.

Generates:
- Personalized learning recommendations for students
- Teaching strategy suggestions for instructors
- Resource recommendations based on skill gaps
- Intervention suggestions for at-risk students
"""

import os
import json
from typing import Optional
import anthropic
from .models import get_session, Student, Assignment, Submission, Evaluation, SkillAssessment
from .analyzer import (
    get_student_summary, get_student_progression,
    get_student_strengths_weaknesses, identify_student_groups,
    get_class_overview
)

# Anthropic configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HAIKU_MODEL = "claude-3-5-haiku-20241022"


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ============================================================================
# Skill-based recommendations
# ============================================================================

# Skill development resources and activities
SKILL_RESOURCES = {
    "writing": {
        "emerging": [
            "Review basic paragraph structure and topic sentences",
            "Practice freewriting exercises (10 minutes daily)",
            "Read examples of clear professional writing",
            "Use Hemingway Editor to identify complex sentences"
        ],
        "developing": [
            "Focus on transitions between paragraphs",
            "Practice writing with specific word count constraints",
            "Study how professional articles structure arguments",
            "Get peer feedback on drafts before submission"
        ],
        "proficient": [
            "Experiment with voice and tone for different audiences",
            "Practice concise writing (cut word count by 20%)",
            "Study persuasive writing techniques",
            "Read industry publications for style inspiration"
        ],
        "advanced": [
            "Mentor peers on writing improvement",
            "Experiment with different narrative structures",
            "Develop a consistent personal writing style",
            "Consider contributing to industry publications"
        ]
    },
    "design": {
        "emerging": [
            "Study the 4 basic design principles (CRAP: Contrast, Repetition, Alignment, Proximity)",
            "Recreate designs you admire to understand their structure",
            "Practice with templates before designing from scratch",
            "Build a swipe file of designs you like"
        ],
        "developing": [
            "Focus on visual hierarchy in every design",
            "Limit yourself to 2-3 fonts and colors per project",
            "Study whitespace and how it creates breathing room",
            "Get critique from design-focused peers"
        ],
        "proficient": [
            "Develop consistent style guides for projects",
            "Study advanced typography and color theory",
            "Create designs for multiple platforms/sizes",
            "Analyze award-winning design campaigns"
        ],
        "advanced": [
            "Lead design reviews for peer projects",
            "Experiment with emerging design trends",
            "Build a portfolio-ready body of work",
            "Consider entering student design competitions"
        ]
    },
    "research": {
        "emerging": [
            "Learn to use academic databases effectively",
            "Practice evaluating source credibility",
            "Start with broad searches, then narrow down",
            "Keep organized notes with proper citations"
        ],
        "developing": [
            "Develop systematic research methodologies",
            "Learn to identify primary vs. secondary sources",
            "Practice synthesizing information from multiple sources",
            "Use reference management tools (Zotero, Mendeley)"
        ],
        "proficient": [
            "Conduct original primary research (surveys, interviews)",
            "Develop data analysis skills",
            "Learn competitive analysis frameworks",
            "Practice presenting research findings"
        ],
        "advanced": [
            "Lead research projects for teams",
            "Develop custom research frameworks",
            "Mentor peers on research methodologies",
            "Consider publishing research findings"
        ]
    },
    "strategy": {
        "emerging": [
            "Study basic marketing strategy frameworks",
            "Learn to write SMART goals",
            "Understand the difference between strategy and tactics",
            "Review case studies of successful campaigns"
        ],
        "developing": [
            "Practice audience analysis techniques",
            "Learn to create content calendars",
            "Study platform-specific strategies",
            "Develop measurement and KPI frameworks"
        ],
        "proficient": [
            "Create integrated cross-platform strategies",
            "Develop competitive positioning strategies",
            "Learn budget allocation and ROI calculation",
            "Practice presenting strategies to stakeholders"
        ],
        "advanced": [
            "Lead strategic planning for team projects",
            "Develop innovative strategic approaches",
            "Study advanced analytics and optimization",
            "Consider case competition participation"
        ]
    },
    "critical_thinking": {
        "emerging": [
            "Practice identifying assumptions in arguments",
            "Learn to distinguish facts from opinions",
            "Study logical fallacies and how to spot them",
            "Read diverse perspectives on the same topic"
        ],
        "developing": [
            "Practice evaluating evidence quality",
            "Develop skills in constructing arguments",
            "Learn to anticipate counterarguments",
            "Engage in structured debates or discussions"
        ],
        "proficient": [
            "Apply critical thinking to media analysis",
            "Develop frameworks for decision-making",
            "Practice Socratic questioning techniques",
            "Analyze complex multi-stakeholder situations"
        ],
        "advanced": [
            "Lead discussions and facilitate debates",
            "Apply systems thinking to complex problems",
            "Mentor peers on analytical approaches",
            "Develop original frameworks for analysis"
        ]
    }
}


def get_skill_recommendations(
    skill_name: str,
    current_level: str
) -> list[str]:
    """Get recommended activities for improving a specific skill."""
    skill_name = skill_name.lower().replace(" ", "_")

    if skill_name in SKILL_RESOURCES:
        level_resources = SKILL_RESOURCES[skill_name].get(current_level, [])
        return level_resources

    # Generic recommendations for unknown skills
    generic = {
        "emerging": [
            f"Study foundational concepts in {skill_name}",
            "Find tutorials and beginner resources",
            "Practice with guided exercises"
        ],
        "developing": [
            f"Practice {skill_name} regularly with feedback",
            "Study examples of excellent work",
            "Identify specific areas for improvement"
        ],
        "proficient": [
            f"Challenge yourself with complex {skill_name} tasks",
            "Seek advanced feedback and critique",
            "Help peers develop their skills"
        ],
        "advanced": [
            f"Mentor others in {skill_name}",
            "Develop innovative approaches",
            "Consider professional development opportunities"
        ]
    }

    return generic.get(current_level, [])


def generate_student_recommendations(student_id: int) -> dict:
    """Generate personalized recommendations for a student."""
    summary = get_student_summary(student_id)
    progression = get_student_progression(student_id)
    strengths_weaknesses = get_student_strengths_weaknesses(student_id)

    if "error" in summary:
        return summary

    # Identify skills needing improvement
    skills = summary.get("current_skills", {})
    skill_recommendations = {}

    for skill, level in skills.items():
        recommendations = get_skill_recommendations(skill, level)
        skill_recommendations[skill] = {
            "current_level": level,
            "recommendations": recommendations
        }

    # Identify priority areas (skills at emerging or developing level)
    priority_skills = [
        skill for skill, level in skills.items()
        if level in ["emerging", "developing"]
    ]

    # Generate overall recommendations using Haiku
    prompt = f"""Based on this student's performance data, generate 3 specific, actionable recommendations.

STUDENT: {summary['student']['name']}
OVERALL GRADE: {summary['metrics']['overall_percentage']:.1f}%
ON-TIME RATE: {summary['metrics']['on_time_rate']:.1f}%

CURRENT SKILL LEVELS:
{json.dumps(skills, indent=2)}

RECURRING STRENGTHS:
{json.dumps(strengths_weaknesses.get('recurring_strengths', []), indent=2)}

RECURRING AREAS FOR IMPROVEMENT:
{json.dumps(strengths_weaknesses.get('recurring_improvements', []), indent=2)}

PRIORITY SKILLS TO DEVELOP: {', '.join(priority_skills) or 'None identified'}

Provide 3 specific, actionable recommendations that:
1. Build on the student's existing strengths
2. Address the most impactful areas for improvement
3. Are appropriate for an undergraduate communications student

Respond in JSON format:
{{
    "top_recommendations": [
        {{
            "title": "Brief title",
            "description": "1-2 sentence explanation",
            "action_items": ["Specific action 1", "Specific action 2"]
        }}
    ],
    "encouragement": "A brief encouraging message acknowledging their strengths"
}}"""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        ai_recommendations = json.loads(response.content[0].text)
    except Exception as e:
        ai_recommendations = {
            "top_recommendations": [],
            "encouragement": "",
            "error": str(e)
        }

    return {
        "student": summary["student"],
        "summary": summary["metrics"],
        "skill_recommendations": skill_recommendations,
        "priority_skills": priority_skills,
        "ai_recommendations": ai_recommendations
    }


# ============================================================================
# Group-based recommendations
# ============================================================================

def get_intervention_strategies(group_type: str) -> dict:
    """Get intervention strategies for different student groups."""
    strategies = {
        "at_risk": {
            "description": "Students at risk of failing or dropping out",
            "immediate_actions": [
                "Schedule one-on-one meeting within 48 hours",
                "Review submission history for patterns",
                "Check for external factors (other classes, personal issues)",
                "Offer extended office hours or tutoring"
            ],
            "support_strategies": [
                "Break assignments into smaller checkpoints",
                "Provide additional scaffolding and templates",
                "Consider peer mentoring from high performers",
                "Connect with academic support services if needed"
            ],
            "communication": [
                "Use supportive, non-judgmental language",
                "Focus on specific, achievable goals",
                "Celebrate small wins to build momentum",
                "Check in regularly between assignments"
            ]
        },
        "struggling": {
            "description": "Students consistently performing below expectations",
            "immediate_actions": [
                "Identify specific skill gaps through evaluation patterns",
                "Provide targeted feedback on recent submissions",
                "Offer revision opportunities on key assignments"
            ],
            "support_strategies": [
                "Provide additional resources for weak skill areas",
                "Create study groups with solid performers",
                "Offer alternative demonstration of learning if appropriate",
                "Consider modified expectations with clear path to improvement"
            ],
            "communication": [
                "Be specific about what needs improvement",
                "Acknowledge effort while addressing gaps",
                "Set clear, achievable improvement goals",
                "Provide positive reinforcement for progress"
            ]
        },
        "inconsistent": {
            "description": "Students with highly variable performance",
            "immediate_actions": [
                "Analyze which assignment types show strongest/weakest performance",
                "Look for time management or prioritization issues",
                "Check if external factors affect certain assignment types"
            ],
            "support_strategies": [
                "Help develop consistent work habits and routines",
                "Provide early feedback on drafts before due dates",
                "Create structured timelines for complex assignments",
                "Address specific weak areas with targeted support"
            ],
            "communication": [
                "Acknowledge their capability shown in strong work",
                "Explore what differs between strong and weak submissions",
                "Set expectations for consistency",
                "Help them identify their own success factors"
            ]
        },
        "improving": {
            "description": "Students showing upward performance trends",
            "immediate_actions": [
                "Acknowledge and reinforce improvement",
                "Identify what's working and encourage continuation",
                "Set slightly higher expectations to maintain momentum"
            ],
            "support_strategies": [
                "Gradually reduce scaffolding as skills develop",
                "Introduce more challenging optional elements",
                "Consider for peer mentoring opportunities",
                "Highlight growth in feedback"
            ],
            "communication": [
                "Celebrate progress explicitly",
                "Share specific examples of improvement",
                "Express confidence in continued growth",
                "Discuss goals for rest of semester"
            ]
        },
        "high_performers": {
            "description": "Students consistently exceeding expectations",
            "immediate_actions": [
                "Ensure they're being appropriately challenged",
                "Look for opportunities to extend their learning",
                "Consider leadership roles in group activities"
            ],
            "support_strategies": [
                "Offer advanced optional challenges",
                "Recruit as peer mentors or tutors",
                "Provide industry connections or opportunities",
                "Support portfolio development"
            ],
            "communication": [
                "Provide advanced feedback beyond basic requirements",
                "Discuss career and professional development",
                "Encourage them to push beyond comfort zone",
                "Connect with industry professionals or alumni"
            ]
        },
        "solid_performers": {
            "description": "Students meeting expectations consistently",
            "immediate_actions": [
                "Identify areas for potential growth",
                "Check for engagement and motivation",
                "Ensure they're not coasting"
            ],
            "support_strategies": [
                "Challenge them to move from good to great",
                "Provide specific feedback for improvement",
                "Offer opportunities for leadership or mentoring",
                "Connect assignments to career interests"
            ],
            "communication": [
                "Acknowledge consistent good work",
                "Push gently for higher achievement",
                "Ask about their goals and aspirations",
                "Provide actionable paths to excellence"
            ]
        }
    }

    return strategies.get(group_type, strategies["solid_performers"])


def generate_group_recommendations(group_type: str, students: list[dict]) -> dict:
    """Generate recommendations for a specific student group."""
    strategies = get_intervention_strategies(group_type)

    if not students:
        return {
            "group_type": group_type,
            "count": 0,
            "strategies": strategies,
            "specific_recommendations": []
        }

    # Calculate group metrics
    avg_score = sum(s.get("average", 0) for s in students) / len(students)
    avg_trend = sum(s.get("trend", 0) for s in students) / len(students)

    # Generate specific recommendations using Haiku
    student_summaries = "\n".join([
        f"- {s['name']}: {s.get('average', 0):.1f}% average, trend: {s.get('trend', 0):+.1f}"
        for s in students[:10]  # Limit to first 10
    ])

    prompt = f"""As an instructor, generate specific recommendations for this group of students.

GROUP TYPE: {group_type}
STUDENTS ({len(students)} total):
{student_summaries}

GROUP AVERAGE: {avg_score:.1f}%
AVERAGE TREND: {avg_trend:+.1f}

Based on the group characteristics, provide:
1. One specific class-wide intervention that would help this group
2. Two individual outreach approaches
3. One assignment modification or support strategy

Respond in JSON format:
{{
    "class_intervention": "Specific intervention description",
    "individual_outreach": ["Approach 1", "Approach 2"],
    "assignment_strategy": "Modification or support description",
    "priority_level": "high|medium|low"
}}"""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        ai_recommendations = json.loads(response.content[0].text)
    except Exception as e:
        ai_recommendations = {"error": str(e)}

    return {
        "group_type": group_type,
        "count": len(students),
        "students": students,
        "metrics": {
            "average_score": avg_score,
            "average_trend": avg_trend
        },
        "strategies": strategies,
        "ai_recommendations": ai_recommendations
    }


# ============================================================================
# Class-wide recommendations
# ============================================================================

def generate_class_recommendations() -> dict:
    """Generate recommendations for the entire class."""
    overview = get_class_overview()
    groups = identify_student_groups()

    # Get recommendations for each group
    group_recommendations = {}
    for group_type, students in groups.items():
        if students:  # Only generate for non-empty groups
            group_recommendations[group_type] = generate_group_recommendations(
                group_type, students
            )

    # Identify class-wide skill gaps
    skill_distribution = overview.get("skill_distribution", {})
    skills_needing_attention = []

    for skill, levels in skill_distribution.items():
        total = sum(levels.values())
        if total > 0:
            emerging_developing = levels.get("emerging", 0) + levels.get("developing", 0)
            if emerging_developing / total > 0.5:  # More than 50% below proficient
                skills_needing_attention.append(skill)

    # Generate overall class recommendations using Haiku
    prompt = f"""As an instructor for a multimedia production course, analyze this class data and provide recommendations.

CLASS SUMMARY:
- Students: {overview['summary']['total_students']}
- Class average: {overview['summary']['class_average']:.1f}%

GRADE DISTRIBUTION:
{json.dumps(overview['grade_distribution'], indent=2)}

STUDENT GROUPS:
- At risk: {len(groups['at_risk'])}
- Struggling: {len(groups['struggling'])}
- Inconsistent: {len(groups['inconsistent'])}
- Improving: {len(groups['improving'])}
- Solid performers: {len(groups['solid_performers'])}
- High performers: {len(groups['high_performers'])}

SKILLS NEEDING CLASS-WIDE ATTENTION: {', '.join(skills_needing_attention) or 'None identified'}

Provide recommendations in JSON format:
{{
    "class_health_assessment": "Brief 2-3 sentence assessment",
    "immediate_priorities": ["Priority 1", "Priority 2"],
    "teaching_adjustments": ["Adjustment 1", "Adjustment 2"],
    "upcoming_assignment_considerations": ["Consideration 1"],
    "positive_observations": ["Something positive about the class"]
}}"""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        class_ai_recommendations = json.loads(response.content[0].text)
    except Exception as e:
        class_ai_recommendations = {"error": str(e)}

    return {
        "overview": overview["summary"],
        "grade_distribution": overview["grade_distribution"],
        "skills_needing_attention": skills_needing_attention,
        "group_recommendations": group_recommendations,
        "class_recommendations": class_ai_recommendations
    }


# ============================================================================
# Assignment-specific recommendations
# ============================================================================

def get_assignment_recommendations(assignment_id: int) -> dict:
    """Get recommendations for improving an assignment based on student performance."""
    session = get_session()

    assignment = session.query(Assignment).get(assignment_id)
    if not assignment:
        session.close()
        return {"error": f"Assignment {assignment_id} not found"}

    # Collect all evaluations for this assignment
    submissions = session.query(Submission).filter_by(assignment_id=assignment_id).all()

    scores = []
    all_strengths = []
    all_improvements = []
    skill_ratings = []

    for sub in submissions:
        for eval in sub.evaluations:
            if eval.is_final:
                if eval.score is not None:
                    scores.append(eval.score / assignment.points_possible * 100
                                 if assignment.points_possible > 0 else 0)
                if eval.strengths:
                    all_strengths.extend(eval.strengths)
                if eval.areas_for_improvement:
                    all_improvements.extend(eval.areas_for_improvement)
                if eval.skill_ratings:
                    skill_ratings.append(eval.skill_ratings)

    session.close()

    if not scores:
        return {
            "assignment": {"id": assignment.id, "name": assignment.name},
            "message": "No evaluated submissions yet"
        }

    # Calculate metrics
    avg_score = sum(scores) / len(scores)
    score_distribution = {
        "A": len([s for s in scores if s >= 90]),
        "B": len([s for s in scores if 80 <= s < 90]),
        "C": len([s for s in scores if 70 <= s < 80]),
        "D": len([s for s in scores if 60 <= s < 70]),
        "F": len([s for s in scores if s < 60])
    }

    # Count common issues
    from collections import Counter
    improvement_counts = Counter(i.lower().strip() for i in all_improvements)
    strength_counts = Counter(s.lower().strip() for s in all_strengths)

    common_issues = improvement_counts.most_common(5)
    common_strengths = strength_counts.most_common(5)

    # Generate recommendations
    prompt = f"""Analyze this assignment's performance data and suggest improvements.

ASSIGNMENT: {assignment.name}
TYPE: {assignment.assignment_type}
POINTS: {assignment.points_possible}

PERFORMANCE:
- Average score: {avg_score:.1f}%
- Evaluated submissions: {len(scores)}

SCORE DISTRIBUTION:
{json.dumps(score_distribution, indent=2)}

COMMON ISSUES STUDENTS HAD:
{json.dumps([{"issue": i, "count": c} for i, c in common_issues], indent=2)}

COMMON STRENGTHS:
{json.dumps([{"strength": s, "count": c} for s, c in common_strengths], indent=2)}

Provide recommendations in JSON format:
{{
    "assignment_feedback": "Brief assessment of how students performed",
    "instructions_improvements": ["Suggestion for clearer instructions"],
    "rubric_adjustments": ["Potential rubric adjustment"],
    "preparation_activities": ["Activity to help future students"],
    "common_misconceptions": ["Misconception students had"]
}}"""

    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )

        ai_recommendations = json.loads(response.content[0].text)
    except Exception as e:
        ai_recommendations = {"error": str(e)}

    return {
        "assignment": {"id": assignment.id, "name": assignment.name},
        "metrics": {
            "average_score": avg_score,
            "submission_count": len(scores),
            "score_distribution": score_distribution
        },
        "common_issues": common_issues,
        "common_strengths": common_strengths,
        "recommendations": ai_recommendations
    }


if __name__ == "__main__":
    # Example usage
    print("=== Recommendation Engine ===")

    # Show skill recommendations
    print("\nWriting recommendations for 'developing' level:")
    recs = get_skill_recommendations("writing", "developing")
    for r in recs:
        print(f"  - {r}")

    print("\nIntervention strategies for 'at_risk' students:")
    strategies = get_intervention_strategies("at_risk")
    print(f"  Immediate actions: {len(strategies['immediate_actions'])}")
    print(f"  Support strategies: {len(strategies['support_strategies'])}")
