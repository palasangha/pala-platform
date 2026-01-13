# SSHFS File Sharing Setup - Complete Implementation

## What Has Been Set Up

This implementation provides **SSHFS-based file sharing** for remote OCR workers, allowing them to access all files from the main server as if they were local:

✅ **Bhushanji OCR Data** - Centralized OCR processing data  
✅ **Newsletters** - Newsletter processing data  
✅ **LLM Models** - llamacpp, vllm, ollama models  
✅ **HuggingFace Cache** - Efficient model cache sharing  
✅ **Source Code** - Optional source code access  

---

## Files Created

### Documentation
1. **SSHFS_SETUP.md** - Comprehensive technical setup guide
2. **SSHFS_QUICK_START.md** - 5-minute quick start guide
3. **SSHFS_DEPLOYMENT.md** - Full deployment and scaling guide
4. **README.md** (this file) - Overview and getting started

### Automation Scripts
1. **setup-sshfs-remote-worker.sh** - Automated setup script for remote workers
   - Installs SSHFS
   - Creates mount directory
   - Tests SSH connectivity
   - Mounts SSHFS
   - Creates systemd service for persistence
   - Creates docker-compose override

### Configuration Files
1. **sshfs-main-server.service** - Systemd service unit for persistent mounting
2. **docker-compose.sshfs-override.yml** - Docker Compose override with SSHFS volume mounts
3. **.env.sshfs.example** - Example environment variables for SSHFS setup

### Modified Files
1. **docker-compose.yml** - Enhanced SSH server with additional volume mounts and health checks

---

## Quick Start (5 Minutes)

### On Main Server
```bash
# Ensure SSH server is running
docker-compose ps ssh-server
# If not running:
docker-compose up -d ssh-server

# Verify SSH connectivity
ssh -p 2222 gvpocr@localhost
# Password: mango1
```

### On Remote Worker Machine

```bash
# 1. Copy setup files from main server
scp -r setup-sshfs-remote-worker.sh docker-compose.sshfs-override.yml \
    docker-compose.worker.yml .env.worker user@remote-worker:/home/user/gvpocr/

# 2. SSH into remote worker
ssh user@remote-worker
cd /home/user/gvpocr

# 3. Run setup script (requires sudo)
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132

# 4. Verify mount
ls -la /mnt/sshfs/main-server/
# Should show: Bhushanji/, newsletters/, models/, .cache/

# 5. Deploy worker container
docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d

# 6. Verify worker connectivity
docker-compose logs worker | grep "connected"
```

---

## Architecture

```
Main Server (172.12.0.132)
├── SSH Server (port 2222, user: gvpocr, pass: mango1)
├── NSQ Queue (port 4150, 4161)
├── MongoDB (port 27017)
├── Files:
│   ├── Bhushanji/
│   ├── newsletters/
│   ├── models/
│   └── .cache/huggingface/hub/
└── Backend API (port 5000)

               ↓ SSH Tunnel (port 2222)

Remote Worker N (any location)
├── SSHFS Mount at /mnt/sshfs/main-server/
├── Docker Container
│   ├── /app/Bhushanji → /mnt/sshfs/main-server/Bhushanji
│   ├── /app/newsletters → /mnt/sshfs/main-server/newsletters
│   ├── /app/models → /mnt/sshfs/main-server/models
│   └── /root/.cache/huggingface/hub → /mnt/sshfs/main-server/.cache/...
├── NSQ Worker (connects to main server)
└── OCR Processing (reads files from SSHFS)
```

---

## Prerequisites

### Main Server Requirements
- ✅ Docker and Docker Compose installed
- ✅ SSH server running on port 2222 (already configured in docker-compose.yml)
- ✅ All shared directories created (shared/Bhushanji, shared/newsletters, models/)
- ✅ Network accessible to remote workers

