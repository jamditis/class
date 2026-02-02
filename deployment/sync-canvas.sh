#!/bin/bash
# Sync Canvas data - run via cron
# Add to crontab: 0 */6 * * * /home/pi/class/deployment/sync-canvas.sh

cd /home/pi/class
source venv/bin/activate

# Sync from Canvas
python -m student_tracker.cli sync

# Optional: Run evaluations on new submissions
# python -m student_tracker.cli evaluate --limit 10

echo "$(date): Canvas sync completed" >> /home/pi/class/logs/sync.log
