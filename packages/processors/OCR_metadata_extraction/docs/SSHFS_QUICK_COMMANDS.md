# SSHFS Passwordless Setup - Quick Command Reference

## Main Server Commands

```bash
# Verify SSH server is running
docker-compose ps ssh-server

# View SSH server logs
docker logs gvpocr-ssh-server | tail -20

# Test SSH locally
ssh -i ./ssh_keys/gvpocr_sshfs -p 2222 gvpocr@127.0.0.1 "ls /home/gvpocr"

# View SSH public key (to verify)
cat ./ssh_keys/gvpocr_sshfs.pub

# Test from another machine on the network
ssh -i ./ssh_keys/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "ls /home/gvpocr"
```

## Remote Worker Setup Commands

### Step 1: Get SSH Key

```bash
# Copy key from main server (uses password auth - enter: mango1)
scp -P 2222 -o StrictHostKeyChecking=no gvpocr@172.12.0.132:~/.ssh/gvpocr_sshfs ~/.ssh/

# Set permissions
chmod 600 ~/.ssh/gvpocr_sshfs

# Verify key
ls -la ~/.ssh/gvpocr_sshfs
```

### Step 2: Test SSH Connection

```bash
# Test SSH key authentication (no password)
ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "whoami"

# Test with verbose output (debugging)
ssh -v -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "echo OK"
```

### Step 3: Deploy SSHFS

```bash
# Run automated setup
sudo ./deploy-sshfs-worker.sh 172.12.0.132

# Or manual setup:
sudo mkdir -p /mnt/sshfs/main-server
sudo apt-get install -y sshfs
sudo sshfs -i ~/.ssh/gvpocr_sshfs \
    -o allow_other,default_permissions,reconnect \
    -o ServerAliveInterval=15,ServerAliveCountMax=3,cache_timeout=3600 \
    -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr \
    /mnt/sshfs/main-server
```

### Step 4: Verify Mount

```bash
# Check if mounted
mount | grep sshfs

# List shared directories
ls -la /mnt/sshfs/main-server/

# Check service status
sudo systemctl status sshfs-main-server.service

# View service logs
sudo journalctl -u sshfs-main-server -n 20
```

## Troubleshooting Commands

```bash
# Test SSH connection
ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "echo TEST"

# Check if SSH key exists
test -f ~/.ssh/gvpocr_sshfs && echo "Key exists" || echo "Key missing"

# Check key permissions (should be 600)
stat -c '%a' ~/.ssh/gvpocr_sshfs

# Test SSHFS mount manually
sudo sshfs -i ~/.ssh/gvpocr_sshfs -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /tmp/test-sshfs

# Unmount SSHFS
sudo umount /mnt/sshfs/main-server
# or
sudo fusermount -u /mnt/sshfs/main-server

# Restart systemd service
sudo systemctl restart sshfs-main-server.service

# Check network latency
ping -c 5 172.12.0.132

# Check mount permissions
ls -ld /mnt/sshfs/main-server/

# Verify Docker can access mount
docker run --rm -v /mnt/sshfs/main-server:/data:ro ubuntu ls /data
```

## Docker Integration Commands

```bash
# Create docker-compose override
cat > docker-compose.override.yml << 'YAML'
services:
  worker:
    volumes:
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
YAML

# Deploy with SSHFS mounts
docker-compose -f docker-compose.worker.yml \
               -f docker-compose.override.yml \
               up -d

# Verify mount in container
docker exec <container_id> ls -la /app/Bhushanji

# Check mounted volumes in container
docker inspect <container_id> | grep -A 30 Mounts
```

## Monitoring Commands

```bash
# Check all SSHFS mounts
mount | grep sshfs

# Monitor mount in real-time
watch 'mount | grep sshfs'

# Check disk usage of mounted directories
du -sh /mnt/sshfs/main-server/*

# Monitor SSH connections
watch 'netstat -tnp | grep 2222'

# Check system logs for SSHFS errors
journalctl -u sshfs-main-server -f

# Monitor file access performance
time ls -laR /mnt/sshfs/main-server/ | wc -l
```

## System Administration Commands

