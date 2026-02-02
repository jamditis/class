# Raspberry Pi deployment with Cloudflare Tunnel

This guide sets up the Student Tracker dashboard on a Raspberry Pi, accessible via Cloudflare Tunnel without exposing your home network.

## Prerequisites

- Raspberry Pi (3B+ or newer recommended) with Raspberry Pi OS
- Cloudflare account with a domain
- SSH access to your Pi

## Quick start

```bash
# On your Pi, clone the repo
git clone https://github.com/jamditis/class.git
cd class

# Run the setup script
chmod +x deployment/setup-pi.sh
./deployment/setup-pi.sh
```

## Manual setup

### 1. Install dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Copy the example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

Required variables:
- `CANVAS_API_TOKEN` - Your Canvas LMS API token
- `CANVAS_COURSE_ID` - The course ID (e.g., 216156)
- `ANTHROPIC_API_KEY` - For Haiku evaluations

### 3. Initialize database

```bash
source venv/bin/activate
python -m student_tracker.cli init
python -m student_tracker.cli sync  # Pull data from Canvas
```

### 4. Install Cloudflare Tunnel

```bash
# Download cloudflared for ARM
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Authenticate (opens browser)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create student-tracker

# Note the tunnel ID that's displayed
```

### 5. Configure tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /home/pi/.cloudflared/<YOUR-TUNNEL-ID>.json

ingress:
  - hostname: tracker.yourdomain.com
    service: http://localhost:5001
  - service: http_status:404
```

Add DNS record:
```bash
cloudflared tunnel route dns student-tracker tracker.yourdomain.com
```

### 6. Set up systemd services

```bash
# Copy service files
sudo cp deployment/student-tracker.service /etc/systemd/system/
sudo cp deployment/cloudflared.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/student-tracker.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable student-tracker cloudflared
sudo systemctl start student-tracker cloudflared
```

### 7. Verify

```bash
# Check services
sudo systemctl status student-tracker
sudo systemctl status cloudflared

# View logs
journalctl -u student-tracker -f
journalctl -u cloudflared -f
```

Visit `https://tracker.yourdomain.com` to access your dashboard.

## Updating

```bash
cd ~/class
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart student-tracker
```

## Troubleshooting

### Dashboard won't start
```bash
# Check logs
journalctl -u student-tracker -n 50

# Test manually
source venv/bin/activate
python -m student_tracker.cli dashboard --port 5001
```

### Tunnel not connecting
```bash
# Check cloudflared status
sudo systemctl status cloudflared

# Test tunnel manually
cloudflared tunnel run student-tracker
```

### Database issues
```bash
# Reinitialize (warning: loses data)
rm student_tracker.db
python -m student_tracker.cli init
python -m student_tracker.cli sync
```