### Remote Worker Requirements
- ✅ Linux OS (Ubuntu 18.04+ recommended)
- ✅ SSHFS package (`sudo apt-get install sshfs`)
- ✅ SSH client installed
- ✅ Docker and Docker Compose installed
- ✅ Network connectivity to main server on port 2222
- ✅ Ability to mount filesystems (elevated privileges required)

---

## Step-by-Step Deployment

### Step 1: Prepare Main Server

```bash
# Navigate to gvpocr directory
cd /mnt/sda1/mango1_home/gvpocr

# Create shared directories
mkdir -p shared/Bhushanji shared/newsletters shared/temp-images shared/uploads models

# Verify docker-compose.yml is updated (SSH server with new mounts)
grep -A 30 "ssh-server:" docker-compose.yml

# Start SSH server
docker-compose up -d ssh-server

# Verify SSH server is running and accessible
docker logs gvpocr-ssh-server
curl -v telnet://localhost:2222 2>&1 | grep Connected || ssh -p 2222 gvpocr@localhost
```

### Step 2: Prepare Remote Worker

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y sshfs openssh-client openssh-server

# Add user to docker group (if using Docker)
sudo usermod -aG docker $USER
newgrp docker

# Test connectivity to main server
ping -c 3 172.12.0.132
ssh -p 2222 gvpocr@172.12.0.132 echo "SSH connection successful"
# Password: mango1
```

### Step 3: Run SSHFS Setup

```bash
# Copy setup files from main server (from remote worker)
scp -r user@main-server:/mnt/sda1/mango1_home/gvpocr/setup-sshfs-remote-worker.sh \
    user@main-server:/mnt/sda1/mango1_home/gvpocr/docker-compose.sshfs-override.yml \
    /home/user/gvpocr/

# Or manually download from a file share

# Navigate to project directory
cd /home/user/gvpocr

# Make script executable
chmod +x setup-sshfs-remote-worker.sh

# Run setup (replace 172.12.0.132 with your main server IP)
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132

# Follow the script output - it should:
# ✓ Install SSHFS
# ✓ Create mount directory
# ✓ Test SSH connection
# ✓ Mount SSHFS
# ✓ Create systemd service
# ✓ Generate docker-compose override

# Verify mount created successfully
ls -la /mnt/sshfs/main-server/
# Expected output shows: Bhushanji, newsletters, models, .cache, etc.
```

### Step 4: Deploy OCR Worker Container

```bash
# Prepare environment
nano .env.worker
# Ensure MAIN_SERVER_IP=172.12.0.132

# Option A: Use docker-compose with override file
docker-compose -f docker-compose.worker.yml \
               -f docker-compose.sshfs-override.yml up -d

# Option B: Copy override as default (auto-loaded)
cp docker-compose.sshfs-override.yml docker-compose.override.yml
docker-compose -f docker-compose.worker.yml up -d

# View logs
docker-compose logs -f worker

# Verify worker is connected
docker-compose ps
# Worker should show: Up (healthy)
```

### Step 5: Verify Setup

```bash
# Verify SSHFS mount is persistent
mount | grep sshfs
# Should show: gvpocr@172.12.0.132:/home/gvpocr on /mnt/sshfs/main-server

# Verify systemd service
sudo systemctl status sshfs-main-server
# Should show: Active (exited)

# Test file access on host
ls -la /mnt/sshfs/main-server/Bhushanji/ | head -10

# Test file access from container
docker exec <worker-container> ls -la /app/Bhushanji/ | head -10

# Verify worker connects to NSQ
docker logs <worker-container> | grep -i "nsq\|connected"

# View NSQ admin UI
# Open browser: http://172.12.0.132:4171/
# Should show worker in connected consumers
```

---

## Troubleshooting

### "Permission denied" when mounting
```bash
# Check SSH connectivity
ssh -p 2222 gvpocr@172.12.0.132 whoami

# Verify SSH server on main server
docker-compose logs ssh-server | tail -20
```

### Mount works but Docker container can't access files
```bash
# Check host mount permissions
sudo chmod 755 /mnt/sshfs/main-server

