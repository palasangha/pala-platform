#!/bin/bash
# Install GVPOCR Worker as macOS LaunchAgent

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is for macOS only!"
    exit 1
fi

# Get configuration
QUEUE_SERVER_IP="${QUEUE_SERVER_IP:-172.12.0.132}"
NSQLOOKUPD_ADDRESS="${NSQLOOKUPD_ADDRESS:-$QUEUE_SERVER_IP:4161}"

# Get current directory and user
INSTALL_DIR=$(cd "$(dirname "$0")/.." && pwd)
BACKEND_DIR="$INSTALL_DIR/backend"
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)

print_info "Installing GVPOCR Worker as macOS LaunchAgent..."
echo "Install Directory: $INSTALL_DIR"
echo "Backend Directory: $BACKEND_DIR"
echo "User: $CURRENT_USER"
echo "Queue Server: $QUEUE_SERVER_IP"
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Check if venv exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    print_error "Virtual environment not found. Run setup_remote_worker_macos.sh first"
    exit 1
fi

# Check if .env exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    print_error ".env file not found. Run setup_remote_worker_macos.sh first"
    exit 1
fi

# Find Python path in venv
PYTHON_PATH="$BACKEND_DIR/venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    print_error "Python not found in venv: $PYTHON_PATH"
    exit 1
fi

# Generate worker ID
WORKER_ID="$(hostname -s)-worker"

# Determine Homebrew path (different for Intel vs Apple Silicon)
if [ -d "/opt/homebrew/bin" ]; then
    HOMEBREW_PATH="/opt/homebrew/bin"
else
    HOMEBREW_PATH="/usr/local/bin"
fi

# Create LaunchAgents directory if it doesn't exist
LAUNCHAGENTS_DIR="$USER_HOME/Library/LaunchAgents"
mkdir -p "$LAUNCHAGENTS_DIR"

# Create LaunchAgent plist file
PLIST_FILE="$LAUNCHAGENTS_DIR/com.gvpocr.worker.plist"

print_info "Creating LaunchAgent plist file..."

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gvpocr.worker</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$BACKEND_DIR/run_worker.py</string>
        <string>--worker-id</string>
        <string>$WORKER_ID</string>
        <string>--nsqlookupd</string>
        <string>$NSQLOOKUPD_ADDRESS</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$BACKEND_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOMEBREW_PATH:$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>StandardOutPath</key>
    <string>$BACKEND_DIR/worker.log</string>

    <key>StandardErrorPath</key>
    <string>$BACKEND_DIR/worker_error.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ProcessType</key>
    <string>Background</string>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

print_success "LaunchAgent plist created: $PLIST_FILE"

# Validate plist file
print_info "Validating plist file..."
if plutil -lint "$PLIST_FILE" > /dev/null 2>&1; then
    print_success "Plist file is valid"
else
    print_error "Plist file validation failed"
    exit 1
fi

# Unload if already loaded
if launchctl list | grep -q com.gvpocr.worker; then
    print_info "Unloading existing worker..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

# Load the LaunchAgent
print_info "Loading LaunchAgent..."
launchctl load "$PLIST_FILE"
print_success "LaunchAgent loaded"

# Wait a moment for it to start
sleep 2

# Check if it's running
if launchctl list | grep -q com.gvpocr.worker; then
    print_success "Worker is running!"

    # Show status
    print_info "Worker status:"
    launchctl list | grep com.gvpocr.worker | awk '{print "  PID: " $1 "\n  Status: " $2 "\n  Label: " $3}'
else
    print_error "Worker failed to start"
    echo ""
    echo "Check error log:"
    echo "  cat $BACKEND_DIR/worker_error.log"
    exit 1
fi

# Create log touch files if they don't exist
touch "$BACKEND_DIR/worker.log"
touch "$BACKEND_DIR/worker_error.log"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
print_success "GVPOCR Worker LaunchAgent installed and running"
echo ""
echo "Service Information:"
echo "  Label: com.gvpocr.worker"
echo "  Worker ID: $WORKER_ID"
echo "  Backend Dir: $BACKEND_DIR"
echo "  Queue Server: $QUEUE_SERVER_IP"
echo ""
echo "Service Management Commands:"
echo "  Status:  launchctl list | grep gvpocr"
echo "  Stop:    launchctl stop com.gvpocr.worker"
echo "  Start:   launchctl start com.gvpocr.worker"
echo "  Restart: launchctl stop com.gvpocr.worker && launchctl start com.gvpocr.worker"
echo "  Unload:  launchctl unload $PLIST_FILE"
echo ""
echo "View Logs:"
echo "  Output:  tail -f $BACKEND_DIR/worker.log"
echo "  Errors:  tail -f $BACKEND_DIR/worker_error.log"
echo ""
echo "Monitor Workers:"
echo "  NSQ Admin UI: http://$QUEUE_SERVER_IP:4171"
echo ""
echo "The worker will automatically start on login."
echo ""
