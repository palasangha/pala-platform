#!/bin/bash
# Push GVPOCR Docker Images to Private Registry
# This script builds and pushes all GVPOCR images to your private Docker registry

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_header() { echo -e "${BLUE}$1${NC}"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

clear
print_header "========================================="
print_header "  Push GVPOCR Images to Registry"
print_header "========================================="
echo ""

# Configuration
read -p "Enter registry domain/IP: " REGISTRY_DOMAIN
read -p "Enter registry port (default: 5000): " REGISTRY_PORT
REGISTRY_PORT=${REGISTRY_PORT:-5000}
read -p "Enter image tag/version (default: latest): " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-latest}

REGISTRY_URL="$REGISTRY_DOMAIN:$REGISTRY_PORT"

print_info "Registry: $REGISTRY_URL"
print_info "Tag: $IMAGE_TAG"
echo ""

# Login to registry
print_info "Logging in to registry..."
if ! docker login "$REGISTRY_URL"; then
    print_error "Failed to login to registry"
    exit 1
fi
print_success "Logged in to registry"

# Change to project root
cd "$PROJECT_ROOT"

# Build and push images
print_header "Building and Pushing Images..."
echo ""

# 1. OCR Worker
print_info "Building OCR Worker image..."
if docker-compose build ocr-worker; then
    print_success "OCR Worker image built"

    # Tag for registry
    print_info "Tagging OCR Worker image..."
    docker tag gvpocr-ocr-worker "$REGISTRY_URL/gvpocr/ocr-worker:$IMAGE_TAG"
    docker tag gvpocr-ocr-worker "$REGISTRY_URL/gvpocr/ocr-worker:$(git rev-parse --short HEAD)"
    print_success "Tagged OCR Worker image"

    # Push to registry
    print_info "Pushing OCR Worker to registry..."
    docker push "$REGISTRY_URL/gvpocr/ocr-worker:$IMAGE_TAG"
    docker push "$REGISTRY_URL/gvpocr/ocr-worker:$(git rev-parse --short HEAD)"
    print_success "Pushed OCR Worker image"
else
    print_error "Failed to build OCR Worker image"
fi

echo ""

# 2. Backend
print_info "Building Backend image..."
if docker-compose build backend; then
    print_success "Backend image built"

    # Tag for registry
    print_info "Tagging Backend image..."
    docker tag gvpocr-backend "$REGISTRY_URL/gvpocr/backend:$IMAGE_TAG"
    docker tag gvpocr-backend "$REGISTRY_URL/gvpocr/backend:$(git rev-parse --short HEAD)"
    print_success "Tagged Backend image"

    # Push to registry
    print_info "Pushing Backend to registry..."
    docker push "$REGISTRY_URL/gvpocr/backend:$IMAGE_TAG"
    docker push "$REGISTRY_URL/gvpocr/backend:$(git rev-parse --short HEAD)"
    print_success "Pushed Backend image"
else
    print_error "Failed to build Backend image"
fi

echo ""

# 3. Frontend
print_info "Building Frontend image..."
if docker-compose build frontend; then
    print_success "Frontend image built"

    # Tag for registry
    print_info "Tagging Frontend image..."
    docker tag gvpocr-frontend "$REGISTRY_URL/gvpocr/frontend:$IMAGE_TAG"
    docker tag gvpocr-frontend "$REGISTRY_URL/gvpocr/frontend:$(git rev-parse --short HEAD)"
    print_success "Tagged Frontend image"

    # Push to registry
    print_info "Pushing Frontend to registry..."
    docker push "$REGISTRY_URL/gvpocr/frontend:$IMAGE_TAG"
    docker push "$REGISTRY_URL/gvpocr/frontend:$(git rev-parse --short HEAD)"
    print_success "Pushed Frontend image"
else
    print_error "Failed to build Frontend image"
fi

echo ""
print_header "========================================="
print_header "  Images Pushed Successfully!"
print_header "========================================="
echo ""
print_success "All images have been pushed to $REGISTRY_URL"
echo ""
echo "Images pushed:"
echo "  - $REGISTRY_URL/gvpocr/ocr-worker:$IMAGE_TAG"
echo "  - $REGISTRY_URL/gvpocr/backend:$IMAGE_TAG"
echo "  - $REGISTRY_URL/gvpocr/frontend:$IMAGE_TAG"
echo ""
echo "Also tagged with commit hash: $(git rev-parse --short HEAD)"
echo ""
echo "To pull on worker machines:"
echo "  docker login $REGISTRY_URL"
echo "  docker pull $REGISTRY_URL/gvpocr/ocr-worker:$IMAGE_TAG"
echo ""
echo "View in registry UI:"
echo "  http://$REGISTRY_DOMAIN:8080"
echo ""