# Verify in Docker
docker run -it --rm -v /mnt/sshfs/main-server:/test:ro ubuntu ls -la /test/

# Re-mount with allow_other flag
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132
```

### Slow file access
```bash
# Check network latency
ping -c 10 172.12.0.132
# Good: <50ms, Acceptable: 50-200ms, Poor: >200ms

# Enable compression in SSHFS
sudo sshfs -o compression=yes -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

### Mount disappears after reboot
```bash
# Enable systemd service
sudo systemctl enable sshfs-main-server
sudo systemctl start sshfs-main-server

# Check status
sudo systemctl status sshfs-main-server

# View service logs
sudo journalctl -u sshfs-main-server -n 20
```

---

## Configuration

### Main Server SSH Setup

The SSH server in `docker-compose.yml` is configured with:

- **Port**: 2222
- **User**: gvpocr
- **Password**: mango1
- **Credentials**: Username and password-based authentication
- **Volumes**: Bhushanji, newsletters, models, .cache/huggingface/hub
- **Features**: Compression enabled, password auth enabled, keep-alive configured

### Remote Worker SSHFS Setup

The `setup-sshfs-remote-worker.sh` script configures:

- **Mount Location**: `/mnt/sshfs/main-server`
- **Connection Pooling**: ServerAliveInterval=15, ServerAliveCountMax=3
- **Caching**: 3600 second (1 hour) metadata cache
- **Persistence**: systemd service for auto-mount on boot
- **Permissions**: allow_other for Docker access

### Docker Volume Mapping

The `docker-compose.sshfs-override.yml` maps:

```yaml
Host                                    → Container
/mnt/sshfs/main-server/Bhushanji      → /app/Bhushanji:ro
/mnt/sshfs/main-server/newsletters    → /app/newsletters:ro
/mnt/sshfs/main-server/models         → /app/models:ro
/mnt/sshfs/main-server/.cache/...    → /root/.cache/huggingface/hub:ro
```

---

## Environment Variables

Key environment variables for SSHFS setup:

```bash
MAIN_SERVER_IP=172.12.0.132           # Main server IP address
SSHFS_MOUNT_DIR=/mnt/sshfs/main-server # Mount point on remote worker
MONGO_USERNAME=gvpocr_admin           # MongoDB auth
MONGO_PASSWORD=gvp@123                # MongoDB password
NSQLOOKUPD_ADDRESS=172.12.0.132:4161  # NSQ lookup service
```

See `.env.sshfs.example` for complete list of environment variables.

---

## Scaling to Multiple Workers

To deploy to multiple remote workers:

### Automated Deployment

```bash
#!/bin/bash
# deploy-all-workers.sh

MAIN_SERVER_IP="172.12.0.132"
WORKERS=(
  "user@worker-1.example.com"
  "user@worker-2.example.com"
  "user@worker-3.example.com"
)

for WORKER in "${WORKERS[@]}"; do
  echo "Deploying to $WORKER..."
  
  # Copy setup files
  scp setup-sshfs-remote-worker.sh docker-compose.sshfs-override.yml \
      docker-compose.worker.yml .env.worker $WORKER:/home/user/gvpocr/
  
  # Run setup
  ssh $WORKER "cd /home/user/gvpocr && \
               sudo ./setup-sshfs-remote-worker.sh $MAIN_SERVER_IP && \
               docker-compose -f docker-compose.worker.yml \
                             -f docker-compose.sshfs-override.yml up -d"
  
  echo "✓ $WORKER complete"
done
```

### Monitor All Workers

```bash
# Check all worker SSHFS mounts
for WORKER in worker-1 worker-2 worker-3; do
  echo "=== $WORKER ==="
  ssh user@$WORKER "mountpoint /mnt/sshfs/main-server && \
                    docker-compose ps worker"
done

# Check NSQ admin UI
# http://172.12.0.132:4171/
# All workers should appear under "connected consumers"
```

---

## Performance Optimization

