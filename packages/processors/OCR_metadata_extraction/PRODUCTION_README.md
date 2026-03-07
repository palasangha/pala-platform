# Production Deployment Guide

Complete guide for deploying the OCR Metadata Extraction system to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Initial Setup](#initial-setup)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **CPU**: 4+ cores recommended
- **RAM**: 16GB minimum (8GB for small scale)
- **Disk**: 100GB+ SSD storage
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Network Requirements

- Public IP address (for production access)
- Domain name (recommended for SSL/TLS)
- Ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)

### Accounts & API Keys

- **GitHub** account (for CI/CD)
- **Anthropic API key** (for Claude AI - optional)
- **Docker Hub** or **GitHub Container Registry** (for images)

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/ocr-metadata-extraction.git
cd ocr-metadata-extraction

# Run initial setup
./scripts/setup-production.sh

# Edit configuration
nano .env.production  # Replace all CHANGE_ME values

# Deploy
./scripts/deploy-production.sh
```

## Initial Setup

### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
```

### 2. Configure Firewall

```bash
# Install UFW if not present
sudo apt install ufw

# Configure rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 3. Configure Environment

```bash
# Run setup script
./scripts/setup-production.sh

# This will:
# - Create .env.production with secure defaults
# - Generate random secrets
# - Create required directories
# - Pull Ollama models
# - Initialize MongoDB
# - Setup automated backups
```

### 4. Update Configuration Files

#### .env.production

Replace all `CHANGE_ME` values:

```bash
# Generate secure passwords
openssl rand -base64 32  # For MongoDB password
openssl rand -base64 64  # For JWT secrets
openssl rand -hex 32     # For API keys

# Edit file
nano .env.production
```

**Required changes:**
- `MONGO_ROOT_PASSWORD`
- `JWT_SECRET_KEY`
- `MCP_JWT_SECRET`
- `GRAFANA_ADMIN_PASSWORD`
- `ANTHROPIC_API_KEY` (if using Claude)
- `REACT_APP_API_URL` (your domain)
- `CORS_ORIGINS` (your domain)

#### Caddyfile

Replace `your-domain.com` with your actual domain:

```bash
nano Caddyfile
```

Example:

```
ocr.example.com {
    reverse_proxy frontend:80
    # ... rest of config
}
```

### 5. Setup SSL Certificates

Caddy automatically handles SSL with Let's Encrypt. Ensure:

1. Domain DNS points to your server IP
2. Ports 80 and 443 are accessible
3. Caddy will automatically obtain certificates

For manual SSL:

```bash
# Generate self-signed certificate (development only)
./generate-certs.sh

# Or use Let's Encrypt with certbot
sudo certbot certonly --standalone -d your-domain.com
```

## Deployment

### First Deployment

```bash
# Deploy all services
./scripts/deploy-production.sh

# This will:
# 1. Check prerequisites
# 2. Backup database (if exists)
# 3. Pull/build Docker images
# 4. Start services
# 5. Wait for health checks
# 6. Verify deployment
```

### Update Deployment

```bash
# Deploy new version
./scripts/deploy-production.sh v1.2.0

# Or using git tags
git tag v1.2.0
git push --tags
# CI/CD will auto-deploy
```

### Rollback

```bash
# Automatic rollback to previous state
./scripts/rollback.sh

# Or rollback to specific backup
./scripts/rollback.sh backups/mongodb_backup_20260307_120000.gz
```

### Using Make (Optional)

```bash
# View all commands
make help

# Deploy
make deploy

# View logs
make logs

# Backup database
make backup

# Rollback
make rollback
```

## Monitoring

### Access Dashboards

- **Grafana**: `https://your-domain.com/grafana`
  - Username: `admin`
  - Password: (from .env.production)
  - 5 pre-configured dashboards

- **Prometheus**: `https://your-domain.com:9090`
  - Metrics collection
  - Alert rules

- **NSQ Admin**: `http://your-server:4171`
  - Queue monitoring
  - Message stats

### Key Metrics to Monitor

1. **Completeness Score**
   - Target: ≥95%
   - Alert: <90%

2. **Processing Cost**
   - Target: ≤$0.50/doc
   - Alert: >$0.75/doc

3. **Queue Depth**
   - Target: <100 messages
   - Alert: >500 messages

4. **Processing Time**
   - Target: 120-240s/doc
   - Alert: >300s/doc

5. **Error Rate**
   - Target: <5%
   - Alert: >10%

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 enrichment-worker

# Search logs
docker-compose -f docker-compose.prod.yml logs | grep ERROR
```

### Alerts

Configured alerts (in `alerts.yml`):

- High error rate
- High cost per document
- Queue backlog
- Service down
- Low completeness
- Memory/CPU usage

Alerts sent to:
- Slack (if configured)
- Email (if configured)
- PagerDuty (if configured)

## Maintenance

### Daily Tasks

```bash
# Check service health
docker ps --filter "name=gvpocr" --format "table {{.Names}}\t{{.Status}}"

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# Check disk space
df -h

# Check metrics
curl -s http://localhost:9090/api/v1/query?query=up | jq
```

### Weekly Tasks

```bash
# Review metrics
# Access Grafana dashboards

# Check backups
ls -lh backups/

# Update system
sudo apt update && sudo apt upgrade -y

# Restart services (if needed)
docker-compose -f docker-compose.prod.yml restart
```

### Monthly Tasks

```bash
# Rotate logs
find logs/ -name "*.log" -mtime +30 -delete

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
./scripts/deploy-production.sh

