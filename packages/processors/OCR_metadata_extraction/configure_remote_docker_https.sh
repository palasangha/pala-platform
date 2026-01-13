#!/bin/bash
# Script to configure remote Docker daemon for HTTPS registry

REMOTE_HOST="${1:-172.12.0.96}"
REMOTE_USER="${2:-rk}"
SSH_KEY="${3:-/root/.ssh/id_rsa}"
REGISTRY_SERVER="172.12.0.132"

echo "Configuring Docker daemon and /etc/hosts on $REMOTE_HOST..."
echo "Registry server: $REGISTRY_SERVER:5010 (HTTPS)"

# SSH into remote and configure
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" << ENDSSH
set -e

echo "=== Step 1: Configure /etc/hosts for registry.docgenai.com ==="
# Add registry hostname to /etc/hosts if not already there
if ! grep -q "registry.docgenai.com" /etc/hosts; then
    echo "$REGISTRY_SERVER registry.docgenai.com" | sudo tee -a /etc/hosts
    echo "✓ Added registry.docgenai.com to /etc/hosts"
else
    # Update existing entry
    sudo sed -i '/registry.docgenai.com/d' /etc/hosts
    echo "$REGISTRY_SERVER registry.docgenai.com" | sudo tee -a /etc/hosts
    echo "✓ Updated registry.docgenai.com in /etc/hosts"
fi

echo ""
echo "=== Step 2: Configure Docker daemon for insecure registry ==="
# Create daemon.json if it doesn't exist
sudo mkdir -p /etc/docker

# Backup existing daemon.json
if [ -f /etc/docker/daemon.json ]; then
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.\$(date +%Y%m%d_%H%M%S)
    echo "✓ Backed up existing daemon.json"
fi

# Create/update daemon.json
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": [
    "registry.docgenai.com:5010",
    "172.12.0.132:5010"
  ]
}
EOF

echo "✓ daemon.json configured:"
sudo cat /etc/docker/daemon.json

echo ""
echo "=== Step 3: Restart Docker daemon ==="
sudo systemctl restart docker

echo "Waiting for Docker to restart..."
sleep 5

# Verify Docker is running
if sudo systemctl is-active --quiet docker; then
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
echo "You can now pull images from registry.docgenai.com:5010"

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
    echo "You can now deploy workers from the supervisor dashboard."
else
    echo ""
    echo "✗ Configuration failed. Please check the errors above."
    exit 1
fi
