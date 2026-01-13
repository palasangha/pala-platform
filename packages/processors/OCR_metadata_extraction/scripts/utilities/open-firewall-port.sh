#!/bin/bash

# Open Port 2222 on Firewall for SSH Server
# Run with: sudo ./open-firewall-port.sh

if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root (use: sudo ./open-firewall-port.sh)"
    exit 1
fi

echo "=== Opening Port 2222 on UFW Firewall ==="
echo ""

# Check UFW status
echo "Current UFW Status:"
ufw status | head -5
echo ""

# Open port 2222 for TCP
echo "Opening port 2222/tcp for SSH server..."
ufw allow 2222/tcp

echo ""
echo "=== Verification ==="
ufw status numbered | grep 2222

echo ""
echo "✓ Port 2222 is now open on the firewall"
echo ""
echo "You can now:"
echo "  1. Access SSH from remote workers: ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132"
echo "  2. Deploy SSHFS mounts on remote workers"
echo "  3. Access shared folders from Docker containers"
