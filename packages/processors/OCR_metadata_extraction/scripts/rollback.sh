#!/bin/bash
# Production Rollback Script
# Usage: ./scripts/rollback.sh [backup_file]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log "========================================="
log "Starting Rollback Process"
log "========================================="

cd "$PROJECT_DIR"

# Find latest backup
BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/mongodb_backup_*.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        warning "No backup file found, skipping database restore"
    else
        log "Using latest backup: $BACKUP_FILE"
    fi
fi

# Stop current services
log "Stopping current services..."
docker-compose -f docker-compose.prod.yml down

# Restore database if backup exists
if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    log "Restoring database from backup..."

    # Start only MongoDB
    docker-compose -f docker-compose.prod.yml up -d mongodb
    sleep 10

    # Get credentials
    MONGO_USER=$(grep MONGO_ROOT_USERNAME .env.production | cut -d '=' -f2)
    MONGO_PASS=$(grep MONGO_ROOT_PASSWORD .env.production | cut -d '=' -f2)

    # Copy backup to container
    docker cp "$BACKUP_FILE" gvpocr-mongodb-prod:/tmp/backup.gz

    # Restore backup
    docker exec gvpocr-mongodb-prod mongorestore \
        --username="$MONGO_USER" \
        --password="$MONGO_PASS" \
        --authenticationDatabase=admin \
        --gzip \
        --archive=/tmp/backup.gz \
        --drop

    log "Database restored successfully"
fi

# Checkout previous git commit
if [ -d .git ]; then
    log "Rolling back code to previous commit..."
    git reset --hard HEAD~1
    log "Code rolled back"
fi

# Pull previous images
log "Pulling previous Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Rebuild with previous code
log "Rebuilding images..."
docker-compose -f docker-compose.prod.yml build

# Start services
log "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for health
log "Waiting for services to be healthy..."
sleep 30

# Run health check
if [ -x ./health-check.sh ]; then
    ./health-check.sh
fi

log "========================================="
log "Rollback completed"
log "========================================="
