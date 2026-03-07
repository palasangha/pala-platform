# Quick Start: Remote OCR Workers on macOS

## Prerequisites

- macOS 10.15 (Catalina) or later
- Network access to queue server (172.12.0.132)
- Homebrew installed

### Install Homebrew (if needed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## On Your Mac

### 1. Clone Repository
```bash
cd ~/
git clone https://github.com/palasangha/OCR_metadata_extraction.git gvpocr-worker
cd gvpocr-worker
```

### 2. Run Automated Setup
```bash
./scripts/setup_remote_worker_macos.sh
```

This script will:
- ✓ Check network connectivity to queue server
- ✓ Install system dependencies (Tesseract, Poppler, etc.)
- ✓ Create Python virtual environment
- ✓ Install Python packages
- ✓ Create `.env` configuration file

### 3. Configure MongoDB Password
```bash
nano backend/.env
```

Change `MONGO_PASSWORD=CHANGEME` to your actual MongoDB password.

### 4. Copy Google Credentials
```bash
scp user@172.12.0.132:/path/to/google-credentials.json ~/gvpocr-worker/backend/google-credentials.json
```

### 5. Test the Worker
```bash
cd ~/gvpocr-worker/backend
source venv/bin/activate
python run_worker.py --worker-id $(hostname -s)-worker-1 --nsqlookupd 172.12.0.132:4161
```

You should see:
```
================================================================================
Starting OCR Worker: YOUR-MAC-worker-1
NSQ lookupd addresses: ['172.12.0.132:4161']
================================================================================
Worker YOUR-MAC-worker-1 initialized
Worker YOUR-MAC-worker-1 is ready and listening for messages
```

Press `Ctrl+C` to stop.

### 6. Install as Background Service
```bash
cd ~/gvpocr-worker
./scripts/install_worker_launchagent.sh
```

The worker will now:
- Run automatically in the background
- Start on login
- Restart if it crashes
- Write logs to `~/gvpocr-worker/backend/worker.log`

## Managing the Worker

### Check Status
```bash
launchctl list | grep gvpocr
```

### View Logs
```bash
# Live log tail
tail -f ~/gvpocr-worker/backend/worker.log

# Error log
tail -f ~/gvpocr-worker/backend/worker_error.log
```

### Stop Worker
```bash
launchctl stop com.gvpocr.worker
```

### Start Worker
```bash
launchctl start com.gvpocr.worker
```

### Restart Worker
```bash
launchctl stop com.gvpocr.worker && launchctl start com.gvpocr.worker
```

### Uninstall Worker
```bash
launchctl unload ~/Library/LaunchAgents/com.gvpocr.worker.plist
rm ~/Library/LaunchAgents/com.gvpocr.worker.plist
```

## Monitoring

### NSQ Admin UI
Open in browser: **http://172.12.0.132:4171**

- Navigate to **Topics** → `bulk_ocr_file_tasks`
- Check channel `bulk_ocr_workers`
- Your Mac worker should appear in connections

### macOS Activity Monitor
```bash
open -a "Activity Monitor"
```

Search for "python" to see the worker process.

## Running Multiple Workers

You can run multiple workers on the same Mac for better performance:

### Option 1: Multiple LaunchAgents
```bash
# Create worker 2
cp ~/Library/LaunchAgents/com.gvpocr.worker.plist ~/Library/LaunchAgents/com.gvpocr.worker2.plist

# Edit the file and change:
# - Label to com.gvpocr.worker2
# - worker-id to a different name
nano ~/Library/LaunchAgents/com.gvpocr.worker2.plist

# Load it
launchctl load ~/Library/LaunchAgents/com.gvpocr.worker2.plist
```

### Option 2: Run Additional Workers Manually
```bash
# In Terminal 1
cd ~/gvpocr-worker/backend
source venv/bin/activate
python run_worker.py --worker-id $(hostname -s)-worker-1 --nsqlookupd 172.12.0.132:4161

# In Terminal 2
python run_worker.py --worker-id $(hostname -s)-worker-2 --nsqlookupd 172.12.0.132:4161

# In Terminal 3
python run_worker.py --worker-id $(hostname -s)-worker-3 --nsqlookupd 172.12.0.132:4161
```

