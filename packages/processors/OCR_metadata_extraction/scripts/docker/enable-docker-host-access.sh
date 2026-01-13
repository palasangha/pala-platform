#!/bin/bash
# Enable Docker containers to access host services
# This script adds iptables rules to allow traffic from Docker networks to reach host services

set -e

BRIDGE_INTERFACE="br-1af5921f0583"  # gvpocr-network bridge
HOST_INTERFACE="enp3s0"              # Host network interface (172.12.0.0/24)
DOCKER_NETWORK="172.23.0.0/16"
HOST_NETWORK="172.12.0.0/24"

echo "Enabling Docker network to reach host services..."
echo "Bridge interface: $BRIDGE_INTERFACE"
echo "Host interface: $HOST_INTERFACE"
echo "Docker network: $DOCKER_NETWORK"
echo "Host network: $HOST_NETWORK"
echo ""

# Add iptables rules to allow communication
echo "Adding iptables rules..."
sudo iptables -I DOCKER-USER -i "$BRIDGE_INTERFACE" -o "$HOST_INTERFACE" -j ACCEPT
sudo iptables -I DOCKER-USER -i "$HOST_INTERFACE" -o "$BRIDGE_INTERFACE" -j ACCEPT

# Optional: Also allow bridge to host loopback if needed
sudo iptables -I DOCKER-USER -i "$BRIDGE_INTERFACE" -d 127.0.0.1 -j ACCEPT

echo "✓ iptables rules added successfully!"
echo ""
echo "To persist these rules across reboots, install iptables-persistent:"
echo "  sudo apt-get install iptables-persistent"
echo "  sudo iptables-save | sudo tee /etc/iptables/rules.v4"
echo ""
echo "You can now test with:"
echo "  docker-compose exec backend python3 -c \"import requests; r = requests.get('http://172.12.0.132:1234/v1/models'); print(f'Status: {r.status_code}')\""
