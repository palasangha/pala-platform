# Docker Worker Setup Guide

This guide explains how to run OCR workers using Docker Compose on any machine with Docker installed.

## Advantages of Docker Workers

- **Easy deployment**: Single command to start a worker
- **Consistent environment**: Same dependencies and configuration everywhere
- **Scalable**: Run multiple workers on the same machine easily
- **Auto-restart**: Workers automatically restart on failure
- **Portable**: Works on Linux, macOS (with Docker Desktop), and Windows

## Prerequisites

1. **Docker and Docker Compose installed**
   ```bash
   # Linux
   sudo apt-get update
   sudo apt-get install docker.io docker-compose

   # macOS
   # Install Docker Desktop from https://www.docker.com/products/docker-desktop

   # Windows
   # Install Docker Desktop from https://www.docker.com/products/docker-desktop
   ```

2. **Network access to main server** (172.12.0.132)
   - NSQ: Port 4150 (TCP), 4161 (HTTP)
   - MongoDB: Port 27017

3. **Google Cloud Vision credentials** (google-credentials.json)

## Quick Start

### 1. Copy Worker Files to Remote Machine

From the main server, copy the necessary files to your worker machine:

```bash
# On your worker machine, create a directory
mkdir -p ~/gvpocr-worker
cd ~/gvpocr-worker

# Copy files from main server
scp user@172.12.0.132:/mnt/sda1/mango1_home/gvpocr/docker-compose.worker.yml .
scp user@172.12.0.132:/mnt/sda1/mango1_home/gvpocr/.env.worker.example .env.worker
scp -r user@172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend .
```

### 2. Configure Environment

Edit `.env.worker` to set your main server IP:

```bash
nano .env.worker
```

### 3. Set Up File Access

Workers need read access to uploaded files. Choose one method:

#### Option A: NFS Mount (Recommended for Remote Workers)

**On Main Server (172.12.0.132):**

```bash
# Install NFS server
sudo apt-get install nfs-kernel-server

# Configure NFS export
echo "/mnt/sda1/mango1_home/gvpocr/backend/uploads 172.12.0.0/24(ro,sync,no_subtree_check)" | sudo tee -a /etc/exports

# Restart NFS
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server

# Open firewall
sudo ufw allow from 172.12.0.0/24 to any port nfs
```

**On Worker Machine:**

```bash
# Install NFS client
sudo apt-get install nfs-common

# Create mount point
sudo mkdir -p /mnt/gvpocr-uploads

# Mount NFS share
sudo mount -t nfs 172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /mnt/gvpocr-uploads

# Make permanent - add to /etc/fstab
echo "172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /mnt/gvpocr-uploads nfs ro,auto 0 0" | sudo tee -a /etc/fstab
```

Then edit `docker-compose.worker.yml` to use the NFS mount:

```yaml
volumes:
  - /mnt/gvpocr-uploads:/app/uploads:ro
```

#### Option B: Same Machine

If running on the same machine as the main server:

```yaml
volumes:
  - ./backend/uploads:/app/uploads:ro
```

### 4. Start Worker

```bash
# Start a single worker
docker-compose -f docker-compose.worker.yml up -d

# Or start multiple workers
docker-compose -f docker-compose.worker.yml up -d --scale worker=3

# View logs
docker-compose -f docker-compose.worker.yml logs -f

# Stop workers
docker-compose -f docker-compose.worker.yml down
```

### 5. Verify Connection

Check the Worker Monitor in the web UI:
- Navigate to: http://172.12.0.132:3000/workers
- Your worker should appear in the connected workers list

Or check NSQ directly:
```bash
curl -s http://172.12.0.132:4161/lookup?topic=bulk_ocr_file_tasks
```

## Running Multiple Workers

### Method 1: Scale Command

Run multiple workers on the same machine:

```bash
# Start 5 workers
docker-compose -f docker-compose.worker.yml up -d --scale worker=5

# Each worker gets a unique container name and ID
```

### Method 2: Custom Worker IDs

Run workers with specific IDs:

```bash
# Worker 1
docker-compose -f docker-compose.worker.yml run -d -e WORKER_ID=server1-worker1 worker

# Worker 2
docker-compose -f docker-compose.worker.yml run -d -e WORKER_ID=server1-worker2 worker

# Worker 3
docker-compose -f docker-compose.worker.yml run -d -e WORKER_ID=server1-worker3 worker
```

## Advanced Configuration

### Resource Limits

Edit `docker-compose.worker.yml` to adjust resource limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Maximum CPU cores
      memory: 8G       # Maximum RAM
    reservations:
      cpus: '2.0'      # Minimum guaranteed CPU
      memory: 4G       # Minimum guaranteed RAM
```

### GPU Support (for EasyOCR, vLLM, etc.)

Add GPU support:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Custom Network

Connect workers to a specific network:

```yaml
networks:
  - worker-network

