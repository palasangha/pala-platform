#!/bin/bash
# Setup Local Docker Registry for GVPOCR
# This script sets up a secure private Docker registry with basic authentication

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
print_header "  GVPOCR - Private Docker Registry Setup"
print_header "========================================="
echo ""

# Configuration
REGISTRY_PORT="${REGISTRY_PORT:-5000}"
REGISTRY_DIR="${REGISTRY_DIR:-$HOME/docker-registry}"
REGISTRY_DATA="$REGISTRY_DIR/data"
REGISTRY_AUTH="$REGISTRY_DIR/auth"
REGISTRY_CERTS="$REGISTRY_DIR/certs"

print_info "Registry Port: $REGISTRY_PORT"
print_info "Registry Directory: $REGISTRY_DIR"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    print_error "OpenSSL is not installed"
    exit 1
fi

print_success "Prerequisites check passed"

# Create registry directories
print_info "Creating registry directories..."
mkdir -p "$REGISTRY_DATA"
mkdir -p "$REGISTRY_AUTH"
mkdir -p "$REGISTRY_CERTS"
print_success "Directories created"

# Generate self-signed certificate (for HTTPS)
print_info "Generating self-signed SSL certificate..."
read -p "Enter registry domain/IP (default: $(hostname -I | awk '{print $1}')): " REGISTRY_DOMAIN
REGISTRY_DOMAIN=${REGISTRY_DOMAIN:-$(hostname -I | awk '{print $1}')}

if [ ! -f "$REGISTRY_CERTS/domain.crt" ]; then
    openssl req -newkey rsa:4096 -nodes -sha256 \
        -keyout "$REGISTRY_CERTS/domain.key" \
        -x509 -days 365 \
        -out "$REGISTRY_CERTS/domain.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$REGISTRY_DOMAIN" \
        -addext "subjectAltName=IP:$REGISTRY_DOMAIN,DNS:$REGISTRY_DOMAIN,DNS:localhost"
    print_success "SSL certificate generated"
else
    print_success "Using existing SSL certificate"
fi

# Create basic auth credentials
print_info "Setting up authentication..."
read -p "Enter registry username (default: admin): " REGISTRY_USER
REGISTRY_USER=${REGISTRY_USER:-admin}

read -s -p "Enter registry password: " REGISTRY_PASS
echo ""

if [ -z "$REGISTRY_PASS" ]; then
    print_error "Password cannot be empty"
    exit 1
fi

# Create htpasswd file
docker run --rm --entrypoint htpasswd httpd:2 -Bbn "$REGISTRY_USER" "$REGISTRY_PASS" > "$REGISTRY_AUTH/htpasswd"
print_success "Authentication configured"

# Create docker-compose file for registry
print_info "Creating docker-compose configuration..."
cat > "$REGISTRY_DIR/docker-compose.yml" <<EOF
version: '3.8'

services:
  registry:
    image: registry:2
    container_name: docker-registry
    restart: always
    ports:
      - "${REGISTRY_PORT}:5000"
    environment:
      REGISTRY_AUTH: htpasswd
      REGISTRY_AUTH_HTPASSWD_PATH: /auth/htpasswd
      REGISTRY_AUTH_HTPASSWD_REALM: "Registry Realm"
      REGISTRY_HTTP_TLS_CERTIFICATE: /certs/domain.crt
      REGISTRY_HTTP_TLS_KEY: /certs/domain.key
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
    volumes:
      - ./data:/var/lib/registry
      - ./auth:/auth
      - ./certs:/certs
    networks:
      - registry-network

  # Optional: Web UI for registry
  registry-ui:
    image: joxit/docker-registry-ui:latest
    container_name: docker-registry-ui
    restart: always
    ports:
      - "8080:80"
    environment:
      SINGLE_REGISTRY: "true"
      REGISTRY_TITLE: "GVPOCR Docker Registry"
      REGISTRY_URL: "https://registry:5000"
      DELETE_IMAGES: "true"
      SHOW_CONTENT_DIGEST: "true"
      NGINX_PROXY_PASS_URL: "https://registry:5000"
      SHOW_CATALOG_NB_TAGS: "true"
      CATALOG_MIN_BRANCHES: "1"
      CATALOG_MAX_BRANCHES: "1"
      TAGLIST_PAGE_SIZE: "100"
      REGISTRY_SECURED: "false"
      CATALOG_ELEMENTS_LIMIT: "1000"
    depends_on:
      - registry
    networks:
      - registry-network

networks:
  registry-network:
    driver: bridge
EOF
print_success "Docker Compose configuration created"

# Start the registry
print_info "Starting Docker registry..."
cd "$REGISTRY_DIR"
docker-compose up -d
sleep 5
print_success "Registry started"

# Test the registry
print_info "Testing registry connectivity..."
if curl -k -u "$REGISTRY_USER:$REGISTRY_PASS" "https://$REGISTRY_DOMAIN:$REGISTRY_PORT/v2/_catalog" &>/dev/null; then
    print_success "Registry is accessible"
else
    print_error "Registry test failed"
    echo "Check logs: docker logs docker-registry"
fi

# Save credentials for future reference
cat > "$REGISTRY_DIR/credentials.txt" <<EOF
Registry URL: https://$REGISTRY_DOMAIN:$REGISTRY_PORT
Username: $REGISTRY_USER
Password: [SAVED IN AUTH FILE]

Web UI: http://$REGISTRY_DOMAIN:8080
EOF
chmod 600 "$REGISTRY_DIR/credentials.txt"

echo ""
print_header "========================================="
print_header "  Registry Setup Complete!"
print_header "========================================="
echo ""
print_success "Docker Registry is running at: https://$REGISTRY_DOMAIN:$REGISTRY_PORT"
print_success "Web UI is available at: http://$REGISTRY_DOMAIN:8080"
echo ""
echo "Configuration saved in: $REGISTRY_DIR"
echo "Credentials: $REGISTRY_DIR/credentials.txt"
echo ""
print_header "Next Steps:"
echo ""
echo "1. Configure client machines to trust the certificate:"
echo "   # Linux:"
echo "   sudo mkdir -p /etc/docker/certs.d/$REGISTRY_DOMAIN:$REGISTRY_PORT"
echo "   sudo cp $REGISTRY_CERTS/domain.crt /etc/docker/certs.d/$REGISTRY_DOMAIN:$REGISTRY_PORT/ca.crt"
echo "   sudo systemctl restart docker"
echo ""
echo "   # macOS:"
echo "   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $REGISTRY_CERTS/domain.crt"
echo "   # Restart Docker Desktop"
echo ""
echo "2. Login to the registry:"
echo "   docker login $REGISTRY_DOMAIN:$REGISTRY_PORT -u $REGISTRY_USER"
echo ""
echo "3. Tag and push images:"
echo "   docker tag gvpocr-ocr-worker $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"
echo "   docker push $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"
echo ""
echo "4. Pull images on worker machines:"
echo "   docker pull $REGISTRY_DOMAIN:$REGISTRY_PORT/gvpocr/ocr-worker:latest"
echo ""
echo "Management Commands:"
echo "  View logs:    docker logs -f docker-registry"
echo "  Stop:         cd $REGISTRY_DIR && docker-compose down"
echo "  Start:        cd $REGISTRY_DIR && docker-compose up -d"
echo "  List images:  curl -k -u $REGISTRY_USER:PASSWORD https://$REGISTRY_DOMAIN:$REGISTRY_PORT/v2/_catalog"
echo ""