# Review costs
curl http://localhost:5002/api/costs/summary | jq

# Database optimization
docker exec gvpocr-mongodb-prod mongo gvpocr --eval "db.runCommand({compact: 'enriched_documents'})"
```

### Backups

**Automated backups** run daily at 2:00 AM (configured in cron).

**Manual backup:**

```bash
./scripts/backup-db.sh
```

**Restore from backup:**

```bash
# List backups
ls -lh backups/

# Restore
./scripts/rollback.sh backups/mongodb_backup_20260307_120000.gz
```

**Backup retention:** 30 days (configurable in backup script)

### Scaling

For higher load:

```bash
# Increase worker replicas
docker-compose -f docker-compose.prod.yml up -d --scale enrichment-worker=3

# Or edit docker-compose.prod.yml:
# enrichment-worker:
#   deploy:
#     replicas: 3
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs service-name

# Check environment
docker-compose -f docker-compose.prod.yml config

# Rebuild
docker-compose -f docker-compose.prod.yml build --no-cache service-name
docker-compose -f docker-compose.prod.yml up -d service-name
```

### Low Completeness Score

```bash
# Check agent logs
docker logs gvpocr-enrichment-worker-prod | grep completeness

# Review failed extractions
docker logs gvpocr-enrichment-worker-prod | grep "failed with"

# Check Ollama models
docker exec gvpocr-ollama-prod ollama list

# Restart enrichment services
docker-compose -f docker-compose.prod.yml restart enrichment-worker enrichment-coordinator
```

### High Costs

```bash
# Check cost breakdown
curl http://localhost:5002/api/costs/breakdown | jq

# Reduce Claude usage
# Edit .env.production:
# OLLAMA_ENABLED=true
# (prefer Ollama over Claude)

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Queue Backlog

```bash
# Check NSQ status
curl http://localhost:4151/stats | jq

# Increase workers
docker-compose -f docker-compose.prod.yml up -d --scale enrichment-worker=3

# Clear stuck messages (CAUTION)
docker exec gvpocr-nsqd-prod nsq_to_file --topic=enrichment --channel=dead_letter
```

### Database Issues

```bash
# Check MongoDB status
docker exec gvpocr-mongodb-prod mongosh --eval "db.adminCommand('ping')"

# Check connections
docker exec gvpocr-mongodb-prod mongosh --eval "db.serverStatus().connections"

# Repair database
docker exec gvpocr-mongodb-prod mongosh gvpocr --eval "db.repairDatabase()"

# Restore from backup
./scripts/rollback.sh
```

### Out of Memory

```bash
# Check memory usage
docker stats --no-stream

# Increase swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Or reduce resource limits in docker-compose.prod.yml
```

## Security

### Best Practices

1. **Secrets Management**
   - Never commit `.env.production`
   - Use strong, random passwords
   - Rotate secrets quarterly

2. **Network Security**
   - Firewall enabled (UFW)
   - Only required ports open
   - Internal services on private network

3. **SSL/TLS**
   - Caddy auto-SSL with Let's Encrypt
   - HTTPS enforced
   - Strong ciphers only

4. **Database Security**
   - MongoDB authentication enabled
   - Strong passwords
   - No public access (127.0.0.1 only)

5. **Docker Security**
   - Non-root users in containers
   - Read-only filesystems where possible
   - Resource limits enforced

### Security Checklist

- [ ] Strong passwords for all services
- [ ] SSH key-based authentication only
- [ ] Firewall configured and enabled
- [ ] SSL/TLS certificates valid
- [ ] MongoDB authentication enabled
- [ ] Regular backups working
- [ ] Monitoring and alerts active
- [ ] Regular security updates
- [ ] Secrets not in git repository
- [ ] CORS configured correctly

### Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
./scripts/deploy-production.sh

# Update dependencies
cd backend && pip install -r requirements.txt --upgrade
cd frontend && npm update
```

## CI/CD Pipeline

### GitHub Actions Setup

1. **Add repository secrets** (Settings → Secrets):
   - `DEPLOY_SSH_KEY`: SSH private key for server
   - `PRODUCTION_SERVER`: Server IP/hostname
   - `PRODUCTION_USER`: SSH username
   - `DEPLOY_PATH`: Path to project on server
   - `SLACK_WEBHOOK`: Slack webhook URL (optional)

2. **Push to trigger deployment:**

```bash
git add .
git commit -m "feat: add new feature"
git push origin main
# Deployment starts automatically
```

3. **Create release:**

```bash
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
# Production deployment with version tag
```

### Pipeline Stages

1. **Lint**: Code quality checks
2. **Security**: Vulnerability scanning
3. **Test**: Unit and integration tests
4. **Build**: Docker image building
5. **E2E**: End-to-end tests
6. **Deploy**: Production deployment

### Manual Deployment

If CI/CD is not set up:

```bash
# SSH to server
ssh user@your-server

# Pull latest code
cd /path/to/project
git pull origin main

# Deploy
./scripts/deploy-production.sh
```

## Support

### Documentation

- [README.md](README.md) - Project overview
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Detailed deployment
- [PRODUCTION_DEPLOYMENT_CHECKLIST.md](PRODUCTION_DEPLOYMENT_CHECKLIST.md) - Checklist

### Logs Location

- Application logs: `./logs/`
- Docker logs: `docker-compose logs`
- System logs: `/var/log/syslog`

### Getting Help

1. Check logs first
2. Review troubleshooting section
3. Check GitHub issues
4. Contact support team

---

**Last Updated:** 2026-03-07
**Version:** 1.0.0
