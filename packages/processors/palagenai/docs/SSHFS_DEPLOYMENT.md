# SSHFS Deployment Guide for OCR Worker Network

Complete guide for deploying SSHFS-based file sharing for remote OCR workers.

## Overview

This setup allows all remote workers to access:
- **Bhushanji data** (main OCR processing data)
- **Newsletters** (newsletter processing data)
- **Models** (LLM models for llamacpp, vllm, ollama)
- **HuggingFace cache** (model cache for efficient loading)
- **Source code** (optional)

All accessible as if they were local files via SSHFS mounts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Main Server (172.12.0.132)                              │
├─────────────────────────────────────────────────────────┤
│ SSH Server (port 2222)                                  │
│   └─ /home/gvpocr/                                      │
│      ├─ Bhushanji/        (→ ./shared/Bhushanji)        │
│      ├─ newsletters/      (→ ./shared/newsletters)      │
│      ├─ models/           (→ ./models)                  │
│      └─ .cache/huggingface/hub/                         │
└─────────────────────────────────────────────────────────┘
           │
           │ SSH Port 2222
           │ (gvpocr:mango1)
           │
      ┌────┴────┬──────────┬──────────┐
      │          │          │          │
   Remote    Remote    Remote    Remote
   Worker-1  Worker-2  Worker-3  Worker-N
   (Ubuntu)  (Ubuntu)  (Ubuntu)  (Ubuntu)
      │          │          │          │
      ├─ SSHFS mount at /mnt/sshfs/main-server
      │
      ├─ docker-compose.worker.yml
      │  └─ Worker Container
      │     ├─ /app/Bhushanji → /mnt/sshfs/main-server/Bhushanji
      │     ├─ /app/newsletters → /mnt/sshfs/main-server/newsletters
      │     ├─ /app/models → /mnt/sshfs/main-server/models
      │     └─ /root/.cache/huggingface/hub → /mnt/sshfs/main-server/.cache/...
      │
      └─ NSQ Worker connects to main server
         (MongoDB, NSQ at 172.12.0.132)
```

---

## Phase 1: Prepare Main Server

### 1.1: Create Shared Directories (if not already present)

```bash
# On main server, in the gvpocr project directory
mkdir -p shared/Bhushanji
mkdir -p shared/newsletters
mkdir -p shared/temp-images
mkdir -p shared/uploads
mkdir -p models

# Set permissions
chmod 755 shared/Bhushanji
chmod 755 shared/newsletters
chmod 755 models
```

### 1.2: Verify SSH Server Service

```bash
# Check SSH server is running
docker ps | grep ssh-server

# Should see: gvpocr-ssh-server

# If not running, start it
docker-compose up -d ssh-server

# Test SSH connectivity from main server
ssh -p 2222 gvpocr@localhost
# Should accept password: mango1
```

### 1.3: Verify Docker Compose Updated

The docker-compose.yml has been updated with:
- Enhanced SSH server configuration
- Additional volume mounts for models and cache
- Health check for SSH server
- Compression enabled for faster transfers

---

## Phase 2: Prepare Remote Worker Machine

### 2.1: Ensure Prerequisites Installed

```bash
# Install SSHFS and SSH client
sudo apt-get update
sudo apt-get install -y sshfs openssh-client openssh-server

# Install Docker (if not already present)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo bash get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2.2: Verify Network Connectivity

```bash
# Test connectivity to main server
ping -c 5 172.12.0.132

# Test SSH connectivity
ssh -p 2222 -v gvpocr@172.12.0.132 echo "Connected"
# Should ask for password: mango1

# Test file access
ssh -p 2222 gvpocr@172.12.0.132 ls -la /home/gvpocr/
# Should list: Bhushanji/, newsletters/, models/, .cache/, etc.
```

### 2.3: Copy Setup Files to Remote Worker

```bash
# From your local machine or main server
scp setup-sshfs-remote-worker.sh docker-compose.sshfs-override.yml docker-compose.worker.yml .env.worker user@remote-worker:/home/user/gvpocr/

# Or directly from main server
docker cp /mnt/sda1/mango1_home/gvpocr/setup-sshfs-remote-worker.sh <container>:/tmp/
```

---

## Phase 3: Run SSHFS Setup on Remote Worker

### 3.1: Execute Setup Script

```bash
# SSH into remote worker
ssh user@remote-worker

# Navigate to project directory
cd /path/to/gvpocr

# Run setup script
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132
```

**Output should show:**
```
[INFO] SSHFS Setup for Remote OCR Workers
[SUCCESS] SSHFS is already installed
[SUCCESS] Mount directory created: /mnt/sshfs/main-server
[SUCCESS] SSH connection successful
[SUCCESS] SSHFS mount successful
[SUCCESS] Mount point verified
[SUCCESS] Systemd service created: /etc/systemd/system/sshfs-main-server.service
[SUCCESS] Service enabled
```

