# Deploy student tracker to House of Jawn

Run this task on your Raspberry Pi with Claude Code. Copy this entire file content and paste it as the prompt.

---

## Task for Claude Code

Deploy the STCM140 Student Tracker dashboard to this Pi. The dashboard will be accessible at `class.amditis.tech` via the existing Cloudflare Tunnel.

### Context

- This is the House of Jawn Raspberry Pi 5 (8GB RAM)
- Cloudflare Tunnel `houseofjawn` is already running
- Environment file is at `~/.claude/.env`
- Existing services: shell.amditis.tech, dashboard.amditis.tech, scrapefruit.amditis.tech

### Steps to execute

1. **Clone the repo**
   ```bash
   cd ~/projects
   git clone https://github.com/jamditis/class.git
   cd class
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Check environment variables**

   Verify these exist in `~/.claude/.env`:
   - `CANVAS_API_TOKEN` - Canvas LMS API token
   - `CANVAS_BASE_URL` - Should be `https://montclair.instructure.com`
   - `CANVAS_COURSE_ID` - Should be `216156`
   - `ANTHROPIC_API_KEY` - For Haiku evaluations

   If missing, add them:
   ```bash
   cat >> ~/.claude/.env << 'EOF'
   # Canvas LMS
   CANVAS_API_TOKEN=NEEDS_VALUE
   CANVAS_BASE_URL=https://montclair.instructure.com
   CANVAS_COURSE_ID=216156
   EOF
   ```

   Then prompt me to provide the actual Canvas API token value.

4. **Initialize the database**
   ```bash
   source venv/bin/activate
   python -m student_tracker.cli init
   ```

5. **Install the systemd service**
   ```bash
   sudo cp deployment/student-tracker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable student-tracker
   ```

6. **Add DNS route to Cloudflare Tunnel**
   ```bash
   cloudflared tunnel route dns houseofjawn class.amditis.tech
   ```

7. **Update tunnel config**

   Edit `/etc/cloudflared/config.yml` and add this entry to the ingress section BEFORE the catch-all `http_status:404` rule:

   ```yaml
     - hostname: class.amditis.tech
       service: http://127.0.0.1:5002
   ```

8. **Restart services**
   ```bash
   sudo systemctl restart cloudflared
   sudo systemctl start student-tracker
   ```

9. **Verify deployment**
   ```bash
   # Check service is running
   sudo systemctl status student-tracker

   # Test local connection
   curl -s http://localhost:5002 | head -20

   # Check logs for errors
   journalctl -u student-tracker -n 20
   ```

10. **Sync Canvas data**
    ```bash
    source ~/projects/class/venv/bin/activate
    python -m student_tracker.cli sync
    ```

### Expected result

- Service running on port 5002
- Accessible at https://class.amditis.tech
- Database populated with Canvas course data

### If something fails

- Check logs: `journalctl -u student-tracker -f`
- Test manually: `cd ~/projects/class && source venv/bin/activate && python -m student_tracker.cli dashboard --port 5002`
- Verify tunnel: `cloudflared tunnel info houseofjawn`

---

## After deployment

Set up automatic Canvas sync by adding to crontab (`crontab -e`):

```cron
# Sync Canvas data every 6 hours
0 */6 * * * cd /home/jamditis/projects/class && /home/jamditis/projects/class/venv/bin/python -m student_tracker.cli sync >> /tmp/canvas-sync.log 2>&1
```
