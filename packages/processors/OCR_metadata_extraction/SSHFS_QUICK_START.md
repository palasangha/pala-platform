# Quick Reference: SSHFS Setup for Remote Workers

## 5-Minute Quick Start

### Step 1: Copy Setup Script to Remote Worker
```bash
# From main server, copy script to remote worker
scp -r setup-sshfs-remote-worker.sh docker-compose.sshfs-override.yml user@remote-worker:/home/user/

# Or manually on remote worker:
# Download and place in /home/user/ directory
```

### Step 2: Run Setup Script on Remote Worker Machine
```bash
cd /home/user

# Run with your main server IP
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132

# If using SSH key (optional)
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132 --key /path/to/private/key
```

### Step 3: Verify Mount
```bash
# Check if mount is active
ls -la /mnt/sshfs/main-server/

# You should see:
# - Bhushanji/
# - newsletters/
# - models/
# - .cache/
```

### Step 4: Deploy Worker Container
```bash
# Option A: Use docker-compose with override
docker-compose -f docker-compose.worker.yml -f docker-compose.sshfs-override.yml up -d

# Option B: Copy override as default and use standard command
cp docker-compose.sshfs-override.yml docker-compose.override.yml
docker-compose -f docker-compose.worker.yml up -d
```

### Step 5: Verify Worker Can Access Files
```bash
# Check worker container has access to mounted files
docker exec -it <worker-container-name> ls -la /app/Bhushanji

# Check model access
docker exec -it <worker-container-name> ls -la /app/models
```

---

## Environment Variables

Set these in `.env.worker` or pass to docker-compose:

```bash
MAIN_SERVER_IP=172.12.0.132
SSH_USER=gvpocr
SSH_PORT=2222
SSHFS_MOUNT_DIR=/mnt/sshfs/main-server
```

---

## SSH Credentials

**Default Credentials** (from main server):
- Username: `gvpocr`
- Password: `mango1`
- SSH Port: `2222`

---

## File Structure After Mount

```
/mnt/sshfs/main-server/
├── Bhushanji/              # Main OCR data (linked to /app/Bhushanji in container)
├── newsletters/            # Newsletter data (linked to /app/newsletters in container)
├── models/                 # LLM model files
├── .cache/
│   └── huggingface/
│       └── hub/            # HuggingFace model cache
├── uploads/                # (Optional) uploaded files
├── temp-images/            # (Optional) temporary images
└── source/                 # (Optional) source code
```

---

## Docker Volume Mapping

The SSHFS override file maps:

```yaml
/mnt/sshfs/main-server/Bhushanji           → /app/Bhushanji:ro
/mnt/sshfs/main-server/newsletters         → /app/newsletters:ro
/mnt/sshfs/main-server/models              → /app/models:ro
/mnt/sshfs/main-server/.cache/huggingface/hub → /root/.cache/huggingface/hub:ro
```

---

## Troubleshooting Quick Fixes

### Mount Failed: "Permission denied"
```bash
# Check SSH connectivity
ssh -p 2222 gvpocr@172.12.0.132 echo "test"

# If fails, verify network and SSH server is running
```

### Mount Failed: "Cannot allocate memory"
```bash
# Try again with reduced cache
sudo ./setup-sshfs-remote-worker.sh 172.12.0.132 --no-cache
```

### Docker Can't Access Mount
```bash
# Check mount is still active
mountpoint /mnt/sshfs/main-server

# If not mounted, reconnect
sudo systemctl restart sshfs-main-server
```

### Slow File Access
```bash
# Check network latency to main server
ping -c 5 172.12.0.132

# If high latency, use cache_timeout parameter
# Re-run setup with different cache settings
```

### Mount Disappears After Reboot
```bash
# Enable systemd service if not already enabled
sudo systemctl enable sshfs-main-server
sudo systemctl start sshfs-main-server

# Check status
sudo systemctl status sshfs-main-server
```

---

## Network Requirements

- SSH connectivity to main server on port 2222
- Minimum 1 Mbps network connection
- Recommended 10 Mbps+ for optimal performance
- Keep-alive packets every 15 seconds (automatic)

---

## Security Considerations

1. **Current Setup**: Uses password authentication (default: mango1)
2. **Recommended**: Use SSH key-based authentication for production
   ```bash
   sudo ./setup-sshfs-remote-worker.sh 172.12.0.132 --key /path/to/key
   ```

3. **Future**: Consider:
   - SSH key rotation
   - Connection encryption verification
   - Network isolation/VPN for remote workers
   - File access logging

---

## Performance Tips

1. **Cache Enabled** (Default):
   - Faster repeated file access
   - Better for high-latency networks
   - Trade-off: Delayed file updates from main server

2. **Cache Disabled** (Use --no-cache):
   - Always reads latest data
   - Better for frequently changing files
   - Performance impact on slow networks

3. **Mount Options in Use**:
   - `ServerAliveInterval=15` - Keep connection alive
   - `ServerAliveCountMax=3` - Auto-reconnect after 45 seconds idle
   - `reconnect` - Automatic reconnection on network issues
   - `cache_timeout=3600` - Cache file metadata for 1 hour

---

## Automation & Scaling

To deploy to multiple remote workers:

```bash
#!/bin/bash
# deploy-workers.sh

MAIN_SERVER_IP="172.12.0.132"
WORKERS=("worker1.example.com" "worker2.example.com" "worker3.example.com")

for worker in "${WORKERS[@]}"; do
    echo "Setting up SSHFS on $worker..."
    
    # Copy files
    scp setup-sshfs-remote-worker.sh docker-compose.sshfs-override.yml user@$worker:~/
    
    # Run setup
    ssh user@$worker "sudo ./setup-sshfs-remote-worker.sh $MAIN_SERVER_IP"
    
    echo "✓ $worker setup complete"
done
```

---

## Monitoring & Maintenance

```bash
# Check mount status
sudo systemctl status sshfs-main-server

# View recent logs
sudo journalctl -u sshfs-main-server -n 20

# Manually remount if needed
sudo systemctl restart sshfs-main-server

# Check space usage
df -h /mnt/sshfs/main-server

# Verify files are accessible
ls -lah /mnt/sshfs/main-server/Bhushanji
```

---

## Comparison: SSHFS vs SMB vs Local Files

| Feature | SSHFS | SMB | Local |
|---------|-------|-----|-------|
| Setup | ⭐⭐ Easy | ⭐⭐⭐ Medium | ⭐ N/A |
| Security | ⭐⭐⭐ Encrypted | ⭐⭐ Cleartext | ⭐⭐⭐ N/A |
| Performance | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Best |
| Flexibility | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐ Limited |
| NAT Traversal | ⭐ Hard | ⭐⭐⭐ Good | ⭐ N/A |
| Docker Compatible | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Best |

---

## Further Reading

- Full setup guide: `SSHFS_SETUP.md`
- Docker Compose docs: `docker-compose.worker.yml`
- Worker deployment: `REMOTE_WORKER_SETUP.md`

---

## Support

For detailed troubleshooting, see `SSHFS_SETUP.md`.

For worker-specific issues, check logs:
```bash
docker logs <worker-container-id>
sudo journalctl -u sshfs-main-server
```

