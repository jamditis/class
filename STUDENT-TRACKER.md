# Student tracking and evaluation system

An automated system for tracking student progress, evaluating submissions with Claude Haiku, and generating insights for STCM140.

## Features

- **Automated evaluation**: Claude Haiku evaluates submissions against rubrics
- **Manual input options**: CLI, CSV import, JSON import, dashboard forms
- **Progression tracking**: Track skill development over the semester
- **Student clustering**: Group students by performance patterns
- **AI-powered insights**: Recommendations for students and instructors
- **Web dashboard**: Visual interface for all data and analysis

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
# Required for Haiku evaluation
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Required for Canvas sync (optional)
export CANVAS_API_TOKEN="your-canvas-token"
export CANVAS_COURSE_ID="your-course-id"

# Optional: custom database location
export STUDENT_TRACKER_DB="path/to/database.db"
```

### 3. Initialize the database

```bash
python -m student_tracker.cli init
```

### 4. Start the dashboard

```bash
python -m student_tracker.cli dashboard
```

Open http://localhost:5000 in your browser.

## Command-line interface

### Database and sync

```bash
# Initialize database
python -m student_tracker.cli init

# Sync from Canvas (pulls students, assignments, submissions)
python -m student_tracker.cli sync
```

### Evaluation

```bash
# Evaluate all pending submissions (up to 10)
python -m student_tracker.cli evaluate

# Evaluate more submissions
python -m student_tracker.cli evaluate --limit 50

# Evaluate specific assignment only
python -m student_tracker.cli evaluate --assignment-id 3

# Evaluate a single submission
python -m student_tracker.cli evaluate --submission-id 42

# Re-evaluate (even if already evaluated)
python -m student_tracker.cli evaluate --submission-id 42 --force
```

### Student management

```bash
# List all students
python -m student_tracker.cli student list

# Search students
python -m student_tracker.cli student list --search "john"

# Add a student manually
python -m student_tracker.cli student add --name "John Doe" --email "jdoe@montclair.edu"

# Get student summary
python -m student_tracker.cli student summary --student-id 1

# Generate AI insights for a student
python -m student_tracker.cli student insights --student-id 1

# Generate recommendations for a student
python -m student_tracker.cli student recommendations --student-id 1
```

### Analysis

```bash
# Class overview
python -m student_tracker.cli analyze overview

# Student groups (at-risk, struggling, high performers, etc.)
python -m student_tracker.cli analyze groups

# Generate AI insights for the class
python -m student_tracker.cli analyze insights

# Generate class-wide recommendations
python -m student_tracker.cli analyze recommendations

# Create a progress snapshot (for historical tracking)
python -m student_tracker.cli analyze snapshot
```

### Import and export

```bash
# Export grades to CSV
python -m student_tracker.cli export grades

# Export to specific file
python -m student_tracker.cli export grades -o my_grades.csv

# Export individual student report
python -m student_tracker.cli export student --student-id 1

# Import students from CSV
python -m student_tracker.cli import students students.csv

# Import submissions from CSV
python -m student_tracker.cli import submissions submissions.csv
```

## Data import formats

### Students CSV

```csv
name,email,canvas_id
John Doe,jdoe@montclair.edu,12345
Jane Smith,jsmith@montclair.edu,12346
```

### Submissions CSV

```csv
student_name,assignment_name,content,submitted_at,status
John Doe,Cluetrain Manifesto media analysis,"My analysis text...",2026-01-29T10:00:00,submitted
Jane Smith,Cluetrain Manifesto media analysis,"Jane's analysis...",2026-01-30T15:30:00,late
```

### Assignments JSON

```json
[
  {
    "name": "Research dossier",
    "points_possible": 50,
    "due_date": "2026-02-26T23:59:00",
    "assignment_type": "research",
    "description": "Create a comprehensive research dossier...",
    "skills_assessed": ["research", "analysis", "writing"]
  }
]
```

## Python API

### Direct evaluation

```python
from student_tracker.haiku_evaluator import batch_evaluate_text

texts = [{
    "content": "Student's submission text...",
    "student_name": "John Doe",
    "assignment_name": "Cluetrain analysis",
    "points_possible": 25
}]

results = batch_evaluate_text(texts, assignment_type="written")
print(results)
```

### Manual data entry

```python
from student_tracker.manual_input import (
    add_student,
    add_submission_by_name,
    add_manual_evaluation
)

# Add a student
student = add_student("John Doe", "jdoe@montclair.edu")

# Add a submission
submission = add_submission_by_name(
    "John Doe",
    "Cluetrain analysis",
    "My analysis of thesis #7..."
)

# Add manual evaluation
evaluation = add_manual_evaluation(
    submission_id=submission.id,
    score=22,
    feedback="Good analysis with clear connections.",
    strengths=["Clear thesis connection", "Good examples"],
    areas_for_improvement=["Could explore implications more deeply"]
)
```

### Analysis

```python
from student_tracker.analyzer import (
    get_student_summary,
    get_class_overview,
    identify_student_groups,
    generate_student_insights
)

# Get student summary
summary = get_student_summary(student_id=1)
print(f"Overall: {summary['metrics']['overall_percentage']:.1f}%")

