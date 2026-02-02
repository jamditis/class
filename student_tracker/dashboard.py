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
from .haiku_evaluator import evaluate_submission, evaluate_all_pending
from .canvas_fetcher import full_sync as canvas_full_sync
from .manual_input import (
    add_student, add_manual_evaluation, add_student_note,
    confirm_haiku_evaluation
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "student-tracker-dev-key")

# ============================================================================
# HTML Templates
# ============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Student Tracker{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="gradient-bg text-white p-4 shadow-lg">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <a href="/" class="text-xl font-bold">STCM140 Student Tracker</a>
            <div class="flex gap-6">
                <a href="/" class="hover:text-blue-200 transition">Dashboard</a>
                <a href="/students" class="hover:text-blue-200 transition">Students</a>
                <a href="/assignments" class="hover:text-blue-200 transition">Assignments</a>
                <a href="/evaluate" class="hover:text-blue-200 transition">Evaluate</a>
                <a href="/insights" class="hover:text-blue-200 transition">Insights</a>
                <a href="/settings" class="hover:text-blue-200 transition">Settings</a>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto p-6">
        {% block content %}{% endblock %}
    </main>
    <script>
        {% block scripts %}{% endblock %}
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Dashboard - Student Tracker{% endblock %}
{% block content %}
<div class="mb-8">
    <h1 class="text-3xl font-bold text-gray-800 mb-2">Class overview</h1>
    <p class="text-gray-600">STCM140 - Spring 2026</p>
</div>

<!-- Stats Cards -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Students</div>
        <div class="text-3xl font-bold text-gray-800">{{ overview.summary.total_students }}</div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Class average</div>
        <div class="text-3xl font-bold text-blue-600">{{ "%.1f"|format(overview.summary.class_average) }}%</div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Assignments</div>
        <div class="text-3xl font-bold text-gray-800">{{ overview.summary.total_assignments }}</div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Evaluated</div>
        <div class="text-3xl font-bold text-green-600">{{ overview.summary.total_evaluated_submissions }}</div>
    </div>
</div>

<!-- Charts Row -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Grade distribution</h3>
        <canvas id="gradeDistChart"></canvas>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Student groups</h3>
        <canvas id="groupsChart"></canvas>
    </div>
</div>

<!-- Assignment Performance -->
<div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 mb-8">
    <h3 class="font-semibold text-gray-800 mb-4">Assignment averages</h3>
    <div class="space-y-3">
        {% for name, avg in overview.assignment_averages.items() %}
        <div class="flex items-center gap-4">
            <div class="w-48 text-sm text-gray-600 truncate">{{ name }}</div>
            <div class="flex-1 bg-gray-200 rounded-full h-4">
                <div class="bg-blue-500 h-4 rounded-full" style="width: {{ avg }}%"></div>
            </div>
            <div class="w-16 text-right text-sm font-medium text-gray-700">{{ "%.1f"|format(avg) }}%</div>
        </div>
        {% endfor %}
    </div>
</div>

