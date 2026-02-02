"""
Database models for the student tracking system.

Uses SQLAlchemy with SQLite for simple, file-based persistence.
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, Boolean, ForeignKey, JSON, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

# Database setup
DB_PATH = os.environ.get("STUDENT_TRACKER_DB", "student_tracker.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class SkillLevel(enum.Enum):
    """Skill proficiency levels for student assessment."""
    EMERGING = "emerging"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"


class SubmissionStatus(enum.Enum):
    """Status of a student submission."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"
    EXCUSED = "excused"


class EvaluationSource(enum.Enum):
    """Source of an evaluation."""
    HAIKU_AUTO = "haiku_auto"      # Automated Haiku evaluation
    MANUAL = "manual"              # Manual instructor evaluation
    HAIKU_ASSISTED = "haiku_assisted"  # Haiku suggestion, instructor confirmed


class Student(Base):
    """Student record."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), unique=True, nullable=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submissions = relationship("Submission", back_populates="student")
    skill_assessments = relationship("SkillAssessment", back_populates="student")
    notes = relationship("StudentNote", back_populates="student")

    def __repr__(self):
        return f"<Student(id={self.id}, name='{self.name}')>"


class Assignment(Base):
    """Assignment definition."""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), unique=True, nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    points_possible = Column(Float, nullable=False, default=0)
    due_date = Column(DateTime, nullable=True)
    assignment_type = Column(String(50), nullable=True)  # written, visual, research, etc.

    # Rubric stored as JSON for flexibility
    rubric = Column(JSON, nullable=True)

    # Skills this assignment assesses
    skills_assessed = Column(JSON, nullable=True)  # ["writing", "design", "research"]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submissions = relationship("Submission", back_populates="assignment")

    def __repr__(self):
        return f"<Assignment(id={self.id}, name='{self.name}')>"


class Submission(Base):
    """Student submission for an assignment."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    canvas_submission_id = Column(String(50), nullable=True)

    # Submission content
    content = Column(Text, nullable=True)  # Text content or URL
    file_path = Column(String(500), nullable=True)  # Local file path if uploaded
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(20), default=SubmissionStatus.PENDING.value)

    # Manual input source tracking
    input_source = Column(String(50), default="canvas")  # canvas, manual, csv_import, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")
    evaluations = relationship("Evaluation", back_populates="submission")

    def __repr__(self):
        return f"<Submission(student_id={self.student_id}, assignment_id={self.assignment_id})>"


class Evaluation(Base):
    """Evaluation of a submission (can be automated or manual)."""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

    # Evaluation source and type
    source = Column(String(20), default=EvaluationSource.HAIKU_AUTO.value)

    # Scores
    score = Column(Float, nullable=True)  # Numeric score
    score_breakdown = Column(JSON, nullable=True)  # Per-rubric-item scores

    # Qualitative feedback
    feedback = Column(Text, nullable=True)  # Overall feedback
    strengths = Column(JSON, nullable=True)  # List of strengths identified
    areas_for_improvement = Column(JSON, nullable=True)  # List of areas to improve

    # Skill-level assessment for this submission
    skill_ratings = Column(JSON, nullable=True)  # {"writing": "proficient", "design": "developing"}

    # Haiku-specific fields
    haiku_model_version = Column(String(50), nullable=True)
    haiku_prompt_version = Column(String(20), nullable=True)
    haiku_raw_response = Column(Text, nullable=True)

    # Manual override tracking
    is_final = Column(Boolean, default=False)  # Whether this is the accepted evaluation
    overridden_by = Column(Integer, ForeignKey("evaluations.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submission = relationship("Submission", back_populates="evaluations")

    def __repr__(self):
        return f"<Evaluation(id={self.id}, submission_id={self.submission_id}, source='{self.source}')>"


class SkillAssessment(Base):
    """Cumulative skill assessment for a student over time."""
    __tablename__ = "skill_assessments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    # Skill being assessed
    skill_name = Column(String(100), nullable=False)  # writing, design, research, strategy, etc.
    skill_level = Column(String(20), nullable=False)  # emerging, developing, proficient, advanced

    # Confidence and evidence
    confidence = Column(Float, default=0.5)  # 0-1, how confident in this assessment
    evidence_count = Column(Integer, default=0)  # Number of submissions informing this

    # Detailed breakdown
    sub_skills = Column(JSON, nullable=True)  # {"clarity": "proficient", "grammar": "developing"}

    # Snapshot date (for tracking progression)
    assessed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="skill_assessments")

    def __repr__(self):
        return f"<SkillAssessment(student_id={self.student_id}, skill='{self.skill_name}', level='{self.skill_level}')>"


class StudentNote(Base):
    """Manual notes about a student (instructor observations, context, etc.)."""
    __tablename__ = "student_notes"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    note_type = Column(String(50), default="general")  # general, concern, praise, accommodation, etc.
    content = Column(Text, nullable=False)

    # Optional: link to specific assignment/submission
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="notes")

    def __repr__(self):
        return f"<StudentNote(student_id={self.student_id}, type='{self.note_type}')>"


