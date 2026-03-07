# LMStudio Docker Bridge Setup Guide

## Overview
This guide helps you connect LMStudio (running on the host) to Docker containers through a network bridge.

## Files Created
- `lmstudio_docker_bridge.py` - Python bridge script
- `start_lmstudio_bridge.sh` - Convenience starter script
- `/etc/systemd/system/lmstudio-bridge.service` - Optional systemd service

---

## Quick Start (Option 1: Manual Run)

### Step 1: Open a Terminal on the Host Machine

### Step 2: Start the Bridge
```bash
cd /mnt/sda1/mango1_home/gvpocr
sudo bash start_lmstudio_bridge.sh
```

You should see:
```
============================================
LMStudio Docker Bridge
============================================

✓ LMStudio is running on localhost:1234

Starting bridge...
  Listening on: 172.23.0.1:1234
  Forwarding to: localhost:1234
  Docker containers can reach: http://172.23.0.1:1234

Press Ctrl+C to stop
============================================
```

### Step 3: Keep This Terminal Open
The bridge must stay running for Docker to access LMStudio.

### Step 4: Test Connection (in another terminal)

```bash
docker exec gvpocr-backend python3 -c "
import requests
resp = requests.get('http://172.23.0.1:1234/v1/models', timeout=3)
print(f'✓ Connected! Status: {resp.status_code}')
models = resp.json()
print(f'✓ Models available: {len(models[\"data\"])}')
"
```

Expected output:
```
✓ Connected! Status: 200
✓ Models available: 2
```

---

## Setup (Option 2: Automatic with Systemd)

### Step 1: Install as System Service
```bash
sudo cp /mnt/sda1/mango1_home/gvpocr/lmstudio_docker_bridge.py /usr/local/bin/
sudo cp /tmp/lmstudio-bridge.service /etc/systemd/system/

# Make it executable
sudo chmod +x /usr/local/bin/lmstudio_docker_bridge.py

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable lmstudio-bridge.service
sudo systemctl start lmstudio-bridge.service
```

### Step 2: Verify Service is Running
```bash
sudo systemctl status lmstudio-bridge.service
```

### Step 3: Check Logs
```bash
sudo journalctl -u lmstudio-bridge.service -f
```

### Step 4: Test Connection
Same as Step 4 above.

---

## Configuration

### .env Settings
The backend `.env` should have:
```
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://172.23.0.1:1234
LMSTUDIO_MODEL=gemma-3-12b
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_SKIP_AVAILABILITY_CHECK=true
LMSTUDIO_TIMEOUT=600
LMSTUDIO_MAX_TOKENS=4096
```

### Restart Backend
After the bridge is running:
```bash
docker-compose down gvpocr-backend
docker-compose up -d gvpocr-backend
```

---

## Troubleshooting

### Bridge won't start: "Address already in use"
- This means another process is using port 1234 on the gateway IP
- Stop any other bridges: `sudo killall lmstudio_docker_bridge.py`
- Or try: `sudo fuser -k 1234/tcp`

### "LMStudio is not running on localhost:1234"
- Make sure LMStudio is actually running on the host
- Check: `netstat -tlnp | grep 1234`
- You should see: `0.0.0.0:1234 LISTEN`

### Docker container still can't connect
- Verify bridge is running: `ps aux | grep lmstudio_docker_bridge`
- Check if service started: `sudo systemctl status lmstudio-bridge.service`
- Test from host: `curl http://172.23.0.1:1234/v1/models`

### Permission Denied
- The bridge requires `sudo` to bind to the Docker gateway IP
- Always run with: `sudo bash start_lmstudio_bridge.sh`

---

## Complete Test Sequence

```bash
# 1. Start the bridge (in Terminal 1)
cd /mnt/sda1/mango1_home/gvpocr
sudo bash start_lmstudio_bridge.sh

# 2. Test from Docker (in Terminal 2)
docker exec gvpocr-backend python3 << 'EOF'
import requests

print("Testing LMStudio connection...")
print("-" * 50)

try:
    # Test 1: HTTP GET
    resp = requests.get('http://172.23.0.1:1234/v1/models', timeout=3)
    print(f"✓ HTTP Status: {resp.status_code}")

    # Test 2: Parse JSON
    data = resp.json()
    print(f"✓ Response parsed successfully")

    # Test 3: Check models
    models = data.get('data', [])
    print(f"✓ Models found: {len(models)}")

    if models:
        print(f"\nAvailable models:")
        for model in models[:3]:
            print(f"  - {model['id']}")

    print("\n" + "="*50)
    print("✓✓✓ SUCCESS - LMStudio is accessible! ✓✓✓")
    print("="*50)

except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    print("\nTroubleshooting:")
    print("1. Is the bridge running with sudo?")
    print("2. Is LMStudio running on the host?")
    print("3. Check: netstat -tlnp | grep 1234")

EOF
```

---

## What's Happening

When you run the bridge:

```
Host Machine:
  LMStudio → listening on 0.0.0.0:1234
         ↓
  Bridge script (with sudo) → listens on 172.23.0.1:1234
                        ↓
  Docker Network Gateway (172.23.0.1)
         ↓
Docker Container (backend) → can now reach http://172.23.0.1:1234
```

---

## Stopping the Bridge

### If Running Manually
- Press `Ctrl+C` in the terminal where you started it

### If Running as Systemd Service
```bash
sudo systemctl stop lmstudio-bridge.service
```

### Disable on Boot
```bash
sudo systemctl disable lmstudio-bridge.service
```

---

## Next Steps

Once the bridge is working:

1. **Update .env** (if needed):
   ```
   LMSTUDIO_HOST=http://172.23.0.1:1234
   ```

2. **Restart backend**:
   ```bash
   docker-compose restart gvpocr-backend
   ```

3. **Use LMStudio in OCR pipelines**:
   - Backend can now process images using LMStudio
   - No more connection timeout errors!

---

## Notes

- The bridge must stay running for Docker containers to access LMStudio
- Using systemd service (Option 2) is recommended for production
- Bridge runs with minimal resource overhead
- All data is forwarded transparently - no buffering or caching

