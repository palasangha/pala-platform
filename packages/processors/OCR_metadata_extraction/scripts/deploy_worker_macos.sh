#!/bin/bash

# GVPOCR Remote Worker Deployment Script for macOS
# This script sets up and deploys the updated worker with file download support
# Usage: ./deploy_worker_macos.sh <server_ip>

set -e

SERVER_IP="${1:-172.12.0.132}"
WORKER_HOME="${HOME}/gvpocr-worker"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=============================================================================="
echo "GVPOCR Remote Worker Deployment for macOS"
echo "=============================================================================="
echo "Server IP: $SERVER_IP"
echo "Worker Home: $WORKER_HOME"
echo ""

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+ using Homebrew:"
    echo "   brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Python 3 found: $PYTHON_VERSION"

# Check Git
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install using Homebrew:"
    echo "   brew install git"
    exit 1
fi
echo "✓ Git found"

# Step 2: Clone or update repository
echo ""
echo "Step 2: Setting up repository..."
echo ""

if [ ! -d "$WORKER_HOME" ]; then
    echo "→ Cloning repository..."
    git clone https://github.com/palasangha/OCR_metadata_extraction.git "$WORKER_HOME"
    echo "✓ Repository cloned"
else
    echo "→ Updating existing repository..."
    cd "$WORKER_HOME"
    git pull origin main
    echo "✓ Repository updated"
fi

cd "$WORKER_HOME/backend"

# Step 3: Setup Python virtual environment
echo ""
echo "Step 3: Setting up Python virtual environment..."
echo ""

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

source venv/bin/activate
echo "✓ Virtual environment activated"

# Step 4: Install Python dependencies
echo ""
echo "Step 4: Installing Python dependencies..."
echo ""

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "✓ Python dependencies installed"

# Step 5: Install system dependencies (macOS)
echo ""
echo "Step 5: Installing system dependencies..."
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install from https://brew.sh"
    exit 1
fi

# Install Tesseract
if ! command -v tesseract &> /dev/null; then
    echo "→ Installing Tesseract OCR..."
    brew install tesseract
    echo "✓ Tesseract installed"
else
    echo "✓ Tesseract already installed"
fi

# Install Poppler for PDF processing
if ! command -v pdftoimage &> /dev/null; then
    echo "→ Installing Poppler..."
    brew install poppler
    echo "✓ Poppler installed"
else
    echo "✓ Poppler already installed"
fi

# Step 6: Configure environment
echo ""
echo "Step 6: Configuring worker environment..."
echo ""

ENV_FILE=".env.worker"

if [ ! -f "$ENV_FILE" ]; then
    echo "→ Creating .env.worker file..."
    
    # Generate a unique worker ID
    WORKER_ID="macos-$(hostname)-$(date +%s)"
    
    cat > "$ENV_FILE" << EOF
# GVPOCR Remote Worker Configuration
# Generated: $(date)

# Worker Identification
WORKER_ID=$WORKER_ID
WORKER_NAME=macOS Worker - $(hostname)

# Server Connection
GVPOCR_SERVER_URL=http://$SERVER_IP:5000
GVPOCR_API_URL=http://$SERVER_IP:5000

# MongoDB Connection
MONGO_URI=mongodb://$SERVER_IP:27017/gvpocr
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=\${MONGO_PASSWORD:-change_me}

# NSQ Configuration
USE_NSQ=true
NSQD_ADDRESS=$SERVER_IP:4150
NSQLOOKUPD_ADDRESSES=$SERVER_IP:4161

# File Storage
GVPOCR_PATH=/Volumes/bhushanji_shared
NEWSLETTERS_PATH=/Volumes/newsletters_shared

# Samba Configuration (fallback)
SAMBA_HOST=$SERVER_IP
SAMBA_SHARE=bhushanji
SAMBA_USER=gvpocr
SAMBA_PASS=\${SAMBA_PASS:-}

# OCR Provider Configuration
DEFAULT_OCR_PROVIDER=tesseract
GOOGLE_VISION_ENABLED=false
TESSERACT_ENABLED=true
OLLAMA_ENABLED=false
VLLM_ENABLED=false
EASYOCR_ENABLED=false
AZURE_ENABLED=false

# Optional: Google Vision
GOOGLE_APPLICATION_CREDENTIALS=\${HOME}/google-credentials.json

