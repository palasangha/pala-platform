#!/bin/bash
# Install GVPOCR Worker as Systemd Service

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Get configuration
QUEUE_SERVER_IP="${QUEUE_SERVER_IP:-172.12.0.132}"
NSQLOOKUPD_ADDRESS="${NSQLOOKUPD_ADDRESS:-$QUEUE_SERVER_IP:4161}"

# Get current directory and user
INSTALL_DIR=$(cd "$(dirname "$0")/.." && pwd)
BACKEND_DIR="$INSTALL_DIR/backend"
CURRENT_USER="${SUDO_USER:-$USER}"

print_info "Installing GVPOCR Worker as systemd service..."
echo "Install Directory: $INSTALL_DIR"
echo "Backend Directory: $BACKEND_DIR"
echo "Running as User: $CURRENT_USER"
echo "Queue Server: $QUEUE_SERVER_IP"
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Check if venv exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    print_error "Virtual environment not found. Run setup_remote_worker.sh first"
    exit 1
fi

# Check if .env exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    print_error ".env file not found. Run setup_remote_worker.sh first"
    exit 1
fi

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/gvpocr-worker.service"

print_info "Creating systemd service file..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GVPOCR OCR Worker
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/venv/bin/python $BACKEND_DIR/run_worker.py --worker-id %H-worker --nsqlookupd $NSQLOOKUPD_ADDRESS
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

print_success "Service file created: $SERVICE_FILE"

# Reload systemd
print_info "Reloading systemd daemon..."
systemctl daemon-reload
print_success "Systemd daemon reloaded"

# Enable service
print_info "Enabling gvpocr-worker service..."
systemctl enable gvpocr-worker
print_success "Service enabled (will start on boot)"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
print_success "GVPOCR Worker service installed"
echo ""
echo "Service Management Commands:"
echo "  Start:   sudo systemctl start gvpocr-worker"
echo "  Stop:    sudo systemctl stop gvpocr-worker"
echo "  Restart: sudo systemctl restart gvpocr-worker"
echo "  Status:  sudo systemctl status gvpocr-worker"
echo "  Logs:    sudo journalctl -u gvpocr-worker -f"
echo ""
echo "To start the worker now:"
echo "  sudo systemctl start gvpocr-worker"
echo ""
