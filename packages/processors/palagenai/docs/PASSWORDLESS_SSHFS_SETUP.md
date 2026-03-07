# Passwordless SSHFS Setup Guide

## Overview

This guide sets up passwordless SSH key-based authentication for SSHFS file sharing between the main server (172.12.0.132) and remote worker machines (like 172.12.0.96).

## How It Works

1. **Main Server (172.12.0.132):**
   - SSH server running on port 2222 in Docker container
   - Public key stored in authorized_keys for passwordless access
   - All shared data mounted and accessible to authenticated users

2. **Remote Worker (172.12.0.96):**
   - SSH private key placed at `~/.ssh/gvpocr_sshfs`
   - SSHFS mounts `/home/gvpocr` from main server to `/mnt/sshfs/main-server`
   - Systemd service ensures mount persists across reboots
   - Docker containers access mounted data as volumes

## Quick Setup (On Remote Worker)

### Step 1: Copy SSH Key from Main Server

```bash
# From remote worker, copy the private key from main server
scp -P 2222 -o StrictHostKeyChecking=no gvpocr@172.12.0.132:~/.ssh/gvpocr_sshfs ~/.ssh/gvpocr_sshfs

# Set proper permissions
chmod 600 ~/.ssh/gvpocr_sshfs
```

**Note:** If prompted for password, use `mango1`

### Step 2: Run Deployment Script

```bash
# Download and run the automated setup script
cd /path/to/gvpocr/project
sudo ./deploy-sshfs-worker.sh 172.12.0.132

# Or specify a different main server IP:
sudo ./deploy-sshfs-worker.sh <MAIN_SERVER_IP>
```

The script will:
- ✓ Install SSHFS and SSH client
- ✓ Create mount point (`/mnt/sshfs/main-server`)
- ✓ Test SSH connection with key-based auth
- ✓ Mount SSHFS filesystem
- ✓ Create systemd service for persistent mount
- ✓ Display mount contents and status

### Step 3: Verify Mount

```bash
# Check if SSHFS is mounted
mount | grep sshfs

# List available shared directories
ls -la /mnt/sshfs/main-server/
```

Expected output:
```
Bhushanji/
.cache/
models/
newsletters/
source/
uploads/
temp-images/
```

## Docker Integration

After SSHFS is mounted, create a `docker-compose.override.yml` to use the mounted filesystems:

```yaml
services:
  worker:
    volumes:
      # SSHFS mounts from main server
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
```

Then deploy:
```bash
docker-compose -f docker-compose.worker.yml -f docker-compose.override.yml up -d
```

## SSH Key Distribution

### On Main Server

Generate and display the public key:
```bash
# Key pair already generated at: ./ssh_keys/gvpocr_sshfs
cat ./ssh_keys/gvpocr_sshfs.pub
```

To copy to remote worker manually:
```bash
# From main server directory
scp -P 2222 ./ssh_keys/gvpocr_sshfs user@remote-worker:~/.ssh/
```

## Troubleshooting

### "Permission denied" when connecting

```bash
# Verify SSH server is running
docker-compose ps ssh-server

# Check SSH logs
docker logs gvpocr-ssh-server | tail -20

# Test SSH connection
ssh -i ~/.ssh/gvpocr_sshfs -o StrictHostKeyChecking=no -p 2222 gvpocr@172.12.0.132
```

### SSHFS mount fails

```bash
# Check if SSH key exists
ls -la ~/.ssh/gvpocr_sshfs

# Check SSH key permissions (should be 600)
chmod 600 ~/.ssh/gvpocr_sshfs

# Test SSH connection manually
ssh -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132 ls /home/gvpocr

# Check SSHFS mount attempt manually
sshfs -i ~/.ssh/gvpocr_sshfs -p 2222 gvpocr@172.12.0.132:/home/gvpocr /tmp/test-mount
```

### Mount disappears after reboot

```bash
# Check systemd service status
sudo systemctl status sshfs-main-server

# Enable the service if not enabled
sudo systemctl enable sshfs-main-server.service

# Start the service
sudo systemctl start sshfs-main-server.service

# View service logs
sudo journalctl -u sshfs-main-server -n 20
```

### Slow file access

```bash
# Check network latency
ping -c 5 172.12.0.132

# Re-mount with compression
sudo umount /mnt/sshfs/main-server
sudo sshfs -i ~/.ssh/gvpocr_sshfs -o compression=yes -p 2222 \
    gvpocr@172.12.0.132:/home/gvpocr /mnt/sshfs/main-server
```

## Security

✓ **Key-based authentication** - No passwords transmitted  
✓ **SSH encryption** - All traffic encrypted over the wire  
✓ **Read-only mounts** - Shared data is mounted read-only (`ro`)  
✓ **Limited user** - SSH user `gvpocr` has no shell access  

## Files Generated

1. `deploy-sshfs-worker.sh` - Automated deployment script for remote workers
2. `ssh_keys/gvpocr_sshfs` - Private key for SSH authentication (main server)
3. `ssh_keys/gvpocr_sshfs.pub` - Public key (embedded in SSH server authorized_keys)

## Scaling to Multiple Workers

To deploy to multiple remote workers:

```bash
#!/bin/bash
MAIN_SERVER_IP="172.12.0.132"
WORKERS=("worker1.example.com" "worker2.example.com" "worker3.example.com")

for WORKER in "${WORKERS[@]}"; do
    echo "Setting up $WORKER..."
    ssh user@$WORKER 'bash -s' < deploy-sshfs-worker.sh $MAIN_SERVER_IP
done
```

## Advanced Configuration

### Increase Cache Timeout (for slower networks)

Edit `/etc/systemd/system/sshfs-main-server.service` and change:
```ini
ExecStart=/bin/bash -c '... -o cache_timeout=7200 ...'
```

### Enable Compression (for high-latency links)

Edit `/etc/systemd/system/sshfs-main-server.service` and change:
```ini
ExecStart=/bin/bash -c '... -o compression=yes ...'
```

### Custom Mount Options

Modify the SSHFS_OPTS in the deploy script:
```bash
SSHFS_OPTS="allow_other,default_permissions,reconnect,ServerAliveInterval=30,cache_timeout=7200,compression=yes"
```

## Next Steps

1. ✅ Set up SSH key-based authentication (this guide)
2. Run `deploy-sshfs-worker.sh` on each remote worker
3. Verify SSHFS mounts with `mount | grep sshfs`
4. Create Docker Compose override files for your worker containers
5. Deploy worker containers with `docker-compose -f docker-compose.worker.yml -f docker-compose.override.yml up -d`

## References

- [SSHFS_SETUP.md](SSHFS_SETUP.md) - Comprehensive technical guide
- [SSHFS_DEPLOYMENT.md](SSHFS_DEPLOYMENT.md) - Full deployment and scaling
- [docker-compose.yml](docker-compose.yml) - SSH server configuration
