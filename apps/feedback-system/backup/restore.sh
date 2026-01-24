#!/bin/bash

set -e

if [ -z "$1" ]; then
  echo "Usage: ./restore.sh <backup_file.tar.gz>"
  echo "Available backups:"
  ls -lh /backups/*.tar.gz 2>/dev/null || echo "No backups found"
  exit 1
fi

BACKUP_FILE="/backups/$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "[$(date)] Starting restore from: $1"

# Extract backup
cd /backups
TEMP_DIR=$(basename "$1" .tar.gz)
tar -xzf "$1"

# Restore database
mongorestore \
  --host="${MONGO_HOST}" \
  --port="${MONGO_PORT}" \
  --username="${MONGO_USER}" \
  --password="${MONGO_PASSWORD}" \
  --db="${MONGO_DATABASE}" \
  --authenticationDatabase=admin \
  --dir="/backups/${TEMP_DIR}/${MONGO_DATABASE}" \
  --drop

# Cleanup extracted files
rm -rf "/backups/${TEMP_DIR}"

echo "[$(date)] Restore completed successfully!"