### 3.2: Verify Mount

```bash
# List mounted files
ls -la /mnt/sshfs/main-server/

# Expected output:
# drwxr-xr-x  Bhushanji/
# drwxr-xr-x  newsletters/
# drwxr-xr-x  models/
# drwxr-xr-x  .cache/
# drwxr-xr-x  uploads/
# drwxr-xr-x  temp-images/
# drwxr-xr-x  source/

# Test file access
cat /mnt/sshfs/main-server/Bhushanji/some-file.txt
# Should display file contents without errors
```

### 3.3: Verify Persistent Mount

```bash
# Check systemd service
sudo systemctl status sshfs-main-server

# Expected output: Active (exited) with RemainAfterExit=yes

# Check mount point
mountpoint /mnt/sshfs/main-server
# Should output: /mnt/sshfs/main-server is a mountpoint

# After reboot, verify mount still exists
sudo reboot
# ... wait for reboot ...
ls /mnt/sshfs/main-server/
# Should still be accessible
```

---

## Phase 4: Deploy OCR Worker Container

### 4.1: Configure Environment

```bash
# Edit .env.worker with main server settings
nano .env.worker

# Ensure these variables are set:
MAIN_SERVER_IP=172.12.0.132
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=gvp@123
NSQLOOKUPD_ADDRESS=172.12.0.132:4161
```

### 4.2: Deploy with Docker Compose

```bash
# Method 1: Use override file
docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d

# Method 2: Copy override as default
cp docker-compose.sshfs-override.yml docker-compose.override.yml
docker-compose -f docker-compose.worker.yml up -d

# Check status
docker-compose ps
```

### 4.3: Verify Container Startup

```bash
# View logs
docker-compose logs -f worker

# Expected logs:
# Connecting to MongoDB at mongodb://...
# Connecting to NSQ at ...
# Mounting volumes...
# Starting OCR worker...
# [OK] Connected to NSQ

# Check container is running
docker-compose ps worker
# Should show: Up (healthy)
```

### 4.4: Verify File Access from Container

```bash
# Test Bhushanji access
docker exec <worker-container> ls -la /app/Bhushanji/

# Test newsletters access
docker exec <worker-container> ls -la /app/newsletters/

# Test models access
docker exec <worker-container> ls -la /app/models/

# Test model cache access
docker exec <worker-container> ls -la /root/.cache/huggingface/hub/

# All should return directory listings without errors
```

---

## Phase 5: Verify OCR Processing

### 5.1: Check Worker Connection to NSQ

```bash
# View NSQ admin UI
# Open: http://172.12.0.132:4171/

# Verify worker appears in connected workers list
# Should show: <worker-container-id> Connected from remote-worker-ip

# Check message queue
# Topics should show: ocr_tasks
# Should have connected consumers
```

### 5.2: Test OCR Task Processing

```bash
# Send test task to NSQ (from main server or any machine)
curl -X POST http://172.12.0.132:5000/api/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "http://example.com/test.jpg",
    "ocr_provider": "tesseract"
  }'

# Check worker processes the task
docker-compose logs -f worker | grep "Processing task"

# Verify task completes
curl http://172.12.0.132:5000/api/ocr/status/<task_id>
# Should show completed status
```

### 5.3: Monitor Performance

```bash
# Watch SSHFS mount usage
watch -n 5 'df -h /mnt/sshfs/main-server && echo "---" && mount | grep sshfs'

# Monitor network traffic
iftop -i eth0
# Should see SSH traffic to main server

# Check worker resource usage
docker stats <worker-container>
# Monitor CPU, memory, and network I/O
```

---

## Phase 6: Scale to Multiple Remote Workers

### 6.1: Repeat Setup for Each Remote Worker

```bash
# For each additional remote worker:
ssh user@remote-worker-2
cd /path/to/gvpocr
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132
docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d
```

### 6.2: Automated Deployment Script

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
      docker-compose.worker.yml .env.worker \
      $WORKER:/home/user/gvpocr/
  
  # Run setup
  ssh $WORKER "cd /home/user/gvpocr && \
               sudo ./setup-sshfs-remote-worker.sh $MAIN_SERVER_IP && \
               docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d"
  
  echo "✓ $WORKER deployment complete"
done

echo "All workers deployed successfully!"
```

### 6.3: Verify All Workers Connected

```bash
# Check NSQ admin UI at http://172.12.0.132:4171/
# Should list all worker containers under connected consumers

# Alternative: Check from main server MongoDB
docker-compose exec mongodb mongosh -u gvpocr_admin -p gvp@123 \
  --eval "db.workers.find().pretty()"

