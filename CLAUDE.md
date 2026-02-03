# STCM140 course site

This is the GitHub Pages site and supporting tools for STCM140: Multimedia Production for Strategic Communications at Montclair State University, Spring 2026.

## Critical instructions

**NEVER use or write in Title Case. Always use and write in sentence case.**

You are a strong reasoner and planner. Use these instructions to structure your plans, thoughts, and responses.

Before taking any action (tool calls or responses), you must plan and reason about:

1. **Logical dependencies and constraints:** Analyze the intended action against these factors (resolve conflicts in order of importance):
   - Policy-based rules, mandatory prerequisites, and constraints
   - Order of operations: Ensure taking an action does not prevent a subsequent necessary action
   - The user may request actions in a random order, but you may need to reorder operations to maximize successful completion
   - Other prerequisites (information and/or actions needed)
   - Explicit user constraints or preferences

2. **Risk assessment:** What are the consequences of taking the action? Will the new state cause any future issues?
   - For exploratory tasks (like searches), missing optional parameters is LOW risk. Prefer calling the tool with available information over asking the user.

3. **Abductive reasoning:** At each step, identify the most logical and likely reason for any problem encountered.
   - Look beyond immediate or obvious causes
   - Hypotheses may require additional research and multiple steps to test
   - Prioritize hypotheses based on likelihood, but do not discard less likely ones prematurely

4. **Outcome evaluation:** Does the previous observation require any changes to your plan?
   - If initial hypotheses are disproven, generate new ones based on gathered information

5. **Information availability:** Incorporate all applicable sources:
   - Available tools and their capabilities
   - All policies, rules, checklists, and constraints
   - Previous observations and conversation history
   - Information only available by asking the user

6. **Precision and grounding:** Ensure reasoning is precise and relevant to each exact situation.
   - Verify claims by quoting exact applicable information when referring to them

7. **Completeness:** Ensure all requirements, constraints, options, and preferences are incorporated.
   - Avoid premature conclusions: There may be multiple relevant options
   - Review applicable sources to confirm which are relevant to the current state

8. **Persistence:** Do not give up unless all reasoning is exhausted.
   - On transient errors, retry unless an explicit retry limit has been reached
   - On other errors, change your strategy or arguments, not repeat the same failed call

## Writing guidelines

Avoid slop phrases and AI-generated filler. Delete or replace:

| Avoid | Use instead |
|-------|-------------|
| comprehensive | full, complete, or delete |
| robust | reliable, stable, or delete |
| leveraging | using |
| seamlessly | delete or describe actual integration |
| innovative | describe what's actually new |
| holistic | complete, full, or be specific |

Delete filler phrases: "It's worth noting that...", "In order to..." (use "To..."), "At the end of the day...", "Moving forward...", "In terms of..."

Delete vague intensifiers: very, extremely, incredibly, absolutely, truly, literally, actually, basically, essentially

**Quick test:** Can you delete this word/phrase without losing meaning? Delete it. Is this the simplest way to say this? Simplify.

## Quick links

- **Live site:** https://jamditis.github.io/class/
- **GitHub repo:** https://github.com/jamditis/class
- **NotebookLM:** https://notebooklm.google.com/notebook/ea55c9b0-0600-4010-a642-cc4d74833871
- **Canvas:** https://montclair.instructure.com

## Project structure