class ProgressSnapshot(Base):
    """Periodic snapshot of class-wide and individual progress."""
    __tablename__ = "progress_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow)

    # Class-wide metrics
    class_average_score = Column(Float, nullable=True)
    submission_rate = Column(Float, nullable=True)  # % of students who submitted

    # Skill distribution (JSON: {"writing": {"emerging": 5, "developing": 10, ...}})
    skill_distribution = Column(JSON, nullable=True)

    # Identified groups/clusters
    student_clusters = Column(JSON, nullable=True)  # Groupings based on performance

    # AI-generated insights
    insights = Column(JSON, nullable=True)  # List of insight strings
    recommendations = Column(JSON, nullable=True)  # List of recommendations

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ProgressSnapshot(id={self.id}, date='{self.snapshot_date}')>"


class SystemConfig(Base):
    """System configuration and settings."""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}')>"


class FeedbackQueueStatus(enum.Enum):
    """Status of a feedback item in the review queue."""
    PENDING = "pending"        # Awaiting instructor review
    APPROVED = "approved"      # Approved, ready to publish
    PUBLISHED = "published"    # Successfully published to Canvas
    REJECTED = "rejected"      # Rejected by instructor
    EDITED = "edited"          # Edited by instructor, ready to publish


class FeedbackType(enum.Enum):
    """Type of feedback to publish."""
    SUBMISSION_COMMENT = "submission_comment"  # Comment on a student submission
    DISCUSSION_POST = "discussion_post"        # New discussion topic
    DISCUSSION_ENTRY = "discussion_entry"      # Reply to existing discussion
    ANNOUNCEMENT = "announcement"              # Course announcement


class FeedbackQueue(Base):
    """
    Queue for AI-generated feedback awaiting instructor approval.

    This implements the human-in-the-loop workflow:
    1. AI generates feedback/insight
    2. Feedback is added to queue with status=PENDING
    3. Instructor reviews, edits if needed, approves/rejects
    4. Approved feedback is published to Canvas
    """
    __tablename__ = "feedback_queue"

    id = Column(Integer, primary_key=True)

    # Type of feedback
    feedback_type = Column(String(30), default=FeedbackType.SUBMISSION_COMMENT.value)

    # Target (depends on feedback_type)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # For individual feedback
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)  # For submission comments
    discussion_topic_id = Column(String(50), nullable=True)  # Canvas topic ID for replies

    # Content
    title = Column(String(300), nullable=True)  # For discussions/announcements
    content = Column(Text, nullable=False)  # The feedback text
    original_content = Column(Text, nullable=True)  # Original AI content (preserved if edited)

    # Review workflow
    status = Column(String(20), default=FeedbackQueueStatus.PENDING.value)
    reviewed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Canvas reference after publishing
    canvas_response_id = Column(String(50), nullable=True)  # ID from Canvas after publish

    # Metadata
    generated_by = Column(String(50), default="haiku")  # haiku, manual, system
    generation_context = Column(JSON, nullable=True)  # Context that prompted this feedback

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("Student", foreign_keys=[student_id])
    submission = relationship("Submission", foreign_keys=[submission_id])

    def __repr__(self):
        return f"<FeedbackQueue(id={self.id}, type='{self.feedback_type}', status='{self.status}')>"


def init_db():
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(engine)
    print(f"Database initialized at: {DB_PATH}")


def get_session():
    """Get a new database session."""
    return Session()


if __name__ == "__main__":
    init_db()
