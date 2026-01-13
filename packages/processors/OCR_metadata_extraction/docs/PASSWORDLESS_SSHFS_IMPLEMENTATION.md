# SSHFS Passwordless Setup - Remote Worker Implementation Guide

## Status: ✅ SSH Key-Based Authentication Ready

The main server (172.12.0.132) is now configured with passwordless SSH key-based authentication.

## Key Components Set Up

### 1. Main Server SSH Configuration (172.12.0.132)

✅ **SSH Server Running:**
- Port: 2222
- User: gvpocr
- Authentication: Key-based (passwordless)
- Container: `gvpocr-ssh-server` (Alpine Linux with OpenSSH)

✅ **SSH Key Pair Generated:**
- Private key: `./ssh_keys/gvpocr_sshfs` (keep secure)
- Public key: `./ssh_keys/gvpocr_sshfs.pub` (distributed to workers)
- Key type: ED25519 (modern, secure)
- Passphrase: None (passwordless)

✅ **Shared Directories Available:**
```
/home/gvpocr/
├── Bhushanji/              (OCR processing data)
├── newsletters/            (Newsletter data)
├── models/                 (LLM models)
├── .cache/huggingface/hub/ (Model cache)
├── source/                 (Source code)
├── uploads/                (Upload directory)
└── temp-images/            (Temporary images)
```

### 2. Verification on Main Server

```bash
# Test SSH key authentication locally
ssh -i ./ssh_keys/gvpocr_sshfs -p 2222 gvpocr@127.0.0.1 "ls /home/gvpocr/"

# Output should show:
# Bhushanji  models  newsletters  source  temp-images  uploads
```

## Setup Instructions for Remote Worker (172.12.0.96)

### Phase 1: Prepare SSH Key on Remote Worker

#### Option A: Copy Key from Main Server (Recommended for First Setup)

```bash
# From remote worker, retrieve the private key using password auth
# (This is the only time password auth is used)
scp -P 2222 -o StrictHostKeyChecking=no \
    gvpocr@172.12.0.132:~/.ssh/gvpocr_sshfs \
    ~/.ssh/gvpocr_sshfs

# Prompt will ask for password, enter: mango1

# Verify key was copied
ls -la ~/.ssh/gvpocr_sshfs

# Set proper permissions (IMPORTANT)
chmod 600 ~/.ssh/gvpocr_sshfs
```

#### Option B: Use Pre-distributed Key

If the SSH key was distributed out-of-band:

```bash
# Place key at ~/.ssh/gvpocr_sshfs
# Set permissions
chmod 600 ~/.ssh/gvpocr_sshfs
```

#### Verify SSH Key Setup

```bash
# Test connection with key (no password)
ssh -i ~/.ssh/gvpocr_sshfs \
    -o StrictHostKeyChecking=no \
    -p 2222 \
    gvpocr@172.12.0.132 \
    "echo 'Key authentication works!'"

# Expected output: "Key authentication works!"
```

### Phase 2: Deploy SSHFS Mount

#### Automated Deployment

```bash
# Navigate to project directory
cd /path/to/gvpocr

# Copy deployment script from main server (if not already available)
# Or use the one in your repository

# Run deployment script
sudo /path/to/deploy-sshfs-worker.sh 172.12.0.132

# The script will:
# ✓ Install SSHFS and SSH client
# ✓ Create mount directory (/mnt/sshfs/main-server)
# ✓ Test SSH connection with key auth
# ✓ Mount SSHFS filesystem
# ✓ Create systemd service for persistence
# ✓ Display status and available directories
```

#### Manual Deployment (If Script Fails)

```bash
# 1. Install SSHFS
sudo apt-get update
sudo apt-get install -y sshfs openssh-client

# 2. Create mount directory
sudo mkdir -p /mnt/sshfs/main-server
sudo chmod 755 /mnt/sshfs/main-server

# 3. Mount SSHFS
sudo sshfs -i ~/.ssh/gvpocr_sshfs \
    -o allow_other,default_permissions,reconnect \
    -o ServerAliveInterval=15,ServerAliveCountMax=3 \
    -o cache_timeout=3600 \
    -o StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null \
    -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr \
    /mnt/sshfs/main-server

# 4. Verify mount
ls -la /mnt/sshfs/main-server/
```

### Phase 3: Create Systemd Service for Persistence

Create `/etc/systemd/system/sshfs-main-server.service`:

```ini
[Unit]
Description=SSHFS mount to main OCR server
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'mkdir -p /mnt/sshfs/main-server && sshfs -i /root/.ssh/gvpocr_sshfs -o allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,cache_timeout=3600,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null -p 2222 gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server || true'
ExecStop=/bin/bash -c 'fusermount -u /mnt/sshfs/main-server || umount /mnt/sshfs/main-server || true'

[Install]
WantedBy=multi-user.target
```

Enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sshfs-main-server.service
sudo systemctl start sshfs-main-server.service

# Check status
sudo systemctl status sshfs-main-server.service

# View logs
sudo journalctl -u sshfs-main-server -n 20
```

### Phase 4: Configure Docker Containers

Create `docker-compose.override.yml`:

```yaml
services:
  worker:
    volumes:
      # SSHFS mounts from main server (read-only)
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
```

Deploy containers:
```bash
docker-compose -f docker-compose.worker.yml \
               -f docker-compose.override.yml \
               up -d

# Verify mount is accessible from container
docker exec <container_id> ls -la /app/Bhushanji
```

## Verification Checklist

Run these commands on the remote worker to verify everything is working:

```bash
# ✅ 1. SSH key exists and has correct permissions
ls -la ~/.ssh/gvpocr_sshfs
# Should show: -rw------- (600 permissions)

# ✅ 2. SSH connection works with key
ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "whoami"
# Should output: gvpocr