networks:
  worker-network:
    driver: bridge
```

## Monitoring

### View Worker Logs

```bash
# All workers
docker-compose -f docker-compose.worker.yml logs -f

# Specific worker
docker logs -f <container-id>

# Last 100 lines
docker-compose -f docker-compose.worker.yml logs --tail=100
```

### Check Worker Status

```bash
# List running workers
docker-compose -f docker-compose.worker.yml ps

# Check resource usage
docker stats

# Worker health
docker inspect <container-id> | grep Health
```

### Web UI

Access the Worker Monitor:
- http://172.12.0.132:3000/workers
- Shows real-time worker statistics
- Auto-refreshes every 5 seconds

## Troubleshooting

### Worker Won't Connect to NSQ

```bash
# Test NSQ connectivity
docker run --rm nicolaka/netshoot nc -zv 172.12.0.132 4150
docker run --rm nicolaka/netshoot nc -zv 172.12.0.132 4161

# Check NSQ is advertising correct IP
curl http://172.12.0.132:4161/lookup?topic=bulk_ocr_file_tasks
# Should show "broadcast_address": "172.12.0.132"
```

### MongoDB Connection Issues

```bash
# Test MongoDB connectivity
docker run --rm mongo:7.0 mongosh "mongodb://172.12.0.132:27017/gvpocr" --eval "db.runCommand({ping:1})"

# Check if authentication is required
# If you get auth errors, ensure MONGO_USERNAME and MONGO_PASSWORD are NOT set
# (to avoid the hostname override issue)
```

### File Access Issues

```bash
# Check NFS mount on worker machine
mount | grep nfs

# Test file access
ls -la /mnt/gvpocr-uploads

# Check NFS server exports
showmount -e 172.12.0.132
```

### Google Credentials Issues

```bash
# Verify credentials file exists
ls -la backend/google-credentials.json

# Test inside container
docker-compose -f docker-compose.worker.yml exec worker ls -la /app/google-credentials.json

# Check environment variable
docker-compose -f docker-compose.worker.yml exec worker env | grep GOOGLE
```

### Worker Crashes/Restarts

```bash
# View crash logs
docker-compose -f docker-compose.worker.yml logs --tail=200 worker

# Check container exit code
docker ps -a | grep worker

# Inspect container
docker inspect <container-id>
```

## Maintenance

### Update Workers

```bash
# Pull latest changes
cd ~/gvpocr-worker
git pull  # if using git
# OR
scp -r user@172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend .

# Rebuild and restart
docker-compose -f docker-compose.worker.yml build --no-cache
docker-compose -f docker-compose.worker.yml up -d --force-recreate
```

### Clean Up

```bash
# Stop and remove workers
docker-compose -f docker-compose.worker.yml down

# Remove volumes
docker-compose -f docker-compose.worker.yml down -v

# Remove images
docker rmi gvpocr-worker

# Clean up Docker
docker system prune -a
```

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/gvpocr-worker.service`:

```ini
[Unit]
Description=GVPOCR Worker
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/gvpocr-worker
ExecStart=/usr/bin/docker-compose -f docker-compose.worker.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.worker.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable gvpocr-worker
sudo systemctl start gvpocr-worker
sudo systemctl status gvpocr-worker
```

### Auto-start on macOS

Use launchd with Docker Desktop. Create `~/Library/LaunchAgents/com.gvpocr.worker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gvpocr.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/docker-compose</string>
        <string>-f</string>
        <string>/Users/YOUR_USERNAME/gvpocr-worker/docker-compose.worker.yml</string>
        <string>up</string>
        <string>-d</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.gvpocr.worker.plist
```

## Performance Tips

1. **SSD Storage**: Use SSD for Docker volumes
2. **Network Speed**: Ensure good network connection to main server
3. **Resource Allocation**: Give workers adequate CPU and RAM
4. **Multiple Workers**: Run 2-4 workers per machine for optimal throughput
5. **Dedicated Workers**: Use separate machines for workers vs main server

## Security Considerations

1. **Firewall**: Only open required ports (4150, 4161, 27017)
2. **Read-Only Mounts**: Mount uploads directory as read-only (`:ro`)
3. **Credentials**: Protect google-credentials.json with proper permissions
4. **Network**: Use VPN or private network for worker communication
5. **Updates**: Keep Docker and base images up to date

## Summary

```bash
# Quick deployment on new worker machine:
mkdir ~/gvpocr-worker && cd ~/gvpocr-worker
scp user@172.12.0.132:/path/to/files/* .
nano .env.worker  # Set MAIN_SERVER_IP
docker-compose -f docker-compose.worker.yml up -d --scale worker=3
docker-compose -f docker-compose.worker.yml logs -f
```

Check workers at: http://172.12.0.132:3000/workers
