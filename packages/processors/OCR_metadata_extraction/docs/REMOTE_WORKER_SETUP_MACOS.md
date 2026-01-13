# Remote OCR Worker Setup Guide - macOS

This guide explains how to install and configure OCR workers on macOS machines to connect to the central NSQ queue.

## Architecture Overview

- **Queue Server (Linux Machine)**: 172.12.0.132
  - NSQ Lookupd: Port 4161 (HTTP), 4160 (TCP)
  - NSQ Daemon: Port 4150 (TCP), 4151 (HTTP)
  - MongoDB: Port 27017
  - NSQ Admin UI: Port 4171

- **Remote Workers (macOS)**: Connect to the queue server to receive and process OCR tasks

## Prerequisites on macOS

### 1. System Requirements
- macOS 10.15 (Catalina) or later
- Python 3.8+
- Network access to the queue server (172.12.0.132)
- At least 4GB RAM
- 10GB free disk space

### 2. Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Step 1: Install System Dependencies

### Install Required Packages
```bash
# Update Homebrew
brew update

# Install Python 3
brew install python@3.11

# Install Tesseract OCR
brew install tesseract tesseract-lang

# Install Poppler (for PDF processing)
brew install poppler

# Install other utilities
brew install netcat curl git
```

### Verify Installations
```bash
# Check Python
python3 --version

# Check Tesseract
tesseract --version
tesseract --list-langs

# Check PDF tools
pdftoppm -v
```

## Step 2: Test Network Connectivity

```bash
# Test NSQ Lookupd
nc -zv 172.12.0.132 4161

# Test NSQ Daemon
nc -zv 172.12.0.132 4150

# Test MongoDB
nc -zv 172.12.0.132 27017

# Test NSQ HTTP API
curl http://172.12.0.132:4161/ping
# Should return: OK
```

## Step 3: Clone Repository and Setup

### Clone the Repository
```bash
cd ~/
git clone https://github.com/palasangha/OCR_metadata_extraction.git gvpocr-worker
cd gvpocr-worker/backend
```

### Create Virtual Environment
```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment

### Create .env File
Create `backend/.env`:

```bash
# MongoDB Connection
MONGO_URI=mongodb://172.12.0.132:27017/gvpocr
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=YOUR_MONGO_PASSWORD_HERE

# NSQ Configuration
USE_NSQ=true
NSQD_ADDRESS=172.12.0.132:4150
NSQLOOKUPD_ADDRESSES=172.12.0.132:4161

# OCR Provider Configuration
GOOGLE_APPLICATION_CREDENTIALS=/Users/YOUR_USERNAME/gvpocr-worker/backend/google-credentials.json
DEFAULT_OCR_PROVIDER=google_vision

# Provider Enablement
GOOGLE_VISION_ENABLED=true
TESSERACT_ENABLED=true
OLLAMA_ENABLED=false
VLLM_ENABLED=false
EASYOCR_ENABLED=false
AZURE_ENABLED=false

# Tesseract Configuration (macOS Homebrew path)
TESSERACT_CMD=/opt/homebrew/bin/tesseract
```

**Note**: On Intel Macs, Homebrew installs to `/usr/local/bin`, on Apple Silicon Macs it's `/opt/homebrew/bin`

### Copy Google Credentials

```bash
# Copy from queue server
scp user@172.12.0.132:/path/to/google-credentials.json ~/gvpocr-worker/backend/google-credentials.json

# Or download and place manually
# Then update the path in .env file
```

## Step 5: Setup File Access

Workers need access to files being processed. Choose one method:

### Option A: NFS Mount (Recommended)

macOS has built-in NFS client support.

**First, ensure NFS is configured on the queue server** (see REMOTE_WORKER_SETUP.md)

**On macOS:**
```bash
# Create mount point
sudo mkdir -p /Volumes/gvpocr-uploads

# Mount NFS share
sudo mount -t nfs -o resvport 172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /Volumes/gvpocr-uploads

# Verify mount
ls /Volumes/gvpocr-uploads

