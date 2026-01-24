#!/bin/bash

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/${TIMESTAMP}"

echo "[$(date)] Starting backup..."

# Create backup
mongodump \
  --host="${MONGO_HOST}" \
  --port="${MONGO_PORT}" \
  --username="${MONGO_USER}" \
  --password="${MONGO_PASSWORD}" \
  --db="${MONGO_DATABASE}" \
  --authenticationDatabase=admin \
  --out="${BACKUP_DIR}"

# Compress backup
cd /backups
tar -czf "${TIMESTAMP}.tar.gz" "${TIMESTAMP}"
rm -rf "${TIMESTAMP}"

echo "[$(date)] Backup created: ${TIMESTAMP}.tar.gz"

# Get file size
FILE_SIZE=$(du -h "${TIMESTAMP}.tar.gz" | cut -f1)
echo "[$(date)] Backup size: ${FILE_SIZE}"

# Cleanup old backups (keep last BACKUP_RETENTION_DAYS days)
find /backups -name "*.tar.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} -delete

REMAINING=$(find /backups -name "*.tar.gz" -type f | wc -l)
echo "[$(date)] Old backups cleaned up. Remaining backups: ${REMAINING}"
echo "[$(date)] Backup completed successfully!"
