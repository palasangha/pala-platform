#!/bin/bash
# OCR Metadata Extraction - Stop Script
# Usage: ./stop.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   OCR Metadata Extraction - Stop Script                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}[*]${NC} Stopping all services..."
docker-compose down

echo ""
echo -e "${GREEN}[✓]${NC} All services stopped"
echo ""
echo -e "${BLUE}Note:${NC} Data in volumes is preserved. To remove volumes, run:"
echo -e "  ${RED}docker-compose down -v${NC} ${BLUE}(WARNING: This deletes all data!)${NC}"
echo ""
