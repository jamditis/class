#!/bin/bash
# Student Tracker - Raspberry Pi Setup Script
# Run this on your Pi after cloning the repo

set -e

echo "=========================================="
echo "Student Tracker - Pi Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Project directory: $PROJECT_DIR${NC}"
cd "$PROJECT_DIR"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo -e "\n${GREEN}[1/7] Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo -e "\n${GREEN}[2/7] Installing Python and dependencies...${NC}"
sudo apt install -y python3 python3-pip python3-venv git curl

# Create virtual environment
echo -e "\n${GREEN}[3/7] Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install Python packages
echo -e "\n${GREEN}[4/7] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment file
echo -e "\n${GREEN}[5/7] Setting up environment...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env file - please edit with your credentials:${NC}"
        echo "  nano .env"
    else
        echo -e "${RED}Warning: .env.example not found${NC}"
    fi
else
    echo ".env file already exists"
fi

# Initialize database
echo -e "\n${GREEN}[6/7] Initializing database...${NC}"
python -m student_tracker.cli init

# Install cloudflared
echo -e "\n${GREEN}[7/7] Installing Cloudflare Tunnel...${NC}"
if ! command -v cloudflared &> /dev/null; then
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif [ "$ARCH" = "armv7l" ]; then
        CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
    else
        echo -e "${YELLOW}Unknown architecture: $ARCH - defaulting to arm64${NC}"
        CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    fi

    echo "Downloading cloudflared..."
    curl -L "$CLOUDFLARED_URL" -o cloudflared
    chmod +x cloudflared
    sudo mv cloudflared /usr/local/bin/
    echo "cloudflared installed successfully"
else
    echo "cloudflared already installed"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your environment variables:"
echo "   nano .env"
echo ""
echo "2. Sync data from Canvas:"
echo "   source venv/bin/activate"
echo "   python -m student_tracker.cli sync"
echo ""
echo "3. Set up Cloudflare Tunnel:"
echo "   cloudflared tunnel login"
echo "   cloudflared tunnel create student-tracker"
echo ""
echo "4. Configure tunnel (see deployment/README.md)"
echo ""
echo "5. Install systemd services:"
echo "   sudo cp deployment/student-tracker.service /etc/systemd/system/"
echo "   sudo cp deployment/cloudflared.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable student-tracker cloudflared"
echo "   sudo systemctl start student-tracker cloudflared"
echo ""
echo "For detailed instructions, see: deployment/README.md"
