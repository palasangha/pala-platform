# GVPOCR Worker Deployment Guide

Complete guide for deploying OCR workers across multiple machines.

## Overview

GVPOCR supports distributed OCR processing using NSQ message queue. Workers can run on:
- Linux servers
- macOS machines
- Windows (with Docker Desktop)
- Kubernetes clusters
- Cloud instances (AWS, GCP, Azure)

## Deployment Methods

### Method 1: Docker (Recommended) ✅

**Advantages:**
- ✅ Easiest deployment
- ✅ Consistent environment
- ✅ Auto-restart on failure
- ✅ Works on all platforms
- ✅ Easy to scale

**Quick Start:**
```bash
# Copy worker files to remote machine
scp -r user@172.12.0.132:/path/to/gvpocr ~/gvpocr-worker

cd ~/gvpocr-worker

# Interactive setup
./start-worker.sh

# Or manual:
docker-compose -f docker-compose.worker.yml up -d --scale worker=3
```

**Documentation:** See [DOCKER_WORKER_SETUP.md](DOCKER_WORKER_SETUP.md)

---

### Method 2: Native Installation (Linux)

**Advantages:**
- ⚡ Slightly better performance
- 🔧 Full control over environment
- 💾 No Docker overhead

**Quick Start:**
```bash
# Run setup script
./scripts/setup_remote_worker.sh

# Or manual setup - see REMOTE_WORKER_SETUP.md
```

**Documentation:** See [REMOTE_WORKER_SETUP.md](REMOTE_WORKER_SETUP.md)

---

### Method 3: Native Installation (macOS)

**Advantages:**
- 🍎 Use Mac hardware for OCR
- ⚡ Direct hardware access
- 🔧 Good for development

**Quick Start:**
```bash
# Run setup script
./scripts/setup_remote_worker_macos.sh

# Or manual setup - see REMOTE_WORKER_SETUP_MACOS.md
```

**Documentation:** See [REMOTE_WORKER_SETUP_MACOS.md](REMOTE_WORKER_SETUP_MACOS.md)

---

## Quick Comparison

| Method | Setup Time | Difficulty | Maintenance | Performance | Cross-Platform |
|--------|-----------|-----------|-------------|-------------|----------------|
| **Docker** | 5 min | ⭐ Easy | ⭐ Easy | ⭐⭐⭐ Good | ✅ Yes |
| **Native Linux** | 15 min | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐⭐⭐ Excellent | ❌ Linux only |
| **Native macOS** | 20 min | ⭐⭐⭐ Hard | ⭐⭐⭐ Hard | ⭐⭐⭐⭐ Excellent | ❌ macOS only |

---

## Prerequisites (All Methods)

### Network Requirements
- Access to main server (172.12.0.132)
- Open ports:
  - **NSQ:** 4150 (TCP), 4161 (HTTP)
  - **MongoDB:** 27017
- Good network bandwidth (for file access)

### File Access
Workers need read access to uploaded files. Choose one:

**Option A: NFS Mount (Recommended)**
```bash
# On worker machine
sudo mount -t nfs 172.12.0.132:/path/to/uploads /mnt/gvpocr-uploads
```

**Option B: SSHFS**
```bash
sshfs user@172.12.0.132:/path/to/uploads ~/gvpocr-uploads
```

**Option C: Same Machine**
- Workers on same machine as main server can access files directly

### Google Cloud Vision Credentials
```bash
# Copy from main server
scp user@172.12.0.132:/path/to/google-credentials.json ~/gvpocr-worker/backend/
```

---

## Configuration

### Main Server Setup

1. **NSQ Broadcast Address** (Already configured ✅)
   ```yaml
   # docker-compose.yml
   nsqd:
     command: /nsqd --broadcast-address=172.12.0.132
   ```

2. **MongoDB Access**
   - Workers use unauthenticated connection to avoid hostname issues
   - Or configure proper MongoDB user if needed

