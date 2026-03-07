#!/bin/bash

# SSHFS Setup Script for Remote OCR Workers
# This script automates the setup of SSHFS mounts on remote worker machines
# It mounts the main server's file systems for use by Docker containers
#
# Usage: ./setup-sshfs-remote-worker.sh <MAIN_SERVER_IP> [options]
#
# Options:
#   -u, --user           SSH username (default: gvpocr)
#   -p, --port           SSH port (default: 2222)
#   -P, --password       SSH password (optional, will prompt if not provided)
#   --key                SSH private key path
#   --no-cache           Disable caching for slower networks
#   --help               Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SSH_USER="gvpocr"
SSH_PORT="2222"
SSH_PASSWORD=""
SSH_KEY=""
CACHE_TIMEOUT="3600"
MAIN_SERVER_IP=""

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print help
show_help() {
    cat << 'EOF'
SSHFS Setup Script for Remote OCR Workers

Usage: ./setup-sshfs-remote-worker.sh <MAIN_SERVER_IP> [options]

Arguments:
  MAIN_SERVER_IP        IP address or hostname of the main server

Options:
  -u, --user USER       SSH username (default: gvpocr)
  -p, --port PORT       SSH port (default: 2222)
  -P, --password PWD    SSH password (will prompt if not provided)
  --key PATH            SSH private key path (for key-based auth)
  --no-cache            Disable caching for slow networks
  --help                Show this help message

Examples:
  # Basic setup with password authentication
  ./setup-sshfs-remote-worker.sh 192.168.1.100

  # With custom SSH port
  ./setup-sshfs-remote-worker.sh 192.168.1.100 -p 2222

  # With SSH key authentication
  ./setup-sshfs-remote-worker.sh 192.168.1.100 --key /home/user/.ssh/gvpocr_sshfs

  # Disable cache for slow networks
  ./setup-sshfs-remote-worker.sh 192.168.1.100 --no-cache

EOF
}

# Parse command line arguments
if [ $# -lt 1 ]; then
    log_error "Main server IP is required"
    show_help
    exit 1
fi

MAIN_SERVER_IP="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user)
            SSH_USER="$2"
            shift 2
            ;;
        -p|--port)
            SSH_PORT="$2"
            shift 2
            ;;
        -P|--password)
            SSH_PASSWORD="$2"
            shift 2
            ;;
        --key)
            SSH_KEY="$2"
            shift 2
            ;;
        --no-cache)
            CACHE_TIMEOUT="0"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate main server IP
if [ -z "$MAIN_SERVER_IP" ]; then
    log_error "Main server IP is required"
    exit 1
fi

log_info "SSHFS Setup for Remote OCR Workers"
log_info "===================================="
log_info "Main Server IP: $MAIN_SERVER_IP"
log_info "SSH User: $SSH_USER"
log_info "SSH Port: $SSH_PORT"
log_info ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Install SSHFS
log_info "Step 1: Installing SSHFS..."
if command -v sshfs &> /dev/null; then
    log_success "SSHFS is already installed"
else
    apt-get update
    apt-get install -y sshfs
    log_success "SSHFS installed successfully"
fi

# Step 2: Create mount directory
log_info "Step 2: Creating mount directory..."
MOUNT_DIR="/mnt/sshfs/main-server"
if [ -d "$MOUNT_DIR" ]; then
    log_warning "Mount directory already exists: $MOUNT_DIR"
else
    mkdir -p "$MOUNT_DIR"
    chmod 755 "$MOUNT_DIR"
    log_success "Mount directory created: $MOUNT_DIR"
fi

# Step 3: Test SSH connection
log_info "Step 3: Testing SSH connection..."
SSH_OPTS="-p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

if ssh $SSH_OPTS "$SSH_USER@$MAIN_SERVER_IP" "echo 'SSH connection successful'" &> /dev/null; then
    log_success "SSH connection successful"
else
    log_error "SSH connection failed"
    log_error "Please check:"
    log_error "  1. Main server IP: $MAIN_SERVER_IP"
    log_error "  2. SSH port: $SSH_PORT"
    log_error "  3. Username: $SSH_USER"
    log_error "  4. Network connectivity"
    exit 1
fi

# Step 4: Unmount if already mounted
log_info "Step 4: Checking for existing mounts..."
if mountpoint -q "$MOUNT_DIR"; then
    log_warning "Mount point already in use, unmounting..."
    fusermount -u "$MOUNT_DIR" || umount "$MOUNT_DIR"
    sleep 1
fi

# Step 5: Mount SSHFS
log_info "Step 5: Mounting SSHFS..."

SSHFS_OPTS="allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3"

if [ "$CACHE_TIMEOUT" != "0" ]; then
    SSHFS_OPTS="$SSHFS_OPTS,cache_timeout=$CACHE_TIMEOUT"