# ✅ 3. SSHFS mount exists and is mounted
mount | grep sshfs
# Should show: gvpocr@172.12.0.132:/home/gvpocr on /mnt/sshfs/main-server type fuse.sshfs

# ✅ 4. Mount is accessible
ls -la /mnt/sshfs/main-server/
# Should list: Bhushanji, newsletters, models, etc.

# ✅ 5. Systemd service is active
sudo systemctl status sshfs-main-server.service
# Should show: Active (exited) since ...

# ✅ 6. Docker can access mount
docker run --rm -v /mnt/sshfs/main-server:/data:ro ubuntu ls /data/

# ✅ 7. Test file access performance
time ls -la /mnt/sshfs/main-server/Bhushanji/ | wc -l
```

## Troubleshooting

### SSH Connection Issues

```bash
# Test SSH connectivity with verbose output
ssh -v -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 "echo test"

# Check if main server SSH is running
# (From main server)
docker-compose ps ssh-server

# View SSH server logs
docker logs gvpocr-ssh-server | tail -30
```

### SSHFS Mount Issues

```bash
# Check if SSHFS is installed
which sshfs

# Manually test mount
sudo sshfs -i ~/.ssh/gvpocr_sshfs -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /tmp/test-mount -o debug,syslog=err

# Check mount error details
dmesg | tail -20

# Try remounting
sudo umount /mnt/sshfs/main-server 2>/dev/null || true
sudo /mnt/sshfs/main-server.sh mount
```

### Systemd Service Issues

```bash
# Check service status
sudo systemctl status sshfs-main-server.service

# Check service logs
sudo journalctl -u sshfs-main-server.service -n 50

# Restart service
sudo systemctl restart sshfs-main-server.service

# Manually test the mount command from service
sudo /bin/bash -c 'sshfs -i ~/.ssh/gvpocr_sshfs ... /mnt/sshfs/main-server'
```

### Performance Issues

```bash
# Check network latency to main server
ping -c 5 172.12.0.132

# Check SSHFS mount options currently active
mount | grep sshfs

# Remount with compression for slow networks
sudo umount /mnt/sshfs/main-server
sudo sshfs -i ~/.ssh/gvpocr_sshfs -p 2222 \
    -o compression=yes \
    gvpocr@172.12.0.132:/home/gvpocr \
    /mnt/sshfs/main-server
```

## Security Notes

✅ **Passwordless SSH:** Once set up, no passwords are transmitted  
✅ **Encrypted Transport:** All data encrypted with SSH  
✅ **Limited Privileges:** User `gvpocr` has no shell/login access  
✅ **Read-Only Mounts:** Shared data mounted read-only (`:ro`)  
✅ **Key Security:** Protect `~/.ssh/gvpocr_sshfs` file carefully

## Performance Characteristics

| Aspect | Value |
|--------|-------|
| Auth Method | Key-based (instant, no password) |
| Transport | SSH encrypted (transparent) |
| Latency | Same as network RTT + SSH overhead (~1-2ms per file op) |
| Throughput | Limited by network and SSH processing |
| Caching | 1 hour metadata cache (configurable) |
| Connection | Auto-reconnect with keepalive packets |

## Scaling to Multiple Workers

To deploy to all remote workers:

```bash
#!/bin/bash
# deploy-all-workers.sh

MAIN_SERVER="172.12.0.132"
WORKERS=(
    "user@172.12.0.96"
    "user@172.12.0.97"
    "user@172.12.0.98"
)

for WORKER in "${WORKERS[@]}"; do
    echo "Setting up SSHFS on $WORKER..."
    
    # Copy SSH key
    scp -P 2222 ./ssh_keys/gvpocr_sshfs "$WORKER:~/.ssh/"
    
    # Run deployment script
    ssh $WORKER "cd gvpocr && sudo ./deploy-sshfs-worker.sh $MAIN_SERVER"
    
    echo "✓ $WORKER complete"
done
```

## Files and References

| File | Purpose |
|------|---------|
| `ssh_keys/gvpocr_sshfs` | Private key (keep secure on main server) |
| `ssh_keys/gvpocr_sshfs.pub` | Public key (distributed to workers) |
| `deploy-sshfs-worker.sh` | Automated setup script for workers |
| `PASSWORDLESS_SSHFS_SETUP.md` | This document |
| `docker-compose.yml` | SSH server configuration |

## Next Steps

1. **For Each Remote Worker (172.12.0.96, etc):**
   - [ ] Copy SSH key from main server
   - [ ] Run `deploy-sshfs-worker.sh 172.12.0.132`
   - [ ] Verify mount: `ls /mnt/sshfs/main-server/`
   - [ ] Create `docker-compose.override.yml`
   - [ ] Deploy worker containers

2. **Verify Integration:**
   - [ ] All workers mounted
   - [ ] Docker containers can access files
   - [ ] Worker processes reading from SSHFS
   - [ ] Performance acceptable

3. **Monitor and Maintain:**
   - [ ] Check systemd services weekly
   - [ ] Monitor SSH logs for issues
   - [ ] Test failover/reconnection behavior
   - [ ] Plan key rotation schedule

## Support

For detailed technical information, see:
- [SSHFS_SETUP.md](SSHFS_SETUP.md) - Technical details
- [SSHFS_DEPLOYMENT.md](SSHFS_DEPLOYMENT.md) - Deployment examples
- [docker-compose.yml](docker-compose.yml) - Configuration

For issues:
1. Check SSH connection: `ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132`
2. Check mount: `mount | grep sshfs`
3. Check service: `sudo systemctl status sshfs-main-server`
4. View logs: `sudo journalctl -u sshfs-main-server -n 50`

---

**Status:** ✅ Ready for remote worker deployment
**Last Updated:** 2024-12-19
