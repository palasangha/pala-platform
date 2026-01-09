#!/bin/bash
# Setup Worker Machine for GVPOCR Docker Registry
# Run this on worker machines to configure access to registry.palatools.me:5005

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_header() { echo -e "${BLUE}$1${NC}"; }

clear
print_header "========================================="
print_header "  GVPOCR Registry - Worker Setup"
print_header "========================================="
echo ""

# Configuration
REGISTRY_DOMAIN="registry.palatools.me"
REGISTRY_IP="172.12.0.132"
REGISTRY_PORT="5005"
REGISTRY_SERVER="mango1@172.12.0.132"
CERT_PATH="/mnt/sda1/mango1_home/registry/certs/domain.crt"

print_info "Registry: $REGISTRY_DOMAIN:$REGISTRY_PORT"
print_info "Server IP: $REGISTRY_IP"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    print_info "Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    print_info "Detected: Linux"
else
    print_error "Unsupported OS: $OSTYPE"
    exit 1
fi

# Step 1: Add DNS entry
print_info "Adding DNS entry to /etc/hosts..."
if grep -q "$REGISTRY_DOMAIN" /etc/hosts 2>/dev/null; then
    print_success "DNS entry already exists"
else
    echo "$REGISTRY_IP    $REGISTRY_DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    print_success "DNS entry added"
fi

# Step 2: Copy certificate
print_info "Copying SSL certificate from registry server..."
TEMP_CERT="/tmp/registry-cert.crt"
if scp "$REGISTRY_SERVER:$CERT_PATH" "$TEMP_CERT"; then
    print_success "Certificate downloaded"
else
    print_error "Failed to download certificate"
    echo "Make sure you can SSH to $REGISTRY_SERVER"
    exit 1
fi

# Step 3: Install certificate
if [ "$OS_TYPE" == "macos" ]; then
    print_info "Installing certificate in macOS keychain..."
    sudo security add-trusted-cert -d -r trustRoot \
        -k /Library/Keychains/System.keychain "$TEMP_CERT"
    print_success "Certificate installed"

    print_info "Please restart Docker Desktop manually"
    print_info "Right-click Docker icon → Quit Docker Desktop → Start Docker Desktop"
    read -p "Press Enter after restarting Docker Desktop..."

elif [ "$OS_TYPE" == "linux" ]; then
    print_info "Installing certificate for Docker..."
    sudo mkdir -p "/etc/docker/certs.d/$REGISTRY_DOMAIN:$REGISTRY_PORT"
    sudo cp "$TEMP_CERT" "/etc/docker/certs.d/$REGISTRY_DOMAIN:$REGISTRY_PORT/ca.crt"
    print_success "Certificate installed"

    print_info "Restarting Docker..."
    sudo systemctl restart docker
    sleep 3
    print_success "Docker restarted"
fi

# Cleanup
rm -f "$TEMP_CERT"

# Step 4: Test connection
print_info "Testing registry connection..."
if curl -k -s "https://$REGISTRY_DOMAIN:$REGISTRY_PORT/v2/" > /dev/null 2>&1; then
    print_success "Registry is accessible"
else
    print_error "Cannot connect to registry"
    echo "Check your network connection and firewall settings"
    exit 1
fi

# Step 5: Login to registry
print_info "Logging in to registry..."
echo ""
echo "Please enter registry credentials:"
echo "  Username: admin"
echo "  Password: gvpocr2024"
echo ""

if docker login "$REGISTRY_DOMAIN:$REGISTRY_PORT"; then
    print_success "Login successful"
else
    print_error "Login failed"
    exit 1
fi

# Step 6: Test pull
print_info "Testing image pull..."
if docker pull "$REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"; then
    print_success "Successfully pulled worker image"
else
    print_error "Failed to pull image"
    exit 1
fi

echo ""
print_header "========================================="
print_header "  Setup Complete!"
print_header "========================================="
echo ""
print_success "Worker is configured for registry.palatools.me"
echo ""
echo "You can now pull images:"
echo "  docker pull $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"
echo "  docker pull $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/backend:latest"
echo "  docker pull $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/frontend:latest"
echo ""
echo "Run worker:"
echo "  docker run -d --name ocr-worker \\"
echo "    -e NSQLOOKUPD_ADDRESSES=$REGISTRY_IP:4161 \\"
echo "    -e MONGODB_URI=mongodb://gvpocr_user:password@$REGISTRY_IP:27017/gvpocr?authSource=admin \\"
echo "    $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"
echo ""
