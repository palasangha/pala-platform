#!/bin/bash
# Production deployment setup script
# Run with: sudo bash scripts/setup-prod.sh
# OR: run individual sections as needed

set -e

SRC="/mnt/sda1/mango1_home/pala-platform/packages/processors/OCR_metadata_extraction"
PROD_DIR="/mnt/sda1/prod/ocr-prod"

echo "=== Step 1: Create prod user and directories ==="
useradd -m -d /mnt/sda1/prod -s /bin/bash prod 2>/dev/null || echo "User 'prod' already exists"
mkdir -p "$PROD_DIR"
chown -R prod:prod /mnt/sda1/prod

echo "=== Step 2: Symlink application assets ==="
cd "$PROD_DIR"

# Symlink directories
for dir in backend frontend enrichment_service ssh_keys models grafana_provisioning shared data; do
    if [ -e "$SRC/$dir" ]; then
        ln -sfn "$SRC/$dir" "$PROD_DIR/$dir"
        echo "  linked: $dir"
    fi
done

# Symlink certs from existing CERTS_PATH
CERTS_PATH="/mnt/sda1/mango1_home/gvpocr/certs"
if [ -d "$CERTS_PATH" ]; then
    ln -sfn "$CERTS_PATH" "$PROD_DIR/certs"
    echo "  linked: certs -> $CERTS_PATH"
fi

# Symlink config files
for file in prometheus.yml alerts.yml alertmanager.yml; do
    if [ -e "$SRC/$file" ]; then
        ln -sfn "$SRC/$file" "$PROD_DIR/$file"
        echo "  linked: $file"
    fi
done

# Symlink Dockerfiles
for f in Dockerfile worker.Dockerfile llama.cpp.Dockerfile lmstudio.Dockerfile lmstudio_entrypoint.sh; do
    if [ -e "$SRC/$f" ]; then
        ln -sfn "$SRC/$f" "$PROD_DIR/$f"
        echo "  linked: $f"
    fi
done

# Symlink google-credentials if it exists in backend
if [ -e "$SRC/backend/google-credentials.json" ]; then
    ln -sfn "$SRC/backend/google-credentials.json" "$PROD_DIR/google-credentials.json"
    echo "  linked: google-credentials.json"
fi

# Copy (not symlink) production config files
cp "$SRC/.env.prod" "$PROD_DIR/.env.prod"
cp "$SRC/Caddyfile.prod" "$PROD_DIR/Caddyfile.prod"
cp "$SRC/docker-compose.prod.yml" "$PROD_DIR/docker-compose.prod.yml"
echo "  copied: .env.prod, Caddyfile.prod, docker-compose.prod.yml"

echo ""
echo "=== Step 3: Fix ownership ==="
chown -R prod:prod "$PROD_DIR"
# But keep symlink targets owned by mango1 (they are read-only mounts)

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To deploy, run:"
echo "  cd $PROD_DIR"
echo "  docker compose -p prod -f docker-compose.prod.yml --env-file .env.prod up -d --build"
echo ""
echo "To test:"
echo "  curl http://localhost:9000            # frontend"
echo "  curl http://localhost:9030/api/tags   # Ollama"
echo "  curl http://localhost:9031/v1/models  # LMStudio"
echo "  curl http://localhost:9014            # NSQ Admin"
echo "  curl http://localhost:9050/-/healthy  # Prometheus"
