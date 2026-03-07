#!/bin/bash
# Quick start script for GVPOCR Docker Workers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GVPOCR Docker Worker Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if google-credentials.json exists
if [ ! -f "backend/google-credentials.json" ]; then
    echo -e "${YELLOW}Warning: backend/google-credentials.json not found${NC}"
    echo "Google Vision API will not work without credentials"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get number of workers to start
echo -e "${YELLOW}How many workers do you want to start?${NC}"
read -p "Number of workers [1]: " NUM_WORKERS
NUM_WORKERS=${NUM_WORKERS:-1}

# Get custom worker ID (optional)
echo -e "${YELLOW}Enter custom worker ID prefix (optional, press Enter to auto-generate):${NC}"
read -p "Worker ID: " WORKER_ID_PREFIX

# Build the images
echo -e "${GREEN}Building Docker images...${NC}"
docker-compose -f docker-compose.worker.yml build

# Start workers
echo -e "${GREEN}Starting $NUM_WORKERS worker(s)...${NC}"
if [ -n "$WORKER_ID_PREFIX" ]; then
    # Start workers with custom IDs
    for i in $(seq 1 $NUM_WORKERS); do
        WORKER_ID="${WORKER_ID_PREFIX}-${i}"
        echo -e "${GREEN}Starting worker: $WORKER_ID${NC}"
        docker-compose -f docker-compose.worker.yml run -d -e WORKER_ID=$WORKER_ID worker
    done
else
    # Start workers with auto-generated IDs
    docker-compose -f docker-compose.worker.yml up -d --scale worker=$NUM_WORKERS
fi

# Wait for workers to start
echo -e "${GREEN}Waiting for workers to start...${NC}"
sleep 5

# Check worker status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Worker Status${NC}"
echo -e "${GREEN}========================================${NC}"
docker-compose -f docker-compose.worker.yml ps

# Show logs
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Recent Worker Logs${NC}"
echo -e "${GREEN}========================================${NC}"
docker-compose -f docker-compose.worker.yml logs --tail=20

# Show NSQ connection
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Verifying NSQ Connection${NC}"
echo -e "${GREEN}========================================${NC}"

MAIN_SERVER="172.12.0.132"
if curl -s "http://$MAIN_SERVER:4161/lookup?topic=bulk_ocr_file_tasks" > /dev/null 2>&1; then
    WORKER_COUNT=$(curl -s "http://$MAIN_SERVER:4161/lookup?topic=bulk_ocr_file_tasks" | grep -o '"broadcast_address"' | wc -l)
    echo -e "${GREEN}✓ Connected to NSQ${NC}"
    echo -e "Total workers connected: $WORKER_COUNT"
else
    echo -e "${RED}✗ Cannot connect to NSQ at $MAIN_SERVER:4161${NC}"
    echo "Please check your network connection and firewall settings"
fi

# Final instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Workers Started Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "View logs:         docker-compose -f docker-compose.worker.yml logs -f"
echo "Stop workers:      docker-compose -f docker-compose.worker.yml down"
echo "Restart workers:   docker-compose -f docker-compose.worker.yml restart"
echo "Worker stats:      docker-compose -f docker-compose.worker.yml ps"
echo ""
echo "Monitor workers at: http://$MAIN_SERVER:3000/workers"
echo ""
