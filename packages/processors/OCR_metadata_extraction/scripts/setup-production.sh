#!/bin/bash
# Initial Production Setup Script
# Usage: ./scripts/setup-production.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log "========================================="
log "Production Environment Setup"
log "========================================="

cd "$PROJECT_DIR"

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

log "Docker and docker-compose are installed"

# Create .env.production from template
if [ ! -f .env.production ]; then
    log "Creating .env.production from template..."
    cp .env.production .env.production.example 2>/dev/null || true

    warning "Please edit .env.production and replace all CHANGE_ME values with real secrets"
    warning "Generate strong passwords with: openssl rand -base64 32"

    # Generate some random secrets
    MONGO_PASS=$(openssl rand -base64 32)
    JWT_SECRET=$(openssl rand -base64 64)
    MCP_JWT=$(openssl rand -base64 32)

    info "Suggested secrets (save these securely):"
    echo "  MONGO_ROOT_PASSWORD: $MONGO_PASS"
    echo "  JWT_SECRET_KEY: $JWT_SECRET"
    echo "  MCP_JWT_SECRET: $MCP_JWT"

    read -p "Press Enter to continue after updating .env.production..."
else
    log ".env.production already exists"
fi

# Check for placeholder values
if grep -q "CHANGE_ME" .env.production; then
    error ".env.production still contains CHANGE_ME placeholders"
    error "Please update all secrets before continuing"
    exit 1
fi

log "Environment file validated"

# Create required directories
log "Creating required directories..."
mkdir -p backups logs uploads

# Create Caddyfile if not exists
if [ ! -f Caddyfile ]; then
    log "Creating Caddyfile..."
    cat > Caddyfile << 'EOF'
# Production Caddyfile
# Replace your-domain.com with your actual domain

your-domain.com {
    # Frontend
    reverse_proxy frontend:80

    # Backend API
    handle /api/* {
        reverse_proxy backend:5000
    }

    # Review API
    handle /review/* {
        reverse_proxy review-api:5001
    }

    # Cost API
    handle /cost/* {
        reverse_proxy cost-api:5002
    }

    # Grafana
    handle /grafana/* {
        reverse_proxy grafana:3000
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Enable gzip
    encode gzip

    # Logging
    log {
        output file /data/access.log
        format json
    }
}
EOF
    warning "Please edit Caddyfile and replace your-domain.com with your actual domain"
fi

# Pull Ollama models
log "Pulling Ollama models (this may take a while)..."
docker-compose -f docker-compose.prod.yml up -d ollama
sleep 10

docker exec gvpocr-ollama-prod ollama pull llama3.2 || warning "Failed to pull llama3.2"
docker exec gvpocr-ollama-prod ollama pull mixtral || warning "Failed to pull mixtral"

log "Ollama models pulled"

# Initialize MongoDB
log "Initializing MongoDB..."
docker-compose -f docker-compose.prod.yml up -d mongodb
sleep 15

# Create MongoDB init script if needed
if [ ! -f mongo/init-mongo.js ]; then
    mkdir -p mongo
    cat > mongo/init-mongo.js << 'EOF'
// MongoDB initialization script
db = db.getSiblingDB('gvpocr');

// Create collections with validation
db.createCollection('ocr_jobs');
db.createCollection('enriched_documents');
db.createCollection('review_queue');
db.createCollection('cost_records');

// Create indexes
db.ocr_jobs.createIndex({ job_id: 1 }, { unique: true });
db.ocr_jobs.createIndex({ status: 1 });
db.ocr_jobs.createIndex({ created_at: -1 });

db.enriched_documents.createIndex({ document_id: 1 }, { unique: true });
db.enriched_documents.createIndex({ 'quality_metrics.completeness_score': 1 });
db.enriched_documents.createIndex({ created_at: -1 });

db.review_queue.createIndex({ document_id: 1 });
db.review_queue.createIndex({ status: 1 });
db.review_queue.createIndex({ created_at: -1 });

db.cost_records.createIndex({ enrichment_job_id: 1 });
db.cost_records.createIndex({ created_at: -1 });

print('MongoDB initialization completed');
EOF
fi

log "MongoDB initialized"

# Setup firewall rules (if running on Linux)
if command -v ufw &> /dev/null; then
    warning "Firewall detected. Recommended rules:"
    info "  sudo ufw allow 80/tcp    # HTTP"
    info "  sudo ufw allow 443/tcp   # HTTPS"
    info "  sudo ufw allow 22/tcp    # SSH"
    info "  sudo ufw enable"
fi

# Setup systemd service (optional)
if [ -d /etc/systemd/system ]; then
    log "Creating systemd service..."
    sudo tee /etc/systemd/system/gvpocr.service > /dev/null << EOF
[Unit]
Description=GVPOCR Production Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PROJECT_DIR}
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable gvpocr.service

    log "Systemd service created and enabled"
    info "  Start: sudo systemctl start gvpocr"
    info "  Stop: sudo systemctl stop gvpocr"
    info "  Status: sudo systemctl status gvpocr"
fi

# Setup cron for backups
log "Setting up automated backups..."
CRON_CMD="0 2 * * * cd ${PROJECT_DIR} && ./scripts/backup-db.sh >> ${PROJECT_DIR}/logs/backup.log 2>&1"

(crontab -l 2>/dev/null || true; echo "$CRON_CMD") | sort -u | crontab - || true

log "Daily backups scheduled at 2:00 AM"

log "========================================="
log "Setup Complete!"
log "========================================="
log ""
log "Next steps:"
log "  1. Review and update Caddyfile with your domain"
log "  2. Verify .env.production has correct values"
log "  3. Deploy: ./scripts/deploy-production.sh"
log ""
log "Monitoring:"
log "  - Grafana: http://your-server:3001"
log "  - Prometheus: http://your-server:9090"
log "  - NSQ Admin: http://your-server:4171"
log ""
log "Backups: ${PROJECT_DIR}/backups/"
log "Logs: ${PROJECT_DIR}/logs/"