else
    log_warning "Cache disabled - performance may be reduced on slow networks"
fi

# Build SSHFS command
SSHFS_CMD="sshfs -o $SSHFS_OPTS $SSH_OPTS $SSH_USER@$MAIN_SERVER_IP:/home/gvpocr $MOUNT_DIR"

if $SSHFS_CMD; then
    log_success "SSHFS mount successful"
else
    log_error "SSHFS mount failed"
    exit 1
fi

# Step 6: Verify mount
log_info "Step 6: Verifying mount..."
if mountpoint -q "$MOUNT_DIR"; then
    log_success "Mount point verified"
    log_info "Contents of $MOUNT_DIR:"
    ls -la "$MOUNT_DIR" | head -20
else
    log_error "Mount verification failed"
    exit 1
fi

# Step 7: Create systemd service for persistence
log_info "Step 7: Creating systemd service for persistent mount..."

SERVICE_FILE="/etc/systemd/system/sshfs-main-server.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SSHFS mount to main server for OCR workers
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes

# Set environment variables from calling environment or defaults
Environment="MAIN_SERVER_IP=$MAIN_SERVER_IP"
Environment="SSH_USER=$SSH_USER"
Environment="SSH_PORT=$SSH_PORT"
Environment="MOUNT_DIR=$MOUNT_DIR"
EOF

if [ -n "$SSH_KEY" ]; then
    cat >> "$SERVICE_FILE" << EOF
Environment="SSH_KEY=$SSH_KEY"
ExecStart=/bin/bash -c 'mkdir -p \$MOUNT_DIR && sshfs -o allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,cache_timeout=$CACHE_TIMEOUT -i \$SSH_KEY -p \$SSH_PORT \$SSH_USER@\$MAIN_SERVER_IP:/home/gvpocr \$MOUNT_DIR || true'
EOF
else
    cat >> "$SERVICE_FILE" << EOF
ExecStart=/bin/bash -c 'mkdir -p \$MOUNT_DIR && sshfs -o allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,cache_timeout=$CACHE_TIMEOUT,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null -p \$SSH_PORT \$SSH_USER@\$MAIN_SERVER_IP:/home/gvpocr \$MOUNT_DIR || true'
EOF
fi

cat >> "$SERVICE_FILE" << EOF
ExecStop=/bin/bash -c 'fusermount -u \$MOUNT_DIR || umount \$MOUNT_DIR || true'

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
log_success "Systemd service created: $SERVICE_FILE"

# Step 8: Enable service
log_info "Step 8: Enabling systemd service for auto-start..."
systemctl enable sshfs-main-server.service
log_success "Service enabled"

# Step 9: Create docker-compose override
log_info "Step 9: Creating docker-compose.sshfs-override.yml..."

OVERRIDE_FILE="docker-compose.sshfs-override.yml"

cat > "$OVERRIDE_FILE" << 'EOF'
# Docker Compose Override for SSHFS Mounts
# This file overrides volume mounts to use SSHFS instead of SMB shares
#
# Usage:
#   docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d

services:
  worker:
    volumes:
      # Override previous mounts with SSHFS mounts
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro

  # If using llamacpp service
  llamacpp:
    volumes:
      - /mnt/sshfs/main-server/models:/models:ro
      - llamacpp_cache:/root/.cache/huggingface/hub
EOF

log_success "Override file created: $OVERRIDE_FILE"

# Summary
log_info ""
log_success "=================================================="
log_success "SSHFS Setup Completed Successfully!"
log_success "=================================================="
log_info ""
log_info "Mount Details:"
log_info "  Location: $MOUNT_DIR"
log_info "  Server: $SSH_USER@$MAIN_SERVER_IP:$SSH_PORT"
log_info "  Status: $(mountpoint -q $MOUNT_DIR && echo 'MOUNTED' || echo 'NOT MOUNTED')"
log_info ""
log_info "Available Shared Directories:"
log_info "  - $MOUNT_DIR/Bhushanji (main OCR data)"
log_info "  - $MOUNT_DIR/newsletters"
log_info "  - $MOUNT_DIR/models (LLM models)"
log_info "  - $MOUNT_DIR/.cache/huggingface/hub (model cache)"
log_info ""
log_info "Next Steps:"
log_info "  1. Update your docker-compose.worker.yml with SSHFS mount paths"
log_info "  2. Or use the override file:"
log_info "     docker-compose -f docker-compose.worker.yml -f $OVERRIDE_FILE up -d"
log_info ""
log_info "To verify the mount manually:"
log_info "  ls -la $MOUNT_DIR"
log_info ""
log_info "To troubleshoot:"
log_info "  sudo systemctl status sshfs-main-server"
log_info "  sudo systemctl restart sshfs-main-server"
log_info ""

exit 0