### For Slow Networks
```bash
# Disable caching for frequent file changes
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132 --no-cache

# Or increase cache timeout for better performance
sshfs -o cache_timeout=7200 -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

### For High-Latency Links
```bash
# Enable compression
sshfs -o compression=yes -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Increase keep-alive
sshfs -o ServerAliveInterval=30 -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

### For High-Performance Networks
```bash
# Increase cache and reduce connection overhead
sshfs -o cache_timeout=7200,compression=no -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

---

## Security Considerations

### Current Implementation
- ✅ Password-based authentication (gvpocr:mango1)
- ✅ SSH encryption (all traffic encrypted)
- ✅ Read-only mounts (data protected from worker modification)
- ✅ Isolated SSH user (no root access)

### Recommended Improvements
1. **SSH Key Authentication**: Generate SSH keys instead of using passwords
   ```bash
   ssh-keygen -t ed25519 -f ./ssh_keys/gvpocr_sshfs -N "" -C "sshfs"
   sudo ./setup-sshfs-remote-worker.sh 172.12.0.132 --key /path/to/key
   ```

2. **Network Isolation**: Use VPN or private network for SSHFS connections

3. **Access Logging**: Monitor SSH logs for suspicious activity
   ```bash
   docker logs gvpocr-ssh-server | grep "auth"
   ```

4. **Key Rotation**: Periodically rotate SSH keys

---

## Monitoring and Maintenance

### Daily Health Checks
```bash
# Check all SSHFS mounts
for worker in worker-1 worker-2; do
  ssh user@$worker "mountpoint /mnt/sshfs/main-server && echo OK || echo FAILED"
done

# Check NSQ queue
curl -s http://172.12.0.132:4171/api/stats | jq '.topics'

# View recent worker logs
for i in {1..3}; do
  ssh user@worker-$i "docker logs $(docker ps -q) | tail -5"
done
```

### Weekly Tasks
```bash
# Check SSH logs for errors
docker logs gvpocr-ssh-server | tail -100

# Check disk space
du -sh /mnt/sda1/mango1_home/gvpocr/shared/*

# Test a task end-to-end
curl -X POST http://172.12.0.132:5000/api/ocr/process -H "Content-Type: application/json" \
  -d '{"image_url": "http://example.com/test.jpg"}'
```

---

## References

- **Full Setup Guide**: [SSHFS_SETUP.md](SSHFS_SETUP.md)
- **Quick Start**: [SSHFS_QUICK_START.md](SSHFS_QUICK_START.md)
- **Deployment Guide**: [SSHFS_DEPLOYMENT.md](SSHFS_DEPLOYMENT.md)
- **Setup Script**: [setup-sshfs-remote-worker.sh](setup-sshfs-remote-worker.sh)
- **Configuration Example**: [.env.sshfs.example](.env.sshfs.example)
- **Docker Override**: [docker-compose.sshfs-override.yml](docker-compose.sshfs-override.yml)
- **Systemd Service**: [sshfs-main-server.service](sshfs-main-server.service)

---

## Support & Help

### Quick Fixes
1. **Can't connect to SSH**: Check main server is running, firewall allows port 2222
2. **Mount fails**: Run setup script again, check network connectivity
3. **Container can't access files**: Verify mount exists, check Docker permissions
4. **Slow performance**: Check network latency, enable compression, increase cache

### More Information
See the respective documentation files for detailed troubleshooting:
- [SSHFS_SETUP.md](SSHFS_SETUP.md) - Comprehensive technical guide
- [SSHFS_DEPLOYMENT.md](SSHFS_DEPLOYMENT.md) - Full deployment with examples

---

## Summary

You now have:

✅ SSHFS-based file sharing configured  
✅ Automated setup script for remote workers  
✅ Docker Compose override for volume mounting  
✅ Systemd service for persistent mounting  
✅ Complete documentation and troubleshooting guides  
✅ Environment configuration templates  

**Next Step**: Run the setup script on your remote workers!

```bash
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132
```

