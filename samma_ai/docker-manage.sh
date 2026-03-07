#!/bin/bash

################################################################################
# Samma AI — Docker Management Script
#
# Usage:
#   ./docker-manage.sh build       Build all Docker images
#   ./docker-manage.sh up          Start all services in background
#   ./docker-manage.sh logs        Follow logs from all services
#   ./docker-manage.sh status      Check status of all services
#   ./docker-manage.sh down        Stop all services
#   ./docker-manage.sh restart     Restart all services
#   ./docker-manage.sh clean       Remove all containers and volumes
#   ./docker-manage.sh shell       Open bash in backend container
#   ./docker-manage.sh mongo       Connect to MongoDB shell
#   ./docker-manage.sh test        Test all service endpoints
################################################################################

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Utility Functions ─────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
log_success() { echo -e "${GREEN}✓  $1${NC}"; }
log_warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
log_error()   { echo -e "${RED}✗  $1${NC}"; }

header() {
    echo -e "\n${CYAN}━━━  $1  ━━━${NC}\n"
}

# ── Check Prerequisites ────────────────────────────────────────────────
check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    if ! command -v docker-compose &>/dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_success "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
    log_success "Docker Compose $(docker-compose --version | awk '{print $4}' | tr -d ',')"
}

# ── Build ──────────────────────────────────────────────────────────────
build_services() {
    header "Building Docker Images"

    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found"
        exit 1
    fi

    log_info "Building backend..."
    docker-compose build backend
    log_success "Backend built"

    log_info "Building frontend..."
    docker-compose build frontend
    log_success "Frontend built"

    log_success "All images built successfully"
}

# ── Up ─────────────────────────────────────────────────────────────────
start_services() {
    header "Starting Services"

    if [ ! -f ".env" ]; then
        log_warn ".env file not found"
        log_info "Creating from .env.docker..."
        cp .env.docker .env
        log_warn "Please edit .env with your API keys"
    fi

    log_info "Starting all services..."
    docker-compose up -d

    log_success "Services started"

    header "Waiting for Services to be Healthy"
    sleep 10

    status_check
}

# ── Status Check ────────────────────────────────────────────────────────
status_check() {
    header "Service Status"

    docker-compose ps

    echo ""
    log_info "Health Checks:"

    # Backend
    if curl -sf http://localhost:5001/api/health >/dev/null 2>&1; then
        log_success "Backend: http://localhost:5001/api/health"
    else
        log_warn "Backend: Not responding yet"
    fi

    # Frontend
    if curl -sf http://localhost:8080 >/dev/null 2>&1; then
        log_success "Frontend: http://localhost:8080"
    else
        log_warn "Frontend: Not responding yet"
    fi

    # MongoDB
    if docker-compose exec -T mongodb mongosh localhost:27017 --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
        log_success "MongoDB: mongodb://localhost:27018/samma_ai"
    else
        log_warn "MongoDB: Not responding yet"
    fi

    # Qdrant
    if curl -sf http://localhost:6334/health >/dev/null 2>&1; then
        log_success "Qdrant: http://localhost:6334/health"
    else
        log_warn "Qdrant: Not responding yet"
    fi

    echo ""
    cat << EOF
${GREEN}━━━  Services Available  ━━━${NC}

Frontend:  http://localhost:8080
Backend:   http://localhost:5001/api
MongoDB:   mongodb://localhost:27018
Qdrant:    http://localhost:6334

EOF
}

# ── Logs ───────────────────────────────────────────────────────────────
follow_logs() {
    header "Following Logs (Ctrl+C to exit)"
    docker-compose logs -f --tail=50
}

# ── Down ───────────────────────────────────────────────────────────────
stop_services() {
    header "Stopping Services"
    docker-compose down
    log_success "All services stopped"
}

# ── Restart ────────────────────────────────────────────────────────────
restart_services() {
    header "Restarting Services"
    docker-compose restart
    log_success "All services restarted"
    sleep 5
    status_check
}

# ── Clean ──────────────────────────────────────────────────────────────
clean_services() {
    header "Cleaning Up"

    log_warn "This will remove all containers and volumes"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Cancelled"
        return
    fi

    log_info "Removing containers and volumes..."
    docker-compose down -v
    log_success "Cleanup complete"
}

# ── Shell ──────────────────────────────────────────────────────────────
open_shell() {
    header "Opening Backend Shell"
    docker-compose exec backend bash
}

# ── MongoDB Shell ──────────────────────────────────────────────────────
open_mongo() {
    header "Connecting to MongoDB"
    docker-compose exec mongodb mongosh mongodb://localhost:27017/samma_ai
}

# ── Test Endpoints ─────────────────────────────────────────────────────
test_endpoints() {
    header "Testing API Endpoints"

    echo "${CYAN}Backend Health:${NC}"
    curl -s http://localhost:5001/api/health | jq . || log_warn "Backend not responding"

    echo ""
    echo "${CYAN}Backend Status:${NC}"
    curl -s http://localhost:5001/api/status | jq . || log_warn "Status endpoint not responding"

    echo ""
    echo "${CYAN}Frontend:${NC}"
    curl -s http://localhost:8080 | head -c 200
    echo ""

    echo ""
    echo "${CYAN}MongoDB Connection:${NC}"
    docker-compose exec -T mongodb mongosh localhost:27017/samma_ai --eval "db.adminCommand('ping')" || log_warn "MongoDB not responding"

    echo ""
    echo "${CYAN}Qdrant Health:${NC}"
    curl -s http://localhost:6334/health | jq . || log_warn "Qdrant not responding"
}

# ── Main ───────────────────────────────────────────────────────────────
main() {
    check_docker

    local command="${1:-help}"

    case "$command" in
        build)
            build_services
            ;;
        up)
            build_services
            start_services
            ;;
        logs)
            follow_logs
            ;;
        status)
            status_check
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        clean)
            clean_services
            ;;
        shell)
            open_shell
            ;;
        mongo)
            open_mongo
            ;;
        test)
            test_endpoints
            ;;
        *)
            cat << EOF
${CYAN}🧘 Samma AI — Docker Management${NC}

${BLUE}Usage:${NC}
  ./docker-manage.sh <command>

${BLUE}Commands:${NC}
  build       Build all Docker images
  up          Build and start all services
  logs        Follow logs from all services
  status      Check status of all services
  down        Stop all services
  restart     Restart all services
  clean       Remove containers and volumes
  shell       Open bash in backend container
  mongo       Connect to MongoDB shell
  test        Test all service endpoints

${BLUE}Quick Start:${NC}
  1. ./docker-manage.sh up      # Start all services
  2. ./docker-manage.sh logs    # View logs
  3. Open http://localhost:8080 # View frontend

EOF
            ;;
    esac
}

main "$@"
