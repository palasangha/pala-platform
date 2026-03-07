#!/bin/bash
# Remote OCR Worker Setup Script for macOS
# This script helps set up a worker on a macOS machine

set -e

echo "========================================="
echo "GVPOCR Remote Worker Setup - macOS"
echo "========================================="
echo ""

# Configuration
QUEUE_SERVER_IP="${QUEUE_SERVER_IP:-172.12.0.132}"
NSQLOOKUPD_PORT="4161"
NSQD_PORT="4150"
MONGODB_PORT="27017"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[$1] $2${NC}"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is for macOS only!"
    echo "For Linux, use: ./scripts/setup_remote_worker.sh"
    exit 1
fi

# Get current IP
CURRENT_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "unknown")
echo "Queue Server: $QUEUE_SERVER_IP"
echo "Worker Machine (Mac): $CURRENT_IP"
echo ""

# Step 1: Check Homebrew
print_step "1/10" "Checking Homebrew..."
if command -v brew &> /dev/null; then
    print_success "Homebrew is installed: $(brew --version | head -n 1)"
else
    print_error "Homebrew is not installed"
    echo ""
    echo "Install Homebrew with:"
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

# Step 2: Test Network Connectivity
print_step "2/10" "Testing network connectivity..."

# Check nc is available
if ! command -v nc &> /dev/null; then
    print_error "netcat (nc) not found, installing..."
    brew install netcat
fi

if nc -z $QUEUE_SERVER_IP $NSQLOOKUPD_PORT 2>/dev/null; then
    print_success "NSQ Lookupd (port $NSQLOOKUPD_PORT) is reachable"
else
    print_error "Cannot reach NSQ Lookupd on $QUEUE_SERVER_IP:$NSQLOOKUPD_PORT"
    echo "Please ensure:"
    echo "  1. Queue server is running"
    echo "  2. Firewall allows connections"
    echo "  3. Network connectivity exists"
    exit 1
fi

if nc -z $QUEUE_SERVER_IP $NSQD_PORT 2>/dev/null; then
    print_success "NSQ Daemon (port $NSQD_PORT) is reachable"
else
    print_error "Cannot reach NSQ Daemon on $QUEUE_SERVER_IP:$NSQD_PORT"
    exit 1
fi

if nc -z $QUEUE_SERVER_IP $MONGODB_PORT 2>/dev/null; then
    print_success "MongoDB (port $MONGODB_PORT) is reachable"
else
    print_error "Cannot reach MongoDB on $QUEUE_SERVER_IP:$MONGODB_PORT"
    exit 1
fi

# Step 3: Check Python
print_step "3/10" "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_success "Python $PYTHON_VERSION is installed"
    else
        print_error "Python version is too old: $PYTHON_VERSION (need 3.8+)"
        echo "Install newer Python with: brew install python@3.11"
        exit 1
    fi
else
    print_error "Python 3 is not installed"
    echo "Install with: brew install python@3.11"
    exit 1
fi

# Step 4: Check/Install System Dependencies
print_step "4/10" "Checking system dependencies..."

# Check and install Tesseract
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n 1)
    print_success "Tesseract is installed: $TESSERACT_VERSION"
    TESSERACT_PATH=$(which tesseract)
else
    print_info "Installing Tesseract OCR..."
    brew install tesseract tesseract-lang
    print_success "Tesseract installed"
    TESSERACT_PATH=$(which tesseract)
fi

# Check and install Poppler
if command -v pdftoppm &> /dev/null; then
    print_success "Poppler (PDF tools) is installed"
else
    print_info "Installing Poppler..."
    brew install poppler
    print_success "Poppler installed"
fi

# Step 5: Check if in git repository
print_step "5/10" "Checking for backend directory..."
if [ ! -d "backend" ]; then
    print_error "backend directory not found. Please run this script from the repository root."
    echo ""
    echo "Clone the repository first:"
    echo "  git clone https://github.com/palasangha/OCR_metadata_extraction.git ~/gvpocr-worker"
    echo "  cd ~/gvpocr-worker"
    echo "  ./scripts/setup_remote_worker_macos.sh"
    exit 1
fi

cd backend
BACKEND_DIR=$(pwd)

# Step 6: Create virtual environment
print_step "6/10" "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

source venv/bin/activate

# Step 7: Install Python dependencies
print_step "7/10" "Installing Python dependencies (this may take a few minutes)..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Python dependencies installed"

# Step 8: Create .env file
print_step "8/10" "Creating environment configuration..."
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
GOOGLE_APPLICATION_CREDENTIALS=$BACKEND_DIR/google-credentials.json
DEFAULT_OCR_PROVIDER=google_vision

# Provider Enablement
GOOGLE_VISION_ENABLED=true
TESSERACT_ENABLED=true
OLLAMA_ENABLED=false
VLLM_ENABLED=false
EASYOCR_ENABLED=false
AZURE_ENABLED=false

# Tesseract Configuration (macOS)
TESSERACT_CMD=$TESSERACT_PATH
EOF
    print_success ".env file created"
    print_error "IMPORTANT: Edit .env file and set MONGO_PASSWORD"
else
    print_success ".env file already exists"
fi

# Step 9: Check Google credentials
print_step "9/10" "Checking Google credentials..."
if [ -f "google-credentials.json" ]; then
    print_success "google-credentials.json found"
else
    print_error "google-credentials.json not found"
    echo ""
    echo "Copy from queue server with:"
    echo "  scp user@$QUEUE_SERVER_IP:/path/to/google-credentials.json $BACKEND_DIR/google-credentials.json"
    echo ""
fi

# Step 10: Test NSQ connection
print_step "10/10" "Testing NSQ API..."
if curl -s http://$QUEUE_SERVER_IP:4161/ping 2>/dev/null | grep -q OK; then
    print_success "NSQ Lookupd is responding"
else
    print_error "NSQ Lookupd is not responding"
fi

# Generate worker ID
WORKER_ID="$(hostname -s)-worker"

# Print summary
echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
print_success "Worker is ready to start"
echo ""
echo "System Information:"
echo "  macOS Version: $(sw_vers -productVersion)"
echo "  Python: $PYTHON_VERSION"
echo "  Tesseract: $TESSERACT_PATH"
echo "  Backend Directory: $BACKEND_DIR"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file and set correct values:"
echo "   nano $BACKEND_DIR/.env"
echo ""
echo "2. Copy Google credentials (if using Google Vision):"
echo "   scp user@$QUEUE_SERVER_IP:/path/to/google-credentials.json $BACKEND_DIR/google-credentials.json"
echo ""
echo "3. Test the worker:"
echo "   cd $BACKEND_DIR"
echo "   source venv/bin/activate"
echo "   python run_worker.py --worker-id $WORKER_ID --nsqlookupd $QUEUE_SERVER_IP:4161"
echo ""
echo "4. Install as LaunchAgent (auto-start on login):"
echo "   ./scripts/install_worker_launchagent.sh"
echo ""
echo "5. Monitor at NSQ Admin UI:"
echo "   http://$QUEUE_SERVER_IP:4171"
echo ""
echo "Worker ID: $WORKER_ID"
echo "Queue Server: $QUEUE_SERVER_IP"
echo ""
