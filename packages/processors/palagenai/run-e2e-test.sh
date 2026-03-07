#!/bin/bash

# End-to-End Test Runner
# Automates the complete enrichment pipeline test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.enrichment.yml"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================"
echo "Enrichment Pipeline E2E Test"
echo "================================"
echo ""

# Parse arguments
SKIP_DEPLOY=false
SKIP_INSERT=false
MONITOR_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deploy)
            SKIP_DEPLOY=true
            echo "Skipping deployment (assuming services already running)"
            shift
            ;;
        --skip-insert)
            SKIP_INSERT=true
            echo "Skipping test data insertion"
            shift
            ;;
        --monitor-only)
            MONITOR_ONLY=true
            echo "Running monitoring only"
            shift
            ;;
        *)
            echo "Usage: $0 [--skip-deploy] [--skip-insert] [--monitor-only]"
            exit 1
            ;;
    esac
done

echo ""

# Step 1: Deploy (if not skipped)
if [ "$SKIP_DEPLOY" = false ]; then
    echo "[1/4] Deploying enrichment stack..."
    echo ""

    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "${YELLOW}WARNING: .env file not found${NC}"
        echo "Creating from .env.example..."
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo "${YELLOW}Please edit .env with your configuration before running again${NC}"
        exit 1
    fi

    # Start services
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q enrichment_mongodb; then
        echo "Starting services..."
        docker-compose -f "$COMPOSE_FILE" up -d

        # Wait for services to be healthy
        echo "Waiting for services to be healthy (this may take 2-3 minutes)..."
        for i in {1..60}; do
            if docker-compose -f "$COMPOSE_FILE" ps | grep -E "(enrichment_mongodb|enrichment_nsqd|enrichment_ollama)" | grep -q "healthy"; then
                echo "✓ Services healthy"
                break
            fi
            if [ $i -eq 60 ]; then
                echo "${RED}✗ Services failed to become healthy${NC}"
                exit 1
            fi
            printf "."
            sleep 2
        done
    else
        echo "✓ Services already running"
    fi

    # Download Ollama models
    echo ""
    echo "Checking Ollama models..."
    if ! docker exec enrichment_ollama ollama list 2>/dev/null | grep -q "llama3.2"; then
        echo "Downloading ollama models (this may take 10-30 minutes on first run)..."
        docker exec enrichment_ollama ollama pull llama3.2 > /dev/null 2>&1 &
        docker exec enrichment_ollama ollama pull mixtral > /dev/null 2>&1 &
        wait
        echo "✓ Models downloaded"
    else
        echo "✓ Ollama models already available"
    fi

    echo ""
fi

# Step 2: Insert test data (if not skipped)
if [ "$SKIP_INSERT" = false ] && [ "$MONITOR_ONLY" = false ]; then
    echo "[2/4] Inserting test data..."
    echo ""

    if [ ! -f "$SCRIPT_DIR/test-data/insert-test-data.sh" ]; then
        echo "${RED}ERROR: insert-test-data.sh not found${NC}"
        exit 1
    fi

    # Run insertion
    cd "$SCRIPT_DIR"
    bash test-data/insert-test-data.sh
    echo ""
fi

# Step 3: Monitor and wait for completion
echo "[3/4] Monitoring enrichment processing..."
echo ""
echo "${BLUE}Processing will take approximately 2-3 minutes for 5 documents${NC}"
echo ""

# Start monitoring in background
MONITOR_PID=""
if command -v tput &> /dev/null && [ -t 1 ]; then
    # Terminal supports colors - show live monitor
    cd "$SCRIPT_DIR"
    bash monitor-enrichment.sh &
    MONITOR_PID=$!

    # Wait for documents to be processed
    echo ""
    echo "Press Ctrl+C to stop monitoring and proceed to analysis"
    wait $MONITOR_PID 2>/dev/null || true
else
    # No color support - just wait and show dot progress
    echo "Waiting for enrichment to complete..."
    for i in {1..120}; do
        PROCESSED=$(mongosh \
            --username enrichment_user \
            --password "${MONGO_PASSWORD:-changeMe123}" \
            --host localhost:27017 \
            --authenticationDatabase admin \
            --quiet \
            --eval "db = db.getSiblingDB('gvpocr'); print(db.enriched_documents.countDocuments({}))" 2>/dev/null || echo "0")

        if [ "$PROCESSED" -ge 5 ]; then
            echo ""
            echo "✓ All documents processed ($PROCESSED/5)"
            break
        fi

        printf "."
        sleep 1
    done
    echo ""
fi

echo ""

# Step 4: Analyze results
echo "[4/4] Analyzing results..."
echo ""

cd "$SCRIPT_DIR"
bash analyze-results.sh

echo ""
echo "================================"
echo "✓ E2E Test Complete"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Review the analysis above for completeness and costs"
echo "2. Check Grafana dashboards: http://localhost:3000 (admin/admin123)"
echo "3. Review review queue: curl http://localhost:5001/api/review/queue"
echo "4. Scale test: run with more test data"
echo "5. Production deployment: Follow DOCKER_DEPLOYMENT.md"
echo ""
