#!/bin/bash
# Database Backup Script
# Usage: ./scripts/backup-db.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mongodb_backup_${TIMESTAMP}.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Starting MongoDB backup..."

# Get MongoDB credentials
ENV_FILE="${PROJECT_DIR}/.env.production"
MONGO_USER=$(grep MONGO_ROOT_USERNAME "$ENV_FILE" | cut -d '=' -f2)
MONGO_PASS=$(grep MONGO_ROOT_PASSWORD "$ENV_FILE" | cut -d '=' -f2)

# Create backup
docker exec gvpocr-mongodb-prod mongodump \
    --username="$MONGO_USER" \
    --password="$MONGO_PASS" \
    --authenticationDatabase=admin \
    --gzip \
    --archive=/tmp/backup.gz

# Copy from container
docker cp gvpocr-mongodb-prod:/tmp/backup.gz "$BACKUP_FILE"

# Calculate size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo "Backup completed: $BACKUP_FILE ($SIZE)"

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "mongodb_backup_*.gz" -mtime +30 -delete

echo "Old backups cleaned up"
