#!/bin/bash

# Enrichment Pipeline Startup Script
# Automates the process of starting the enrichment stack and initializing components

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.enrichment.yml"

echo "================================"
echo "Enrichment Pipeline Startup"
echo "================================"
echo ""

# Check prerequisites
echo "[1/5] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "WARNING: .env file not found, creating from .env.example"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "IMPORTANT: Edit .env with your actual configuration values!"
fi

echo "✓ Prerequisites OK"
echo ""

# Start services
echo "[2/5] Starting Docker services..."
cd "$SCRIPT_DIR"
docker-compose -f "$COMPOSE_FILE" up -d
echo "✓ Services started"
echo ""

# Wait for services to be healthy
echo "[3/5] Waiting for services to be healthy..."
SERVICES=(
    "enrichment_mongodb:27017"
    "enrichment_nsqd:4150"
    "enrichment_ollama:11434"
    "enrichment_prometheus:9090"
    "enrichment_grafana:3000"
)

for service in "${SERVICES[@]}"; do
    SERVICE_NAME="${service%%:*}"
    PORT="${service##*:}"
    
    echo -n "  Waiting for $SERVICE_NAME..."
    for i in {1..60}; do
        if docker exec "$SERVICE_NAME" curl -s http://localhost:$PORT > /dev/null 2>&1; then
            echo " ✓"
            break
        fi
        if [ $i -eq 60 ]; then
            echo " TIMEOUT"
            exit 1
        fi
        sleep 1
    done
done
echo "✓ All services healthy"
echo ""

# Pull Ollama models
echo "[4/5] Downloading Ollama models (this may take 10-30 minutes)..."
echo "  Pulling llama3.2..."
docker exec enrichment_ollama ollama pull llama3.2 > /dev/null 2>&1
echo "    ✓ llama3.2 ready"

echo "  Pulling mixtral..."
docker exec enrichment_ollama ollama pull mixtral > /dev/null 2>&1
echo "    ✓ mixtral ready"
echo ""

# Health check
echo "[5/5] Running health checks..."
docker-compose -f "$COMPOSE_FILE" ps
echo ""

echo "================================"
echo "✓ Enrichment Pipeline Started"
echo "================================"
echo ""
echo "Access points:"
echo "  MongoDB:        mongodb://localhost:27017 (user: enrichment_user)"
echo "  NSQ Admin:      http://localhost:4161"
echo "  Prometheus:     http://localhost:9090"
echo "  Grafana:        http://localhost:3000 (admin/admin123)"
echo "  Review API:     http://localhost:5001"
echo "  Cost API:       http://localhost:5002"
echo ""
echo "Next steps:"
echo "  1. View logs:     docker-compose -f docker-compose.enrichment.yml logs -f"
echo "  2. Test pipeline: ./test-enrichment.sh"
echo "  3. Monitor:       Open http://localhost:3000 in your browser"
echo ""
