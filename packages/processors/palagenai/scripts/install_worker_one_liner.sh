#!/bin/bash
# One-liner installer for GVPOCR Worker
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/palasangha/OCR_metadata_extraction/main/scripts/install_worker_one_liner.sh)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_header() { echo -e "${BLUE}$1${NC}"; }

clear
print_header "========================================="
print_header "  GVPOCR Worker - One-Liner Installer"
print_header "========================================="
echo ""

# Check for update mode
UPDATE_MODE=false
if [ "$1" == "update" ] || [ "$1" == "--update" ]; then
    UPDATE_MODE=true
    print_info "Running in UPDATE mode"
fi

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    print_info "Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    print_info "Detected: Linux"
else
    print_error "Unsupported OS: $OSTYPE"
    exit 1
fi

# Configuration
REPO_URL="https://github.com/palasangha/OCR_metadata_extraction.git"
INSTALL_DIR="$HOME/gvpocr-worker"
QUEUE_SERVER="${QUEUE_SERVER_IP:-172.12.0.132}"

echo ""
echo "Installation Directory: $INSTALL_DIR"
echo "Queue Server: $QUEUE_SERVER"
echo ""

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    print_error "Installation directory already exists: $INSTALL_DIR"
    read -p "Remove and reinstall? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        print_success "Removed existing installation"
    else
        print_error "Installation cancelled"
        exit 1
    fi
fi

# Step 1: Clone repository
print_info "Cloning repository..."
if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
    print_error "Failed to clone repository"
    echo "Make sure git is installed and you have internet access"
    exit 1
fi
print_success "Repository cloned"

# Step 2: Run appropriate setup script
cd "$INSTALL_DIR"

if [ "$OS_TYPE" == "macos" ]; then
    print_info "Running macOS setup script..."
    if [ -f "scripts/setup_remote_worker_macos.sh" ]; then
        chmod +x scripts/setup_remote_worker_macos.sh
        ./scripts/setup_remote_worker_macos.sh
    else
        print_error "macOS setup script not found"
        exit 1
    fi
elif [ "$OS_TYPE" == "linux" ]; then
    print_info "Running Linux setup script..."
    if [ -f "scripts/setup_remote_worker.sh" ]; then
        chmod +x scripts/setup_remote_worker.sh
        ./scripts/setup_remote_worker.sh
    else
        print_error "Linux setup script not found"
        exit 1
    fi
fi

echo ""
print_header "========================================="
print_header "  Installation Complete!"
print_header "========================================="
echo ""
print_success "GVPOCR Worker has been set up at: $INSTALL_DIR"
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit configuration:"
echo "   nano $INSTALL_DIR/backend/.env"
echo ""
echo "2. Set MongoDB password in .env file"
echo ""
echo "3. Copy Google credentials (if using Google Vision)"
echo ""
echo "4. Test the worker:"
echo "   cd $INSTALL_DIR/backend"
echo "   source venv/bin/activate"
echo "   python run_worker.py --worker-id \$(hostname)-worker --nsqlookupd $QUEUE_SERVER:4161"
echo ""
if [ "$OS_TYPE" == "macos" ]; then
    echo "5. Install as service:"
    echo "   cd $INSTALL_DIR"
    echo "   ./scripts/install_worker_launchagent.sh"
else
    echo "5. Install as service:"
    echo "   cd $INSTALL_DIR"
    echo "   sudo ./scripts/install_worker_service.sh"
fi
echo ""
echo "Documentation: $INSTALL_DIR/QUICK_START_$(echo $OS_TYPE | tr '[:lower:]' '[:upper:]').md"
echo ""
