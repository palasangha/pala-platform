#!/bin/bash

# Enrichment Pipeline Health Check Script
# Monitors the health of all components in the enrichment stack

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "Enrichment Pipeline Health Check"
echo "================================"
echo ""

check_service() {
    local name=$1
    local url=$2
    local port=$3
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name (port $port)"
        return 0
    else
        echo -e "${RED}✗${NC} $name (port $port)"
        return 1
    fi
}

# Check all services
echo "Service Health:"
check_service "MongoDB" "http://localhost:27017" "27017"
check_service "NSQ Lookupd" "http://localhost:4161/api/nodes" "4161"
check_service "NSQ Admin" "http://localhost:4151/api/stats" "4151"
check_service "Ollama" "http://localhost:11434/api/tags" "11434"
check_service "Prometheus" "http://localhost:9090/-/healthy" "9090"
check_service "Grafana" "http://localhost:3000/api/health" "3000"
check_service "Review API" "http://localhost:5001/health" "5001"
check_service "Cost API" "http://localhost:5002/health" "5002"

echo ""
echo "Container Status:"
docker-compose -f docker-compose.enrichment.yml ps 2>/dev/null || echo "Docker Compose file not found"

echo ""
echo "Resource Usage:"
docker stats --no-stream enrichment_mongodb enrichment_ollama 2>/dev/null || echo "Containers not running"

echo ""
echo "Recent Errors (last 20 lines from worker log):"
docker logs --tail 20 enrichment_worker_1 2>/dev/null | grep -i error || echo "  (No errors found)"

echo ""
echo "Database Collections:"
docker exec enrichment_mongodb mongosh \
    --username enrichment_user \
    --password "$(grep MONGO_PASSWORD docker-compose.enrichment.yml | head -1 | cut -d'=' -f2)" \
    --quiet \
    --eval "use gvpocr; show collections" 2>/dev/null || echo "  (Unable to connect)"

echo ""
echo "Queue Status:"
curl -s http://localhost:4161/api/stats | python3 -m json.tool 2>/dev/null || echo "  (Unable to connect)"

echo ""
echo "================================"
echo "Health check complete"
echo "================================"
