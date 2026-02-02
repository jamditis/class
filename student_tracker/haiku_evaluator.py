"""
Claude Haiku evaluation engine for student submissions.

Uses Claude Haiku to:
- Evaluate submissions against rubrics
- Classify skill levels
- Generate feedback and suggestions
- Identify patterns and areas for improvement
"""

import os
import json
from datetime import datetime
from typing import Optional
import anthropic
from .models import (
    get_session, Submission, Evaluation, Assignment,
    EvaluationSource, SkillLevel
)

# Anthropic API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HAIKU_MODEL = "claude-3-5-haiku-20241022"
PROMPT_VERSION = "1.0"


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# Default rubrics for different assignment types
DEFAULT_RUBRICS = {
    "written": {
        "criteria": [
            {
                "name": "Clarity and coherence",
                "description": "Writing is clear, well-organized, and easy to follow",
                "weight": 30,
                "levels": {
                    "advanced": "Writing is exceptionally clear with sophisticated organization",
                    "proficient": "Writing is clear and logically organized",
                    "developing": "Writing has some unclear sections or organizational issues",
                    "emerging": "Writing is difficult to follow or poorly organized"
                }
            },
            {
                "name": "Content depth",
                "description": "Demonstrates understanding and provides substantive analysis",
                "weight": 40,
                "levels": {
                    "advanced": "Shows deep insight with original, nuanced analysis",
                    "proficient": "Demonstrates solid understanding with good analysis",
                    "developing": "Shows basic understanding but analysis is surface-level",
                    "emerging": "Limited understanding or missing key elements"
                }
            },
            {
                "name": "Writing mechanics",
                "description": "Grammar, spelling, punctuation, and formatting",
                "weight": 15,
                "levels": {
                    "advanced": "Nearly flawless mechanics",
                    "proficient": "Minor errors that don't impede understanding",
                    "developing": "Some errors that occasionally affect clarity",
                    "emerging": "Frequent errors that impede understanding"
                }
            },
            {
                "name": "Task completion",
                "description": "Addresses all required elements of the assignment",
                "weight": 15,
                "levels": {
                    "advanced": "Exceeds requirements with additional valuable elements",
                    "proficient": "Meets all requirements completely",
                    "developing": "Meets most requirements but missing some elements",
                    "emerging": "Missing multiple required elements"
                }
            }
        ],
        "skills_assessed": ["writing", "critical_thinking", "communication"]
    },
    "visual": {
        "criteria": [
            {
                "name": "Visual hierarchy",
                "description": "Clear organization of visual elements guiding the viewer's eye",
                "weight": 25,
                "levels": {
                    "advanced": "Masterful use of hierarchy with clear focal points",
                    "proficient": "Good hierarchy that effectively guides attention",
                    "developing": "Some hierarchy present but inconsistent",
                    "emerging": "No clear hierarchy; elements compete for attention"
                }
            },
            {
                "name": "Design principles",
                "description": "Use of contrast, alignment, repetition, and proximity",
                "weight": 30,
                "levels": {
                    "advanced": "Strong command of all design principles",
                    "proficient": "Solid application of most design principles",
                    "developing": "Some design principles applied inconsistently",
                    "emerging": "Design principles not evident"
                }
            },
            {
                "name": "Color and typography",
                "description": "Effective use of color palette and font choices",
                "weight": 20,
                "levels": {
                    "advanced": "Sophisticated color/type choices that enhance message",
                    "proficient": "Appropriate color/type that supports the design",
                    "developing": "Color/type choices are functional but unremarkable",
                    "emerging": "Color/type choices detract from the message"
                }
            },
            {
                "name": "Concept and creativity",
                "description": "Original approach and effective communication of concept",
                "weight": 25,
                "levels": {
                    "advanced": "Highly creative and memorable concept",
                    "proficient": "Good concept that effectively communicates",
                    "developing": "Basic concept that meets minimum requirements",
                    "emerging": "Concept is unclear or missing"
                }
            }
        ],
        "skills_assessed": ["design", "visual_communication", "creativity"]
    },
    "research": {
        "criteria": [
            {
                "name": "Research quality",
                "description": "Depth and relevance of sources and findings",
                "weight": 35,
                "levels": {
                    "advanced": "Comprehensive research with excellent sources",
                    "proficient": "Good research with relevant sources",
                    "developing": "Basic research with some relevant sources",
                    "emerging": "Limited research or irrelevant sources"
                }
            },
            {
                "name": "Analysis",
                "description": "Interpretation and synthesis of research findings",
                "weight": 30,
                "levels": {
                    "advanced": "Insightful analysis that draws meaningful conclusions",
                    "proficient": "Solid analysis with clear takeaways",
                    "developing": "Some analysis but mostly descriptive",
                    "emerging": "Little to no analysis of findings"
                }
            },
            {
                "name": "Organization",
                "description": "Structure and presentation of research",
                "weight": 20,
                "levels": {
                    "advanced": "Highly organized and easy to navigate",
                    "proficient": "Well organized with clear sections",
                    "developing": "Some organization but could be clearer",
                    "emerging": "Poorly organized or difficult to follow"
                }
            },
            {
                "name": "Strategic implications",
                "description": "Ability to connect research to actionable insights",
                "weight": 15,
                "levels": {
                    "advanced": "Clear, actionable strategic recommendations",
                    "proficient": "Good connection between research and strategy",
                    "developing": "Some strategic implications mentioned",
                    "emerging": "No connection to strategy"
                }
            }
        ],
        "skills_assessed": ["research", "analysis", "strategic_thinking"]
    },
    "strategy": {
        "criteria": [
            {
                "name": "Strategic thinking",
                "description": "Quality of strategic reasoning and planning",
                "weight": 35,
                "levels": {
                    "advanced": "Sophisticated strategy with clear rationale",
                    "proficient": "Solid strategy with good reasoning",
                    "developing": "Basic strategy but missing key elements",
                    "emerging": "Strategy is unclear or poorly reasoned"
                }
            },
            {
                "name": "Audience understanding",
                "description": "Demonstrates understanding of target audience",
                "weight": 25,
                "levels": {
                    "advanced": "Deep audience insight informing all decisions",
                    "proficient": "Good audience awareness throughout",
                    "developing": "Some audience consideration but inconsistent",
                    "emerging": "Little evidence of audience understanding"
                }
            },
            {
                "name": "Practicality",
                "description": "Feasibility and actionability of the plan",
                "weight": 25,
                "levels": {
                    "advanced": "Highly realistic and immediately actionable",
                    "proficient": "Realistic plan that could be executed",
                    "developing": "Some practical elements but needs refinement",
                    "emerging": "Plan is unrealistic or vague"
                }
            },
            {
                "name": "Measurement approach",
                "description": "Clear metrics and success criteria",
                "weight": 15,
                "levels": {
                    "advanced": "Well-defined, appropriate metrics with benchmarks",
                    "proficient": "Good metrics tied to objectives",
                    "developing": "Some metrics mentioned but incomplete",
                    "emerging": "No clear measurement approach"
                }
            }
        ],
        "skills_assessed": ["strategy", "planning", "audience_analysis"]
    },
    "general": {
        "criteria": [
            {
                "name": "Quality",
                "description": "Overall quality of the submission",
                "weight": 40,
                "levels": {
                    "advanced": "Exceptional quality exceeding expectations",
                    "proficient": "Good quality meeting all expectations",
                    "developing": "Acceptable quality with room for improvement",
                    "emerging": "Quality below expectations"
                }
            },
            {
                "name": "Completeness",
                "description": "All required elements are present",
                "weight": 30,
                "levels": {
                    "advanced": "All elements present with additional value",
                    "proficient": "All required elements present",
                    "developing": "Most elements present, some missing",
                    "emerging": "Many required elements missing"
                }
            },
            {
                "name": "Effort",
                "description": "Evidence of thought and effort invested",
                "weight": 30,
                "levels": {
                    "advanced": "Clear evidence of significant effort",
                    "proficient": "Good effort evident throughout",
                    "developing": "Some effort but could be more thorough",
                    "emerging": "Minimal effort evident"
                }
            }
        ],
        "skills_assessed": ["general"]
    }
}


