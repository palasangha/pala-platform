#!/bin/bash
# Script to configure remote Docker daemon to allow insecure registries

REMOTE_HOST="${1:-172.12.0.96}"
REMOTE_USER="${2:-rk}"
SSH_KEY="${3:-/root/.ssh/id_rsa}"

echo "Configuring Docker daemon on $REMOTE_HOST..."
echo "This will add registry.docgenai.com:5009 and registry.docgenai.com:5010 as insecure registries"

# SSH into remote and configure Docker daemon
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" << 'ENDSSH'
# Create daemon.json if it doesn't exist
sudo mkdir -p /etc/docker

# Check if daemon.json exists
if [ -f /etc/docker/daemon.json ]; then
    echo "Backing up existing daemon.json..."
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
fi

# Create/update daemon.json with insecure registries
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": [
    "registry.docgenai.com:5009",
    "registry.docgenai.com:5010"
  ]
}
EOF

echo "daemon.json configured:"
sudo cat /etc/docker/daemon.json

# Restart Docker daemon to apply changes
echo "Restarting Docker daemon..."
sudo systemctl restart docker

echo "Waiting for Docker to restart..."
sleep 3

# Verify Docker is running
if sudo systemctl is-active --quiet docker; then
    echo "✓ Docker daemon restarted successfully"
    echo "✓ Insecure registries configured"
else
    echo "✗ Docker daemon failed to restart"
    exit 1
fi
ENDSSH

echo ""
echo "Configuration complete!"
echo "You can now deploy workers to $REMOTE_HOST"
