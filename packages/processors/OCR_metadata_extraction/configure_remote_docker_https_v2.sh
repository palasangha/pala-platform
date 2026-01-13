#!/bin/bash
# Script to configure remote Docker daemon for HTTPS registry with sudo password

REMOTE_HOST="${1:-172.12.0.96}"
REMOTE_USER="${2:-pala-1}"
SSH_KEY="${3:-/mnt/sda1/mango1_home/gvpocr/ssh_keys/gvpocr_worker}"
SUDO_PASSWORD="${4:-mango1}"
REGISTRY_SERVER="172.12.0.132"

echo "Configuring Docker daemon and /etc/hosts on $REMOTE_HOST..."
echo "Registry server: $REGISTRY_SERVER:5010 (HTTPS)"

# SSH into remote and configure
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" bash -s << ENDSSH
set -e

echo "=== Step 1: Configure /etc/hosts for registry.docgenai.com ==="
# Add registry hostname to /etc/hosts if not already there
if ! grep -q "registry.docgenai.com" /etc/hosts 2>/dev/null; then
    echo "$SUDO_PASSWORD" | sudo -S sh -c "echo '$REGISTRY_SERVER registry.docgenai.com' >> /etc/hosts"
    echo "✓ Added registry.docgenai.com to /etc/hosts"
else
    # Update existing entry
    echo "$SUDO_PASSWORD" | sudo -S sed -i '/registry.docgenai.com/d' /etc/hosts
    echo "$SUDO_PASSWORD" | sudo -S sh -c "echo '$REGISTRY_SERVER registry.docgenai.com' >> /etc/hosts"
    echo "✓ Updated registry.docgenai.com in /etc/hosts"
fi

echo ""
echo "=== Step 2: Configure Docker daemon for insecure registry ==="
# Create daemon.json if it doesn't exist
echo "$SUDO_PASSWORD" | sudo -S mkdir -p /etc/docker

# Backup existing daemon.json
if [ -f /etc/docker/daemon.json ]; then
    echo "$SUDO_PASSWORD" | sudo -S cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.\$(date +%Y%m%d_%H%M%S)
    echo "✓ Backed up existing daemon.json"
fi

# Create/update daemon.json
echo "$SUDO_PASSWORD" | sudo -S tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": [
    "registry.docgenai.com:5010",
    "172.12.0.132:5010"
  ]
}
EOF

echo "✓ daemon.json configured:"
echo "$SUDO_PASSWORD" | sudo -S cat /etc/docker/daemon.json

echo ""
echo "=== Step 3: Restart Docker daemon ==="
echo "$SUDO_PASSWORD" | sudo -S systemctl restart docker

echo "Waiting for Docker to restart..."
sleep 5

# Verify Docker is running
if echo "$SUDO_PASSWORD" | sudo -S systemctl is-active --quiet docker; then
    echo "✓ Docker daemon restarted successfully"
else
    echo "✗ Docker daemon failed to restart"
    exit 1
fi

echo ""
echo "=== Step 4: Test registry connectivity ==="
# Test if we can reach the registry
if curl -sk https://registry.docgenai.com:5010/v2/ > /dev/null 2>&1; then
    echo "✓ Registry is accessible via HTTPS"
    curl -sk https://registry.docgenai.com:5010/v2/_catalog
elif curl -sk https://172.12.0.132:5010/v2/ > /dev/null 2>&1; then
    echo "✓ Registry is accessible via IP"
else
    echo "⚠ Warning: Could not verify registry connectivity"
    echo "  This might be OK if certificates need to be configured"
fi

echo ""
echo "=== Configuration Summary ==="
echo "  ✓ /etc/hosts configured with registry hostname"
echo "  ✓ Docker daemon configured for insecure registry"
echo "  ✓ Docker daemon restarted"
echo ""
echo "Configuration complete on remote host"

ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✓ Configuration complete!"
    echo "========================================="
    echo ""
    echo "Remote Docker daemon on $REMOTE_HOST is now configured to:"
    echo "  1. Resolve registry.docgenai.com to $REGISTRY_SERVER"
    echo "  2. Allow pulling from registry.docgenai.com:5010"
    echo ""
    echo "Testing pull from remote machine..."
    echo ""

    # Test pull using Docker Socket API with correct API version
    DOCKER_API_VERSION=1.41 docker -H tcp://$REMOTE_HOST:2375 pull registry.docgenai.com:5010/gvpocr-worker-updated:latest

else
    echo ""
    echo "✗ Configuration failed. Please check the errors above."
    exit 1
fi
