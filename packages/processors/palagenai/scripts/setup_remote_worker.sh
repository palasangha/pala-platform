#!/bin/bash
# Remote OCR Worker Setup Script
# This script helps set up a worker on a remote machine

set -e

echo "========================================="
echo "GVPOCR Remote Worker Setup"
echo "========================================="
echo ""

# Configuration
QUEUE_SERVER_IP="172.12.0.132"
NSQLOOKUPD_PORT="4161"
NSQD_PORT="4150"
MONGODB_PORT="27017"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if running on the queue server
CURRENT_IP=$(hostname -I | awk '{print $1}')
if [ "$CURRENT_IP" == "$QUEUE_SERVER_IP" ]; then
    print_error "This script should be run on a REMOTE worker machine, not the queue server!"
    echo "Current IP: $CURRENT_IP"
    echo "Queue Server IP: $QUEUE_SERVER_IP"
    exit 1
fi

echo "Queue Server: $QUEUE_SERVER_IP"
echo "Worker Machine: $CURRENT_IP"
echo ""

# Step 1: Test Network Connectivity
print_info "Testing network connectivity to queue server..."
if nc -zv $QUEUE_SERVER_IP $NSQLOOKUPD_PORT 2>&1 | grep -q succeeded; then
    print_success "NSQ Lookupd (port $NSQLOOKUPD_PORT) is reachable"
else
    print_error "Cannot reach NSQ Lookupd on $QUEUE_SERVER_IP:$NSQLOOKUPD_PORT"
    echo "Please ensure:"
    echo "  1. Queue server is running"
    echo "  2. Firewall allows connections"
    echo "  3. Network connectivity exists"
    exit 1
fi

if nc -zv $QUEUE_SERVER_IP $NSQD_PORT 2>&1 | grep -q succeeded; then
    print_success "NSQ Daemon (port $NSQD_PORT) is reachable"
else
    print_error "Cannot reach NSQ Daemon on $QUEUE_SERVER_IP:$NSQD_PORT"
    exit 1
fi

if nc -zv $QUEUE_SERVER_IP $MONGODB_PORT 2>&1 | grep -q succeeded; then
    print_success "MongoDB (port $MONGODB_PORT) is reachable"
else
    print_error "Cannot reach MongoDB on $QUEUE_SERVER_IP:$MONGODB_PORT"
    exit 1
fi

# Step 2: Check Python
print_info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python $PYTHON_VERSION is installed"
else
    print_error "Python 3 is not installed"
    echo "Install with: sudo apt-get install python3 python3-venv python3-pip"
    exit 1
fi

# Step 3: Check if in git repository
print_info "Checking for backend directory..."
if [ ! -d "backend" ]; then
    print_error "backend directory not found. Please run this script from the repository root."
    echo ""
    echo "Clone the repository first:"
    echo "  git clone https://github.com/palasangha/OCR_metadata_extraction.git gvpocr-worker"
    echo "  cd gvpocr-worker"
    echo "  ./scripts/setup_remote_worker.sh"
    exit 1
fi

cd backend

# Step 4: Create virtual environment
print_info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

source venv/bin/activate

# Step 5: Install dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Python dependencies installed"

# Step 6: Check system dependencies
print_info "Checking system dependencies..."

# Check Tesseract
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n 1)
    print_success "Tesseract is installed: $TESSERACT_VERSION"
else
    print_error "Tesseract is not installed"
    echo "Install with: sudo apt-get install tesseract-ocr"
fi

# Check poppler (for PDF processing)
if command -v pdftoppm &> /dev/null; then
    print_success "Poppler utils (PDF processing) is installed"
else
    print_error "Poppler utils not installed"
    echo "Install with: sudo apt-get install poppler-utils"
fi

# Step 7: Create .env file if it doesn't exist
print_info "Checking environment configuration..."
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cat > .env << EOF
# MongoDB Connection
MONGO_URI=mongodb://$QUEUE_SERVER_IP:27017/gvpocr
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=CHANGEME

# NSQ Configuration
USE_NSQ=true
NSQD_ADDRESS=$QUEUE_SERVER_IP:4150
NSQLOOKUPD_ADDRESSES=$QUEUE_SERVER_IP:4161

# OCR Provider Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json
DEFAULT_OCR_PROVIDER=google_vision

# Provider Enablement
GOOGLE_VISION_ENABLED=true
TESSERACT_ENABLED=true
OLLAMA_ENABLED=false
VLLM_ENABLED=false
EASYOCR_ENABLED=false
AZURE_ENABLED=false
EOF
    print_success ".env file created"
    print_error "IMPORTANT: Edit .env file and set correct values (especially MONGO_PASSWORD)"
    echo ""
else
    print_success ".env file already exists"
fi

# Step 8: Check Google credentials
print_info "Checking Google credentials..."
if [ -f "google-credentials.json" ]; then
    print_success "google-credentials.json found"
else
    print_error "google-credentials.json not found"
    echo "Copy from queue server with:"
    echo "  scp user@$QUEUE_SERVER_IP:/path/to/google-credentials.json ./google-credentials.json"
fi

# Step 9: Test NSQ connection
print_info "Testing NSQ API..."
if curl -s http://$QUEUE_SERVER_IP:4161/ping | grep -q OK; then
    print_success "NSQ Lookupd is responding"
else
    print_error "NSQ Lookupd is not responding"
fi

# Step 10: Generate worker ID
WORKER_ID="$(hostname)-worker-$$"
echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
print_success "Worker is ready to start"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file and set correct values:"
echo "   nano .env"
echo ""
echo "2. Copy Google credentials (if using Google Vision):"
echo "   scp user@$QUEUE_SERVER_IP:/path/to/google-credentials.json ./google-credentials.json"
echo ""
echo "3. Start the worker:"
echo "   source venv/bin/activate"
echo "   python run_worker.py --worker-id $WORKER_ID --nsqlookupd $QUEUE_SERVER_IP:4161"
echo ""
echo "4. Or install as systemd service:"
echo "   sudo ./scripts/install_worker_service.sh"
echo ""
echo "Worker ID: $WORKER_ID"
echo "Queue Server: $QUEUE_SERVER_IP"
echo ""