<!-- Student Groups -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="bg-red-50 rounded-xl p-6 border border-red-100">
        <h3 class="font-semibold text-red-800 mb-3">At risk ({{ groups.at_risk|length }})</h3>
        {% if groups.at_risk %}
        <ul class="space-y-2">
            {% for s in groups.at_risk[:5] %}
            <li class="text-sm">
                <a href="/student/{{ s.id }}" class="text-red-700 hover:underline">{{ s.name }}</a>
                <span class="text-red-500 text-xs ml-2">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-red-600">No students at risk</p>
        {% endif %}
    </div>
    <div class="bg-yellow-50 rounded-xl p-6 border border-yellow-100">
        <h3 class="font-semibold text-yellow-800 mb-3">Struggling ({{ groups.struggling|length }})</h3>
        {% if groups.struggling %}
        <ul class="space-y-2">
            {% for s in groups.struggling[:5] %}
            <li class="text-sm">
                <a href="/student/{{ s.id }}" class="text-yellow-700 hover:underline">{{ s.name }}</a>
                <span class="text-yellow-500 text-xs ml-2">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-yellow-600">No struggling students</p>
        {% endif %}
    </div>
    <div class="bg-green-50 rounded-xl p-6 border border-green-100">
        <h3 class="font-semibold text-green-800 mb-3">High performers ({{ groups.high_performers|length }})</h3>
        {% if groups.high_performers %}
        <ul class="space-y-2">
            {% for s in groups.high_performers[:5] %}
            <li class="text-sm">
                <a href="/student/{{ s.id }}" class="text-green-700 hover:underline">{{ s.name }}</a>
                <span class="text-green-500 text-xs ml-2">{{ "%.0f"|format(s.average) }}%</span>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-sm text-green-600">No high performers yet</p>
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
            backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#F97316', '#EF4444']
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
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
            backgroundColor: ['#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#F97316', '#EF4444']
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { position: 'right' } }
    }
});
{% endblock %}
"""

STUDENTS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Students - Student Tracker{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold text-gray-800">Students</h1>
    <div class="flex gap-3">
        <input type="text" id="search" placeholder="Search students..."
               class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
        <button onclick="location.href='/student/add'" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            Add student
        </button>
    </div>
</div>

<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Submissions</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Average</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for student in students %}
            <tr class="hover:bg-gray-50 student-row">
                <td class="px-6 py-4 whitespace-nowrap">
                    <a href="/student/{{ student.id }}" class="text-blue-600 hover:underline font-medium">{{ student.name }}</a>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ student.email or '-' }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ student.submission_count }}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-medium {% if student.average >= 90 %}text-green-600{% elif student.average >= 70 %}text-blue-600{% elif student.average > 0 %}text-yellow-600{% else %}text-gray-400{% endif %}">
                        {% if student.average > 0 %}{{ "%.1f"|format(student.average) }}%{% else %}-{% endif %}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    {% if student.status == 'at_risk' %}
                    <span class="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">At risk</span>
                    {% elif student.status == 'struggling' %}
                    <span class="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">Struggling</span>
                    {% elif student.status == 'high' %}
                    <span class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">High performer</span>
                    {% else %}
                    <span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">Active</span>
                    {% endif %}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <a href="/student/{{ student.id }}" class="text-blue-600 hover:underline">View</a>
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
{% block title %}{{ student.name }} - Student Tracker{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-6">
    <div>
        <a href="/students" class="text-blue-600 hover:underline text-sm mb-2 inline-block">&larr; Back to students</a>
        <h1 class="text-3xl font-bold text-gray-800">{{ student.name }}</h1>
        <p class="text-gray-600">{{ student.email or 'No email' }}</p>
    </div>
    <div class="flex gap-3">
        <button onclick="location.href='/student/{{ student.id }}/note'" class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
            Add note
        </button>
        <button onclick="generateInsights()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            Generate insights
        </button>
    </div>
</div>

<!-- Stats -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Overall grade</div>
        <div class="text-3xl font-bold {% if summary.metrics.overall_percentage >= 90 %}text-green-600{% elif summary.metrics.overall_percentage >= 70 %}text-blue-600{% else %}text-yellow-600{% endif %}">
            {{ "%.1f"|format(summary.metrics.overall_percentage) }}%
        </div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Submissions</div>
        <div class="text-3xl font-bold text-gray-800">{{ summary.metrics.submissions }}/{{ summary.metrics.total_assignments }}</div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">On-time rate</div>
        <div class="text-3xl font-bold text-gray-800">{{ "%.0f"|format(summary.metrics.on_time_rate) }}%</div>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <div class="text-sm text-gray-500 mb-1">Total points</div>
        <div class="text-3xl font-bold text-gray-800">{{ "%.0f"|format(summary.metrics.total_earned) }}/{{ "%.0f"|format(summary.metrics.total_possible) }}</div>
    </div>
</div>

<!-- Two columns -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <!-- Skills -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Current skill levels</h3>
        {% if summary.current_skills %}
        <div class="space-y-3">
            {% for skill, level in summary.current_skills.items() %}
            <div class="flex items-center justify-between">
                <span class="text-sm text-gray-600 capitalize">{{ skill.replace('_', ' ') }}</span>
                <span class="px-2 py-1 text-xs rounded-full
                    {% if level == 'advanced' %}bg-green-100 text-green-800
                    {% elif level == 'proficient' %}bg-blue-100 text-blue-800
                    {% elif level == 'developing' %}bg-yellow-100 text-yellow-800
                    {% else %}bg-gray-100 text-gray-800{% endif %}">
                    {{ level|capitalize }}
                </span>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-sm text-gray-500">No skill assessments yet</p>
        {% endif %}
    </div>

    <!-- Strengths & Improvements -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Patterns</h3>
        <div class="mb-4">
            <h4 class="text-sm font-medium text-green-700 mb-2">Recurring strengths</h4>
            {% if strengths.recurring_strengths %}
            <ul class="space-y-1">
                {% for s in strengths.recurring_strengths[:3] %}
                <li class="text-sm text-gray-600">{{ s.text }}</li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="text-sm text-gray-500">No patterns identified yet</p>
            {% endif %}
        </div>
        <div>
            <h4 class="text-sm font-medium text-yellow-700 mb-2">Areas for growth</h4>
            {% if strengths.recurring_improvements %}
            <ul class="space-y-1">
                {% for i in strengths.recurring_improvements[:3] %}
                <li class="text-sm text-gray-600">{{ i.text }}</li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="text-sm text-gray-500">No patterns identified yet</p>
            {% endif %}
        </div>
    </div>
</div>

<!-- Progression Chart -->
<div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 mb-8">
    <h3 class="font-semibold text-gray-800 mb-4">Score progression</h3>
    <canvas id="progressionChart" height="100"></canvas>
</div>

<!-- Submissions Table -->
<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mb-8">
    <h3 class="font-semibold text-gray-800 p-4 border-b border-gray-200">Submissions</h3>
    <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignment</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submitted</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for sub in submissions %}
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm font-medium text-gray-900">{{ sub.assignment_name }}</td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs rounded-full
                        {% if sub.status == 'submitted' %}bg-green-100 text-green-800
                        {% elif sub.status == 'late' %}bg-yellow-100 text-yellow-800
                        {% elif sub.status == 'missing' %}bg-red-100 text-red-800
                        {% else %}bg-gray-100 text-gray-800{% endif %}">
                        {{ sub.status|capitalize }}
                    </span>
                </td>
                <td class="px-6 py-4 text-sm text-gray-500">
                    {% if sub.score is not none %}
                    {{ "%.1f"|format(sub.score) }}/{{ "%.0f"|format(sub.max_score) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ sub.submitted_at or '-' }}</td>
                <td class="px-6 py-4 text-right text-sm">
                    <a href="/submission/{{ sub.id }}" class="text-blue-600 hover:underline">View</a>
                    {% if sub.status != 'pending' and sub.score is none %}
                    <a href="/submission/{{ sub.id }}/evaluate" class="text-green-600 hover:underline ml-3">Evaluate</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Notes -->
<div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
    <h3 class="font-semibold text-gray-800 mb-4">Instructor notes</h3>
    {% if notes %}
    <div class="space-y-4">
        {% for note in notes %}
        <div class="p-4 bg-gray-50 rounded-lg">
            <div class="flex justify-between items-start mb-2">
                <span class="px-2 py-1 text-xs rounded-full bg-gray-200 text-gray-700">{{ note.type }}</span>
                <span class="text-xs text-gray-500">{{ note.created_at }}</span>
            </div>
            <p class="text-sm text-gray-700">{{ note.content }}</p>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-sm text-gray-500">No notes yet</p>
    {% endif %}
</div>

<!-- Insights Modal -->
<div id="insightsModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="p-6">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-xl font-bold text-gray-800">AI insights</h3>
                <button onclick="closeInsights()" class="text-gray-500 hover:text-gray-700">&times;</button>
            </div>
            <div id="insightsContent" class="space-y-4">
                <p class="text-gray-500">Loading...</p>
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
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, max: 100 }
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
            let html = '';
            if (data.error) {
                html = `<p class="text-red-500">${data.error}</p>`;
            } else {
                html = `
                    <div class="p-4 bg-blue-50 rounded-lg">
                        <h4 class="font-medium text-blue-800 mb-2">Overall assessment</h4>
                        <p class="text-sm text-blue-700">${data.overall_assessment}</p>
                    </div>
                    <div>
                        <h4 class="font-medium text-gray-800 mb-2">Recommendations</h4>
                        <ul class="list-disc list-inside space-y-1">
                            ${data.recommendations.map(r => `<li class="text-sm text-gray-600">${r}</li>`).join('')}
                        </ul>
                    </div>
                    <div>
                        <h4 class="font-medium text-gray-800 mb-2">Teaching strategies</h4>
                        <ul class="list-disc list-inside space-y-1">
                            ${data.teaching_strategies.map(s => `<li class="text-sm text-gray-600">${s}</li>`).join('')}
                        </ul>
                    </div>
                    ${data.concerns ? `
                    <div class="p-4 bg-yellow-50 rounded-lg">
                        <h4 class="font-medium text-yellow-800 mb-2">Concerns</h4>
                        <ul class="list-disc list-inside space-y-1">
                            ${data.concerns.map(c => `<li class="text-sm text-yellow-700">${c}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                `;
            }
            document.getElementById('insightsContent').innerHTML = html;
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
{% block title %}Assignments - Student Tracker{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold text-gray-800">Assignments</h1>
    <button onclick="location.href='/assignment/add'" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
        Add assignment
    </button>
</div>

<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignment</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Points</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submissions</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Average</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for a in assignments %}
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4">
                    <a href="/assignment/{{ a.id }}" class="text-blue-600 hover:underline font-medium">{{ a.name }}</a>
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 capitalize">{{ a.assignment_type or 'General' }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ a.points_possible }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ a.due_date or '-' }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ a.submission_count }}</td>
                <td class="px-6 py-4 text-sm font-medium {% if a.average >= 80 %}text-green-600{% elif a.average >= 60 %}text-yellow-600{% elif a.average > 0 %}text-red-600{% else %}text-gray-400{% endif %}">
                    {% if a.average > 0 %}{{ "%.1f"|format(a.average) }}%{% else %}-{% endif %}
                </td>
                <td class="px-6 py-4 text-right text-sm">
                    <a href="/assignment/{{ a.id }}" class="text-blue-600 hover:underline">View</a>
                    <a href="/assignment/{{ a.id }}/evaluate-all" class="text-green-600 hover:underline ml-3">Evaluate all</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

EVALUATE_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Evaluate - Student Tracker{% endblock %}
{% block content %}
<div class="mb-6">
    <h1 class="text-3xl font-bold text-gray-800 mb-2">Evaluate submissions</h1>
    <p class="text-gray-600">Run automated Haiku evaluations or add manual grades</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <!-- Automated Evaluation -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Automated evaluation</h3>
        <p class="text-sm text-gray-600 mb-4">Use Claude Haiku to evaluate pending submissions against rubrics.</p>

        <form action="/api/evaluate/batch" method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Assignment (optional)</label>
                <select name="assignment_id" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="">All assignments</option>
                    {% for a in assignments %}
                    <option value="{{ a.id }}">{{ a.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Limit</label>
                <input type="number" name="limit" value="10" min="1" max="50"
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg">
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                Run evaluation
            </button>
        </form>
    </div>

    <!-- Manual Evaluation -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Manual evaluation</h3>
        <p class="text-sm text-gray-600 mb-4">Add or override grades manually for specific submissions.</p>

        <form action="/api/evaluate/manual" method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Student</label>
                <select name="student_id" id="manual-student" class="w-full px-3 py-2 border border-gray-300 rounded-lg" onchange="loadStudentSubmissions()">
                    <option value="">Select student</option>
                    {% for s in students %}
                    <option value="{{ s.id }}">{{ s.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Submission</label>
                <select name="submission_id" id="manual-submission" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="">Select student first</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Score</label>
                <input type="number" name="score" step="0.5" min="0"
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Feedback</label>
                <textarea name="feedback" rows="3"
                          class="w-full px-3 py-2 border border-gray-300 rounded-lg" required></textarea>
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                Save evaluation
            </button>
        </form>
    </div>
</div>

<!-- Pending Evaluations -->
<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <h3 class="font-semibold text-gray-800 p-4 border-b border-gray-200">Pending evaluations ({{ pending|length }})</h3>
    {% if pending %}
    <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignment</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submitted</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for p in pending[:20] %}
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-900">{{ p.student_name }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ p.assignment_name }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ p.submitted_at or '-' }}</td>
                <td class="px-6 py-4 text-right text-sm">
                    <a href="/submission/{{ p.id }}/evaluate" class="text-blue-600 hover:underline">Evaluate</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="p-4 text-sm text-gray-500">No pending evaluations</p>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
function loadStudentSubmissions() {
    const studentId = document.getElementById('manual-student').value;
    const submissionSelect = document.getElementById('manual-submission');

    if (!studentId) {
        submissionSelect.innerHTML = '<option value="">Select student first</option>';
        return;
    }

    fetch(`/api/student/${studentId}/submissions`)
        .then(r => r.json())
        .then(data => {
            submissionSelect.innerHTML = '<option value="">Select submission</option>' +
                data.map(s => `<option value="${s.id}">${s.assignment_name} (${s.status})</option>`).join('');
        });
}
{% endblock %}
"""