# Make permanent - add to /etc/fstab
echo "172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /Volumes/gvpocr-uploads nfs resvport,ro 0 0" | sudo tee -a /etc/fstab
```

**Auto-mount on login:**
Create a LaunchAgent to mount on startup (see Step 7 below).

### Option B: SSHFS (Alternative)
```bash
# Install macFUSE and SSHFS
brew install --cask macfuse
brew install sshfs

# Create mount point
mkdir -p ~/gvpocr-uploads

# Mount via SSHFS
sshfs user@172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads ~/gvpocr-uploads -o allow_other,defer_permissions
```

## Step 6: Test the Worker

### Manual Test Run
```bash
# Navigate to backend directory
cd ~/gvpocr-worker/backend

# Activate virtual environment
source venv/bin/activate

# Set worker ID
WORKER_ID="$(hostname -s)-worker-1"

# Run worker
python run_worker.py --worker-id $WORKER_ID --nsqlookupd 172.12.0.132:4161
```

You should see output like:
```
================================================================================
Starting OCR Worker: YOUR-MAC-worker-1
NSQ lookupd addresses: ['172.12.0.132:4161']
================================================================================
Worker YOUR-MAC-worker-1 initialized
Worker YOUR-MAC-worker-1 is ready and listening for messages
```

Press `Ctrl+C` to stop the worker.

## Step 7: Run Worker as Background Service

macOS uses **LaunchAgents** instead of systemd. Here's how to set it up:

### Create LaunchAgent Configuration

Create file `~/Library/LaunchAgents/com.gvpocr.worker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gvpocr.worker</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/gvpocr-worker/backend/venv/bin/python</string>
        <string>/Users/YOUR_USERNAME/gvpocr-worker/backend/run_worker.py</string>
        <string>--worker-id</string>
        <string>YOUR-MAC-worker</string>
        <string>--nsqlookupd</string>
        <string>172.12.0.132:4161</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/gvpocr-worker/backend</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/gvpocr-worker/backend/worker.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/gvpocr-worker/backend/worker_error.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

**Replace `YOUR_USERNAME` with your actual macOS username!**

### Load and Start the Service

```bash
# Load the LaunchAgent
launchctl load ~/Library/LaunchAgents/com.gvpocr.worker.plist

# Start the service
launchctl start com.gvpocr.worker

# Check if it's running
launchctl list | grep gvpocr

# View logs
tail -f ~/gvpocr-worker/backend/worker.log
```

### Service Management Commands

```bash
# Start service
launchctl start com.gvpocr.worker

# Stop service
launchctl stop com.gvpocr.worker

# Restart service (stop and start)
launchctl stop com.gvpocr.worker && launchctl start com.gvpocr.worker

# Unload service (disable)
launchctl unload ~/Library/LaunchAgents/com.gvpocr.worker.plist

# Reload service (after editing plist)
launchctl unload ~/Library/LaunchAgents/com.gvpocr.worker.plist
launchctl load ~/Library/LaunchAgents/com.gvpocr.worker.plist

# View logs
tail -f ~/gvpocr-worker/backend/worker.log
tail -f ~/gvpocr-worker/backend/worker_error.log
```

## Step 8: Verify Worker is Connected

### Check NSQ Admin UI
Open in browser: http://172.12.0.132:4171

Look for:
- Topic: `bulk_ocr_file_tasks`
- Channel: `bulk_ocr_workers`
- Your Mac worker should appear in the connections

### Monitor Worker Activity
```bash
# Watch worker logs
tail -f ~/gvpocr-worker/backend/worker.log

# Or if running manually
# Logs will appear in terminal
```

## Running Multiple Workers on Same Mac

### Option 1: Multiple LaunchAgents
Create multiple plist files with different worker IDs:
- `com.gvpocr.worker1.plist`
- `com.gvpocr.worker2.plist`
- `com.gvpocr.worker3.plist`

### Option 2: Run Additional Workers Manually
```bash
# Terminal 1
cd ~/gvpocr-worker/backend
source venv/bin/activate
python run_worker.py --worker-id $(hostname -s)-worker-1 --nsqlookupd 172.12.0.132:4161

# Terminal 2
python run_worker.py --worker-id $(hostname -s)-worker-2 --nsqlookupd 172.12.0.132:4161

# Terminal 3
python run_worker.py --worker-id $(hostname -s)-worker-3 --nsqlookupd 172.12.0.132:4161
```

