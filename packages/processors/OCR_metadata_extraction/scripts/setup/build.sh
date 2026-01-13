#!/bin/bash

# Simplified Docker Compose Build Script
# Usage: ./build.sh [backend|workers|all] [--no-cache]

set -e

SERVICE=${1:-all}
NO_CACHE=${2}

echo "=========================================="
echo "GVPOCR Docker Compose Build"
echo "=========================================="
echo "Service: $SERVICE"
echo "No Cache: $NO_CACHE"
echo

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

BUILD_ARGS=""
if [ "$NO_CACHE" == "--no-cache" ]; then
    BUILD_ARGS="--no-cache"
    echo "⚠ Building without cache..."
fi

case $SERVICE in
    backend)
        echo -e "${BLUE}Building backend service...${NC}"
        docker-compose build $BUILD_ARGS backend
        echo -e "${GREEN}✓ Backend built${NC}"
        echo
        echo "To restart backend:"
        echo "  docker-compose restart backend"
        ;;
    
    workers)
        echo -e "${BLUE}Building OCR workers...${NC}"
        docker-compose build $BUILD_ARGS ocr-worker
        echo -e "${GREEN}✓ Workers built${NC}"
        echo
        echo "To restart workers:"
        echo "  docker-compose restart ocr-worker"
        ;;
    
    all)
        echo -e "${BLUE}Building all services...${NC}"
        docker-compose build $BUILD_ARGS backend ocr-worker
        echo -e "${GREEN}✓ All services built${NC}"
        echo
        echo "To restart all services:"
        echo "  docker-compose restart"
        ;;
    
    *)
        echo "Usage: $0 [backend|workers|all] [--no-cache]"
        echo
        echo "Examples:"
        echo "  $0 backend          # Build backend only"
        echo "  $0 workers          # Build workers only"
        echo "  $0 all              # Build all services"
        echo "  $0 backend --no-cache  # Force rebuild without cache"
        exit 1
        ;;
esac

echo
echo "=========================================="