INSIGHTS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Insights - Student Tracker{% endblock %}
{% block content %}
<div class="mb-6">
    <h1 class="text-3xl font-bold text-gray-800 mb-2">Class insights</h1>
    <p class="text-gray-600">AI-powered analysis and recommendations</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Generate new insights</h3>
        <p class="text-sm text-gray-600 mb-4">Analyze current class performance and generate recommendations.</p>
        <button onclick="generateClassInsights()" class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            Generate class insights
        </button>
    </div>

    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Create snapshot</h3>
        <p class="text-sm text-gray-600 mb-4">Save current class state for historical tracking.</p>
        <form action="/api/snapshot" method="POST">
            <button type="submit" class="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                Create progress snapshot
            </button>
        </form>
    </div>
</div>

<!-- Insights Display -->
<div id="insightsDisplay" class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 mb-8 hidden">
    <h3 class="font-semibold text-gray-800 mb-4">Latest insights</h3>
    <div id="insightsContent" class="space-y-4"></div>
</div>

<!-- Historical Snapshots -->
<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <h3 class="font-semibold text-gray-800 p-4 border-b border-gray-200">Progress history</h3>
    {% if snapshots %}
    <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Class average</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submission rate</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Insights</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for s in snapshots %}
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-900">{{ s.date }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ "%.1f"|format(s.class_average or 0) }}%</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ "%.0f"|format(s.submission_rate or 0) }}%</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ (s.insights or [])|length }} insights</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="p-4 text-sm text-gray-500">No snapshots yet. Create one to start tracking progress over time.</p>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
function generateClassInsights() {
    const display = document.getElementById('insightsDisplay');
    const content = document.getElementById('insightsContent');

    display.classList.remove('hidden');
    content.innerHTML = '<p class="text-gray-500">Analyzing class data...</p>';

    fetch('/api/class/insights')
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                content.innerHTML = `<p class="text-red-500">${data.error}</p>`;
                return;
            }

            content.innerHTML = `
                <div class="p-4 bg-blue-50 rounded-lg">
                    <h4 class="font-medium text-blue-800 mb-2">Class health</h4>
                    <p class="text-sm text-blue-700">${data.class_health}</p>
                </div>

                <div>
                    <h4 class="font-medium text-gray-800 mb-2">Skills needing attention</h4>
                    <div class="flex flex-wrap gap-2">
                        ${data.skills_needing_attention.map(s => `<span class="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">${s}</span>`).join('')}
                    </div>
                </div>

                <div>
                    <h4 class="font-medium text-gray-800 mb-2">Group recommendations</h4>
                    <div class="space-y-2">
                        ${Object.entries(data.group_recommendations).map(([group, rec]) => `
                            <div class="p-3 bg-gray-50 rounded-lg">
                                <span class="text-sm font-medium text-gray-700 capitalize">${group}:</span>
                                <span class="text-sm text-gray-600">${rec}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div>
                    <h4 class="font-medium text-gray-800 mb-2">Suggested interventions</h4>
                    <ul class="list-disc list-inside space-y-1">
                        ${data.suggested_interventions.map(i => `<li class="text-sm text-gray-600">${i}</li>`).join('')}
                    </ul>
                </div>
            `;
        });
}
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "base.html" %}
{% block title %}Settings - Student Tracker{% endblock %}
{% block content %}
<div class="mb-6">
    <h1 class="text-3xl font-bold text-gray-800 mb-2">Settings</h1>
    <p class="text-gray-600">Configure integrations and sync data</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <!-- Canvas Sync -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Canvas integration</h3>
        <p class="text-sm text-gray-600 mb-4">Sync students, assignments, and submissions from Canvas LMS.</p>

        <div class="mb-4 p-3 bg-gray-50 rounded-lg">
            <div class="text-sm text-gray-600">
                <strong>Status:</strong>
                {% if canvas_configured %}
                <span class="text-green-600">Configured</span>
                {% else %}
                <span class="text-red-600">Not configured</span>
                {% endif %}
            </div>
        </div>

        <form action="/api/sync/canvas" method="POST">
            <button type="submit" {% if not canvas_configured %}disabled{% endif %}
                    class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
                Sync from Canvas
            </button>
        </form>
    </div>

    <!-- Database -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Database</h3>
        <p class="text-sm text-gray-600 mb-4">Initialize or reset the database.</p>

        <div class="space-y-3">
            <form action="/api/db/init" method="POST">
                <button type="submit" class="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                    Initialize database
                </button>
            </form>

            <a href="/api/export/grades" class="block w-full px-4 py-2 border border-gray-300 rounded-lg text-center hover:bg-gray-50 transition">
                Export grades (CSV)
            </a>
        </div>
    </div>

    <!-- Import -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">Import data</h3>
        <p class="text-sm text-gray-600 mb-4">Import students or submissions from files.</p>

        <form action="/api/import" method="POST" enctype="multipart/form-data" class="space-y-3">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Import type</label>
                <select name="import_type" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="students_csv">Students (CSV)</option>
                    <option value="submissions_csv">Submissions (CSV)</option>
                    <option value="assignments_json">Assignments (JSON)</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">File</label>
                <input type="file" name="file" accept=".csv,.json"
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg">
            </div>
            <button type="submit" class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                Import
            </button>
        </form>
    </div>

    <!-- API Keys -->
    <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 class="font-semibold text-gray-800 mb-4">API configuration</h3>
        <p class="text-sm text-gray-600 mb-4">Required environment variables:</p>

        <div class="space-y-2 text-sm">
            <div class="flex items-center gap-2">
                {% if anthropic_configured %}
                <span class="w-2 h-2 bg-green-500 rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-red-500 rounded-full"></span>
                {% endif %}
                <code class="bg-gray-100 px-2 py-1 rounded">ANTHROPIC_API_KEY</code>
            </div>
            <div class="flex items-center gap-2">
                {% if canvas_configured %}
                <span class="w-2 h-2 bg-green-500 rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-red-500 rounded-full"></span>
                {% endif %}
                <code class="bg-gray-100 px-2 py-1 rounded">CANVAS_API_TOKEN</code>
            </div>
            <div class="flex items-center gap-2">
                {% if canvas_course_configured %}
                <span class="w-2 h-2 bg-green-500 rounded-full"></span>
                {% else %}
                <span class="w-2 h-2 bg-red-500 rounded-full"></span>
                {% endif %}
                <code class="bg-gray-100 px-2 py-1 rounded">CANVAS_COURSE_ID</code>
            </div>
        </div>
    </div>
</div>
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
        "student_detail.html": STUDENT_DETAIL_TEMPLATE,
        "assignments.html": ASSIGNMENTS_TEMPLATE,
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


def run_dashboard(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the dashboard server."""
    init_db()
    print(f"Starting Student Tracker dashboard at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(debug=True)