3. **Firewall Rules**
   ```bash
   # Allow NSQ and MongoDB
   sudo ufw allow from 172.12.0.0/24 to any port 4150
   sudo ufw allow from 172.12.0.0/24 to any port 4161
   sudo ufw allow from 172.12.0.0/24 to any port 27017
   ```

### Worker Configuration

**For Docker:**
```bash
# Edit .env.worker
MAIN_SERVER_IP=172.12.0.132
GOOGLE_VISION_ENABLED=true
TESSERACT_ENABLED=true
```

**For Native:**
```bash
# Edit backend/.env
MONGO_URI=mongodb://172.12.0.132:27017/gvpocr
NSQD_ADDRESS=172.12.0.132:4150
NSQLOOKUPD_ADDRESSES=172.12.0.132:4161
```

---

## Monitoring Workers

### Web UI
- **Worker Monitor:** http://172.12.0.132:3000/workers
- Real-time worker statistics
- Connection status
- Processing activity

### NSQ Admin UI
- **NSQ Admin:** http://172.12.0.132:4171
- Queue depth
- Message rates
- Worker connections

### Command Line

**Check connected workers:**
```bash
curl -s http://172.12.0.132:4161/lookup?topic=bulk_ocr_file_tasks | jq .
```

**View queue stats:**
```bash
curl -s http://172.12.0.132:4151/stats?format=json | jq .
```

**Worker logs (Docker):**
```bash
docker-compose -f docker-compose.worker.yml logs -f
```

**Worker logs (Native):**
```bash
# macOS LaunchAgent
tail -f ~/gvpocr-worker/backend/worker.log

# Linux systemd
sudo journalctl -u gvpocr-worker -f
```

---

## Scaling Workers

### Docker Scaling
```bash
# Scale to 5 workers
docker-compose -f docker-compose.worker.yml up -d --scale worker=5

# On multiple machines
# Machine 1: 3 workers
docker-compose -f docker-compose.worker.yml up -d --scale worker=3

# Machine 2: 5 workers
docker-compose -f docker-compose.worker.yml up -d --scale worker=5

# Total: 8 workers across 2 machines
```

### Native Scaling

**Linux (systemd):**
```bash
# Create multiple service files
sudo cp /etc/systemd/system/gvpocr-worker.service /etc/systemd/system/gvpocr-worker-2.service
# Edit worker ID in service file
sudo systemctl start gvpocr-worker gvpocr-worker-2
```

**macOS (LaunchAgent):**
```bash
# Create multiple plist files
cp ~/Library/LaunchAgents/com.gvpocr.worker.plist ~/Library/LaunchAgents/com.gvpocr.worker2.plist
# Edit worker ID
launchctl load ~/Library/LaunchAgents/com.gvpocr.worker2.plist
```

---

## Troubleshooting

### Worker Can't Connect to NSQ

**Check NSQ broadcast address:**
```bash
curl http://172.12.0.132:4161/lookup?topic=bulk_ocr_file_tasks
# Should show: "broadcast_address": "172.12.0.132"
```

**Test connectivity:**
```bash
nc -zv 172.12.0.132 4150
nc -zv 172.12.0.132 4161
```

### MongoDB Connection Failed

**Issue:** Worker tries to connect to `localhost:27017`

**Solution:** Remove `MONGO_USERNAME` and `MONGO_PASSWORD` from worker config
```bash
# In worker .env file, only set:
MONGO_URI=mongodb://172.12.0.132:27017/gvpocr
# DO NOT set MONGO_USERNAME or MONGO_PASSWORD
```

### File Not Found Errors

**Check NFS mount:**
```bash
mount | grep nfs
ls -la /mnt/gvpocr-uploads
```

**Verify file paths match:**
- Main server stores files at: `/path/to/uploads/file.jpg`
- Worker must see same file at: `/app/uploads/file.jpg` (Docker) or `/mnt/gvpocr-uploads/file.jpg` (Native)

### Google Vision API Errors

