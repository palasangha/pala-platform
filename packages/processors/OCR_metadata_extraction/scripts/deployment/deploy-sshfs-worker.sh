#!/bin/bash

# SSHFS Deployment Script for Remote Workers
# Configures passwordless SSHFS file sharing from main server
# 
# Usage: ./deploy-sshfs-worker.sh <MAIN_SERVER_IP>
# 
# Example: ./deploy-sshfs-worker.sh 172.12.0.132

set -e

MAIN_SERVER_IP="${1:-172.12.0.132}"
SSH_USER="gvpocr"
SSH_PORT="2222"
SSH_KEY_PATH="$HOME/.ssh/gvpocr_sshfs"
SSHFS_MOUNT_DIR="/mnt/sshfs/main-server"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then 
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "=================================================="
log_info "SSHFS Deployment for Remote Worker"
log_info "=================================================="
log_info "Main Server: $MAIN_SERVER_IP:$SSH_PORT"
log_info "Mount Point: $SSHFS_MOUNT_DIR"
log_info ""

# Step 1: Install SSHFS
log_info "Step 1: Installing SSHFS..."
if command -v sshfs &> /dev/null; then
    log_success "SSHFS is already installed"
else
    apt-get update -qq
    apt-get install -y sshfs openssh-client > /dev/null 2>&1
    log_success "SSHFS installed"
fi

# Step 2: Create mount directory
log_info "Step 2: Creating mount directory..."
mkdir -p "$SSHFS_MOUNT_DIR"
chmod 755 "$SSHFS_MOUNT_DIR"
log_success "Mount directory created"

# Step 3: Test connection to main server
log_info "Step 3: Testing connection to main server..."
if ! timeout 5 ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
       -p $SSH_PORT "$SSH_USER@$MAIN_SERVER_IP" "echo 'Connection OK'" &> /dev/null; then
    log_error "Cannot connect to $MAIN_SERVER_IP:$SSH_PORT"
    log_info "Please ensure:"
    log_info "  1. Main server is accessible at $MAIN_SERVER_IP"
    log_info "  2. SSH server is running on port $SSH_PORT"
    log_info "  3. SSH key exists at $SSH_KEY_PATH"
    exit 1
fi
log_success "Connection to main server verified"

# Step 4: Unmount if already mounted
log_info "Step 4: Checking for existing mounts..."
if mountpoint -q "$SSHFS_MOUNT_DIR"; then
    log_warning "Already mounted, unmounting..."
    fusermount -u "$SSHFS_MOUNT_DIR" 2>/dev/null || umount "$SSHFS_MOUNT_DIR" || true
    sleep 1
fi

# Step 5: Mount SSHFS
log_info "Step 5: Mounting SSHFS with key-based authentication..."
SSHFS_OPTS="allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,cache_timeout=3600"

if sshfs -i "$SSH_KEY_PATH" \
         -o $SSHFS_OPTS \
         -o StrictHostKeyChecking=no \
         -o UserKnownHostsFile=/dev/null \
         -p $SSH_PORT \
         "$SSH_USER@$MAIN_SERVER_IP:/home/gvpocr" \
         "$SSHFS_MOUNT_DIR"; then
    log_success "SSHFS mount successful"
else
    log_error "SSHFS mount failed"
    exit 1
fi

# Step 6: Verify mount
log_info "Step 6: Verifying mount..."
if mountpoint -q "$SSHFS_MOUNT_DIR"; then
    log_success "Mount verified"
    log_info "Contents:"
    ls -la "$SSHFS_MOUNT_DIR" | head -15
else
    log_error "Mount verification failed"
    exit 1
fi

# Step 7: Create systemd service
log_info "Step 7: Creating systemd service for persistent mount..."
cat > /etc/systemd/system/sshfs-main-server.service << EOF
[Unit]
Description=SSHFS mount to main OCR server
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'mkdir -p $SSHFS_MOUNT_DIR && sshfs -i $SSH_KEY_PATH -o $SSHFS_OPTS,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null -p $SSH_PORT $SSH_USER@$MAIN_SERVER_IP:/home/gvpocr $SSHFS_MOUNT_DIR || true'
ExecStop=/bin/bash -c 'fusermount -u $SSHFS_MOUNT_DIR || umount $SSHFS_MOUNT_DIR || true'

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sshfs-main-server.service
log_success "Systemd service created and enabled"

# Step 8: Summary
log_info ""
log_success "=================================================="
log_success "SSHFS Setup Complete!"
log_success "=================================================="
log_info "Mount Details:"
log_info "  Location: $SSHFS_MOUNT_DIR"
log_info "  Server: $SSH_USER@$MAIN_SERVER_IP:$SSH_PORT"
log_info "  Method: Key-based authentication (passwordless)"
log_info "  Status: $(mountpoint -q $SSHFS_MOUNT_DIR && echo 'MOUNTED' || echo 'NOT MOUNTED')"
log_info ""
log_info "Shared Directories Available:"
log_info "  - $SSHFS_MOUNT_DIR/Bhushanji"
log_info "  - $SSHFS_MOUNT_DIR/newsletters"
log_info "  - $SSHFS_MOUNT_DIR/models"
log_info "  - $SSHFS_MOUNT_DIR/.cache/huggingface/hub"
log_info ""
log_info "To verify mount:"
log_info "  ls -la $SSHFS_MOUNT_DIR"
log_info ""
log_info "To check service status:"
log_info "  sudo systemctl status sshfs-main-server"
log_info ""

exit 0