# Logging
LOG_LEVEL=INFO
EOF
    
    echo "✓ .env.worker created"
    echo ""
    echo "⚠️  UPDATE REQUIRED: Edit .env.worker to set:"
    echo "   - MONGO_PASSWORD: MongoDB password"
    echo "   - GVPOCR_PATH: Mount point for shared files"
    echo "   - SAMBA_PASS: Samba password (if using as fallback)"
    echo ""
    echo "   nano .env.worker"
else
    echo "✓ .env.worker already exists"
    echo "  Review and update if needed:"
    echo "  nano .env.worker"
fi

# Step 7: Setup file mount points
echo ""
echo "Step 7: Configuring file mount points..."
echo ""

GVPOCR_MOUNT="/Volumes/bhushanji_shared"
NEWSLETTERS_MOUNT="/Volumes/newsletters_shared"

echo "→ File mount configuration needed:"
echo ""
echo "  You need to mount the shared files from the server."
echo "  Options:"
echo ""
echo "  Option 1: NFS Mount (Recommended)"
echo "    sudo mkdir -p $GVPOCR_MOUNT"
echo "    sudo mount -t nfs -o ro $SERVER_IP:/Volumes/bhushanji_shared $GVPOCR_MOUNT"
echo ""
echo "  Option 2: SMB/CIFS Mount"
echo "    sudo mkdir -p $GVPOCR_MOUNT"
echo "    mount_smbfs //gvpocr:\${SAMBA_PASS}@$SERVER_IP/bhushanji $GVPOCR_MOUNT"
echo ""
echo "  Option 3: Use HTTP Downloads Only (No Local Mount)"
echo "    - Set GVPOCR_PATH and NEWSLETTERS_PATH to empty in .env.worker"
echo "    - Worker will download files via HTTP API"
echo ""

# Step 8: Create launch script
echo ""
echo "Step 8: Creating worker launch script..."
echo ""

LAUNCH_SCRIPT="$WORKER_HOME/start-worker.sh"

cat > "$LAUNCH_SCRIPT" << 'EOF'
#!/bin/bash
# Start GVPOCR Remote Worker on macOS

WORKER_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$WORKER_HOME/backend"

# Load environment
if [ -f ".env.worker" ]; then
    export $(cat .env.worker | grep -v '^#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Get worker ID from environment or generate
WORKER_ID=${WORKER_ID:-"macos-$(hostname)-$$"}

echo "=============================================================================="
echo "Starting GVPOCR Remote Worker"
echo "=============================================================================="
echo "Worker ID: $WORKER_ID"
echo "Server: $GVPOCR_SERVER_URL"
echo "NSQ Lookupd: $NSQLOOKUPD_ADDRESSES"
echo ""

# Start worker
python run_worker.py \
    --worker-id "$WORKER_ID" \
    --nsqlookupd $NSQLOOKUPD_ADDRESSES
EOF

chmod +x "$LAUNCH_SCRIPT"
echo "✓ Launch script created: $LAUNCH_SCRIPT"

# Step 9: Create LaunchAgent for background operation (optional)
echo ""
echo "Step 9: Setting up background service (optional)..."
echo ""

LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.gvpocr.worker.plist"

echo "→ To run worker as background service, create LaunchAgent:"
echo ""
echo "   1. Create plist file:"
echo "      cat > '$LAUNCH_AGENT_PLIST' << 'PLIST'"
cat << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gvpocr.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>WORKER_HOME/start-worker.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>WORKER_HOME/worker.log</string>
    <key>StandardErrorPath</key>
    <string>WORKER_HOME/worker.error.log</string>
</dict>
</plist>
PLIST

echo ""
echo "   2. Load the agent:"
echo "      launchctl load '$LAUNCH_AGENT_PLIST'"
echo ""
echo "   3. Verify:"
echo "      launchctl list | grep gvpocr"
echo ""

# Summary
echo ""
echo "=============================================================================="
echo "Deployment Complete!"
echo "=============================================================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit configuration:"
echo "   nano $WORKER_HOME/backend/.env.worker"
echo ""
echo "2. Setup file mounts (if needed):"
echo "   - For NFS: sudo mount -t nfs $SERVER_IP:/Volumes/bhushanji_shared /Volumes/bhushanji_shared"
echo "   - Or configure Samba fallback credentials in .env.worker"
echo ""
echo "3. Test connectivity:"
echo "   curl http://$SERVER_IP:4161/ping"
echo "   # Should return: OK"
echo ""
echo "4. Start worker:"
echo "   $LAUNCH_SCRIPT"
echo ""
echo "5. Monitor worker:"
echo "   tail -f $WORKER_HOME/worker.log"
echo ""
echo "=============================================================================="
