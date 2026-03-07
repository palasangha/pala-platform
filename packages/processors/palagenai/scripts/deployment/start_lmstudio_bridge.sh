#!/bin/bash

# LMStudio Docker Bridge Starter Script
# Run this with: sudo bash start_lmstudio_bridge.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BRIDGE_SCRIPT="$SCRIPT_DIR/lmstudio_docker_bridge.py"

echo "=============================================="
echo "LMStudio Docker Bridge"
echo "=============================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "✗ This script must be run as root (use sudo)"
   echo ""
   echo "Run with:"
   echo "  sudo bash $0"
   exit 1
fi

# Check if LMStudio is running
if ! nc -z 127.0.0.1 1234 2>/dev/null; then
    echo "✗ LMStudio is not running on localhost:1234"
    echo ""
    echo "Please start LMStudio first, then run this script again."
    exit 1
fi

echo "✓ LMStudio is running on localhost:1234"
echo ""

# Check if bridge script exists
if [ ! -f "$BRIDGE_SCRIPT" ]; then
    echo "✗ Bridge script not found: $BRIDGE_SCRIPT"
    exit 1
fi

echo "Starting bridge..."
echo "  Listening on: 172.23.0.1:1234"
echo "  Forwarding to: localhost:1234"
echo "  Docker containers can reach: http://172.23.0.1:1234"
echo ""
echo "Press Ctrl+C to stop"
echo "=============================================="
echo ""

# Run the bridge
python3 "$BRIDGE_SCRIPT"
