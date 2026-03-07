# Scripts Directory

This directory contains all utility and deployment scripts organized by category.

## Directory Structure

```
scripts/
├── setup/              # Installation and setup scripts
├── deployment/         # Worker and service deployment
├── docker/            # Docker configuration and utilities
├── utilities/         # General utility scripts
└── examples/          # Example usage and integration scripts
```

## Setup Scripts (`setup/`)

Essential scripts for initial setup and installation.

### Core Setup
- **setup.sh** - Main installation script. Run this first to set up the project
- **build.sh** - Build the application
- **build_workers.sh** - Build worker containers

### Environment-Specific Setup
- **setup_llamacpp_mac.sh** - macOS-specific Llama.cpp setup
- **setup-sshfs-remote-worker.sh** - Configure passwordless SSHFS for remote workers

### Initial Configuration
- **SETUP_GITHUB.sh** - Initial GitHub setup (if needed)
- **download_gemma3_model.sh** - Download Gemma3 LLM model

## Deployment Scripts (`deployment/`)

Scripts for deploying and managing workers and services.

- **deploy-sshfs-worker.sh** - Deploy a worker using SSHFS
- **start-worker.sh** - Start worker process
- **start_lmstudio_bridge.sh** - Start LMStudio bridge service
- **swarm-manage.sh** - Manage Docker Swarm services

## Docker Scripts (`docker/`)

Docker configuration and management utilities.

- **DOCKER_QUICKSTART.sh** - Quick Docker setup guide (executable)
- **docker-entrypoint-worker.sh** - Docker entrypoint for worker containers
- **configure_remote_docker.sh** - Configure remote Docker daemon
- **configure_remote_docker_https.sh** - Configure remote Docker with HTTPS
- **configure_remote_docker_https_v2.sh** - HTTPS configuration v2
- **enable-docker-host-access.sh** - Enable Docker host access for containers

## Utility Scripts (`utilities/`)

General purpose utility and maintenance scripts.

- **verify-sshfs-setup.sh** - Verify SSHFS configuration is correct
- **open-firewall-port.sh** - Open firewall ports for services
- **upload.sh** - Upload utilities
- **getform.sh** - Form retrieval utility

## Example Scripts (`examples/`)

Example code and integration templates for reference.

### Integration Examples
- **LANGCHAIN_INTEGRATION_EXAMPLES.py** - LangChain integration patterns
- **extract_pdf_metadata.py** - PDF metadata extraction examples
- **extract_pdf_metadata_standalone.py** - Standalone PDF extraction
- **example_pdf_metadata.py** - Simple PDF metadata examples
- **example_lmstudio_usage.py** - LMStudio integration examples

### AMI Examples
- **ami_upload_bhushanji.py** - AMI upload example

### Configuration & Utilities
- **lmstudio_docker_bridge.py** - LMStudio Docker bridge example
- **check_ocr_provider_status.py** - Check OCR provider status
- **list_endpoints.py** - List available endpoints
- **fetch_do.py** - DigitalOcean integration example
- **fix_node_18.py** - Node 18 compatibility fixes
- **fix_node_233_metadata.py** - Node metadata fixes
- **diagnose_deployments.py** - Deployment diagnostics

## Quick Start

### Initial Setup (Run Once)
```bash
# Complete setup
cd scripts/setup/
./setup.sh

# Or platform-specific setup
./setup_llamacpp_mac.sh  # macOS
```

### Building
```bash
cd scripts/setup/
./build.sh              # Build main application
./build_workers.sh      # Build worker containers
```

### Deployment
```bash
cd scripts/deployment/
./start-worker.sh       # Start a worker
./swarm-manage.sh       # Manage swarm services
```

### Docker Setup
```bash
cd scripts/docker/
./DOCKER_QUICKSTART.sh  # Quick Docker setup
```

## Running Scripts

Most scripts require executable permissions:

```bash
# Make a script executable
chmod +x script_name.sh

# Run with bash
bash script_name.sh

# Or directly if executable
./script_name.sh
```

## Script Dependencies

Scripts may require:
- Bash shell
- Docker and Docker Compose
- Git
- Python 3.8+
- SSH/SSHFS utilities
- MongoDB (for some scripts)

## Common Issues

### Permission Denied
```bash
chmod +x scripts/setup/setup.sh
./scripts/setup/setup.sh
```

### Docker Connection Issues
```bash
# Check if Docker daemon is running
docker ps

# Run Docker setup
./scripts/docker/configure_remote_docker.sh
```

### Worker Deployment Issues
```bash
# Verify SSHFS
./scripts/utilities/verify-sshfs-setup.sh

# Check deployment logs
./scripts/deployment/deploy-sshfs-worker.sh
```

## Creating New Scripts

1. Create in appropriate subdirectory
2. Add shebang: `#!/bin/bash`
3. Add comments explaining purpose
4. Make executable: `chmod +x script_name.sh`
5. Add to this README with description

## Testing Scripts

Before deploying scripts:

```bash
# Test setup scripts in development first
bash scripts/setup/setup.sh --dry-run

# Check syntax
bash -n script_name.sh
```

## Support & Documentation

For detailed information, see:
- `../docs/DOCKER_QUICKSTART.md` - Docker setup guide
- `../docs/START_HERE.md` - Project overview
- `../docs/INDEX.md` - Complete documentation index

---

**Last Updated:** January 13, 2026
