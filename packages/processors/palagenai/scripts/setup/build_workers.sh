#!/bin/bash

# OCR Worker Build Helper Script
# This script helps rebuild worker images with proper cache handling
#
# Usage:
#   ./build_workers.sh              # Normal build (uses cache when possible)
#   ./build_workers.sh --no-cache   # Force rebuild without cache
#   ./build_workers.sh --up         # Build and start workers
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_ARGS=""
START_WORKERS=false
NO_CACHE_FLAG=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --no-cache)
            NO_CACHE_FLAG="--no-cache"
            BUILD_ARGS="--no-cache"
            echo -e "${YELLOW}⚠ Building without cache (full rebuild)${NC}"
            ;;
        --up)
            START_WORKERS=true
            echo -e "${BLUE}ℹ Will start workers after build${NC}"
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Usage: $0 [--no-cache] [--up]"
            exit 1
            ;;
    esac
done

cd "$SCRIPT_DIR"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}OCR Worker Build Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Check Docker is running
echo -e "${BLUE}Step 1: Checking Docker${NC}"
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Step 2: Enable BuildKit for better caching
echo -e "${BLUE}Step 2: Setting up BuildKit${NC}"
export DOCKER_BUILDKIT=1
echo -e "${GREEN}✓ BuildKit enabled${NC}"
echo ""

# Step 3: Build worker image
echo -e "${BLUE}Step 3: Building worker image${NC}"
echo "Command: docker-compose build $BUILD_ARGS ocr-worker"
echo ""

# Capture build start time
BUILD_START=$(date +%s)

if docker-compose build $BUILD_ARGS ocr-worker; then
    BUILD_END=$(date +%s)
    BUILD_TIME=$((BUILD_END - BUILD_START))
    echo ""
    echo -e "${GREEN}✓ Build completed in ${BUILD_TIME} seconds${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# Step 4: Verify image was built
echo -e "${BLUE}Step 4: Verifying image${NC}"
if docker images gvpocr-ocr-worker --format "{{.Repository}}:{{.Tag}}" | grep -q "gvpocr-ocr-worker:latest"; then
    IMAGE_SIZE=$(docker images gvpocr-ocr-worker --format "{{.Size}}")
    echo -e "${GREEN}✓ Image created: gvpocr-ocr-worker:latest (Size: ${IMAGE_SIZE})${NC}"
else
    echo -e "${RED}✗ Image not found${NC}"
    exit 1
fi
echo ""

# Step 5: Test image (optional)
echo -e "${BLUE}Step 5: Testing worker image${NC}"
if docker run --rm gvpocr-ocr-worker:latest python -c "from app.workers.ocr_worker import OCRWorker; print('✓ Worker import successful')" 2>&1 | head -5; then
    echo -e "${GREEN}✓ Image validation passed${NC}"
else
    echo -e "${YELLOW}⚠ Image validation had issues (non-fatal)${NC}"
fi
echo ""

# Step 6: Optional - start workers
if [ "$START_WORKERS" = true ]; then
    echo -e "${BLUE}Step 6: Starting workers${NC}"
    docker-compose restart ocr-worker
    echo -e "${GREEN}✓ Workers restarted${NC}"
    echo ""

    # Wait a moment for workers to initialize
    sleep 3

    # Check worker status
    echo -e "${BLUE}Worker Status:${NC}"
    docker-compose ps ocr-worker | tail -n +2
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Build process completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}IMPORTANT BUILD INFORMATION:${NC}"
echo ""
echo "BuildKit Enabled: ✓"
echo "Cache Usage: $([ -n \"$NO_CACHE_FLAG\" ] && echo \"Disabled (full rebuild)\" || echo \"Enabled (incremental build)\")"
echo "Build Time: ${BUILD_TIME} seconds"
echo ""

if [ -z "$NO_CACHE_FLAG" ]; then
    echo -e "${YELLOW}💡 If code changes aren't reflected in the image:${NC}"
    echo "   Run: ./build_workers.sh --no-cache"
    echo ""
fi

echo -e "${YELLOW}📝 Next steps:${NC}"
if [ "$START_WORKERS" = false ]; then
    echo "   Start workers:    docker-compose restart ocr-worker"
    echo "   View logs:        docker-compose logs -f ocr-worker"
else
    echo "   View logs:        docker-compose logs -f ocr-worker"
fi
echo ""
echo -e "${YELLOW}🔧 Troubleshooting:${NC}"
echo "   If workers fail to start:"
echo "   1. Check logs: docker-compose logs ocr-worker"
echo "   2. Look for 'TypeError: NsqdTCPClient.__init__()' errors"
echo "   3. Verify docker-compose.yml has correct worker.Dockerfile reference"
echo ""
