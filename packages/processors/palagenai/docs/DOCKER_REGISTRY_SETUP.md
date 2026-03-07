# Private Docker Registry Setup for GVPOCR

This guide explains how to set up and use a private Docker registry for your organization to distribute GVPOCR Docker images internally.

## Table of Contents
- [Why Use a Private Registry?](#why-use-a-private-registry)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Using the Registry](#using-the-registry)
- [Worker Deployment](#worker-deployment)
- [Troubleshooting](#troubleshooting)

---

## Why Use a Private Registry?

A private Docker registry allows you to:
- **Distribute images internally** without uploading to public registries
- **Version control** your Docker images
- **Faster deployment** on local networks
- **Security & compliance** - keep images within your infrastructure
- **Bandwidth savings** - pull images from local network instead of internet

---

## Quick Start

### 1. Setup the Registry (One-time setup on your server)

```bash
cd /path/to/gvpocr
./scripts/setup_docker_registry.sh
```

This will:
- Create a secure Docker registry with HTTPS
- Set up basic authentication
- Start a web UI for browsing images
- Generate SSL certificates

**Default ports:**
- Registry: `5000` (HTTPS)
- Web UI: `8080` (HTTP)

### 2. Build and Push Images

```bash
./scripts/push_to_registry.sh
```

Enter your registry details when prompted.

### 3. Configure Worker Machines

On each worker machine:

```bash
# Trust the registry certificate (Linux)
sudo mkdir -p /etc/docker/certs.d/YOUR_REGISTRY_IP:5000
sudo scp user@registry-server:/path/to/registry/certs/domain.crt \
    /etc/docker/certs.d/YOUR_REGISTRY_IP:5000/ca.crt
sudo systemctl restart docker

# Login to registry
docker login YOUR_REGISTRY_IP:5000
```

### 4. Pull and Run Images

```bash
# Pull the worker image
docker pull YOUR_REGISTRY_IP:5000/gvpocr/ocr-worker:latest

# Or use docker-compose with registry override
cd /path/to/gvpocr
export REGISTRY_URL=YOUR_REGISTRY_IP:5000
docker-compose -f docker-compose.yml -f docker-compose.registry.yml up -d
```

---

## Detailed Setup

### Registry Server Setup

#### Prerequisites
- Linux server with Docker installed
- Static IP address or domain name
- Sufficient disk space for images (recommend 50GB+)

#### Installation

1. **Run the setup script:**
   ```bash
   ./scripts/setup_docker_registry.sh
   ```

2. **During setup, you'll be asked for:**
   - Registry domain/IP (use server's IP address)
   - Registry username (default: `admin`)
   - Registry password (choose a strong password)

3. **The script will create:**
   ```
   ~/docker-registry/
   ├── data/              # Image storage
   ├── auth/              # Authentication files
   ├── certs/             # SSL certificates
   ├── docker-compose.yml # Registry configuration
   └── credentials.txt    # Login info
   ```

#### Registry Configuration

The registry is configured in `~/docker-registry/docker-compose.yml`:

```yaml
services:
  registry:
    image: registry:2
    ports:
      - "5000:5000"
    environment:
      REGISTRY_AUTH: htpasswd
      REGISTRY_HTTP_TLS_CERTIFICATE: /certs/domain.crt
      REGISTRY_HTTP_TLS_KEY: /certs/domain.key
    volumes:
      - ./data:/var/lib/registry
      - ./auth:/auth
      - ./certs:/certs

  registry-ui:
    image: joxit/docker-registry-ui:latest
    ports:
      - "8080:80"
    environment:
      REGISTRY_URL: "https://registry:5000"
```

#### Managing the Registry

```bash
cd ~/docker-registry

# Start registry
docker-compose up -d

# Stop registry
docker-compose down

# View logs
docker logs -f docker-registry

# Check status
docker-compose ps

# Restart registry
docker-compose restart
```

---

## Using the Registry

### Building and Pushing Images

#### Automated (Recommended)

```bash
./scripts/push_to_registry.sh
```

This script will:
1. Build all GVPOCR images (backend, frontend, worker)
2. Tag them with version and git commit hash
3. Push to your private registry

#### Manual

```bash
# Build images
docker-compose build

# Tag for registry
docker tag gvpocr-ocr-worker YOUR_REGISTRY:5000/gvpocr/ocr-worker:latest
docker tag gvpocr-backend YOUR_REGISTRY:5000/gvpocr/backend:latest
docker tag gvpocr-frontend YOUR_REGISTRY:5000/gvpocr/frontend:latest

# Login
docker login YOUR_REGISTRY:5000

# Push
docker push YOUR_REGISTRY:5000/gvpocr/ocr-worker:latest
docker push YOUR_REGISTRY:5000/gvpocr/backend:latest
docker push YOUR_REGISTRY:5000/gvpocr/frontend:latest
```

### Pulling Images

On any machine in your network:

```bash
# Login first
docker login YOUR_REGISTRY:5000

# Pull specific image
docker pull YOUR_REGISTRY:5000/gvpocr/ocr-worker:latest

# Pull specific version
docker pull YOUR_REGISTRY:5000/gvpocr/ocr-worker:v1.0.0
docker pull YOUR_REGISTRY:5000/gvpocr/ocr-worker:a88a141  # git commit hash
```

### Browsing Images (Web UI)

Open your browser: `http://YOUR_REGISTRY:8080`

The Web UI allows you to:
- Browse all images and tags
- View image details and layers
- Delete old images
- Search for images

---

## Worker Deployment

### Option 1: Using Registry Override

Create `.env` file in project root:
```bash
REGISTRY_URL=192.168.1.100:5000
IMAGE_TAG=latest
```

Run with registry override:
```bash
docker-compose -f docker-compose.yml -f docker-compose.registry.yml up -d
```

### Option 2: Direct Pull and Run

```bash
# Pull worker image
docker pull YOUR_REGISTRY:5000/gvpocr/ocr-worker:latest

# Run worker
docker run -d \
  --name ocr-worker \
  -e NSQLOOKUPD_ADDRESSES=queue-server:4161 \
  -e MONGODB_URI=mongodb://user:pass@db:27017/gvpocr \
  YOUR_REGISTRY:5000/gvpocr/ocr-worker:latest
```

### Option 3: Remote Worker Installation

Update `install_worker_one_liner.sh` to use registry images instead of building locally.

---

## Client Machine Configuration

### Linux

```bash
# 1. Copy certificate
sudo mkdir -p /etc/docker/certs.d/REGISTRY_IP:5000
sudo scp user@registry:/path/to/certs/domain.crt \
    /etc/docker/certs.d/REGISTRY_IP:5000/ca.crt

# 2. Restart Docker
sudo systemctl restart docker

# 3. Login
docker login REGISTRY_IP:5000

# 4. Test
docker pull REGISTRY_IP:5000/gvpocr/ocr-worker:latest
```

### macOS

```bash
# 1. Copy certificate
scp user@registry:/path/to/certs/domain.crt ~/

# 2. Add to keychain
sudo security add-trusted-cert -d -r trustRoot \
    -k /Library/Keychains/System.keychain ~/domain.crt

# 3. Restart Docker Desktop
# (Right-click Docker icon > Quit Docker Desktop > Start Docker Desktop)

# 4. Login
docker login REGISTRY_IP:5000

# 5. Test
docker pull REGISTRY_IP:5000/gvpocr/ocr-worker:latest
```

### Windows

1. Copy `domain.crt` to Windows machine
2. Double-click certificate → Install Certificate
3. Choose "Local Machine" → "Trusted Root Certification Authorities"
4. Restart Docker Desktop
5. Open PowerShell:
   ```powershell
   docker login REGISTRY_IP:5000
   docker pull REGISTRY_IP:5000/gvpocr/ocr-worker:latest
   ```

---

## Troubleshooting

### Cannot Connect to Registry

**Error:** `connection refused` or `timeout`

**Solutions:**
1. Check if registry is running:
   ```bash
   docker ps | grep registry
   ```

2. Check firewall:
   ```bash
   # Allow port 5000
   sudo ufw allow 5000/tcp
   sudo ufw reload
   ```

3. Verify network connectivity:
   ```bash
   ping REGISTRY_IP
   telnet REGISTRY_IP 5000
   ```

### Certificate Errors

**Error:** `x509: certificate signed by unknown authority`

**Solutions:**
1. Verify certificate is copied correctly:
   ```bash
   ls -la /etc/docker/certs.d/REGISTRY_IP:5000/
   ```

2. Check certificate validity:
   ```bash
   openssl x509 -in /path/to/domain.crt -text -noout
   ```

3. Restart Docker after adding certificate:
   ```bash
   sudo systemctl restart docker
   ```

### Authentication Failures

**Error:** `401 Unauthorized`

**Solutions:**
1. Check credentials:
   ```bash
   cat ~/docker-registry/credentials.txt
   ```

2. Re-login:
   ```bash
   docker logout REGISTRY_IP:5000
   docker login REGISTRY_IP:5000
   ```

3. Verify htpasswd file:
   ```bash
   cat ~/docker-registry/auth/htpasswd
   ```

### Disk Space Issues

**Error:** `no space left on device`

**Solutions:**
1. Check disk usage:
   ```bash
   df -h ~/docker-registry/data
   ```

2. Remove old images:
   - Use Web UI to delete old tags
   - Run garbage collection:
     ```bash
     docker exec docker-registry bin/registry garbage-collect \
       /etc/docker/registry/config.yml
     ```

3. Configure storage limits in `docker-compose.yml`

### Slow Pulls/Pushes

**Solutions:**
1. Check network speed:
   ```bash
   iperf3 -c REGISTRY_IP
   ```

2. Use compression:
   ```bash
   docker pull --compress REGISTRY_IP:5000/gvpocr/ocr-worker:latest
   ```

3. Consider setting up a registry cache/mirror

---

## Advanced Configuration

### Enable Image Deletion

Already enabled by default in the setup script:
```yaml
REGISTRY_STORAGE_DELETE_ENABLED: "true"
```

### Set Up Registry Mirror/Cache

For frequently accessed external images, configure a pull-through cache.

### Backup Registry Data

```bash
# Backup
tar -czf registry-backup-$(date +%Y%m%d).tar.gz \
    ~/docker-registry/data

# Restore
tar -xzf registry-backup-20250101.tar.gz -C ~/docker-registry/
```

### Monitoring

```bash
# Registry stats
curl -k -u admin:password https://REGISTRY_IP:5000/v2/_catalog

# Image tags
curl -k -u admin:password \
    https://REGISTRY_IP:5000/v2/gvpocr/ocr-worker/tags/list
```

---

## Security Best Practices

1. **Use Strong Passwords**: Generate random passwords for registry authentication
2. **Keep Certificates Updated**: Renew SSL certificates before expiry
3. **Regular Backups**: Backup registry data weekly
4. **Network Isolation**: Use firewall rules to restrict registry access
5. **Monitor Access**: Review registry logs regularly
6. **Update Registry**: Keep registry image updated
7. **Scan Images**: Use tools like `trivy` to scan for vulnerabilities

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `setup_docker_registry.sh` | Initial registry setup |
| `push_to_registry.sh` | Build and push GVPOCR images |
| `update_and_restart_docker_workers.sh` | Update local workers from registry |

---

## Support

For issues or questions:
- Check logs: `docker logs docker-registry`
- Web UI: `http://REGISTRY_IP:8080`
- Registry API: `https://REGISTRY_IP:5000/v2/`