```bash
# Enable SSHFS mount at boot
sudo systemctl enable sshfs-main-server.service

# Disable SSHFS mount at boot
sudo systemctl disable sshfs-main-server.service

# Start mount service
sudo systemctl start sshfs-main-server.service

# Stop mount service
sudo systemctl stop sshfs-main-server.service

# View systemd service file
cat /etc/systemd/system/sshfs-main-server.service

# Edit systemd service
sudo nano /etc/systemd/system/sshfs-main-server.service
sudo systemctl daemon-reload

# Check if key is in SSH agent
ssh-add -L

# Add key to SSH agent (for easier use)
ssh-add ~/.ssh/gvpocr_sshfs

# List all SSH identities
ssh-add -l
```

## Performance Tuning Commands

```bash
# Remount with compression (for slow networks)
sudo umount /mnt/sshfs/main-server
sudo sshfs -i ~/.ssh/gvpocr_sshfs -o compression=yes \
    -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Remount with longer cache timeout
sudo umount /mnt/sshfs/main-server
sudo sshfs -i ~/.ssh/gvpocr_sshfs -o cache_timeout=7200 \
    -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Remount without cache (for dynamic content)
sudo umount /mnt/sshfs/main-server
sudo sshfs -i ~/.ssh/gvpocr_sshfs -o cache_timeout=0 \
    -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server

# Test file read performance
time dd if=/mnt/sshfs/main-server/models/large-file.bin of=/dev/null bs=1M count=10

# Test directory listing performance
time find /mnt/sshfs/main-server -type f | wc -l
```

## Batch Operations

```bash
# Deploy to multiple workers
for IP in 172.12.0.96 172.12.0.97 172.12.0.98; do
    echo "Setting up $IP..."
    ssh user@$IP "cd gvpocr && \
                 scp -P 2222 gvpocr@172.12.0.132:~/.ssh/gvpocr_sshfs ~/.ssh/ && \
                 chmod 600 ~/.ssh/gvpocr_sshfs && \
                 sudo ./deploy-sshfs-worker.sh 172.12.0.132"
done

# Check all worker mounts
for IP in 172.12.0.96 172.12.0.97 172.12.0.98; do
    echo "=== $IP ==="
    ssh user@$IP "mount | grep sshfs || echo 'NOT MOUNTED'"
done

# Restart mounts on all workers
for IP in 172.12.0.96 172.12.0.97 172.12.0.98; do
    ssh user@$IP "sudo systemctl restart sshfs-main-server.service"
    echo "Restarted $IP"
done
```

## Debug Commands

```bash
# SSH debug output
ssh -vvv -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "echo test"

# SSHFS debug output
sudo sshfs -d -i ~/.ssh/gvpocr_sshfs -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /tmp/test-mount

# Check system limits for file handles
cat /proc/sys/fs/file-max
ulimit -n

# Check SSHFS process details
ps aux | grep sshfs

# Check open file descriptors for SSHFS
lsof | grep sshfs

# Monitor SSHFS I/O operations
iotop -p $(pgrep -f sshfs)

# Check SSHFS cache status
stat /mnt/sshfs/main-server/

# View detailed mount options
mount | grep sshfs | sed 's/,/\n/g'
```

## Quick Status Check

```bash
#!/bin/bash
# Quick status check script

echo "=== SSH KEY ==="
test -f ~/.ssh/gvpocr_sshfs && echo "✓ Key exists" || echo "✗ Key missing"

echo -e "\n=== SSH CONNECTION ==="
ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "echo ✓ SSH works" || echo "✗ SSH failed"

echo -e "\n=== SSHFS MOUNT ==="
mount | grep sshfs > /dev/null && echo "✓ Mounted" || echo "✗ Not mounted"

echo -e "\n=== SYSTEMD SERVICE ==="
sudo systemctl is-active sshfs-main-server && echo "✓ Service active" || echo "✗ Service inactive"

echo -e "\n=== MOUNT CONTENTS ==="
ls /mnt/sshfs/main-server/ 2>/dev/null | head -5 || echo "✗ Cannot read mount"

echo -e "\n=== DOCKER VOLUME TEST ==="
docker run --rm -v /mnt/sshfs/main-server:/test:ro ubuntu ls /test >/dev/null 2>&1 && \
    echo "✓ Docker can access" || echo "✗ Docker cannot access"
```

---

**Tip:** Save this file locally and use as a reference during setup!

```bash
# Copy commands quickly:
cd /path/to/gvpocr
cat SSHFS_QUICK_COMMANDS.md | grep -A 2 "Your Section"
```