# Should show all registered workers with their IPs
```

---

## Troubleshooting Guide

### Issue: SSHFS Mount Fails with "Connection refused"

**Cause**: SSH server not running on main server

**Solution**:
```bash
# On main server
docker-compose up -d ssh-server

# Or check container
docker ps | grep ssh-server
docker logs gvpocr-ssh-server
```

### Issue: SSHFS Mount Works but Container Can't Access Files

**Cause**: Mount not accessible to Docker container

**Solution**:
```bash
# Check host mount
ls -la /mnt/sshfs/main-server/

# Check container mount
docker exec <container> ls -la /app/Bhushanji/

# If host works but container doesn't, check Docker permission
sudo chmod 755 /mnt/sshfs/main-server

# Remount with allow_other
sudo umount /mnt/sshfs/main-server
sudo sshfs -o allow_other,default_permissions -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

### Issue: Slow File Access from Remote Workers

**Cause**: Network latency or insufficient cache

**Solution**:
```bash
# Enable compression
sshfs -o compression=yes -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Increase cache timeout
sshfs -o cache_timeout=3600 -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Check network latency
ping -c 10 172.12.0.132
# Acceptable: <50ms, Borderline: 50-200ms, Poor: >200ms
```

### Issue: Mount Disconnects After Idle Period

**Cause**: Network timeout or SSH keep-alive issue

**Solution**:
```bash
# Mount with improved keep-alive settings
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132
# Already includes ServerAliveInterval=15 and ServerAliveCountMax=3

# Or restart service
sudo systemctl restart sshfs-main-server

# Check service logs
sudo journalctl -u sshfs-main-server -n 50
```

### Issue: Workers Can't Connect to NSQ on Main Server

**Cause**: Network routing or firewall issue

**Solution**:
```bash
# Test NSQ connectivity from remote worker
nc -zv 172.12.0.132 4150
nc -zv 172.12.0.132 4161

# If fails, check firewall on main server
sudo ufw status
sudo ufw allow 4150
sudo ufw allow 4161

# Or check Docker networking
docker network ls
docker network inspect gvpocr-network
```

---

## Monitoring & Maintenance

### Daily Checks

```bash
# Check all worker mounts are active
for worker in worker-1 worker-2 worker-3; do
  echo "Checking $worker..."
  ssh user@$worker "mountpoint /mnt/sshfs/main-server && echo 'OK' || echo 'FAILED'"
done

# Check NSQ queue status
curl -s http://172.12.0.132:4171/api/stats | jq '.topics[] | {name: .topic_name, depth: .depth}'

# Check worker logs
docker-compose logs --tail 100 worker
```

### Weekly Tasks

```bash
# Verify SSHFS cache isn't stale
ssh user@remote-worker "sudo systemctl restart sshfs-main-server"

# Check disk usage on main server
docker-compose exec mongodb du -sh /shared/Bhushanji /shared/newsletters
```

### Monthly Tasks

```bash
# Review SSH logs
docker logs gvpocr-ssh-server

# Update SSHFS settings if needed
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132

# Backup worker configurations
tar czf worker-configs-$(date +%Y%m%d).tar.gz docker-compose.*.yml .env.worker
```

---

## Performance Benchmarks

Expected performance on standard infrastructure:

| Metric | Value | Notes |
|--------|-------|-------|
| SSHFS Mount Time | 2-5 sec | One-time on boot |
| File List (1000 items) | 50-100 ms | With cache |
| File Read (1 MB) | 10-50 ms | Local network |
| Latency to Main Server | <50 ms | Recommended |
| Network Bandwidth | 1+ Mbps | Minimum |
| Model Load Time | 5-10 sec | Includes cache |

---

## Rollback Plan

If SSHFS setup causes issues, revert to SMB:

```bash
# Remove SSHFS mount
sudo umount /mnt/sshfs/main-server || true
sudo systemctl disable sshfs-main-server
sudo systemctl stop sshfs-main-server || true

# Use previous docker-compose.worker.yml
# (restore SMB mount configuration)
docker-compose down
git checkout docker-compose.worker.yml

# Redeploy with SMB
docker-compose up -d
```

---

## Next Steps

1. ✅ Prepare main server (SSH server running)
2. ✅ Prepare remote worker machines (SSHFS, Docker installed)
3. ✅ Run SSHFS setup script on each remote worker
4. ✅ Deploy OCR worker containers with SSHFS mounts
5. ✅ Verify file access and worker connectivity
6. ✅ Monitor and maintain (daily/weekly checks)
7. Scale to additional remote workers as needed

---

## References

- SSHFS Setup: `SSHFS_SETUP.md`
- Quick Start: `SSHFS_QUICK_START.md`
- Setup Script: `setup-sshfs-remote-worker.sh`
- Docker Override: `docker-compose.sshfs-override.yml`
- Systemd Service: `sshfs-main-server.service`