def build_evaluation_prompt(
    submission_content: str,
    assignment_name: str,
    assignment_description: str,
    rubric: dict,
    points_possible: float
) -> str:
    """Build the evaluation prompt for Haiku."""

    criteria_text = ""
    for i, criterion in enumerate(rubric.get("criteria", []), 1):
        criteria_text += f"\n{i}. {criterion['name']} ({criterion['weight']}%)\n"
        criteria_text += f"   Description: {criterion['description']}\n"
        criteria_text += "   Levels:\n"
        for level, desc in criterion.get("levels", {}).items():
            criteria_text += f"   - {level}: {desc}\n"

    prompt = f"""You are an experienced instructor evaluating a student submission for an undergraduate multimedia production course. Evaluate the following submission carefully and provide detailed feedback.

ASSIGNMENT: {assignment_name}
DESCRIPTION: {assignment_description}
POINTS POSSIBLE: {points_possible}

RUBRIC CRITERIA:
{criteria_text}

STUDENT SUBMISSION:
---
{submission_content[:10000]}
---

Evaluate this submission and respond with a JSON object containing:

{{
    "overall_score": <number from 0 to {points_possible}>,
    "score_breakdown": {{
        "<criterion_name>": {{
            "level": "<emerging|developing|proficient|advanced>",
            "score": <number>,
            "feedback": "<brief specific feedback for this criterion>"
        }}
    }},
    "skill_ratings": {{
        "<skill_name>": "<emerging|developing|proficient|advanced>"
    }},
    "strengths": [
        "<specific strength 1>",
        "<specific strength 2>"
    ],
    "areas_for_improvement": [
        "<specific area 1>",
        "<specific area 2>"
    ],
    "overall_feedback": "<2-3 sentences of constructive, encouraging feedback>",
    "next_steps": "<1-2 specific suggestions for what the student should focus on next>"
}}

Be specific in your feedback, referencing actual content from the submission. Be constructive and encouraging while being honest about areas for improvement. Calibrate scores appropriately - not every submission should be advanced, and emerging doesn't mean failure.

Respond ONLY with the JSON object, no other text."""

    return prompt


