"""
Student tracking and evaluation system for STCM140.

This system provides:
- Automated submission fetching from Canvas
- AI-powered evaluation using Claude Haiku
- Manual input interfaces (CLI, file import, dashboard)
- Progression tracking and analysis
- Dashboard with insights and recommendations
"""

import os
from pathlib import Path

# Load .env file if it exists (before any other imports use env vars)
try:
    from dotenv import load_dotenv

    # Look for .env in the class directory (parent of student_tracker)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars

__version__ = "1.0.0"
