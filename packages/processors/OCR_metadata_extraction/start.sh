#!/bin/bash
# OCR Metadata Extraction - One Command Startup Script
# Usage: ./start.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   OCR Metadata Extraction - Startup Script                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Step 1: Check Docker
print_status "Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi
print_success "Docker and Docker Compose found"

# Step 2: Create directories
print_status "Creating required directories..."
mkdir -p data/{Bhushanji,newsletters,dhamma_for_all}
mkdir -p backend/uploads
mkdir -p certs
print_success "Directories created"

# Check for root-owned directories and warn
if [ -d "shared" ] && [ "$(stat -c '%U' shared 2>/dev/null)" = "root" ]; then
    print_warning "Some directories are owned by root (from previous Docker runs)"
fi
if [ -d "models" ] && [ "$(stat -c '%U' models 2>/dev/null)" = "root" ]; then
    print_warning "Models directory is owned by root (from previous Docker runs)"
fi

# Step 3: Check .env file
print_status "Checking configuration files..."
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_status "Creating .env from template..."
    if [ -f ".env.docker" ]; then
        cp .env.docker .env
        print_warning "Please edit .env and set required values (MONGO_ROOT_PASSWORD, etc.)"
    else
        print_error "No .env template found!"
        exit 1
    fi
else
    print_success ".env file exists"
fi

# Check for google-credentials.json
if [ -d "backend/google-credentials.json" ]; then
    print_warning "backend/google-credentials.json is a directory, removing..."
    rmdir backend/google-credentials.json 2>/dev/null || rm -rf backend/google-credentials.json 2>/dev/null || true
fi
if [ ! -f "backend/google-credentials.json" ]; then
    print_warning "backend/google-credentials.json not found, creating placeholder"
    mkdir -p backend
    echo "{}" > backend/google-credentials.json
fi

# Step 4: Stop any existing containers
print_status "Stopping existing containers (if any)..."
docker-compose down 2>/dev/null || true
print_success "Cleaned up existing containers"

# Step 5: Pull/build images
print_status "Pulling and building Docker images..."
docker-compose build backend 2>&1 | grep -E "(Building|Successfully|ERROR)" || true

# Build enrichment services
print_status "Building enrichment services..."
docker build -t ocr_metadata_extraction-enrichment-coordinator -f enrichment_service/Dockerfile.coordinator . 2>&1 | grep -E "(Building|Successfully|ERROR|Step)" || true
docker build -t ocr_metadata_extraction-enrichment-worker -f enrichment_service/Dockerfile.worker . 2>&1 | grep -E "(Building|Successfully|ERROR|Step)" || true
print_success "Images ready"

# Step 6: Start core services first
print_status "Starting core services (MongoDB, NSQ, Ollama)..."
docker-compose up -d mongodb nsqlookupd nsqd ollama
sleep 5
print_success "Core services started"

# Step 7: Initialize NSQ topics
print_status "Initializing NSQ topics and channels..."
docker-compose up nsq-init 2>&1 | grep -v "Creating\|Attaching" || true
print_success "NSQ topics initialized"

# Step 8: Start remaining services (exclude enrichment services that need building)
print_status "Starting all services..."
docker-compose up -d --remove-orphans 2>&1 | grep -v "pull access denied" || true
sleep 10
print_success "Services started (some optional services may need building)"

# Step 9: Wait for services to be healthy
print_status "Waiting for services to be healthy (30 seconds)..."
sleep 30

# Step 10: Check service status
print_status "Checking service status..."
RUNNING=$(docker-compose ps --filter "status=running" --format "{{.Service}}" | wc -l)
TOTAL=$(docker-compose config --services | wc -l)

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Startup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Services Running:${NC} ${RUNNING} / ${TOTAL}"
echo ""

# Display access URLs
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Access Points                           ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Frontend:${NC}          http://localhost:9003                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Backend API:${NC}       http://localhost:9001/api              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}MongoDB:${NC}          localhost:9000                          ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Ollama:${NC}           http://localhost:9007                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Ollama UI:${NC}        http://localhost:9010                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}NSQ Admin:${NC}        http://localhost:9015                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Grafana:${NC}          http://localhost:9024                  ${BLUE}║${NC}"
echo -e "${BLUE}║${NC} ${GREEN}Prometheus:${NC}       http://localhost:9023                  ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show worker status
WORKERS=$(docker-compose ps ocr-worker --format "{{.Service}}" 2>/dev/null | wc -l)
if [ "$WORKERS" -gt 0 ]; then
    echo -e "${GREEN}OCR Workers:${NC} ${WORKERS} workers running"
else
    print_warning "OCR workers not started"
fi

# Check NSQ topics
TOPICS=$(curl -s http://localhost:9012/topics 2>/dev/null | grep -o '"topics":\[.*\]' | grep -o '\[.*\]' | tr -d '[]"' || echo "")
if [ -n "$TOPICS" ]; then
    echo -e "${GREEN}NSQ Topics:${NC} $TOPICS"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  ${GREEN}docker-compose ps${NC}              - View all services"
echo -e "  ${GREEN}docker-compose logs -f${NC}         - View all logs"
echo -e "  ${GREEN}docker-compose logs -f backend${NC} - View backend logs"
echo -e "  ${GREEN}docker-compose down${NC}            - Stop all services"
echo -e "  ${GREEN}docker-compose restart SERVICE${NC} - Restart a service"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Final health check
print_status "Running final health check..."
HEALTHY=$(docker-compose ps --filter "health=healthy" --format "{{.Service}}" 2>/dev/null | wc -l)
UNHEALTHY=$(docker-compose ps --filter "health=unhealthy" --format "{{.Service}}" 2>/dev/null | wc -l)

if [ "$UNHEALTHY" -gt 0 ]; then
    print_warning "$UNHEALTHY service(s) are unhealthy"
    echo -e "${YELLOW}Run 'docker-compose ps' to see details${NC}"
fi

if [ "$HEALTHY" -gt 0 ]; then
    print_success "$HEALTHY service(s) are healthy"
fi

echo ""
print_success "System is ready! Open http://localhost:9003 in your browser"
echo ""
