#!/bin/bash
# Sync Canvas data - run via cron
# Add to crontab: 0 */6 * * * ~/bin/sync-canvas.sh

set -e

PROJECT_DIR="/home/jamditis/projects/class"
LOG_FILE="/tmp/canvas-sync.log"

cd "$PROJECT_DIR"
source venv/bin/activate

# Load environment
export $(grep -v '^#' /home/jamditis/.claude/.env | xargs)

# Sync from Canvas
python -m student_tracker.cli sync

# Optional: Run evaluations on new submissions
# python -m student_tracker.cli evaluate --limit 10

echo "$(date): Canvas sync completed" >> "$LOG_FILE"
