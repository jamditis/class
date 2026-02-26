"""
Flask dashboard for the student tracking system.

Provides:
- Class overview with visualizations
- Individual student profiles
- Assignment drill-down
- Manual evaluation interface
- Settings and configuration
"""

import os
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from .models import (
    get_session, init_db, Student, Assignment, Submission,
    Evaluation, StudentNote, SkillAssessment
)
from .analyzer import (
    get_student_summary, get_student_progression,
    get_student_strengths_weaknesses, get_class_overview,
    identify_student_groups, generate_student_insights,
    generate_class_insights, create_progress_snapshot,
    get_progress_history
)
from .evaluator import evaluate_submission, evaluate_all_pending
from .canvas_fetcher import full_sync as canvas_full_sync
from .manual_input import (
    add_student, add_manual_evaluation, add_student_note,
    confirm_haiku_evaluation
)
from .feedback_queue import (
    get_pending_feedback, get_feedback_by_id, get_feedback_stats,
    update_feedback_content, approve_feedback, reject_feedback,
    publish_feedback, publish_all_approved, queue_submission_feedback,
    generate_submission_feedback_for_queue
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "student-tracker-dev-key")

# ============================================================================
# HTML Templates
# ============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Student Tracker{% endblock %} | STCM140</title>

    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">

    <!-- Fonts (matching GitHub Pages) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,300;1,9..144,900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        display: ['Fraunces', 'serif'],
                        sans: ['Plus Jakarta Sans', 'sans-serif'],
                    },
                    colors: {
                        canvas: '#ede6d4',
                        ink: '#121212',
                        clay: '#d6cdb7',
                        mist: '#6b6b6b',
                        accent: '#3d4b40',
                        crimson: '#CA3553',
                    }
                }
            }
        }
    </script>

    <style>
        body {
            background-color: #ede6d4;
            color: #121212;
            font-family: 'Plus Jakarta Sans', sans-serif;
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }
        .paper-overlay {
            position: fixed;
            inset: 0;
            background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png");
            opacity: 0.4;
            pointer-events: none;
            z-index: 1;
        }
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: -4px;
            left: 0;
            width: 0;
            height: 1px;
            background: #121212;
            transition: width 0.3s ease;
        }
        .nav-link:hover::after { width: 100%; }
        .nav-link.active::after { width: 100%; background: #CA3553; }
        .deckle-card {
            background-color: rgba(255, 255, 255, 0.35);
            border: 1px solid rgba(18, 18, 18, 0.06);
            box-shadow: 0 8px 30px -8px rgba(18, 18, 18, 0.08);
        }
        .stat-card {
            background-color: rgba(255, 255, 255, 0.4);
            border: 1px solid rgba(18, 18, 18, 0.05);
        }
        h1, h2 { font-family: 'Fraunces', serif; }
        h1 { font-weight: 300; font-style: italic; }
        h2 { font-weight: 400; border-bottom: 1px solid rgba(18, 18, 18, 0.1); padding-bottom: 0.5rem; }
        h3 { font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.75rem; color: #6b6b6b; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th { text-align: left; font-weight: 600; padding: 0.75rem 1rem; background: rgba(18, 18, 18, 0.03);
             border-bottom: 2px solid rgba(18, 18, 18, 0.1); font-size: 0.65rem; text-transform: uppercase;
             letter-spacing: 0.1em; color: #6b6b6b; }
        td { padding: 0.75rem 1rem; border-bottom: 1px solid rgba(18, 18, 18, 0.05); }
        tr:hover td { background: rgba(255, 255, 255, 0.4); }
        a { color: #3d4b40; transition: color 0.2s; }
        a:hover { color: #CA3553; }
        .badge { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
                 padding: 0.25rem 0.5rem; border-radius: 9999px; }
        .badge-risk { background: rgba(202, 53, 83, 0.15); color: #CA3553; }
        .badge-warn { background: rgba(217, 164, 6, 0.15); color: #b8860b; }
        .badge-good { background: rgba(61, 75, 64, 0.15); color: #3d4b40; }
        .badge-neutral { background: rgba(18, 18, 18, 0.08); color: #6b6b6b; }
    </style>
</head>
<body class="font-sans min-h-screen">
    <div class="paper-overlay"></div>

    <div class="relative z-10">
        <!-- Navigation -->
        <nav class="fixed top-0 w-full flex justify-between items-center p-6 md:px-10 z-50 bg-canvas/90 backdrop-blur-md border-b border-ink/5">
            <div class="flex items-center gap-4">
                <a href="/" class="font-display text-2xl font-black italic tracking-tighter hover:text-crimson transition-colors">
                    STCM<span class="text-crimson">140</span>
                </a>
                <span class="text-[9px] tracking-[0.3em] font-bold opacity-30 uppercase hidden md:block">Tracker</span>
            </div>
            <div class="flex gap-8 text-[10px] font-bold uppercase tracking-widest text-ink items-center">
                <a href="/" class="nav-link relative">Dashboard</a>
                <a href="/students" class="nav-link relative">Students</a>
                <a href="/assignments" class="nav-link relative">Assignments</a>
                <a href="/evaluate" class="nav-link relative">Evaluate</a>
                <a href="/feedback" class="nav-link relative">Feedback</a>
                <a href="/insights" class="nav-link relative">Insights</a>
                <a href="/settings" class="nav-link relative">Settings</a>
            </div>
        </nav>

        <!-- Main Content -->
        <main class="max-w-5xl mx-auto pt-28 pb-20 px-6 md:px-8">
            {% block content %}{% endblock %}
        </main>

        <!-- Footer -->
        <footer class="bg-ink text-canvas py-12 relative z-10">
            <div class="max-w-5xl mx-auto px-6 md:px-8">
                <div class="flex justify-between items-center">
                    <div>
                        <span class="font-display text-xl italic font-light">Student</span>
                        <span class="font-display text-xl font-black"> Tracker</span>
                        <p class="text-xs text-canvas/40 mt-1">STCM140 | Spring 2026</p>
                    </div>
                    <div class="text-right text-xs text-canvas/40">
                        <a href="https://jamditis.github.io/class/" class="hover:text-crimson transition-colors">Course site</a>
                        <span class="mx-2">·</span>
                        <a href="https://montclair.instructure.com" class="hover:text-crimson transition-colors">Canvas</a>
                    </div>
                </div>
            </div>
        </footer>
    </div>

    <script>
        {% block scripts %}{% endblock %}
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<div class="mb-10">
    <h1 class="text-4xl mb-2">Class overview</h1>
    <p class="text-mist text-sm tracking-wide">STCM140 · Spring 2026</p>
</div>

<!-- Stats Cards -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Students</h3>
        <div class="text-3xl font-display font-black text-ink">{{ overview.summary.total_students }}</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Class average</h3>
        <div class="text-3xl font-display font-black text-accent">{{ "%.1f"|format(overview.summary.class_average) }}%</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Assignments</h3>
        <div class="text-3xl font-display font-black text-ink">{{ overview.summary.total_assignments }}</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Evaluated</h3>
        <div class="text-3xl font-display font-black text-accent">{{ overview.summary.total_evaluated_submissions }}</div>
    </div>
</div>

<!-- Charts Row -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Grade distribution</h2>
        <canvas id="gradeDistChart"></canvas>
    </div>
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Student groups</h2>
        <canvas id="groupsChart"></canvas>
    </div>
</div>

<!-- Assignment Performance -->
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-6">Assignment averages</h2>
    <div class="space-y-4">
        {% for name, avg in overview.assignment_averages.items() %}
        <div class="flex items-center gap-4">
            <div class="w-48 text-sm text-mist truncate">{{ name }}</div>
            <div class="flex-1 bg-clay/50 rounded-full h-3">
                <div class="bg-accent h-3 rounded-full transition-all" style="width: {{ avg }}%"></div>
            </div>
            <div class="w-16 text-right text-sm font-semibold text-ink">{{ "%.1f"|format(avg) }}%</div>
        </div>
        {% endfor %}
    </div>
</div>

<!-- Student Groups -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="deckle-card rounded-lg p-6 border-l-4 border-crimson">
        <h2 class="text-lg mb-4 text-crimson">At risk <span class="text-sm font-normal">({{ groups.at_risk|length }})</span></h2>
        {% if groups.at_risk %}
        <ul class="space-y-3">
            {% for s in groups.at_risk[:5] %}
            <li class="flex justify-between items-center">
                <a href="/student/{{ s.id }}" class="text-sm hover:text-crimson">{{ s.name }}</a>
                <span class="badge badge-risk">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-mist">No students at risk</p>
        {% endif %}
    </div>
    <div class="deckle-card rounded-lg p-6 border-l-4 border-yellow-600">
        <h2 class="text-lg mb-4 text-yellow-700">Struggling <span class="text-sm font-normal">({{ groups.struggling|length }})</span></h2>
        {% if groups.struggling %}
        <ul class="space-y-3">
            {% for s in groups.struggling[:5] %}
            <li class="flex justify-between items-center">
                <a href="/student/{{ s.id }}" class="text-sm hover:text-crimson">{{ s.name }}</a>
                <span class="badge badge-warn">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-mist">No struggling students</p>
        {% endif %}
    </div>
    <div class="deckle-card rounded-lg p-6 border-l-4 border-accent">
        <h2 class="text-lg mb-4 text-accent">High performers <span class="text-sm font-normal">({{ groups.high_performers|length }})</span></h2>
        {% if groups.high_performers %}
        <ul class="space-y-3">
            {% for s in groups.high_performers[:5] %}
            <li class="flex justify-between items-center">
                <a href="/student/{{ s.id }}" class="text-sm hover:text-crimson">{{ s.name }}</a>
                <span class="badge badge-good">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-mist">No high performers yet</p>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block scripts %}
const gradeData = {{ overview.grade_distribution | tojson }};
const groupsData = {{ groups_counts | tojson }};

new Chart(document.getElementById('gradeDistChart'), {
    type: 'bar',
    data: {
        labels: ['A', 'B', 'C', 'D', 'F'],
        datasets: [{
            data: [gradeData.A, gradeData.B, gradeData.C, gradeData.D, gradeData.F],
            backgroundColor: ['#3d4b40', '#5a6b5e', '#CA3553', '#d6cdb7', '#121212']
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(18,18,18,0.05)' } },
            x: { grid: { display: false } }
        }
    }
});

new Chart(document.getElementById('groupsChart'), {
    type: 'doughnut',
    data: {
        labels: ['High performers', 'Solid', 'Improving', 'Inconsistent', 'Struggling', 'At risk'],
        datasets: [{
            data: [
                groupsData.high_performers,
                groupsData.solid_performers,
                groupsData.improving,
                groupsData.inconsistent,
                groupsData.struggling,
                groupsData.at_risk
            ],
            backgroundColor: ['#3d4b40', '#5a6b5e', '#7a8b7e', '#d6cdb7', '#e8a849', '#CA3553']
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { position: 'right', labels: { font: { family: 'Plus Jakarta Sans', size: 11 } } } }
    }
});
{% endblock %}
"""

STUDENTS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Students{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-8">
    <h1 class="text-4xl">Students</h1>
    <div class="flex gap-3">
        <input type="text" id="search" placeholder="Search students..."
               class="px-4 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
        <button onclick="location.href='/student/add'" class="px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
            Add student
        </button>
    </div>
</div>

<div class="deckle-card rounded-lg overflow-hidden">
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Submissions</th>
                <th>Average</th>
                <th>Status</th>
                <th class="text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for student in students %}
            <tr class="student-row">
                <td>
                    <a href="/student/{{ student.id }}" class="font-medium">{{ student.name }}</a>
                </td>
                <td class="text-mist">{{ student.email or '—' }}</td>
                <td class="text-mist">{{ student.submission_count }}</td>
                <td>
                    <span class="font-semibold {% if student.average >= 90 %}text-accent{% elif student.average >= 70 %}text-ink{% elif student.average > 0 %}text-yellow-700{% else %}text-mist{% endif %}">
                        {% if student.average > 0 %}{{ "%.1f"|format(student.average) }}%{% else %}—{% endif %}
                    </span>
                </td>
                <td>
                    {% if student.status == 'at_risk' %}
                    <span class="badge badge-risk">At risk</span>
                    {% elif student.status == 'struggling' %}
                    <span class="badge badge-warn">Struggling</span>
                    {% elif student.status == 'high_performers' %}
                    <span class="badge badge-good">High performer</span>
                    {% else %}
                    <span class="badge badge-neutral">Active</span>
                    {% endif %}
                </td>
                <td class="text-right">
                    <a href="/student/{{ student.id }}" class="text-sm hover:text-crimson">View →</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}

{% block scripts %}
document.getElementById('search').addEventListener('input', function(e) {
    const term = e.target.value.toLowerCase();
    document.querySelectorAll('.student-row').forEach(row => {
        const name = row.querySelector('td:first-child').textContent.toLowerCase();
        row.style.display = name.includes(term) ? '' : 'none';
    });
});
{% endblock %}
"""

STUDENT_DETAIL_TEMPLATE = """
{% extends "base.html" %}
{% block title %}{{ student.name }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-8">
    <div>
        <a href="/students" class="text-sm text-mist hover:text-crimson mb-3 inline-block">← Back to students</a>
        <h1 class="text-4xl">{{ student.name }}</h1>
        <p class="text-mist mt-1">{{ student.email or 'No email on file' }}</p>
    </div>
    <div class="flex gap-3">
        <button onclick="location.href='/student/{{ student.id }}/note'" class="px-4 py-2 border border-ink/10 rounded-lg hover:bg-white/50 transition text-sm">
            Add note
        </button>
        <button onclick="generateInsights()" class="px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
            Generate insights
        </button>
    </div>
</div>

<!-- Stats -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Overall grade</h3>
        <div class="text-3xl font-display font-black {% if summary.metrics.overall_percentage >= 90 %}text-accent{% elif summary.metrics.overall_percentage >= 70 %}text-ink{% else %}text-crimson{% endif %}">
            {{ "%.1f"|format(summary.metrics.overall_percentage) }}%
        </div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Submissions</h3>
        <div class="text-3xl font-display font-black text-ink">{{ summary.metrics.submissions }}/{{ summary.metrics.total_assignments }}</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">On-time rate</h3>
        <div class="text-3xl font-display font-black text-ink">{{ "%.0f"|format(summary.metrics.on_time_rate) }}%</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Total points</h3>
        <div class="text-3xl font-display font-black text-ink">{{ "%.0f"|format(summary.metrics.total_earned) }}<span class="text-mist font-normal text-lg">/{{ "%.0f"|format(summary.metrics.total_possible) }}</span></div>
    </div>
</div>

<!-- Two columns -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
    <!-- Skills -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-5">Current skill levels</h2>
        {% if summary.current_skills %}
        <div class="space-y-3">
            {% for skill, level in summary.current_skills.items() %}
            <div class="flex items-center justify-between py-2 border-b border-ink/5 last:border-0">
                <span class="text-sm capitalize">{{ skill.replace('_', ' ') }}</span>
                <span class="badge {% if level == 'advanced' %}badge-good{% elif level == 'proficient' %}badge-neutral{% elif level == 'developing' %}badge-warn{% else %}badge-neutral{% endif %}">
                    {{ level|capitalize }}
                </span>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-sm text-mist">No skill assessments yet</p>
        {% endif %}
    </div>

    <!-- Strengths & Improvements -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-5">Patterns</h2>
        <div class="mb-5">
            <h3 class="text-accent mb-3">Recurring strengths</h3>
            {% if strengths.recurring_strengths %}
            <ul class="space-y-2">
                {% for s in strengths.recurring_strengths[:3] %}
                <li class="text-sm pl-4 border-l-2 border-accent/30">{{ s.text|replace('**', '')|replace('*', '') }}</li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="text-sm text-mist">No patterns identified yet</p>
            {% endif %}
        </div>
        <div>
            <h3 class="text-yellow-700 mb-3">Areas for growth</h3>
            {% if strengths.recurring_improvements %}
            <ul class="space-y-2">
                {% for i in strengths.recurring_improvements[:3] %}
                <li class="text-sm pl-4 border-l-2 border-yellow-400/50">{{ i.text|replace('**', '')|replace('*', '') }}</li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="text-sm text-mist">No patterns identified yet</p>
            {% endif %}
        </div>
    </div>
</div>

<!-- Progression Chart -->
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-5">Score progression</h2>
    <canvas id="progressionChart" height="100"></canvas>
</div>

<!-- Submissions Table -->
<div class="deckle-card rounded-lg overflow-hidden mb-10">
    <div class="p-5 border-b border-ink/5">
        <h2 class="text-lg">Submissions</h2>
    </div>
    <table>
        <thead>
            <tr>
                <th>Assignment</th>
                <th>Status</th>
                <th>Score</th>
                <th>Submitted</th>
                <th class="text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for sub in submissions %}
            <tr>
                <td class="font-medium">{{ sub.assignment_name }}</td>
                <td>
                    <span class="badge {% if sub.status == 'submitted' %}badge-good{% elif sub.status == 'late' %}badge-warn{% elif sub.status == 'missing' %}badge-risk{% else %}badge-neutral{% endif %}">
                        {{ sub.status|capitalize }}
                    </span>
                </td>
                <td class="text-mist">
                    {% if sub.canvas_score is not none %}
                    <span class="font-medium text-ink">{{ "%.1f"|format(sub.canvas_score) }}</span>/{{ "%.0f"|format(sub.max_score) }}
                    <span class="text-xs text-mist ml-1">Canvas</span>
                    {% elif sub.score is not none %}
                    {{ "%.1f"|format(sub.score) }}/{{ "%.0f"|format(sub.max_score) }}
                    <span class="text-xs text-mist ml-1">AI</span>
                    {% else %}
                    —
                    {% endif %}
                </td>
                <td class="text-mist">{{ sub.submitted_at or '—' }}</td>
                <td class="text-right">
                    <a href="/submission/{{ sub.id }}" class="text-sm hover:text-crimson">View</a>
                    {% if sub.status != 'pending' and sub.score is none %}
                    <a href="/submission/{{ sub.id }}/evaluate" class="text-sm text-accent hover:text-crimson ml-3">Evaluate</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Notes -->
<div class="deckle-card rounded-lg p-6">
    <h2 class="text-lg mb-5">Instructor notes</h2>
    {% if notes %}
    <div class="space-y-4">
        {% for note in notes %}
        <div class="p-4 bg-white/30 rounded-lg">
            <div class="flex justify-between items-start mb-3">
                <span class="badge badge-neutral">{{ note.type }}</span>
                <span class="text-xs text-mist">{{ note.created_at }}</span>
            </div>
            <p class="text-sm leading-relaxed">{{ note.content|replace('**', '')|replace('*', '') }}</p>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-sm text-mist">No notes yet</p>
    {% endif %}
</div>

<!-- Insights Modal -->
<div id="insightsModal" class="fixed inset-0 bg-ink/60 hidden items-center justify-center z-50 backdrop-blur-sm">
    <div class="bg-canvas rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="p-6">
            <div class="flex justify-between items-start mb-6">
                <h2 class="text-2xl">AI insights</h2>
                <button onclick="closeInsights()" class="text-mist hover:text-crimson text-2xl leading-none">×</button>
            </div>
            <div id="insightsContent" class="space-y-5">
                <p class="text-mist">Loading...</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
const progressionData = {{ progression | tojson }};

if (progressionData.timeline && progressionData.timeline.length > 0) {
    new Chart(document.getElementById('progressionChart'), {
        type: 'line',
        data: {
            labels: progressionData.timeline.map(t => t.assignment.substring(0, 20)),
            datasets: [{
                label: 'Score %',
                data: progressionData.timeline.map(t => t.percentage),
                borderColor: '#3d4b40',
                backgroundColor: 'rgba(61, 75, 64, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: 'rgba(18,18,18,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function generateInsights() {
    document.getElementById('insightsModal').classList.remove('hidden');
    document.getElementById('insightsModal').classList.add('flex');

    fetch('/api/student/{{ student.id }}/insights')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('insightsContent');
            container.replaceChildren(); // Clear safely

            if (data.error) {
                const errorP = document.createElement('p');
                errorP.className = 'text-crimson';
                errorP.textContent = data.error;
                container.appendChild(errorP);
                return;
            }

            // Overall assessment
            const assessDiv = document.createElement('div');
            assessDiv.className = 'p-4 bg-accent/10 rounded-lg border-l-4 border-accent';
            const assessH = document.createElement('h3');
            assessH.className = 'font-semibold text-accent mb-2 text-sm uppercase tracking-wide';
            assessH.textContent = 'Overall assessment';
            const assessP = document.createElement('p');
            assessP.className = 'text-sm leading-relaxed';
            assessP.textContent = data.overall_assessment;
            assessDiv.appendChild(assessH);
            assessDiv.appendChild(assessP);
            container.appendChild(assessDiv);

            // Recommendations
            const recDiv = document.createElement('div');
            const recH = document.createElement('h3');
            recH.className = 'font-semibold mb-3 text-sm uppercase tracking-wide text-mist';
            recH.textContent = 'Recommendations';
            recDiv.appendChild(recH);
            const recUl = document.createElement('ul');
            recUl.className = 'space-y-2';
            data.recommendations.forEach(r => {
                const li = document.createElement('li');
                li.className = 'text-sm pl-4 border-l-2 border-ink/10';
                li.textContent = r;
                recUl.appendChild(li);
            });
            recDiv.appendChild(recUl);
            container.appendChild(recDiv);

            // Teaching strategies
            const stratDiv = document.createElement('div');
            const stratH = document.createElement('h3');
            stratH.className = 'font-semibold mb-3 text-sm uppercase tracking-wide text-mist';
            stratH.textContent = 'Teaching strategies';
            stratDiv.appendChild(stratH);
            const stratUl = document.createElement('ul');
            stratUl.className = 'space-y-2';
            data.teaching_strategies.forEach(s => {
                const li = document.createElement('li');
                li.className = 'text-sm pl-4 border-l-2 border-ink/10';
                li.textContent = s;
                stratUl.appendChild(li);
            });
            stratDiv.appendChild(stratUl);
            container.appendChild(stratDiv);

            // Concerns (if any)
            if (data.concerns && data.concerns.length > 0) {
                const conDiv = document.createElement('div');
                conDiv.className = 'p-4 bg-crimson/10 rounded-lg border-l-4 border-crimson';
                const conH = document.createElement('h3');
                conH.className = 'font-semibold text-crimson mb-2 text-sm uppercase tracking-wide';
                conH.textContent = 'Concerns';
                conDiv.appendChild(conH);
                const conUl = document.createElement('ul');
                conUl.className = 'space-y-2';
                data.concerns.forEach(c => {
                    const li = document.createElement('li');
                    li.className = 'text-sm';
                    li.textContent = c;
                    conUl.appendChild(li);
                });
                conDiv.appendChild(conUl);
                container.appendChild(conDiv);
            }
        });
}

function closeInsights() {
    document.getElementById('insightsModal').classList.add('hidden');
    document.getElementById('insightsModal').classList.remove('flex');
}
{% endblock %}
"""

ASSIGNMENTS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Assignments{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-8">
    <h1 class="text-4xl">Assignments</h1>
    <button onclick="location.href='/assignment/add'" class="px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
        Add assignment
    </button>
</div>

<div class="deckle-card rounded-lg overflow-hidden">
    <table>
        <thead>
            <tr>
                <th>Assignment</th>
                <th>Type</th>
                <th>Points</th>
                <th>Due date</th>
                <th>Submissions</th>
                <th>Average</th>
                <th class="text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for a in assignments %}
            <tr>
                <td>
                    <a href="/assignment/{{ a.id }}" class="font-medium">{{ a.name }}</a>
                </td>
                <td class="text-mist capitalize">{{ a.assignment_type or 'General' }}</td>
                <td class="text-mist">{{ a.points_possible }}</td>
                <td class="text-mist">{{ a.due_date or '—' }}</td>
                <td class="text-mist">{{ a.submission_count }}</td>
                <td>
                    <span class="font-semibold {% if a.average >= 80 %}text-accent{% elif a.average >= 60 %}text-yellow-700{% elif a.average > 0 %}text-crimson{% else %}text-mist{% endif %}">
                        {% if a.average > 0 %}{{ "%.1f"|format(a.average) }}%{% else %}—{% endif %}
                    </span>
                </td>
                <td class="text-right">
                    <a href="/assignment/{{ a.id }}" class="text-sm hover:text-crimson">View</a>
                    <a href="/assignment/{{ a.id }}/evaluate-all" class="text-sm text-accent hover:text-crimson ml-3">Evaluate all</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

ASSIGNMENT_DETAIL_TEMPLATE = """
{% extends "base.html" %}
{% block title %}{{ assignment.name }}{% endblock %}
{% block content %}
<div class="mb-8">
    <a href="/assignments" class="text-sm text-mist hover:text-crimson mb-3 inline-block">← Back to assignments</a>
    <h1 class="text-4xl">{{ assignment.name }}</h1>
    <p class="text-mist mt-1">{{ assignment.assignment_type|capitalize if assignment.assignment_type else 'General' }} · {{ assignment.points_possible }} points{% if assignment.due_date %} · Due {{ assignment.due_date }}{% endif %}</p>
</div>

<!-- Stats -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Submissions</h3>
        <div class="text-3xl font-display font-black text-ink">{{ stats.total_submissions }}</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Evaluated</h3>
        <div class="text-3xl font-display font-black text-accent">{{ stats.evaluated }}</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Average</h3>
        <div class="text-3xl font-display font-black text-ink">{{ "%.1f"|format(stats.average_pct) }}%</div>
    </div>
    <div class="stat-card rounded-lg p-5">
        <h3 class="mb-2">Range</h3>
        <div class="text-xl font-display font-black text-mist">{{ "%.0f"|format(stats.lowest) }}-{{ "%.0f"|format(stats.highest) }}</div>
    </div>
</div>

{% if assignment.description %}
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-4">Description</h2>
    <p class="text-sm text-mist leading-relaxed">{{ assignment.description }}</p>
</div>
{% endif %}

<!-- Submissions Table -->
<div class="deckle-card rounded-lg overflow-hidden">
    <div class="p-5 border-b border-ink/5 flex justify-between items-center">
        <h2 class="text-lg">Submissions</h2>
        <a href="/assignment/{{ assignment.id }}/evaluate-all" class="px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
            Evaluate all pending
        </a>
    </div>
    <table>
        <thead>
            <tr>
                <th>Student</th>
                <th>Status</th>
                <th>Score</th>
                <th>Submitted</th>
                <th class="text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for sub in submissions %}
            <tr>
                <td>
                    <a href="/student/{{ sub.student_id }}" class="font-medium hover:text-crimson">{{ sub.student_name }}</a>
                </td>
                <td>
                    <span class="badge {% if sub.status == 'submitted' %}badge-good{% elif sub.status == 'late' %}badge-warn{% elif sub.status == 'missing' %}badge-risk{% else %}badge-neutral{% endif %}">
                        {{ sub.status|capitalize }}
                    </span>
                </td>
                <td>
                    {% if sub.canvas_score is not none %}
                    {% set canvas_pct = (sub.canvas_score / assignment.points_possible * 100) if assignment.points_possible > 0 else 0 %}
                    <span class="font-semibold {% if canvas_pct >= 80 %}text-accent{% elif canvas_pct >= 60 %}text-yellow-700{% else %}text-crimson{% endif %}">
                        {{ "%.1f"|format(sub.canvas_score) }}/{{ assignment.points_possible }} ({{ "%.0f"|format(canvas_pct) }}%)
                    </span>
                    <span class="text-xs text-mist ml-1">Canvas</span>
                    {% elif sub.score is not none %}
                    <span class="font-semibold {% if sub.percentage >= 80 %}text-accent{% elif sub.percentage >= 60 %}text-yellow-700{% else %}text-crimson{% endif %}">
                        {{ "%.1f"|format(sub.score) }}/{{ assignment.points_possible }} ({{ "%.0f"|format(sub.percentage) }}%)
                    </span>
                    <span class="text-xs text-mist ml-1">AI</span>
                    {% else %}
                    <span class="text-mist">Not evaluated</span>
                    {% endif %}
                </td>
                <td class="text-mist">{{ sub.submitted_at or '—' }}</td>
                <td class="text-right">
                    <a href="/submission/{{ sub.id }}" class="text-sm hover:text-crimson">View →</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

SUBMISSION_DETAIL_TEMPLATE = """
{% extends "base.html" %}
{% block title %}{{ submission.student_name }} - {{ submission.assignment_name }}{% endblock %}
{% block content %}
<div class="mb-8">
    <a href="/assignment/{{ submission.assignment_id }}" class="text-sm text-mist hover:text-crimson mb-3 inline-block">← Back to {{ submission.assignment_name }}</a>
    <h1 class="text-4xl">{{ submission.student_name }}</h1>
    <p class="text-mist mt-1">{{ submission.assignment_name }} · {{ submission.points_possible }} points</p>
</div>

<!-- Canvas grade -->
{% if submission.canvas_score is not none %}
<div class="deckle-card rounded-lg p-4 mb-6 border-l-4 border-blue-400 bg-blue-50/30">
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-xs text-mist mb-1 uppercase tracking-wide">Canvas grade</h3>
            <span class="text-2xl font-bold">{{ "%.1f"|format(submission.canvas_score) }}</span>
            <span class="text-mist">/{{ submission.points_possible }}</span>
            {% if submission.canvas_grade %}
            <span class="ml-3 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-sm font-medium">{{ submission.canvas_grade }}</span>
            {% endif %}
        </div>
        {% set canvas_pct = (submission.canvas_score / submission.points_possible * 100) if submission.points_possible > 0 else 0 %}
        <span class="text-lg font-semibold {% if canvas_pct >= 80 %}text-accent{% elif canvas_pct >= 60 %}text-yellow-700{% else %}text-crimson{% endif %}">
            {{ "%.0f"|format(canvas_pct) }}%
        </span>
    </div>
</div>
{% endif %}

<!-- Stats Row -->
{% if evaluation %}
<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
    <!-- Score Gauge -->
    <div class="deckle-card rounded-lg p-4 text-center">
        <h3 class="text-xs text-mist mb-2 uppercase tracking-wide">AI score</h3>
        <div class="relative w-20 h-20 mx-auto">
            <svg class="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="35" stroke="#d6cdb7" stroke-width="6" fill="none"/>
                <circle cx="40" cy="40" r="35"
                    stroke="{% if evaluation.percentage >= 80 %}#3d4b40{% elif evaluation.percentage >= 60 %}#ca8a04{% else %}#CA3553{% endif %}"
                    stroke-width="6" fill="none"
                    stroke-dasharray="{{ evaluation.percentage * 2.2 }} 220"
                    stroke-linecap="round"/>
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-lg font-bold">{{ "%.0f"|format(evaluation.percentage) }}%</span>
            </div>
        </div>
        <div class="text-sm mt-2 font-medium">{{ "%.1f"|format(evaluation.score) }}/{{ submission.points_possible }}</div>
    </div>

    <!-- AI Likelihood Gauge -->
    <div class="deckle-card rounded-lg p-4 text-center">
        <h3 class="text-xs text-mist mb-2 uppercase tracking-wide">AI likelihood</h3>
        {% set ai_score = evaluation.ai_likelihood.score if evaluation.ai_likelihood else 0 %}
        <div class="relative w-20 h-20 mx-auto">
            <svg class="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="35" stroke="#d6cdb7" stroke-width="6" fill="none"/>
                <circle cx="40" cy="40" r="35"
                    stroke="{% if ai_score <= 20 %}#3d4b40{% elif ai_score <= 50 %}#ca8a04{% else %}#CA3553{% endif %}"
                    stroke-width="6" fill="none"
                    stroke-dasharray="{{ ai_score * 2.2 }} 220"
                    stroke-linecap="round"/>
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-lg font-bold">{{ ai_score }}%</span>
            </div>
        </div>
        <div class="text-sm mt-2 {% if ai_score <= 20 %}text-accent{% elif ai_score <= 50 %}text-yellow-700{% else %}text-crimson{% endif %}">
            {% if ai_score <= 20 %}Human{% elif ai_score <= 50 %}Mixed{% elif ai_score <= 80 %}Likely AI{% else %}AI-generated{% endif %}
        </div>
    </div>

    <!-- Skill Levels Mini -->
    <div class="deckle-card rounded-lg p-4">
        <h3 class="text-xs text-mist mb-3 uppercase tracking-wide">Skills</h3>
        {% if evaluation.skill_ratings %}
        <div class="space-y-2">
            {% for skill, level in evaluation.skill_ratings.items() if not skill.startswith('_') %}
            <div class="flex items-center justify-between text-xs">
                <span class="truncate">{{ skill|replace('_', ' ')|title }}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-medium
                    {% if level == 'advanced' %}bg-accent/20 text-accent
                    {% elif level == 'proficient' %}bg-blue-100 text-blue-700
                    {% elif level == 'developing' %}bg-yellow-100 text-yellow-700
                    {% else %}bg-gray-100 text-gray-600{% endif %}">
                    {{ level[:3]|upper }}
                </span>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-xs text-mist">No skills rated</p>
        {% endif %}
    </div>

    <!-- Meta Info -->
    <div class="deckle-card rounded-lg p-4">
        <h3 class="text-xs text-mist mb-3 uppercase tracking-wide">Details</h3>
        <div class="space-y-2 text-xs">
            <div class="flex justify-between">
                <span class="text-mist">Status</span>
                <span class="badge {% if submission.status == 'submitted' %}badge-good{% elif submission.status == 'late' %}badge-warn{% else %}badge-neutral{% endif %}">
                    {{ submission.status }}
                </span>
            </div>
            <div class="flex justify-between">
                <span class="text-mist">Evaluator</span>
                <span>{{ evaluation.evaluator_type }}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-mist">Submitted</span>
                <span>{{ submission.submitted_at or '—' }}</span>
            </div>
        </div>
    </div>
</div>

<!-- AI Signals (if detected) -->
{% if evaluation.ai_likelihood and evaluation.ai_likelihood.score > 30 %}
<div class="deckle-card rounded-lg p-4 mb-6 border-l-4 border-yellow-500 bg-yellow-50/30">
    <h3 class="text-sm font-medium text-yellow-800 mb-2">AI writing signals detected</h3>
    {% if evaluation.ai_likelihood.signals %}
    <div class="flex flex-wrap gap-2 mb-2">
        {% for signal in evaluation.ai_likelihood.signals[:5] %}
        <span class="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">"{{ signal }}"</span>
        {% endfor %}
    </div>
    {% endif %}
    {% if evaluation.ai_likelihood.note %}
    <p class="text-xs text-yellow-700">{{ evaluation.ai_likelihood.note }}</p>
    {% endif %}
</div>
{% endif %}
{% else %}
<div class="deckle-card rounded-lg p-6 mb-10 border-l-4 border-mist">
    <p class="text-mist">Not yet evaluated</p>
    <a href="/submission/{{ submission.id }}/evaluate" class="inline-block mt-3 px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
        Evaluate now
    </a>
</div>
{% endif %}

<!-- Feedback -->
{% if evaluation and evaluation.feedback %}
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-4">Feedback</h2>
    <p class="text-sm leading-relaxed">{{ evaluation.feedback }}</p>
</div>
{% endif %}

<!-- Canvas comments -->
{% if submission.canvas_comments %}
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-4">Canvas comments</h2>
    <div class="space-y-4">
        {% for comment in submission.canvas_comments %}
        <div class="p-4 bg-blue-50/30 rounded-lg border-l-2 border-blue-300">
            <div class="flex justify-between items-start mb-2">
                <span class="text-sm font-medium">{{ comment.author_name }}</span>
                <span class="text-xs text-mist">{{ comment.created_at[:10] if comment.created_at else '' }}</span>
            </div>
            <p class="text-sm leading-relaxed">{{ comment.comment }}</p>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}

<!-- Strengths & Areas for Improvement -->
{% if evaluation %}
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4 text-accent">Strengths</h2>
        {% if evaluation.strengths %}
        <ul class="space-y-2">
            {% for s in evaluation.strengths %}
            <li class="text-sm pl-4 border-l-2 border-accent/30">{{ s }}</li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-mist">No strengths recorded</p>
        {% endif %}
    </div>
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4 text-yellow-700">Areas for improvement</h2>
        {% if evaluation.areas_for_improvement %}
        <ul class="space-y-2">
            {% for i in evaluation.areas_for_improvement %}
            <li class="text-sm pl-4 border-l-2 border-yellow-400/50">{{ i }}</li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-mist">No areas recorded</p>
        {% endif %}
    </div>
</div>
{% endif %}

<!-- Submission Content -->
<div class="deckle-card rounded-lg p-6 mb-10">
    <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg">Submission content</h2>
        <span class="badge {% if submission.status == 'submitted' %}badge-good{% elif submission.status == 'late' %}badge-warn{% else %}badge-neutral{% endif %}">
            {{ submission.status|capitalize }}{% if submission.submitted_at %} · {{ submission.submitted_at }}{% endif %}
        </span>
    </div>
    <div class="prose prose-sm max-w-none bg-white/30 rounded-lg p-4">
        {{ submission.content|safe if submission.content else '<p class="text-mist">No content</p>' }}
    </div>
</div>

<!-- Re-evaluate with Notes -->
<div class="deckle-card rounded-lg p-6 mb-10">
    <h2 class="text-lg mb-4">Re-evaluate</h2>
    <form action="/api/submission/{{ submission.id }}/evaluate" method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium mb-2">Additional context (optional)</label>
            <textarea name="context_notes" rows="3" placeholder="Add notes to guide the evaluation (e.g., 'Student discussed topic with me in office hours' or 'Focus on visual hierarchy')"
                class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm"></textarea>
            <p class="text-xs text-mist mt-1">These notes will be included in the evaluation prompt</p>
        </div>
        <button type="submit" class="px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
            Re-evaluate submission
        </button>
    </form>
</div>

<!-- Evaluation History -->
{% if eval_history and eval_history|length > 1 %}
<div class="deckle-card rounded-lg p-6">
    <h2 class="text-lg mb-4">Evaluation history</h2>
    <div class="overflow-x-auto">
        <table class="w-full text-sm">
            <thead>
                <tr class="border-b border-ink/10">
                    <th class="text-left py-2 text-mist font-medium">Date</th>
                    <th class="text-left py-2 text-mist font-medium">Score</th>
                    <th class="text-left py-2 text-mist font-medium">AI %</th>
                    <th class="text-left py-2 text-mist font-medium">Model</th>
                    <th class="text-left py-2 text-mist font-medium">Status</th>
                </tr>
            </thead>
            <tbody>
                {% for hist in eval_history %}
                <tr class="border-b border-ink/5 {% if hist.is_final %}bg-accent/5{% endif %}">
                    <td class="py-2">{{ hist.created_at or '—' }}</td>
                    <td class="py-2">
                        <span class="font-medium">{{ "%.1f"|format(hist.score) if hist.score else '—' }}</span>
                        <span class="text-mist text-xs">({{ "%.0f"|format(hist.percentage) }}%)</span>
                    </td>
                    <td class="py-2">
                        {% if hist.ai_score is not none %}
                        <span class="{% if hist.ai_score <= 20 %}text-accent{% elif hist.ai_score <= 50 %}text-yellow-700{% else %}text-crimson{% endif %}">
                            {{ hist.ai_score }}%
                        </span>
                        {% else %}—{% endif %}
                    </td>
                    <td class="py-2 text-xs text-mist">{{ hist.model[:20] if hist.model else '—' }}...</td>
                    <td class="py-2">
                        {% if hist.is_final %}
                        <span class="badge badge-good">Current</span>
                        {% else %}
                        <span class="badge badge-neutral">Archived</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <p class="text-xs text-mist mt-4">Previous evaluations are preserved for comparison. Only the current evaluation is shown to students.</p>
</div>
{% endif %}
{% endblock %}
"""

EVALUATE_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Evaluate{% endblock %}
{% block content %}
<div class="mb-10">
    <h1 class="text-4xl mb-2">Evaluate submissions</h1>
    <p class="text-mist text-sm">Run automated Haiku evaluations or add manual grades</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
    <!-- Automated Evaluation -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Automated evaluation</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Use Claude Haiku to evaluate pending submissions against rubrics.</p>

        <form action="/api/evaluate/batch" method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium mb-2">Assignment (optional)</label>
                <select name="assignment_id" class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
                    <option value="">All assignments</option>
                    {% for a in assignments %}
                    <option value="{{ a.id }}">{{ a.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium mb-2">Limit</label>
                <input type="number" name="limit" value="10" min="1" max="50"
                       class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
                Run evaluation
            </button>
        </form>
    </div>

    <!-- Manual Evaluation -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Manual evaluation</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Add or override grades manually for specific submissions.</p>

        <form action="/api/evaluate/manual" method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium mb-2">Student</label>
                <select name="student_id" id="manual-student" class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm" onchange="loadStudentSubmissions()">
                    <option value="">Select student</option>
                    {% for s in students %}
                    <option value="{{ s.id }}">{{ s.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium mb-2">Submission</label>
                <select name="submission_id" id="manual-submission" class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
                    <option value="">Select student first</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium mb-2">Score</label>
                <input type="number" name="score" step="0.5" min="0"
                       class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm" required>
            </div>
            <div>
                <label class="block text-sm font-medium mb-2">Feedback</label>
                <textarea name="feedback" rows="3"
                          class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm leading-relaxed" required></textarea>
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
                Save evaluation
            </button>
        </form>
    </div>
</div>

<!-- Pending Evaluations -->
<div class="deckle-card rounded-lg overflow-hidden">
    <div class="p-5 border-b border-ink/5">
        <h2 class="text-lg">Pending evaluations <span class="text-mist font-normal">({{ pending|length }})</span></h2>
    </div>
    {% if pending %}
    <table>
        <thead>
            <tr>
                <th>Student</th>
                <th>Assignment</th>
                <th>Submitted</th>
                <th class="text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for p in pending[:20] %}
            <tr>
                <td>{{ p.student_name }}</td>
                <td class="text-mist">{{ p.assignment_name }}</td>
                <td class="text-mist">{{ p.submitted_at or '—' }}</td>
                <td class="text-right">
                    <a href="/submission/{{ p.id }}/evaluate" class="text-sm hover:text-crimson">Evaluate →</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="p-5 text-sm text-mist">No pending evaluations</p>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
function loadStudentSubmissions() {
    const studentId = document.getElementById('manual-student').value;
    const submissionSelect = document.getElementById('manual-submission');

    if (!studentId) {
        submissionSelect.replaceChildren();
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Select student first';
        submissionSelect.appendChild(opt);
        return;
    }

    fetch(`/api/student/${studentId}/submissions`)
        .then(r => r.json())
        .then(data => {
            submissionSelect.replaceChildren();
            const defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = 'Select submission';
            submissionSelect.appendChild(defaultOpt);

            data.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `${s.assignment_name} (${s.status})`;
                submissionSelect.appendChild(opt);
            });
        });
}
{% endblock %}
"""

INSIGHTS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Insights{% endblock %}
{% block content %}
<div class="mb-10">
    <h1 class="text-4xl mb-2">Class insights</h1>
    <p class="text-mist text-sm">AI-powered analysis and recommendations</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Generate new insights</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Analyze current class performance and generate recommendations.</p>
        <button onclick="generateClassInsights()" class="w-full px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
            Generate class insights
        </button>
    </div>

    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Create snapshot</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Save current class state for historical tracking.</p>
        <form action="/api/snapshot" method="POST">
            <button type="submit" class="w-full px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
                Create progress snapshot
            </button>
        </form>
    </div>
</div>

<!-- Insights Display -->
<div id="insightsDisplay" class="deckle-card rounded-lg p-6 mb-10 hidden">
    <h2 class="text-lg mb-5">Latest insights</h2>
    <div id="insightsContent" class="space-y-5"></div>
</div>

<!-- Historical Snapshots -->
<div class="deckle-card rounded-lg overflow-hidden">
    <div class="p-5 border-b border-ink/5">
        <h2 class="text-lg">Progress history</h2>
    </div>
    {% if snapshots %}
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Class average</th>
                <th>Submission rate</th>
                <th>Insights</th>
            </tr>
        </thead>
        <tbody>
            {% for s in snapshots %}
            <tr>
                <td>{{ s.date }}</td>
                <td class="text-mist">{{ "%.1f"|format(s.class_average or 0) }}%</td>
                <td class="text-mist">{{ "%.0f"|format(s.submission_rate or 0) }}%</td>
                <td class="text-mist">{{ (s.insights or [])|length }} insights</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="p-5 text-sm text-mist">No snapshots yet. Create one to start tracking progress over time.</p>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
function generateClassInsights() {
    const display = document.getElementById('insightsDisplay');
    const content = document.getElementById('insightsContent');

    display.classList.remove('hidden');
    content.replaceChildren();
    const loadingP = document.createElement('p');
    loadingP.className = 'text-mist';
    loadingP.textContent = 'Analyzing class data...';
    content.appendChild(loadingP);

    fetch('/api/class/insights')
        .then(r => r.json())
        .then(data => {
            content.replaceChildren();

            if (data.error) {
                const errorP = document.createElement('p');
                errorP.className = 'text-crimson';
                errorP.textContent = data.error;
                content.appendChild(errorP);
                return;
            }

            // Class health
            const healthDiv = document.createElement('div');
            healthDiv.className = 'p-4 bg-accent/10 rounded-lg border-l-4 border-accent';
            const healthH = document.createElement('h3');
            healthH.className = 'font-semibold text-accent mb-2 text-sm uppercase tracking-wide';
            healthH.textContent = 'Class health';
            const healthP = document.createElement('p');
            healthP.className = 'text-sm leading-relaxed';
            healthP.textContent = data.class_health;
            healthDiv.appendChild(healthH);
            healthDiv.appendChild(healthP);
            content.appendChild(healthDiv);

            // Skills needing attention
            const skillsDiv = document.createElement('div');
            const skillsH = document.createElement('h3');
            skillsH.className = 'font-semibold mb-3 text-sm uppercase tracking-wide text-mist';
            skillsH.textContent = 'Skills needing attention';
            skillsDiv.appendChild(skillsH);
            const skillsContainer = document.createElement('div');
            skillsContainer.className = 'flex flex-wrap gap-2';
            data.skills_needing_attention.forEach(s => {
                const span = document.createElement('span');
                span.className = 'badge badge-warn';
                span.textContent = s;
                skillsContainer.appendChild(span);
            });
            skillsDiv.appendChild(skillsContainer);
            content.appendChild(skillsDiv);

            // Group recommendations
            const recDiv = document.createElement('div');
            const recH = document.createElement('h3');
            recH.className = 'font-semibold mb-3 text-sm uppercase tracking-wide text-mist';
            recH.textContent = 'Group recommendations';
            recDiv.appendChild(recH);
            const recContainer = document.createElement('div');
            recContainer.className = 'space-y-2';
            Object.entries(data.group_recommendations).forEach(([group, rec]) => {
                const item = document.createElement('div');
                item.className = 'p-3 bg-white/30 rounded-lg';
                const label = document.createElement('span');
                label.className = 'text-sm font-medium capitalize';
                label.textContent = group + ': ';
                const text = document.createElement('span');
                text.className = 'text-sm text-mist';
                text.textContent = rec;
                item.appendChild(label);
                item.appendChild(text);
                recContainer.appendChild(item);
            });
            recDiv.appendChild(recContainer);
            content.appendChild(recDiv);

            // Suggested interventions
            const intDiv = document.createElement('div');
            const intH = document.createElement('h3');
            intH.className = 'font-semibold mb-3 text-sm uppercase tracking-wide text-mist';
            intH.textContent = 'Suggested interventions';
            intDiv.appendChild(intH);
            const intUl = document.createElement('ul');
            intUl.className = 'space-y-2';
            data.suggested_interventions.forEach(i => {
                const li = document.createElement('li');
                li.className = 'text-sm pl-4 border-l-2 border-ink/10';
                li.textContent = i;
                intUl.appendChild(li);
            });
            intDiv.appendChild(intUl);
            content.appendChild(intDiv);
        });
}
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="mb-10">
    <h1 class="text-4xl mb-2">Settings</h1>
    <p class="text-mist text-sm">Configure integrations and sync data</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <!-- Canvas Sync -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Canvas integration</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Sync students, assignments, and submissions from Canvas LMS.</p>

        <div class="mb-5 p-3 bg-white/30 rounded-lg">
            <div class="text-sm">
                <span class="font-medium">Status:</span>
                {% if canvas_configured %}
                <span class="text-accent font-semibold">Configured</span>
                {% else %}
                <span class="text-crimson font-semibold">Not configured</span>
                {% endif %}
            </div>
        </div>

        <form action="/api/sync/canvas" method="POST">
            <button type="submit" {% if not canvas_configured %}disabled{% endif %}
                    class="w-full px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed">
                Sync from Canvas
            </button>
        </form>
    </div>

    <!-- Database -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Database</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Initialize or reset the database.</p>

        <div class="space-y-3">
            <form action="/api/db/init" method="POST">
                <button type="submit" class="w-full px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
                    Initialize database
                </button>
            </form>

            <a href="/api/export/grades" class="block w-full px-4 py-2 border border-ink/10 rounded-lg text-center hover:bg-white/50 transition text-sm">
                Export grades (CSV)
            </a>
        </div>
    </div>

    <!-- Import -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">Import data</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Import students or submissions from files.</p>

        <form action="/api/import" method="POST" enctype="multipart/form-data" class="space-y-4">
            <div>
                <label class="block text-sm font-medium mb-2">Import type</label>
                <select name="import_type" class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
                    <option value="students_csv">Students (CSV)</option>
                    <option value="submissions_csv">Submissions (CSV)</option>
                    <option value="assignments_json">Assignments (JSON)</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium mb-2">File</label>
                <input type="file" name="file" accept=".csv,.json"
                       class="w-full px-3 py-2 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm">
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
                Import
            </button>
        </form>
    </div>

    <!-- API Keys -->
    <div class="deckle-card rounded-lg p-6">
        <h2 class="text-lg mb-4">API configuration</h2>
        <p class="text-sm text-mist mb-5 leading-relaxed">Required environment variables:</p>

        <div class="space-y-3 text-sm">
            <div class="flex items-center gap-3 py-2 border-b border-ink/5">
                {% if anthropic_configured %}
                <span class="w-2 h-2 bg-accent rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-crimson rounded-full"></span>
                {% endif %}
                <code class="bg-white/50 px-2 py-1 rounded text-xs">ANTHROPIC_API_KEY</code>
            </div>
            <div class="flex items-center gap-3 py-2 border-b border-ink/5">
                {% if canvas_configured %}
                <span class="w-2 h-2 bg-accent rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-crimson rounded-full"></span>
                {% endif %}
                <code class="bg-white/50 px-2 py-1 rounded text-xs">CANVAS_API_TOKEN</code>
            </div>
            <div class="flex items-center gap-3 py-2">
                {% if canvas_course_configured %}
                <span class="w-2 h-2 bg-accent rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-crimson rounded-full"></span>
                {% endif %}
                <code class="bg-white/50 px-2 py-1 rounded text-xs">CANVAS_COURSE_ID</code>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

FEEDBACK_QUEUE_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Feedback queue{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-10">
    <div>
        <h1 class="text-4xl mb-2">Feedback queue</h1>
        <p class="text-mist text-sm">Review and publish AI-generated feedback to Canvas</p>
    </div>
    <div class="flex gap-3">
        <button onclick="location.reload()" class="px-4 py-2 border border-ink/10 rounded-lg hover:bg-white/50 transition text-sm">
            Refresh
        </button>
        {% if stats.approved > 0 or stats.edited > 0 %}
        <form action="/api/feedback/publish-all" method="POST" class="inline">
            <button type="submit" class="px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
                Publish all approved ({{ stats.approved + stats.edited }})
            </button>
        </form>
        {% endif %}
    </div>
</div>

<!-- Stats -->
<div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
    <div class="stat-card rounded-lg p-4 text-center">
        <div class="text-2xl font-display font-black text-crimson">{{ stats.pending }}</div>
        <h3 class="mt-1">Pending</h3>
    </div>
    <div class="stat-card rounded-lg p-4 text-center">
        <div class="text-2xl font-display font-black text-accent">{{ stats.approved }}</div>
        <h3 class="mt-1">Approved</h3>
    </div>
    <div class="stat-card rounded-lg p-4 text-center">
        <div class="text-2xl font-display font-black text-yellow-700">{{ stats.edited }}</div>
        <h3 class="mt-1">Edited</h3>
    </div>
    <div class="stat-card rounded-lg p-4 text-center">
        <div class="text-2xl font-display font-black text-ink">{{ stats.published }}</div>
        <h3 class="mt-1">Published</h3>
    </div>
    <div class="stat-card rounded-lg p-4 text-center">
        <div class="text-2xl font-display font-black text-mist">{{ stats.rejected }}</div>
        <h3 class="mt-1">Rejected</h3>
    </div>
</div>

<!-- Pending Feedback Items -->
{% if pending %}
<div class="space-y-6">
    {% for item in pending %}
    <div class="deckle-card rounded-lg p-6" id="feedback-{{ item.id }}">
        <div class="flex justify-between items-start mb-4">
            <div>
                {% if item.student_name %}
                <span class="badge badge-neutral">{{ item.type|replace('_', ' ')|title }}</span>
                <h2 class="text-lg mt-2">{{ item.student_name }}</h2>
                {% if item.assignment_name %}
                <p class="text-mist text-sm">{{ item.assignment_name }}</p>
                {% endif %}
                {% else %}
                <span class="badge badge-neutral">{{ item.type|replace('_', ' ')|title }}</span>
                {% if item.title %}
                <h2 class="text-lg mt-2">{{ item.title }}</h2>
                {% endif %}
                {% endif %}
            </div>
            <div class="text-xs text-mist">
                {{ item.created_at[:10] if item.created_at else '' }}
                <span class="ml-2 badge badge-neutral">{{ item.generated_by }}</span>
            </div>
        </div>

        <div class="mb-5">
            <textarea id="content-{{ item.id }}" rows="6"
                class="w-full px-4 py-3 bg-white/50 border border-ink/10 rounded-lg focus:outline-none focus:border-accent text-sm leading-relaxed font-mono">{{ item.content }}</textarea>
        </div>

        <div class="flex justify-end gap-3">
            <button onclick="rejectFeedback({{ item.id }})"
                class="px-4 py-2 text-crimson border border-crimson/30 rounded-lg hover:bg-crimson/10 transition text-sm">
                Reject
            </button>
            <button onclick="saveFeedback({{ item.id }})"
                class="px-4 py-2 border border-ink/10 rounded-lg hover:bg-white/50 transition text-sm">
                Save edits
            </button>
            <button onclick="approveFeedback({{ item.id }})"
                class="px-4 py-2 bg-accent text-canvas rounded-lg hover:bg-accent/90 transition text-sm font-medium">
                Approve
            </button>
            <button onclick="approveAndPublish({{ item.id }})"
                class="px-4 py-2 bg-crimson text-canvas rounded-lg hover:bg-crimson/90 transition text-sm font-medium">
                Approve & publish
            </button>
        </div>
    </div>
    {% endfor %}
</div>
{% else %}
<div class="deckle-card rounded-lg p-10 text-center">
    <p class="text-mist">No pending feedback to review.</p>
    <p class="text-sm text-mist mt-2">Generate feedback from evaluated submissions using the Evaluate page.</p>
</div>
{% endif %}
{% endblock %}

{% block scripts %}
function saveFeedback(id) {
    const content = document.getElementById('content-' + id).value;
    fetch('/api/feedback/' + id + '/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content: content})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast('Saved');
        } else {
            showToast('Error: ' + (data.error || 'Unknown'), true);
        }
    });
}

function approveFeedback(id) {
    fetch('/api/feedback/' + id + '/approve', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('feedback-' + id).style.opacity = '0.5';
                showToast('Approved');
                setTimeout(() => location.reload(), 1000);
            }
        });
}

function rejectFeedback(id) {
    if (!confirm('Reject this feedback?')) return;
    fetch('/api/feedback/' + id + '/reject', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('feedback-' + id).remove();
                showToast('Rejected');
            }
        });
}

function approveAndPublish(id) {
    const content = document.getElementById('content-' + id).value;
    fetch('/api/feedback/' + id + '/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content: content})
    }).then(() => {
        return fetch('/api/feedback/' + id + '/approve', {method: 'POST'});
    }).then(() => {
        return fetch('/api/feedback/' + id + '/publish', {method: 'POST'});
    }).then(r => r.json()).then(data => {
        if (data.error) {
            showToast('Error: ' + data.error, true);
        } else {
            document.getElementById('feedback-' + id).remove();
            showToast('Published to Canvas');
        }
    });
}

function showToast(msg, isError) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg text-sm font-medium z-50 ' +
        (isError ? 'bg-crimson text-canvas' : 'bg-accent text-canvas');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
{% endblock %}
"""


# ============================================================================
# Template rendering helper
# ============================================================================

def render(template_name: str, **kwargs):
    """Render a template with base template."""
    templates = {
        "base.html": BASE_TEMPLATE,
        "dashboard.html": DASHBOARD_TEMPLATE,
        "students.html": STUDENTS_TEMPLATE,
        "feedback_queue.html": FEEDBACK_QUEUE_TEMPLATE,
        "student_detail.html": STUDENT_DETAIL_TEMPLATE,
        "assignments.html": ASSIGNMENTS_TEMPLATE,
        "assignment_detail.html": ASSIGNMENT_DETAIL_TEMPLATE,
        "submission_detail.html": SUBMISSION_DETAIL_TEMPLATE,
        "evaluate.html": EVALUATE_TEMPLATE,
        "insights.html": INSIGHTS_TEMPLATE,
        "settings.html": SETTINGS_TEMPLATE,
    }

    # Create a custom Jinja environment with the base template
    from jinja2 import Environment, BaseLoader, TemplateNotFound

    class DictLoader(BaseLoader):
        def get_source(self, environment, template):
            if template in templates:
                source = templates[template]
                return source, template, lambda: True
            raise TemplateNotFound(template)

    env = Environment(loader=DictLoader())
    template = env.get_template(template_name)
    return template.render(**kwargs)


# ============================================================================
# Routes
# ============================================================================

@app.route("/")
def dashboard():
    overview = get_class_overview()
    groups = identify_student_groups()
    groups_counts = {k: len(v) for k, v in groups.items()}

    return render("dashboard.html",
                  overview=overview,
                  groups=groups,
                  groups_counts=groups_counts)


@app.route("/students")
def students_list():
    session = get_session()
    students_raw = session.query(Student).order_by(Student.name).all()

    students = []
    groups = identify_student_groups()

    # Create lookup for status
    status_lookup = {}
    for group_name, group_students in groups.items():
        for s in group_students:
            status_lookup[s["id"]] = group_name

    for s in students_raw:
        summary = get_student_summary(s.id)
        students.append({
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "submission_count": len(s.submissions),
            "average": summary["metrics"]["overall_percentage"] if "metrics" in summary else 0,
            "status": status_lookup.get(s.id, "active")
        })

    session.close()
    return render("students.html", students=students)


@app.route("/student/<int:student_id>")
def student_detail(student_id: int):
    session = get_session()
    student = session.query(Student).get(student_id)

    if not student:
        session.close()
        return "Student not found", 404

    summary = get_student_summary(student_id)
    progression = get_student_progression(student_id)
    strengths = get_student_strengths_weaknesses(student_id)

    # Get submissions with evaluations
    submissions = []
    for sub in student.submissions:
        final_eval = None
        for e in sub.evaluations:
            if e.is_final:
                final_eval = e
                break

        submissions.append({
            "id": sub.id,
            "assignment_name": sub.assignment.name,
            "status": sub.status,
            "score": final_eval.score if final_eval else None,
            "max_score": sub.assignment.points_possible,
            "canvas_score": sub.canvas_score,
            "canvas_grade": sub.canvas_grade,
            "submitted_at": sub.submitted_at.strftime("%Y-%m-%d") if sub.submitted_at else None
        })

    # Get notes
    notes = [{
        "type": n.note_type,
        "content": n.content,
        "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
    } for n in student.notes]

    student_dict = {"id": student.id, "name": student.name, "email": student.email}
    session.close()

    return render("student_detail.html",
                  student=student_dict,
                  summary=summary,
                  progression=progression,
                  strengths=strengths,
                  submissions=submissions,
                  notes=notes)


@app.route("/assignments")
def assignments_list():
    session = get_session()
    assignments_raw = session.query(Assignment).order_by(Assignment.due_date).all()

    assignments = []
    for a in assignments_raw:
        # Calculate average
        scores = []
        for sub in a.submissions:
            for e in sub.evaluations:
                if e.is_final and e.score is not None:
                    scores.append(e.score / a.points_possible * 100 if a.points_possible > 0 else 0)

        assignments.append({
            "id": a.id,
            "name": a.name,
            "assignment_type": a.assignment_type,
            "points_possible": a.points_possible,
            "due_date": a.due_date.strftime("%Y-%m-%d") if a.due_date else None,
            "submission_count": len(a.submissions),
            "average": sum(scores) / len(scores) if scores else 0
        })

    session.close()
    return render("assignments.html", assignments=assignments)


@app.route("/assignment/<int:assignment_id>")
def assignment_detail(assignment_id: int):
    session = get_session()
    assignment = session.query(Assignment).get(assignment_id)

    if not assignment:
        session.close()
        return "Assignment not found", 404

    # Get all submissions with evaluations
    submissions = []
    for sub in assignment.submissions:
        final_eval = None
        for e in sub.evaluations:
            if e.is_final:
                final_eval = e
                break

        submissions.append({
            "id": sub.id,
            "student_name": sub.student.name,
            "student_id": sub.student.id,
            "status": sub.status,
            "score": final_eval.score if final_eval else None,
            "percentage": (final_eval.score / assignment.points_possible * 100) if final_eval and assignment.points_possible > 0 else None,
            "canvas_score": sub.canvas_score,
            "submitted_at": sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else None,
            "has_evaluation": final_eval is not None
        })

    # Calculate stats
    scores = [s["score"] for s in submissions if s["score"] is not None]
    stats = {
        "total_submissions": len(submissions),
        "evaluated": len(scores),
        "average": sum(scores) / len(scores) if scores else 0,
        "average_pct": (sum(scores) / len(scores) / assignment.points_possible * 100) if scores and assignment.points_possible > 0 else 0,
        "highest": max(scores) if scores else 0,
        "lowest": min(scores) if scores else 0
    }

    assignment_dict = {
        "id": assignment.id,
        "name": assignment.name,
        "description": assignment.description,
        "assignment_type": assignment.assignment_type,
        "points_possible": assignment.points_possible,
        "due_date": assignment.due_date.strftime("%Y-%m-%d") if assignment.due_date else None
    }

    session.close()
    return render("assignment_detail.html", assignment=assignment_dict, submissions=submissions, stats=stats)


@app.route("/assignment/<int:assignment_id>/evaluate-all")
def assignment_evaluate_all(assignment_id: int):
    """Evaluate all pending submissions for an assignment."""
    from .evaluator import evaluate_all_pending

    results = evaluate_all_pending(assignment_id=assignment_id, limit=50)

    # Redirect back to assignment page with flash message
    return redirect(f"/assignment/{assignment_id}?evaluated={len(results)}")


@app.route("/submission/<int:submission_id>/evaluate", methods=["GET"])
def submission_evaluate(submission_id: int):
    """Evaluate a single submission (GET - no context)."""
    from .evaluator import evaluate_submission

    result = evaluate_submission(submission_id, force=True)

    if result:
        return redirect(f"/submission/{submission_id}?evaluated=1")
    else:
        return redirect(f"/submission/{submission_id}?error=evaluation_failed")


@app.route("/api/submission/<int:submission_id>/evaluate", methods=["POST"])
def api_submission_evaluate_with_context(submission_id: int):
    """Evaluate a single submission with optional context notes."""
    from .evaluator import evaluate_submission_with_context

    context_notes = request.form.get("context_notes", "").strip()

    result = evaluate_submission_with_context(submission_id, context_notes=context_notes, force=True)

    if result:
        return redirect(f"/submission/{submission_id}?evaluated=1")
    else:
        return redirect(f"/submission/{submission_id}?error=evaluation_failed")


@app.route("/submission/<int:submission_id>")
def submission_detail(submission_id: int):
    session = get_session()
    submission = session.query(Submission).get(submission_id)

    if not submission:
        session.close()
        return "Submission not found", 404

    # Get the final evaluation
    final_eval = None
    for e in submission.evaluations:
        if e.is_final:
            final_eval = e
            break

    import json
    evaluation = None
    if final_eval:
        # Handle strengths - might be JSON string or already a list
        strengths = final_eval.strengths
        if isinstance(strengths, str):
            try:
                strengths = json.loads(strengths)
            except:
                strengths = [strengths] if strengths else []
        elif not strengths:
            strengths = []

        # Handle areas_for_improvement - might be JSON string or already a list
        improvements = final_eval.areas_for_improvement
        if isinstance(improvements, str):
            try:
                improvements = json.loads(improvements)
            except:
                improvements = [improvements] if improvements else []
        elif not improvements:
            improvements = []

        # Handle skill_ratings and extract AI likelihood
        skill_ratings = final_eval.skill_ratings or {}
        if isinstance(skill_ratings, str):
            try:
                skill_ratings = json.loads(skill_ratings)
            except:
                skill_ratings = {}

        ai_likelihood = skill_ratings.pop("_ai_likelihood", None)

        evaluation = {
            "score": final_eval.score,
            "percentage": (final_eval.score / submission.assignment.points_possible * 100) if submission.assignment.points_possible > 0 else 0,
            "feedback": final_eval.feedback,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "evaluated_at": final_eval.created_at.strftime("%Y-%m-%d %H:%M") if final_eval.created_at else None,
            "evaluator_type": final_eval.source,
            "skill_ratings": skill_ratings,
            "ai_likelihood": ai_likelihood
        }

    submission_dict = {
        "id": submission.id,
        "student_name": submission.student.name,
        "student_id": submission.student.id,
        "assignment_name": submission.assignment.name,
        "assignment_id": submission.assignment.id,
        "points_possible": submission.assignment.points_possible,
        "status": submission.status,
        "content": submission.content,
        "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M") if submission.submitted_at else None,
        "canvas_score": submission.canvas_score,
        "canvas_grade": submission.canvas_grade,
        "canvas_comments": submission.canvas_comments
    }

    # Get evaluation history (all evaluations, not just final)
    eval_history = []
    for e in sorted(submission.evaluations, key=lambda x: x.created_at or datetime.min, reverse=True):
        hist_skill_ratings = e.skill_ratings or {}
        if isinstance(hist_skill_ratings, str):
            try:
                hist_skill_ratings = json.loads(hist_skill_ratings)
            except:
                hist_skill_ratings = {}
        hist_ai = hist_skill_ratings.get("_ai_likelihood", {})

        eval_history.append({
            "id": e.id,
            "score": e.score,
            "percentage": (e.score / submission.assignment.points_possible * 100) if e.score and submission.assignment.points_possible > 0 else 0,
            "feedback": e.feedback[:100] + "..." if e.feedback and len(e.feedback) > 100 else e.feedback,
            "is_final": e.is_final,
            "model": e.haiku_model_version,
            "prompt_version": e.haiku_prompt_version,
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else None,
            "ai_score": hist_ai.get("score") if hist_ai else None
        })

    session.close()
    return render("submission_detail.html", submission=submission_dict, evaluation=evaluation, eval_history=eval_history)


@app.route("/evaluate")
def evaluate_page():
    session = get_session()

    # Get assignments for dropdown
    assignments = [{
        "id": a.id,
        "name": a.name
    } for a in session.query(Assignment).order_by(Assignment.name).all()]

    # Get students for dropdown
    students = [{
        "id": s.id,
        "name": s.name
    } for s in session.query(Student).order_by(Student.name).all()]

    # Get pending evaluations (submissions without final evaluation)
    pending = []
    submissions = session.query(Submission).filter(
        Submission.content.isnot(None),
        Submission.content != ""
    ).all()

    for sub in submissions:
        has_final = any(e.is_final for e in sub.evaluations)
        if not has_final:
            pending.append({
                "id": sub.id,
                "student_name": sub.student.name,
                "assignment_name": sub.assignment.name,
                "submitted_at": sub.submitted_at.strftime("%Y-%m-%d") if sub.submitted_at else None
            })

    session.close()
    return render("evaluate.html",
                  assignments=assignments,
                  students=students,
                  pending=pending)


@app.route("/insights")
def insights_page():
    snapshots = get_progress_history(days=90)
    return render("insights.html", snapshots=snapshots)


@app.route("/settings")
def settings_page():
    return render("settings.html",
                  canvas_configured=bool(os.environ.get("CANVAS_API_TOKEN")),
                  canvas_course_configured=bool(os.environ.get("CANVAS_COURSE_ID")),
                  anthropic_configured=bool(os.environ.get("ANTHROPIC_API_KEY")))


@app.route("/feedback")
def feedback_queue_page():
    """Feedback review queue page."""
    pending = get_pending_feedback(limit=50)
    stats = get_feedback_stats()
    return render("feedback_queue.html", pending=pending, stats=stats)


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/student/<int:student_id>/insights")
def api_student_insights(student_id: int):
    return jsonify(generate_student_insights(student_id))


@app.route("/api/student/<int:student_id>/submissions")
def api_student_submissions(student_id: int):
    session = get_session()
    student = session.query(Student).get(student_id)

    if not student:
        session.close()
        return jsonify([])

    submissions = [{
        "id": sub.id,
        "assignment_name": sub.assignment.name,
        "status": sub.status
    } for sub in student.submissions]

    session.close()
    return jsonify(submissions)


@app.route("/api/class/insights")
def api_class_insights():
    return jsonify(generate_class_insights())


@app.route("/api/evaluate/batch", methods=["POST"])
def api_evaluate_batch():
    assignment_id = request.form.get("assignment_id")
    limit = int(request.form.get("limit", 10))

    assignment_id = int(assignment_id) if assignment_id else None
    evaluations = evaluate_all_pending(assignment_id=assignment_id, limit=limit)

    return redirect(url_for("evaluate_page"))


@app.route("/api/evaluate/manual", methods=["POST"])
def api_evaluate_manual():
    submission_id = int(request.form.get("submission_id"))
    score = float(request.form.get("score"))
    feedback = request.form.get("feedback")

    add_manual_evaluation(submission_id, score, feedback)
    return redirect(url_for("evaluate_page"))


@app.route("/api/snapshot", methods=["POST"])
def api_create_snapshot():
    create_progress_snapshot()
    return redirect(url_for("insights_page"))


@app.route("/api/sync/canvas", methods=["POST"])
def api_sync_canvas():
    canvas_full_sync()
    return redirect(url_for("settings_page"))


@app.route("/api/db/init", methods=["POST"])
def api_init_db():
    init_db()
    return redirect(url_for("settings_page"))


@app.route("/api/export/grades")
def api_export_grades():
    from io import StringIO
    import csv as csv_module
    from flask import Response

    session = get_session()
    students = session.query(Student).order_by(Student.name).all()
    assignments = session.query(Assignment).order_by(Assignment.due_date).all()

    output = StringIO()
    writer = csv_module.writer(output)

    # Header
    header = ["Student Name", "Email"] + [a.name for a in assignments] + ["Total", "Percentage"]
    writer.writerow(header)

    total_possible = sum(a.points_possible for a in assignments)

    for student in students:
        row = [student.name, student.email or ""]
        total_earned = 0

        for assignment in assignments:
            submission = session.query(Submission).filter_by(
                student_id=student.id,
                assignment_id=assignment.id
            ).first()

            if submission:
                evaluation = None
                for e in submission.evaluations:
                    if e.is_final:
                        evaluation = e
                        break

                if evaluation and evaluation.score is not None:
                    row.append(evaluation.score)
                    total_earned += evaluation.score
                else:
                    row.append("")
            else:
                row.append("Missing")

        percentage = (total_earned / total_possible * 100) if total_possible > 0 else 0
        row.extend([total_earned, f"{percentage:.1f}%"])
        writer.writerow(row)

    session.close()

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=grades.csv"}
    )


# ============================================================================
# Feedback Queue API Routes
# ============================================================================

@app.route("/api/feedback/<int:feedback_id>/update", methods=["POST"])
def api_feedback_update(feedback_id: int):
    """Update feedback content (instructor edit)."""
    data = request.get_json() or {}
    content = data.get("content")
    title = data.get("title")

    if not content:
        return jsonify({"error": "Content is required"}), 400

    success = update_feedback_content(feedback_id, content, title)
    return jsonify({"success": success})


@app.route("/api/feedback/<int:feedback_id>/approve", methods=["POST"])
def api_feedback_approve(feedback_id: int):
    """Approve feedback for publishing."""
    success = approve_feedback(feedback_id)
    return jsonify({"success": success})


@app.route("/api/feedback/<int:feedback_id>/reject", methods=["POST"])
def api_feedback_reject(feedback_id: int):
    """Reject feedback."""
    success = reject_feedback(feedback_id)
    return jsonify({"success": success})


@app.route("/api/feedback/<int:feedback_id>/publish", methods=["POST"])
def api_feedback_publish(feedback_id: int):
    """Publish a single feedback item to Canvas."""
    result = publish_feedback(feedback_id)
    return jsonify(result)


@app.route("/api/feedback/publish-all", methods=["POST"])
def api_feedback_publish_all():
    """Publish all approved feedback to Canvas."""
    result = publish_all_approved()
    return redirect(url_for("feedback_queue_page"))


@app.route("/api/feedback/generate/<int:submission_id>", methods=["POST"])
def api_generate_feedback(submission_id: int):
    """Generate feedback for a submission and add to queue."""
    result = generate_submission_feedback_for_queue(submission_id)
    if result:
        return jsonify({"success": True, "feedback_id": result.id})
    return jsonify({"error": "Could not generate feedback"}), 400


@app.route("/api/feedback/generate-batch", methods=["POST"])
def api_generate_feedback_batch():
    """Generate feedback for all evaluated submissions without queued feedback."""
    session = get_session()

    # Find submissions with final evaluations but no pending feedback
    from .models import FeedbackQueue, FeedbackQueueStatus

    submissions_with_evals = session.query(Submission).join(Evaluation).filter(
        Evaluation.is_final == True
    ).all()

    generated = 0
    for sub in submissions_with_evals:
        # Check if feedback already queued
        existing = session.query(FeedbackQueue).filter(
            FeedbackQueue.submission_id == sub.id,
            FeedbackQueue.status.in_([
                FeedbackQueueStatus.PENDING.value,
                FeedbackQueueStatus.APPROVED.value,
                FeedbackQueueStatus.EDITED.value
            ])
        ).first()

        if not existing:
            session.close()
            result = generate_submission_feedback_for_queue(sub.id)
            if result:
                generated += 1
            session = get_session()

    session.close()
    return redirect(url_for("feedback_queue_page"))


def run_dashboard(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the dashboard server."""
    init_db()
    print(f"Starting Student Tracker dashboard at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(debug=True)