**Verify credentials:**
```bash
# Check file exists
ls -la backend/google-credentials.json

# Test credentials
export GOOGLE_APPLICATION_CREDENTIALS=backend/google-credentials.json
gcloud auth application-default print-access-token
```

---

## Production Recommendations

### Hardware

**Minimum per worker:**
- 2 CPU cores
- 4 GB RAM
- 10 GB storage
- 100 Mbps network

**Recommended per worker:**
- 4 CPU cores
- 8 GB RAM
- 50 GB SSD storage
- 1 Gbps network

### Deployment Strategy

**Small Scale (< 10 workers):**
- 2-3 machines with 3-5 workers each
- Docker deployment for simplicity

**Medium Scale (10-50 workers):**
- 5-10 machines with 5 workers each
- Mix of Docker and native for optimization
- Dedicated NFS server for file access

**Large Scale (50+ workers):**
- Kubernetes deployment
- Auto-scaling based on queue depth
- Distributed file storage (S3/MinIO)
- Load balancing

### High Availability

1. **Multiple Workers:** Always run 3+ workers
2. **Geographic Distribution:** Workers in different data centers
3. **Auto-restart:** Use systemd/Docker restart policies
4. **Monitoring:** Alert on worker disconnections
5. **Backup Workers:** Keep spare workers ready to deploy

---

## Cost Optimization

### Cloud Deployment

**AWS:**
- EC2 t3.medium instances ($30/month)
- Spot instances for 70% savings
- Auto-scaling groups

**GCP:**
- e2-medium instances ($25/month)
- Preemptible VMs for 80% savings
- Managed instance groups

**Azure:**
- B2s instances ($35/month)
- Spot VMs for savings

### On-Premise

**Repurpose old hardware:**
- Old workstations as workers
- Mac minis for macOS workers
- Raspberry Pi 4 for light workloads

---

## Quick Reference

### Start Workers

```bash
# Docker
./start-worker.sh                          # Interactive
docker-compose -f docker-compose.worker.yml up -d --scale worker=3

# Native Linux
sudo systemctl start gvpocr-worker

# Native macOS
launchctl start com.gvpocr.worker
```

### Stop Workers

```bash
# Docker
docker-compose -f docker-compose.worker.yml down

# Native Linux
sudo systemctl stop gvpocr-worker

# Native macOS
launchctl stop com.gvpocr.worker
```

### View Logs

```bash
# Docker
docker-compose -f docker-compose.worker.yml logs -f

# Native Linux
sudo journalctl -u gvpocr-worker -f

# Native macOS
tail -f ~/gvpocr-worker/backend/worker.log
```

### Check Status

```bash
# Web UI
open http://172.12.0.132:3000/workers

# NSQ Stats
curl -s http://172.12.0.132:4161/lookup?topic=bulk_ocr_file_tasks | jq .

# Docker
docker-compose -f docker-compose.worker.yml ps
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.worker.yml` | Docker worker configuration |
| `.env.worker.example` | Docker worker environment template |
| `start-worker.sh` | Interactive Docker worker setup |
| `DOCKER_WORKER_SETUP.md` | Complete Docker guide |
| `scripts/setup_remote_worker.sh` | Linux setup script |
| `REMOTE_WORKER_SETUP.md` | Linux setup guide |
| `scripts/setup_remote_worker_macos.sh` | macOS setup script |
| `REMOTE_WORKER_SETUP_MACOS.md` | macOS setup guide |

---

## Support

- **GitHub Issues:** https://github.com/yourusername/gvpocr/issues
- **Documentation:** See individual setup guides
- **Worker Monitor:** http://172.12.0.132:3000/workers
- **NSQ Admin:** http://172.12.0.132:4171

---

## Next Steps

1. ✅ Choose deployment method (Docker recommended)
2. ✅ Set up file access (NFS recommended)
3. ✅ Configure Google credentials
4. ✅ Deploy first worker
5. ✅ Verify in Worker Monitor
6. ✅ Scale to desired number of workers
7. ✅ Set up monitoring and alerts

**Ready to deploy? Start with:** `./start-worker.sh`
