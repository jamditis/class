#!/bin/bash
# Student Tracker - House of Jawn Setup Script
# Run this on your Pi after cloning the repo to ~/projects/class

set -e

echo "=========================================="
echo "STCM140 Student Tracker - Pi Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration for House of Jawn
INSTALL_DIR="/home/jamditis/projects/class"
ENV_FILE="/home/jamditis/.claude/.env"
SERVICE_PORT=5002
HOSTNAME="class.amditis.tech"
TUNNEL_NAME="houseofjawn"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Project directory: $PROJECT_DIR${NC}"
cd "$PROJECT_DIR"

# Check if we're in the right place
if [ "$PROJECT_DIR" != "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Warning: Expected to be in $INSTALL_DIR${NC}"
    echo -e "${YELLOW}Current directory: $PROJECT_DIR${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if required env vars exist in ~/.claude/.env
echo -e "\n${GREEN}[1/6] Checking environment configuration...${NC}"
if [ -f "$ENV_FILE" ]; then
    if grep -q "CANVAS_API_TOKEN" "$ENV_FILE" && grep -q "ANTHROPIC_API_KEY" "$ENV_FILE"; then
        echo -e "${GREEN}Found required env vars in $ENV_FILE${NC}"
    else
        echo -e "${YELLOW}Warning: Missing CANVAS_API_TOKEN or ANTHROPIC_API_KEY in $ENV_FILE${NC}"
        echo "Add these to your .env file:"
        echo "  CANVAS_API_TOKEN=your-canvas-token"
        echo "  CANVAS_BASE_URL=https://montclair.instructure.com"
        echo "  CANVAS_COURSE_ID=216156"
        echo "  ANTHROPIC_API_KEY=your-anthropic-key"
    fi
else
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    echo "Create this file with your credentials first."
    exit 1
fi

# Create virtual environment
echo -e "\n${GREEN}[2/6] Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install Python packages
echo -e "\n${GREEN}[3/6] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo -e "\n${GREEN}[4/6] Initializing database...${NC}"
python -m student_tracker.cli init

# Install systemd service
echo -e "\n${GREEN}[5/6] Installing systemd service...${NC}"
sudo cp deployment/student-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable student-tracker
echo "Service installed and enabled"

# Add to cloudflared tunnel
echo -e "\n${GREEN}[6/6] Configuring Cloudflare Tunnel...${NC}"
if command -v cloudflared &> /dev/null; then
    # Check if route already exists
    if cloudflared tunnel route ip show 2>/dev/null | grep -q "$HOSTNAME"; then
        echo "DNS route for $HOSTNAME already exists"
    else
        echo "Adding DNS route for $HOSTNAME..."
        cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME" || {
            echo -e "${YELLOW}Could not add DNS route automatically.${NC}"
            echo "Run manually: cloudflared tunnel route dns $TUNNEL_NAME $HOSTNAME"
        }
    fi

    echo ""
    echo -e "${YELLOW}Don't forget to update /etc/cloudflared/config.yml!${NC}"
    echo "Add this to the ingress section (before the catch-all):"
    echo ""
    echo "  - hostname: $HOSTNAME"
    echo "    service: http://127.0.0.1:$SERVICE_PORT"
    echo ""
else
    echo -e "${YELLOW}cloudflared not found - skipping tunnel config${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Sync data from Canvas:"
echo "   source venv/bin/activate"
echo "   python -m student_tracker.cli sync"
echo ""
echo "2. Update /etc/cloudflared/config.yml:"
echo "   sudo nano /etc/cloudflared/config.yml"
echo "   (Add the hostname entry shown above)"
echo ""
echo "3. Restart services:"
echo "   sudo systemctl restart cloudflared"
echo "   sudo systemctl start student-tracker"
echo ""
echo "4. Verify:"
echo "   sudo systemctl status student-tracker"
echo "   curl http://localhost:$SERVICE_PORT"
echo "   Then visit: https://$HOSTNAME"
echo ""
