#!/bin/bash
# OCR Metadata Extraction - Status Script
# Usage: ./status.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   OCR Metadata Extraction - System Status                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Service Status
echo -e "${BLUE}═══ Service Status ═══${NC}"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | head -30

echo ""

# Count services
RUNNING=$(docker-compose ps --filter "status=running" --format "{{.Service}}" | wc -l)
TOTAL=$(docker-compose config --services | wc -l)
echo -e "${GREEN}Running Services:${NC} $RUNNING / $TOTAL"

# Health status
HEALTHY=$(docker-compose ps --filter "health=healthy" --format "{{.Service}}" 2>/dev/null | wc -l)
UNHEALTHY=$(docker-compose ps --filter "health=unhealthy" --format "{{.Service}}" 2>/dev/null | wc -l)

if [ "$HEALTHY" -gt 0 ]; then
    echo -e "${GREEN}Healthy Services:${NC} $HEALTHY"
fi
if [ "$UNHEALTHY" -gt 0 ]; then
    echo -e "${RED}Unhealthy Services:${NC} $UNHEALTHY"
    echo -e "${YELLOW}Run 'docker-compose ps' for details${NC}"
fi

echo ""

# Worker Status
echo -e "${BLUE}═══ Worker Status ═══${NC}"
WORKERS=$(docker-compose ps ocr-worker --filter "status=running" 2>/dev/null | grep -c "Up" || echo "0")
echo -e "${GREEN}OCR Workers:${NC} $WORKERS running"

# NSQ Status
echo ""
echo -e "${BLUE}═══ NSQ Queue Status ═══${NC}"
if curl -s http://localhost:9012/topics &>/dev/null; then
    TOPICS=$(curl -s http://localhost:9012/topics 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); print(','.join(data.get('topics',[])))" 2>/dev/null || echo "N/A")
    echo -e "${GREEN}Topics:${NC} $TOPICS"

    # Get worker connections
    CLIENTS=$(curl -s http://localhost:9014/stats?format=json 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); topics=data.get('topics',[]); print(sum(ch.get('client_count',0) for t in topics for ch in t.get('channels',[])))" 2>/dev/null || echo "0")
    echo -e "${GREEN}Connected Workers:${NC} $CLIENTS"
else
    echo -e "${RED}NSQ not accessible${NC}"
fi

echo ""

# Ollama Models
echo -e "${BLUE}═══ Ollama Status ═══${NC}"
if curl -s http://localhost:9007/api/tags &>/dev/null; then
    MODELS=$(curl -s http://localhost:9007/api/tags 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data.get('models',[])))" 2>/dev/null || echo "0")
    echo -e "${GREEN}Available Models:${NC} $MODELS"
else
    echo -e "${RED}Ollama not accessible${NC}"
fi

echo ""

# Access URLs
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Access Points                           ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Frontend:${NC}          http://localhost:9003                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Backend API:${NC}       http://localhost:9001/api              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}NSQ Admin:${NC}        http://localhost:9015                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Ollama UI:${NC}        http://localhost:9010                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Grafana:${NC}          http://localhost:9024                  ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Resource Usage
echo -e "${BLUE}═══ Resource Usage ═══${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -15

echo ""