def evaluate_submission(
    submission_id: int,
    force: bool = False,
    custom_rubric: dict = None
) -> Optional[Evaluation]:
    """
    Evaluate a submission using Claude Haiku.

    Args:
        submission_id: Database ID of the submission to evaluate
        force: If True, create new evaluation even if one exists
        custom_rubric: Optional custom rubric to use instead of default

    Returns:
        Evaluation object or None if evaluation failed
    """
    session = get_session()

    submission = session.query(Submission).get(submission_id)
    if not submission:
        print(f"Submission {submission_id} not found")
        session.close()
        return None

    # Check for existing evaluation
    if not force:
        existing = session.query(Evaluation).filter_by(
            submission_id=submission_id,
            is_final=True
        ).first()
        if existing:
            print(f"Submission {submission_id} already has a final evaluation")
            session.close()
            return existing

    assignment = submission.assignment
    if not submission.content:
        print(f"Submission {submission_id} has no content to evaluate")
        session.close()
        return None

    # Get rubric
    rubric = custom_rubric or assignment.rubric
    if not rubric:
        # Use default rubric based on assignment type
        rubric = DEFAULT_RUBRICS.get(
            assignment.assignment_type or "general",
            DEFAULT_RUBRICS["general"]
        )

    # Build prompt
    prompt = build_evaluation_prompt(
        submission_content=submission.content,
        assignment_name=assignment.name,
        assignment_description=assignment.description or "",
        rubric=rubric,
        points_possible=assignment.points_possible
    )

    # Call Haiku
    try:
        client = get_client()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = response.content[0].text
        result = json.loads(response_text)

        # Create evaluation record
        evaluation = Evaluation(
            submission_id=submission_id,
            source=EvaluationSource.HAIKU_AUTO.value,
            score=result.get("overall_score"),
            score_breakdown=result.get("score_breakdown"),
            feedback=result.get("overall_feedback"),
            strengths=result.get("strengths"),
            areas_for_improvement=result.get("areas_for_improvement"),
            skill_ratings=result.get("skill_ratings"),
            haiku_model_version=HAIKU_MODEL,
            haiku_prompt_version=PROMPT_VERSION,
            haiku_raw_response=response_text,
            is_final=True
        )

        session.add(evaluation)
        session.commit()

        print(f"Evaluated submission {submission_id}: {result.get('overall_score')}/{assignment.points_possible}")
        session.close()
        return evaluation

    except json.JSONDecodeError as e:
        print(f"Failed to parse Haiku response: {e}")
        session.close()
        return None
    except Exception as e:
        print(f"Evaluation failed: {e}")
        session.close()
        return None


