# SSHFS File Sharing Setup for Remote Workers

This guide sets up SSHFS (SSH File System) to allow remote workers to access files on the main server, including Bhushanji data, newsletters, models (llamacpp, vllm), and other shared resources.

## Architecture Overview

```
Main Server (172.12.0.132)
├── SSH Server on port 2222
├── /mnt/sda1/mango1_home/gvpocr (Bhushanji data)
├── /mnt/sda1/mango1_home/newsletters (Newsletter data)
├── ~/.cache/huggingface/hub (Model cache)
└── ./models (Model directory)

Remote Worker Machines
├── Mount via SSHFS at /mnt/sshfs/main-server
│   ├── /mnt/sshfs/main-server/Bhushanji
│   ├── /mnt/sshfs/main-server/newsletters
│   ├── /mnt/sshfs/main-server/models
│   └── /mnt/sshfs/main-server/.cache/huggingface/hub
└── Docker containers can access mounted paths
```

## Prerequisites

### Main Server Requirements
- SSH server running (already set up via gvpocr-ssh-server service)
- SSH on port 2222
- User: `gvpocr` with password: `mango1`
- Files shared from `/home/gvpocr/` in container

### Remote Worker Requirements
- SSHFS package installed
- SSH client installed
- Ability to mount filesystems (requires elevated privileges)
- SSH key or password authentication to main server

## Step 1: Set Up SSH Key-Based Authentication (Optional but Recommended)

### On Main Server:

```bash
# Generate SSH key pair (if not already done)
ssh-keygen -t ed25519 -f /path/to/ssh_keys/gvpocr_sshfs -N "" -C "gvpocr@sshfs"

# Key will be at: ./ssh_keys/gvpocr_sshfs (private) and gvpocr_sshfs.pub (public)
```

### On Remote Worker:

```bash
# Copy the public key to authorized_keys in the container/main server
# This is handled by Docker volume mounts in the SSH server container

# Or use password authentication (default: mango1)
```

## Step 2: Mount SSHFS on Remote Worker

### Manual Mount (for testing):

```bash
#!/bin/bash
# Create mount directory
sudo mkdir -p /mnt/sshfs/main-server

# Install SSHFS (if not already installed)
sudo apt-get update
sudo apt-get install -y sshfs

# Mount via SSHFS (using password)
# Replace MAIN_SERVER_IP with your main server IP
sshfs -o allow_other,default_permissions \
      -p 2222 \
      gvpocr@MAIN_SERVER_IP:/home/gvpocr \
      /mnt/sshfs/main-server

# Or mount with known_hosts bypass (useful for fresh deployments)
sshfs -o allow_other,default_permissions,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null \
      -p 2222 \
      gvpocr@MAIN_SERVER_IP:/home/gvpocr \
      /mnt/sshfs/main-server

# Verify mount
ls /mnt/sshfs/main-server/
```

### Persistent Mount (via /etc/fstab):

```bash
# Add to /etc/fstab on remote worker
gvpocr@MAIN_SERVER_IP:/home/gvpocr /mnt/sshfs/main-server fuse.sshfs allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,_netdev,x-systemd.automount,x-systemd.device-timeout=10,identityfile=/home/user/.ssh/gvpocr_sshfs 0 0

# Then mount
sudo mount /mnt/sshfs/main-server
```

## Step 3: Update Docker Compose on Remote Worker

Modify `docker-compose.worker.yml` to use SSHFS mounts:

```yaml
services:
  worker:
    volumes:
      # ... existing volumes ...
      
      # SSHFS mounts from main server
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
```

## Step 4: Configure Remote Worker with SSHFS in Docker

Create `/etc/fstab` entries for SSHFS mounts to persist across reboots:

```bash
# Edit /etc/fstab
sudo nano /etc/fstab

# Add these lines (replace MAIN_SERVER_IP with actual IP)
gvpocr@MAIN_SERVER_IP:/home/gvpocr /mnt/sshfs/main-server fuse.sshfs allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,_netdev,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null 0 0
```

Then mount and verify:

```bash
sudo mount /mnt/sshfs/main-server
ls -la /mnt/sshfs/main-server/
```

## Step 5: Create Docker Service for SSHFS Mount (Alternative Method)

For cleaner Docker integration, create a systemd service:

```bash
# Create /etc/systemd/system/sshfs-main-server.service
sudo nano /etc/systemd/system/sshfs-main-server.service
```

Add the following content:

```ini
[Unit]
Description=SSHFS mount to main server
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'mkdir -p /mnt/sshfs/main-server && sshfs -o allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,StrictHostKeyChecking=no,UserKnownHostsFile=/dev/null -p 2222 gvpocr@${MAIN_SERVER_IP}:/home/gvpocr /mnt/sshfs/main-server'
ExecStop=fusermount -u /mnt/sshfs/main-server

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sshfs-main-server.service
sudo systemctl start sshfs-main-server.service

# Check status
sudo systemctl status sshfs-main-server.service
```

## Step 6: Update Worker Docker Compose

Update the worker's `docker-compose.worker.yml` to reference SSHFS mounts:

```yaml
services:
  worker:
    image: registry.docgenai.com:5010/gvpocr-worker-updated:latest
    # ... other configuration ...
    volumes:
      - ./backend/google-credentials.json:/app/google-credentials:ro
      - gvpocr-uploads:/app/uploads
      
      # SSHFS mounts from main server (replaces SMB shares)
      - /mnt/sshfs/main-server/Bhushanji:/app/Bhushanji:ro
      - /mnt/sshfs/main-server/newsletters:/app/newsletters:ro
      - /mnt/sshfs/main-server/models:/app/models:ro
      - /mnt/sshfs/main-server/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
```

## Step 7: Verify SSHFS Connection

```bash
# Test connection to SSH server
ssh -p 2222 gvpocr@MAIN_SERVER_IP

# Test SSHFS mount
sshfs -p 2222 gvpocr@MAIN_SERVER_IP:/home/gvpocr /tmp/test-sshfs
ls /tmp/test-sshfs/
umount /tmp/test-sshfs
```

## Troubleshooting

### SSHFS Mount Fails with "Permission denied"

```bash
# Ensure SSH server is running
ssh -p 2222 gvpocr@MAIN_SERVER_IP echo "Connection successful"

# Check SSH credentials (username: gvpocr, password: mango1)
```

### SSHFS Mount Fails with "Cannot allocate memory"

```bash
# Increase SSHFS cache timeout
sshfs -o allow_other,default_permissions,cache_timeout=3600 \
      -p 2222 \
      gvpocr@MAIN_SERVER_IP:/home/gvpocr \
      /mnt/sshfs/main-server
```

### Docker Container Cannot Access SSHFS Mount

```bash
# Ensure mount has proper permissions
sudo chmod 755 /mnt/sshfs/main-server

# Add allow_other to SSHFS mount options
sshfs -o allow_other,default_permissions \
      -p 2222 \
      gvpocr@MAIN_SERVER_IP:/home/gvpocr \
      /mnt/sshfs/main-server
```

### Connection Timeouts Over Slow Networks

```bash
# Use connection pooling and keep-alive
sshfs -o allow_other,default_permissions \
      -o ServerAliveInterval=15 \
      -o ServerAliveCountMax=3 \
      -o compression=yes \
      -p 2222 \
      gvpocr@MAIN_SERVER_IP:/home/gvpocr \
      /mnt/sshfs/main-server
```

## Performance Optimization

For optimal performance over remote connections:

1. **Enable Compression**: Add `-o compression=yes` to SSHFS command
2. **Tune Cache**: Use `-o cache_timeout=3600` for slower connections
3. **Connection Pooling**: SSHFS automatically pools connections
4. **Read-Only Mounts**: Use `:ro` in docker-compose.yml for shared data
5. **Network Optimization**: Use faster network connections (1Gbps minimum recommended)

## Advantages Over SMB/Samba

| Feature | SSHFS | SMB/Samba |
|---------|-------|-----------|
| Setup Complexity | Simple | Medium |
| Security | Encrypted (SSH) | Can be unencrypted |
| Performance | Good | Excellent |
| Compatibility | Unix/Linux | All OS |
| NAT Traversal | Difficult | Medium |
| Remote Access | Easy (single port 2222) | Needs port range |

## Next Steps

1. Install SSHFS on all remote worker machines
2. Create SSHFS mounts for each remote worker pointing to main server
3. Update docker-compose.worker.yml with SSHFS mount paths
4. Test worker connectivity and file access
5. Scale workers using updated configuration

## Files Generated

- `setup-sshfs-remote-worker.sh` - Automated setup script for remote workers
- `sshfs-main-server.service` - Systemd service for persistent SSHFS mounts
- Updated `docker-compose.worker.yml` - Uses SSHFS mounts instead of SMB

