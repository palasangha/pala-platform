#!/bin/bash

# Stop all Pala Platform services

echo "Stopping all services..."

# Kill processes by name
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "packages/PalaAgents/sample-agent/main.py" 2>/dev/null || true
pkill -f "packages/PalaAgents/metadata-extraction-agent/main.py" 2>/dev/null || true
pkill -f "packages/PalaAgents/storage-agent/main.py" 2>/dev/null || true

# Kill any node processes on port 3000 or 3001
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

echo "✓ All services stopped"
