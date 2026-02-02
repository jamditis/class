# Raspberry Pi deployment (House of Jawn)

Deploy the Student Tracker dashboard to your Raspberry Pi 5, accessible via Cloudflare Tunnel at `class.amditis.tech`.

This integrates with your existing House of Jawn infrastructure — same tunnel, same env file location, same service patterns.

---

## Quick start

SSH into your Pi and run:

```bash
# Clone the repo
cd ~/projects
git clone https://github.com/jamditis/class.git
cd class

# Run setup script
chmod +x deployment/setup-pi.sh
./deployment/setup-pi.sh
```

---

## Prerequisites

Your House of Jawn Pi should already have:

- [x] Cloudflare Tunnel (`houseofjawn`) running
- [x] Environment file at `~/.claude/.env`
- [x] Python 3 with venv support
- [x] systemd for service management

You'll need to add these vars to `~/.claude/.env`:

```bash
# Canvas LMS
CANVAS_API_TOKEN=your-canvas-token
CANVAS_BASE_URL=https://montclair.instructure.com
CANVAS_COURSE_ID=216156

# Anthropic (for Haiku evaluations)
ANTHROPIC_API_KEY=your-anthropic-key
```

---

## Manual setup

### 1. Clone and install

```bash
cd ~/projects
git clone https://github.com/jamditis/class.git
cd class

# Create venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
python -m student_tracker.cli init
```

### 2. Add env vars

Edit `~/.claude/.env` and add the Canvas/Anthropic keys listed above.

### 3. Install systemd service

```bash
sudo cp deployment/student-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable student-tracker
```

### 4. Configure Cloudflare Tunnel

Add DNS route:

```bash
cloudflared tunnel route dns houseofjawn class.amditis.tech
```

Update `/etc/cloudflared/config.yml` — add this to the ingress section **before** the catch-all:

```yaml
  - hostname: class.amditis.tech
    service: http://127.0.0.1:5002
```

### 5. Start services

```bash
sudo systemctl restart cloudflared
sudo systemctl start student-tracker
```

### 6. Sync Canvas data

```bash
source venv/bin/activate
python -m student_tracker.cli sync
```

---

## Verify deployment

```bash
# Check service status
sudo systemctl status student-tracker

# Test locally
curl http://localhost:5002

# Check logs
journalctl -u student-tracker -f
```

Visit https://class.amditis.tech to access the dashboard.

---

## Updating

```bash
cd ~/projects/class
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart student-tracker
```

---

## Automatic Canvas sync

Add to your crontab (`crontab -e`):

```cron
# Sync Canvas data every 6 hours
0 */6 * * * cd /home/jamditis/projects/class && /home/jamditis/projects/class/venv/bin/python -m student_tracker.cli sync >> /tmp/canvas-sync.log 2>&1
```

Or use the provided script:

```bash
# Copy sync script
cp deployment/sync-canvas.sh ~/bin/
chmod +x ~/bin/sync-canvas.sh

# Add to cron
0 */6 * * * ~/bin/sync-canvas.sh
```

---

## Service architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    House of Jawn Server                          │
│                   Raspberry Pi 5 (8GB RAM)                       │
├─────────────────────────────────────────────────────────────────┤
│  Existing services:                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ shell.amditis   │  │ dashboard       │  │ scrapefruit     │  │
│  │ .tech (:7681)   │  │ .amditis.tech   │  │ .amditis.tech   │  │
│  └─────────────────┘  │ (:9090)         │  │ (:5150)         │  │
│                       └─────────────────┘  └─────────────────┘  │
│                                                                  │
│  NEW:                                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ class.amditis.tech (:5002) - Student Tracker Dashboard      ││
│  │   Flask app → SQLite → Canvas API → Haiku evaluations       ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  Cloudflare Tunnel (houseofjawn) → All services via HTTPS       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Dashboard won't start

```bash
# Check logs
journalctl -u student-tracker -n 50

# Test manually
cd ~/projects/class
source venv/bin/activate
python -m student_tracker.cli dashboard --port 5002
```

### Tunnel not routing

```bash
# Check tunnel status
cloudflared tunnel info houseofjawn

# Verify DNS route exists
cloudflared tunnel route dns houseofjawn class.amditis.tech

# Check config syntax
cloudflared tunnel ingress validate
```

### Database issues

```bash
# Reinitialize (warning: loses local data)
cd ~/projects/class
rm student_tracker.db
source venv/bin/activate
python -m student_tracker.cli init
python -m student_tracker.cli sync
```

---

## File structure

```
deployment/
├── README.md                      # This file
├── setup-pi.sh                    # Automated setup script
├── student-tracker.service        # systemd unit file
├── cloudflared-config.example.yml # Tunnel config reference
└── sync-canvas.sh                 # Cron script for syncing
```

---

## Related House of Jawn services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| ttyd | 7681 | shell.amditis.tech | Web terminal |
| Cockpit | 9090 | dashboard.amditis.tech | Server management |
| Scrapefruit | 5150 | scrapefruit.amditis.tech | Web scraping |
| **Student Tracker** | **5002** | **class.amditis.tech** | **STCM140 dashboard** |