## Preventing Sleep During Processing

To keep your Mac awake while processing jobs:

### Option 1: caffeinate Command
```bash
# Keep Mac awake (run in a terminal)
caffeinate -d
```

### Option 2: System Settings
1. Open **System Settings** → **Battery** (or **Energy Saver**)
2. Click **Options** (if on a MacBook)
3. Adjust "Turn display off after" to a longer time
4. Check "Prevent automatic sleeping when display is off" (if available)

## File Access Setup (Optional but Recommended)

Workers need access to files being processed. Set up NFS mount:

### On Queue Server (172.12.0.132)
```bash
sudo ./scripts/configure_queue_server.sh
# Select "yes" when prompted for NFS setup
```

### On Your Mac
```bash
# Create mount point
sudo mkdir -p /Volumes/gvpocr-uploads

# Mount NFS share
sudo mount -t nfs -o resvport 172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /Volumes/gvpocr-uploads

# Test access
ls /Volumes/gvpocr-uploads
```

### Auto-mount on Login
Add to `/etc/fstab`:
```bash
echo "172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /Volumes/gvpocr-uploads nfs resvport,ro 0 0" | sudo tee -a /etc/fstab
```

## Troubleshooting

### Can't Connect to Queue Server
```bash
# Test connectivity
nc -zv 172.12.0.132 4161
curl http://172.12.0.132:4161/ping

# Should return: OK
```

### Worker Won't Start
```bash
# Check error log
cat ~/gvpocr-worker/backend/worker_error.log

# Check system log
log show --predicate 'process == "gvpocr"' --last 10m

# Validate plist
plutil ~/Library/LaunchAgents/com.gvpocr.worker.plist
```

### Tesseract Not Found
```bash
# Find Tesseract path
which tesseract

# Update .env file
nano ~/gvpocr-worker/backend/.env
# Set: TESSERACT_CMD=/path/to/tesseract
```

### Python Module Import Errors
```bash
# Ensure virtual environment is activated
cd ~/gvpocr-worker/backend
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Permission Denied Errors
```bash
# Give Terminal full disk access
# System Settings → Privacy & Security → Full Disk Access → Add Terminal
```

## macOS-Specific Tips

### For Apple Silicon (M1/M2/M3) Macs
Some Python packages may benefit from ARM-native builds:
```bash
# Use ARM-native Python
brew install python@3.11

# Force reinstall packages for ARM
cd ~/gvpocr-worker/backend
source venv/bin/activate
pip install --force-reinstall --no-cache-dir -r requirements.txt
```

### Finding Tesseract Path
```bash
# Apple Silicon
/opt/homebrew/bin/tesseract

# Intel Mac
/usr/local/bin/tesseract

# Check yours
which tesseract
```

### Disable Spotlight on Upload Directory
If using NFS mount, disable Spotlight indexing to save resources:
```bash
sudo mdutil -i off /Volumes/gvpocr-uploads
```

## Quick Reference

| Task | Command |
|------|---------|
| Setup worker | `./scripts/setup_remote_worker_macos.sh` |
| Install service | `./scripts/install_worker_launchagent.sh` |
| Start worker | `launchctl start com.gvpocr.worker` |
| Stop worker | `launchctl stop com.gvpocr.worker` |
| View logs | `tail -f ~/gvpocr-worker/backend/worker.log` |
| Check status | `launchctl list \| grep gvpocr` |
| NSQ Admin | http://172.12.0.132:4171 |

## Getting Help

For detailed information, see:
- **REMOTE_WORKER_SETUP_MACOS.md** - Complete setup guide
- **REMOTE_WORKER_SETUP.md** - Linux setup guide
- **NSQ Admin UI**: http://172.12.0.132:4171

## Summary

Your macOS machine is now a distributed OCR worker! It will:
- ✓ Connect to the NSQ queue on 172.12.0.132
- ✓ Receive OCR tasks automatically
- ✓ Process files using Google Vision, Tesseract, or other providers
- ✓ Save results back to MongoDB
- ✓ Run in the background and auto-start on login