# Get class overview
overview = get_class_overview()
print(f"Class average: {overview['summary']['class_average']:.1f}%")

# Identify student groups
groups = identify_student_groups()
print(f"At risk: {len(groups['at_risk'])} students")

# Generate AI insights
insights = generate_student_insights(student_id=1)
print(insights['overall_assessment'])
```

### Recommendations

```python
from student_tracker.recommendations import (
    get_skill_recommendations,
    generate_student_recommendations,
    generate_class_recommendations
)

# Get skill-specific recommendations
recs = get_skill_recommendations("writing", "developing")
for r in recs:
    print(f"- {r}")

# Generate full recommendations for a student
student_recs = generate_student_recommendations(student_id=1)
print(student_recs['ai_recommendations'])

# Generate class-wide recommendations
class_recs = generate_class_recommendations()
print(class_recs['class_recommendations'])
```

## Dashboard

The web dashboard provides:

- **Class overview**: Stats, grade distribution, student groups
- **Student profiles**: Individual performance, skills, progression charts
- **Assignment view**: Submission rates, averages, common issues
- **Evaluation interface**: Run batch evaluations, add manual grades
- **Insights page**: AI-generated class insights, progress snapshots
- **Settings**: Canvas sync, data import/export

Start the dashboard:

```bash
python -m student_tracker.cli dashboard --port 5000
```

Or run directly:

```python
from student_tracker.dashboard import run_dashboard
run_dashboard(host="0.0.0.0", port=5000, debug=True)
```

## Rubric system

The system includes default rubrics for different assignment types:

- **written**: Clarity, content depth, mechanics, task completion
- **visual**: Visual hierarchy, design principles, color/typography, creativity
- **research**: Research quality, analysis, organization, strategic implications
- **strategy**: Strategic thinking, audience understanding, practicality, measurement

### Custom rubrics

You can set custom rubrics for assignments:

```python
from student_tracker.haiku_evaluator import set_assignment_rubric

custom_rubric = {
    "criteria": [
        {
            "name": "Thesis connection",
            "description": "Clear connection to specific Cluetrain theses",
            "weight": 40,
            "levels": {
                "advanced": "Multiple theses connected with nuanced analysis",
                "proficient": "Clear connection to relevant thesis",
                "developing": "Connection present but surface-level",
                "emerging": "Weak or missing connection"
            }
        },
        # ... more criteria
    ],
    "skills_assessed": ["critical_thinking", "writing"]
}

set_assignment_rubric(assignment_id=1, rubric=custom_rubric)
```

## Student groups

The system automatically categorizes students:

| Group | Criteria |
|-------|----------|
| High performers | Consistently scoring 90%+ |
| Solid performers | Consistently scoring 80-90% |
| Improving | Showing upward trend (10%+ improvement) |
| Inconsistent | High variance in scores |
| Struggling | Consistently below 70% |
| At risk | Missing submissions or declining trend |

## Skills tracked

Default skills assessed by the system:

- Writing
- Design
- Research
- Strategy
- Critical thinking
- Visual communication
- Creativity
- Planning
- Audience analysis

Each skill is rated: emerging → developing → proficient → advanced

## Architecture

```
student_tracker/
├── __init__.py           # Package init
├── models.py             # SQLAlchemy models and database
├── canvas_fetcher.py     # Canvas API integration
├── haiku_evaluator.py    # Claude Haiku evaluation engine
├── manual_input.py       # Manual data entry functions
├── analyzer.py           # Analysis and progression tracking
├── recommendations.py    # Recommendation engine
├── dashboard.py          # Flask web dashboard
└── cli.py                # Command-line interface
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for evaluation) | Anthropic API key for Claude Haiku |
| `CANVAS_API_TOKEN` | No | Canvas LMS API token |
| `CANVAS_COURSE_ID` | No | Canvas course ID |
| `CANVAS_BASE_URL` | No | Canvas instance URL (default: montclair.instructure.com) |
| `STUDENT_TRACKER_DB` | No | Database file path (default: student_tracker.db) |
| `FLASK_SECRET_KEY` | No | Flask session secret key |

## Deployment options

### Local development

```bash
python -m student_tracker.cli dashboard --debug
```

### Production with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "student_tracker.dashboard:app"
```

### Cloudflare Tunnel (with Tailscale)

1. Install cloudflared on your machine
2. Run the dashboard locally
3. Create a tunnel: `cloudflared tunnel --url http://localhost:5000`

### Firebase (future enhancement)

The SQLite database can be replaced with Firestore for cloud sync:

1. Replace SQLAlchemy models with Firestore collections
2. Update the session management in each module
3. Deploy dashboard to Firebase Functions or Cloud Run

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

Set your API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Canvas sync failed"

1. Check CANVAS_API_TOKEN is set and valid
2. Check CANVAS_COURSE_ID is correct
3. Verify you have access to the course

### "No submissions to evaluate"

1. Run `sync` to pull submissions from Canvas
2. Or import submissions manually via CSV
3. Check that submissions have content (not just status)

### Dashboard not loading

1. Check port is not in use: `lsof -i :5000`
2. Try a different port: `--port 8080`
3. Check Flask errors in terminal output