```
class/
├── docs/                    # GitHub Pages site (Jekyll)
│   ├── _config.yml          # Jekyll config
│   ├── _layouts/
│   │   └── default.html     # Custom Tailwind layout (amditis-design-library-v2 style)
│   ├── index.md             # Home page
│   ├── schedule.md          # Week-by-week schedule
│   ├── assignments.md       # Assignment descriptions
│   ├── lectures.md          # Recordings and key concepts
│   └── resources.md         # Tools and reference materials
├── student_tracker/         # Student dashboard and AI evaluator
│   ├── dashboard.py         # Flask web dashboard (port 5002)
│   ├── evaluator.py         # Claude Sonnet evaluation engine
│   ├── teaching_context.py  # Course philosophy and AI detection patterns
│   ├── analyzer.py          # Student analytics and skill tracking
│   ├── models.py            # SQLAlchemy models (Student, Submission, Evaluation)
│   ├── canvas_fetcher.py    # Canvas LMS API sync
│   └── cli.py               # Command-line interface
├── fathom_stcm140.py        # Fetch class recordings from Fathom API
├── fathom_webhook_server.py # Webhook server for auto-sync
├── fathom_fetch.py          # Basic Fathom API fetch script
├── canvas_sync.py           # Canvas LMS API integration
└── FATHOM-NOTEBOOKLM-SETUP.md  # Setup guide for Fathom → NotebookLM
```

## Environment variables

These must be set for the Python scripts to work:

```
FATHOM_API_KEY=<your-api-key>
FATHOM_WEBHOOK_SECRET=<your-webhook-secret>
```

## Course schedule (Spring 2026)

- **First class:** January 20, 2026
- **Spring Break:** March 7-15
- **Last class:** April 30, 2026
- **Final project due:** May 4, 2026
- **Schedule:** Tu/Th 10:00-11:25 AM, MRHD-143

## Assignment flow

The course follows a strategy-before-production sequence:

1. **Weeks 1-4:** Foundations (digital literacy, Cluetrain, design principles)
2. **Weeks 5-7:** Research & strategy (dossier, campaign strategy, personas)
3. **Weeks 9-13:** Production (copywriting, visuals, social graphics, branding)
4. **Weeks 14-16:** Integration (final project workshop and presentations)

## Fathom integration

Class recordings are automatically named using NotebookLM convention:
- `🎙️ LECTURE: [title] (DDMMMYY)`

Run `python fathom_stcm140.py` to fetch and export recordings to `fathom_stcm140/` folder.

## Student tracker

**Dashboard:** https://class.amditis.tech (Cloudflare Access protected)
**Service:** `student-tracker` (systemd, port 5002)
**Database:** `student_tracker/students.db` (SQLite)

### Evaluator system

The evaluator uses Claude Sonnet to provide feedback in Joe's voice with teaching context:

| Component | Purpose |
|-----------|---------|
| `evaluator.py` | Main eval engine using claude-sonnet-4-20250514 |
| `teaching_context.py` | Course philosophy, assignment contexts, AI detection |

**Features:**
- Feedback in Joe's voice (brief, direct, warm)
- Assignment-specific context (Cluetrain, research dossier, persona, copywriting)
- AI writing detection with "slop" phrase patterns
- Evaluation history (old evals marked `is_final=False`)
- Re-evaluate with custom instructor notes

### Common tasks

**Sync Canvas data:**
```bash
cd /home/jamditis/projects/class
source venv/bin/activate
python -m student_tracker.cli sync
```

**Evaluate submissions:**
```bash
python -m student_tracker.cli evaluate --assignment "Cluetrain"
```

**Re-evaluate with context:**
Use the dashboard form at `/submission/<id>` or:
```python
from student_tracker.evaluator import evaluate_submission_with_context
evaluate_submission_with_context(submission_id=49, context_notes="Student discussed in office hours", force=True)
```

**Restart service:**
```bash
sudo systemctl restart student-tracker
```

## Design system

The GitHub Pages site uses a custom Jekyll layout based on the amditis-design-library-v2:

- **Fonts:** Fraunces (display), Plus Jakarta Sans (body)
- **Colors:** canvas (#ede6d4), ink (#121212), crimson (#CA3553), accent (#3d4b40)
- **Features:** Paper texture overlay, scroll-triggered nav blur, mobile drawer menu

## Common tasks

### Update the schedule

Edit `docs/schedule.md` and push to GitHub. The site rebuilds automatically.

### Add a new recording

1. Run `python fathom_stcm140.py` to fetch latest recordings
2. Add the recording link to `docs/lectures.md`
3. Commit and push

### Refresh Fathom cache

Delete `fathom_meetings_2026.json` and run the fetch script again.