## macOS-Specific Considerations

### 1. Firewall
macOS firewall typically doesn't block outgoing connections, so no configuration needed.

### 2. Preventing Sleep
To prevent Mac from sleeping during processing:

```bash
# Keep Mac awake while worker is running
caffeinate -s &
```

Or in System Preferences:
- System Settings → Battery/Energy Saver
- Check "Prevent automatic sleeping when display is off"

### 3. Finding Tesseract Path
```bash
# Find Tesseract installation
which tesseract

# Common paths:
# Apple Silicon: /opt/homebrew/bin/tesseract
# Intel Mac: /usr/local/bin/tesseract
```

### 4. Python Path
```bash
# Find Python path
which python3

# Common paths:
# Apple Silicon Homebrew: /opt/homebrew/bin/python3
# Intel Homebrew: /usr/local/bin/python3
# System Python: /usr/bin/python3
```

## Troubleshooting

### Can't Connect to NSQ
```bash
# Test connectivity
nc -zv 172.12.0.132 4161

# Check if VPN is required
ping 172.12.0.132

# Test HTTP API
curl http://172.12.0.132:4161/ping
```

### Import Errors
```bash
# Make sure virtual environment is activated
source ~/gvpocr-worker/backend/venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Tesseract Not Found
```bash
# Check if installed
brew list tesseract

# Reinstall if needed
brew reinstall tesseract

# Find path and update .env
which tesseract
```

### NFS Mount Issues
```bash
# Check NFS mounts
mount | grep nfs

# Unmount and remount
sudo umount /Volumes/gvpocr-uploads
sudo mount -t nfs -o resvport 172.12.0.132:/path/to/uploads /Volumes/gvpocr-uploads

# Check NFS server exports
showmount -e 172.12.0.132
```

### LaunchAgent Won't Start
```bash
# Check for errors
launchctl list | grep gvpocr

# Check system log
log show --predicate 'process == "gvpocr"' --last 10m

# Validate plist file
plutil ~/Library/LaunchAgents/com.gvpocr.worker.plist

# Check logs
cat ~/gvpocr-worker/backend/worker_error.log
```

### Permission Issues
```bash
# Give full disk access to Terminal
# System Settings → Privacy & Security → Full Disk Access
# Add Terminal.app

# Fix file permissions
chmod +x ~/gvpocr-worker/backend/run_worker.py
```

## Performance Tips for macOS

### 1. Disable Spotlight Indexing on Upload Directory
```bash
sudo mdutil -i off /Volumes/gvpocr-uploads
```

### 2. Monitor Resource Usage
```bash
# Activity Monitor (GUI)
open -a "Activity Monitor"

# Terminal
top -o cpu
```

### 3. Optimize for Apple Silicon
If you have an M1/M2/M3 Mac, some OCR libraries may benefit from ARM optimization:
```bash
# Install ARM-native Python
brew install python@3.11

# Reinstall dependencies for ARM
pip install --force-reinstall --no-cache-dir -r requirements.txt
```

## Uninstall Worker

```bash
# Stop and unload service
launchctl stop com.gvpocr.worker
launchctl unload ~/Library/LaunchAgents/com.gvpocr.worker.plist

# Remove LaunchAgent
rm ~/Library/LaunchAgents/com.gvpocr.worker.plist

# Unmount NFS
sudo umount /Volumes/gvpocr-uploads

# Remove directory
rm -rf ~/gvpocr-worker
```

## Quick Reference

### Start Worker (Manual)
```bash
cd ~/gvpocr-worker/backend
source venv/bin/activate
python run_worker.py --worker-id $(hostname -s)-worker-1 --nsqlookupd 172.12.0.132:4161
```

### Start Worker (Service)
```bash
launchctl start com.gvpocr.worker
```

### View Logs
```bash
tail -f ~/gvpocr-worker/backend/worker.log
```

### Check Status
```bash
launchctl list | grep gvpocr
```

### NSQ Admin UI
```
http://172.12.0.132:4171
```
