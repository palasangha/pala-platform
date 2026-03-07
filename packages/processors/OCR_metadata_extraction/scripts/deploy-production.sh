#!/bin/bash
# Production Deployment Script
# Usage: ./scripts/deploy-production.sh [version]

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="${1:-latest}"
ENV_FILE="${PROJECT_DIR}/.env.production"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/logs/deployment_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${BACKUP_DIR}"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed"
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        error ".env.production file not found"
        exit 1
    fi

    # Check if required secrets are set
    if grep -q "CHANGE_ME" "$ENV_FILE"; then
        error ".env.production contains placeholder values (CHANGE_ME). Please update with real values."
        exit 1
    fi

    log "Prerequisites check passed"
}

# Backup database
backup_database() {
    log "Backing up MongoDB database..."

    BACKUP_FILE="${BACKUP_DIR}/mongodb_backup_$(date +%Y%m%d_%H%M%S).gz"

    # Get MongoDB credentials from .env
    MONGO_USER=$(grep MONGO_ROOT_USERNAME "$ENV_FILE" | cut -d '=' -f2)
    MONGO_PASS=$(grep MONGO_ROOT_PASSWORD "$ENV_FILE" | cut -d '=' -f2)

    # Create backup
    if docker exec gvpocr-mongodb-prod mongodump \
        --username="$MONGO_USER" \
        --password="$MONGO_PASS" \
        --authenticationDatabase=admin \
        --gzip \
        --archive=/tmp/backup.gz 2>> "$LOG_FILE"; then

        docker cp gvpocr-mongodb-prod:/tmp/backup.gz "$BACKUP_FILE"
        log "Database backed up to: $BACKUP_FILE"
    else
        warning "Database backup failed or MongoDB not running (first deployment?)"
    fi
}

# Pull latest code
update_code() {
    log "Updating code from repository..."
    cd "$PROJECT_DIR"

    # Check if git repository
    if [ -d .git ]; then
        git fetch origin
        git pull origin main
        log "Code updated successfully"
    else
        warning "Not a git repository, skipping code update"
    fi
}

# Pull Docker images
pull_images() {
    log "Pulling Docker images..."
    cd "$PROJECT_DIR"

    if docker-compose -f docker-compose.prod.yml pull 2>> "$LOG_FILE"; then
        log "Docker images pulled successfully"
    else
        error "Failed to pull Docker images"
        exit 1
    fi
}

# Build custom images
build_images() {
    log "Building custom Docker images..."
    cd "$PROJECT_DIR"

    export VERSION="$VERSION"
    export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    export VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    if docker-compose -f docker-compose.prod.yml build 2>> "$LOG_FILE"; then
        log "Docker images built successfully"
    else
        error "Failed to build Docker images"
        exit 1
    fi
}

# Stop services gracefully
stop_services() {
    log "Stopping services gracefully..."
    cd "$PROJECT_DIR"

    # Give services time to finish current requests
    docker-compose -f docker-compose.prod.yml stop 2>> "$LOG_FILE" || true

    log "Services stopped"
}

# Start services
start_services() {
    log "Starting services..."
    cd "$PROJECT_DIR"

    if docker-compose -f docker-compose.prod.yml up -d 2>> "$LOG_FILE"; then
        log "Services started successfully"
    else
        error "Failed to start services"
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to be healthy..."

    TIMEOUT=300  # 5 minutes
    ELAPSED=0
    INTERVAL=5

    while [ $ELAPSED -lt $TIMEOUT ]; do
        HEALTHY=$(docker ps --filter "health=healthy" --filter "name=gvpocr" --format "{{.Names}}" | wc -l)
        TOTAL=$(docker ps --filter "name=gvpocr" --format "{{.Names}}" | wc -l)

        info "Healthy containers: $HEALTHY/$TOTAL"

        if [ "$HEALTHY" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
            log "All services are healthy"
            return 0
        fi

        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    warning "Timeout waiting for services to be healthy"
    return 1
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    cd "$PROJECT_DIR"

    if [ -x ./health-check.sh ]; then
        if ./health-check.sh >> "$LOG_FILE" 2>&1; then
            log "Health checks passed"
            return 0
        else
            error "Health checks failed"
            return 1
        fi
    else
        warning "health-check.sh not found or not executable, skipping"
        return 0
    fi
}

# Cleanup old resources
cleanup() {
    log "Cleaning up old resources..."

    # Remove unused images
    docker image prune -f >> "$LOG_FILE" 2>&1 || true

    # Remove old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "mongodb_backup_*.gz" -mtime +7 -delete 2>/dev/null || true

    # Remove old logs (keep last 30 days)
    find "${PROJECT_DIR}/logs" -name "deployment_*.log" -mtime +30 -delete 2>/dev/null || true

    log "Cleanup completed"
}

# Rollback function
rollback() {
    error "Deployment failed, initiating rollback..."

    if [ -x "${SCRIPT_DIR}/rollback.sh" ]; then
        "${SCRIPT_DIR}/rollback.sh"
    else
        warning "Rollback script not found, manual intervention required"
    fi
}

# Main deployment flow
main() {
    log "========================================="
    log "Starting Production Deployment"
    log "Version: $VERSION"
    log "========================================="

    # Pre-deployment checks
    check_prerequisites

    # Backup
    backup_database

    # Update code
    update_code

    # Pull and build images
    pull_images
    build_images

    # Stop old services
    stop_services

    # Start new services
    start_services

    # Wait for services
    if ! wait_for_health; then
        rollback
        exit 1
    fi

    # Run health checks
    if ! run_health_checks; then
        rollback
        exit 1
    fi

    # Cleanup
    cleanup

    log "========================================="
    log "Deployment completed successfully!"
    log "Version: $VERSION"
    log "Log file: $LOG_FILE"
    log "========================================="
}

# Trap errors and rollback
trap 'error "Deployment failed on line $LINENO"; rollback; exit 1' ERR

# Run main
main
