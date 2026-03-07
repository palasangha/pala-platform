# Directory Setup and Structure

## Overview
This document describes the complete directory structure for the OCR Metadata Extraction service with all folders properly mapped in Docker Compose.

## Directory Structure

### 📁 Data Directories (`/data/`)
Main data storage for document collections (created locally)

```
data/
├── Bhushanji/          # Main document collection
├── newsletters/        # Newsletter documents
└── dhamma_for_all/     # Shared dhamma documents
```

**Docker Compose Mappings:**
- Backend: `./data/Bhushanji:/app/Bhushanji:ro`
- File Server: `./data/newsletters:/files/newsletters:ro`
- Workers: `./data/newsletters:/app/newsletters:ro`

### 📁 Shared Directories (`/shared/`)
Samba and SSH accessible shared storage

```
shared/
├── temp-images/        # Temporary image processing
├── uploads/           # User uploaded files
├── Bhushanji/         # Shared access to Bhushanji (can be symlink)
└── newsletters/       # Shared access to newsletters (can be symlink)
```

**Docker Compose Mappings:**
- Samba: `./shared/temp-images:/shared/temp-images`
- Samba: `./shared/uploads:/shared/uploads`
- SSH Server: `./shared/Bhushanji:/home/gvpocr/Bhushanji:ro`
- SSH Server: `./shared/uploads:/home/gvpocr/uploads`

### 📁 Backend Directories (`/backend/`)
Backend service files and uploads

```
backend/
├── app/                      # Application code
├── uploads/                  # Backend file uploads
├── google-credentials.json   # Google Cloud credentials (placeholder)
└── run.py                   # Main entry point
```

**Docker Compose Mappings:**
- Backend: `./backend/app:/app/app`
- Backend: `./backend/uploads:/app/uploads`
- Workers: `./backend/uploads:/app/uploads`

### 📁 Model Storage (`/models/`)
Storage for ML models

```
models/
└── [LlamaCPP, VLLM, and other ML models]
```

**Docker Compose Mappings:**
- LlamaCPP: `./models:/models`
- SSH Server: `./models:/home/gvpocr/models:ro`

### 📁 SSH Keys (`/ssh_keys/`)
SSH keys for remote worker deployment

```
ssh_keys/
└── [SSH public/private keys]
```

**Docker Compose Mappings:**
- Backend: `./ssh_keys:/app/ssh_keys:ro`

### 📁 Certificates (`/certs/`)
SSL/TLS certificates for HTTPS

```
certs/
└── [SSL certificates if using HTTPS]
```

**Docker Compose Mappings:**
- Caddy: `${CERTS_PATH:-./certs}:/certs:ro`

### 📁 Configuration Files
Required configuration files

```
.
├── .env                      # Environment variables (created)
├── Caddyfile                 # Caddy reverse proxy config
├── docker-compose.yml        # Main compose file
├── prometheus.yml            # Prometheus monitoring
├── alertmanager.yml          # Alert manager config
└── alerts.yml               # Prometheus alert rules
```

## Docker Named Volumes

These are managed by Docker and don't need manual creation:

- `mongodb_data` - MongoDB database storage
- `mongodb_config` - MongoDB configuration
- `ollama_data` - Ollama model storage
- `caddy_data` - Caddy certificates
- `caddy_config` - Caddy configuration
- `caddy_logs` - Caddy logs
- `prometheus_data` - Prometheus time-series data
- `grafana_data` - Grafana dashboards
- `grafana_provisioning` - Grafana provisioning
- `alertmanager_data` - Alertmanager data
- `registry_data` - Docker registry images
- `enrichment_logs` - Enrichment service logs
- `open_webui_data` - Open WebUI data
- `vllm_cache` - vLLM cache
- `llamacpp_models` - LlamaCPP models
- `bhushanji_shared` - Bind mount to GVPOCR_PATH

## Environment Variables

Key paths configured in `.env`:

```bash
GVPOCR_PATH=/mnt/sda1/prod/pala-platform/packages/processors/OCR_metadata_extraction/data/Bhushanji
CERTS_PATH=./certs
```

## Permissions

Some directories may be owned by root from Docker. To fix permissions:

```bash
# If needed, change ownership (requires sudo)
sudo chown -R $USER:$USER shared/ models/ ssh_keys/ backend/uploads/
```

## Verification

Run the verification script:

```bash
./setup_directories.sh
```

Should show:
```
✅ All required directories exist!
```

## Notes

1. **Data vs Shared**:
   - `data/` is the main storage
   - `shared/` provides Samba/SSH access (can symlink to data/)

2. **Read-Only Mounts**:
   - Most data mounts are `:ro` (read-only) to prevent accidental modification

3. **Google Credentials**:
   - Currently a placeholder directory
   - Should be replaced with actual JSON file for Google Cloud Vision

4. **Auto-Created on Startup**:
   - Docker volumes are auto-created
   - Local directories must exist before `docker-compose up`

## Quick Setup

All directories are created automatically. If you need to recreate:

```bash
mkdir -p data/{Bhushanji,newsletters,dhamma_for_all}
mkdir -p shared/{temp-images,uploads,Bhushanji,newsletters}
mkdir -p backend/uploads models ssh_keys certs
touch backend/google-credentials.json
```

## Summary

✅ **11 local directories** properly created and mapped
✅ **16 Docker named volumes** configured
✅ **All paths** mapped in docker-compose.yml
✅ **NSQ queues** auto-created at startup
✅ **Port range** 9000-9028 configured

The complete infrastructure is ready for production use!
