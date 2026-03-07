# Directory Structure for OCR Metadata Extraction

## Data Directories

### `/data/` - Main data storage (created locally)
- `Bhushanji/` - Main document collection
- `newsletters/` - Newsletter documents  
- `dhamma_for_all/` - Shared dhamma documents

### `/shared/` - Samba/SSH shared access
- `temp-images/` - Temporary image processing
- `uploads/` - User uploaded files
- `Bhushanji/` - Shared access to Bhushanji collection
- `newsletters/` - Shared access to newsletters

### `/backend/` - Backend service files
- `uploads/` - Backend file uploads
- `google-credentials.json` - Google Cloud credentials (placeholder)
- `app/` - Application code
- `run.py` - Main entry point

### `/models/` - ML model storage
- Storage for LlamaCPP, VLLM models

### `/ssh_keys/` - SSH keys for remote workers
- SSH public/private keys for worker deployment

### `/certs/` - SSL certificates
- TLS certificates for HTTPS (if using Caddyfile.https-backup)

## Docker Volumes (Named)
- `mongodb_data` - MongoDB database
- `ollama_data` - Ollama models  
- `caddy_data` - Caddy certificates
- `prometheus_data` - Prometheus metrics
- `grafana_data` - Grafana dashboards
- `registry_data` - Docker registry
- `enrichment_logs` - Enrichment service logs

## Files Required
- `.env` - Environment configuration (created)
- `Caddyfile` - Caddy configuration (exists)
- `prometheus.yml` - Prometheus config (if exists)
- `alertmanager.yml` - Alertmanager config (if exists)
- `alerts.yml` - Prometheus alerts (if exists)
- `docker-compose.yml` - Main compose file (exists)