def evaluate_all_pending(
    assignment_id: Optional[int] = None,
    limit: int = 50
) -> list[Evaluation]:
    """
    Evaluate all submissions that don't have final evaluations.

    Args:
        assignment_id: Optional filter to specific assignment
        limit: Maximum number of submissions to evaluate

    Returns:
        List of created Evaluation objects
    """
    session = get_session()

    # Find submissions without final evaluations
    query = session.query(Submission).filter(
        Submission.content.isnot(None),
        Submission.content != ""
    )

    if assignment_id:
        query = query.filter(Submission.assignment_id == assignment_id)

    # Exclude submissions that already have final evaluations
    evaluated_ids = session.query(Evaluation.submission_id).filter(
        Evaluation.is_final == True
    ).subquery()

    query = query.filter(~Submission.id.in_(evaluated_ids))

    submissions = query.limit(limit).all()
    session.close()

    print(f"Found {len(submissions)} submissions to evaluate")

    evaluations = []
    for sub in submissions:
        eval_result = evaluate_submission(sub.id)
        if eval_result:
            evaluations.append(eval_result)

    print(f"Completed {len(evaluations)} evaluations")
    return evaluations


def batch_evaluate_text(
    texts: list[dict],
    assignment_type: str = "written"
) -> list[dict]:
    """
    Evaluate multiple text submissions without database storage.

    Useful for quick evaluation of content not yet in the system.

    Args:
        texts: List of dicts with 'content' and optional 'student_name' keys
        assignment_type: Type of assignment for rubric selection

    Returns:
        List of evaluation results
    """
    rubric = DEFAULT_RUBRICS.get(assignment_type, DEFAULT_RUBRICS["general"])
    results = []

    for item in texts:
        prompt = build_evaluation_prompt(
            submission_content=item.get("content", ""),
            assignment_name=item.get("assignment_name", "Submission"),
            assignment_description=item.get("description", ""),
            rubric=rubric,
            points_possible=item.get("points_possible", 100)
        )

        try:
            client = get_client()
            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            result["student_name"] = item.get("student_name", "Unknown")
            results.append(result)

        except Exception as e:
            results.append({
                "error": str(e),
                "student_name": item.get("student_name", "Unknown")
            })

    return results


def get_rubric_for_assignment(assignment_id: int) -> dict:
    """Get the effective rubric for an assignment."""
    session = get_session()
    assignment = session.query(Assignment).get(assignment_id)
    session.close()

    if not assignment:
        return DEFAULT_RUBRICS["general"]

    if assignment.rubric:
        return assignment.rubric

    return DEFAULT_RUBRICS.get(
        assignment.assignment_type or "general",
        DEFAULT_RUBRICS["general"]
    )


def set_assignment_rubric(assignment_id: int, rubric: dict) -> bool:
    """Set a custom rubric for an assignment."""
    session = get_session()
    assignment = session.query(Assignment).get(assignment_id)

    if not assignment:
        session.close()
        return False

    assignment.rubric = rubric
    session.commit()
    session.close()
    return True


if __name__ == "__main__":
    # Test evaluation with sample text
    sample_texts = [{
        "content": """The Cluetrain Manifesto's thesis #7 states that hyperlinks subvert hierarchy.
        I found this particularly relevant when looking at how TikTok creators can now
        bypass traditional media gatekeepers to reach millions directly. For example,
        independent journalist Casey Newton built a substantial following through his
        newsletter Platformer, which he runs independently rather than through a
        traditional publication. This demonstrates that 27 years later, the principle
        not only holds true but has intensified - individual voices can now compete
        with institutional ones in ways unimaginable in 1999.""",
        "student_name": "Test Student",
        "assignment_name": "Cluetrain Manifesto media analysis",
        "description": "Analyze a piece of media through the lens of the Cluetrain Manifesto",
        "points_possible": 25
    }]

    results = batch_evaluate_text(sample_texts, "written")
    print(json.dumps(results, indent=2))
