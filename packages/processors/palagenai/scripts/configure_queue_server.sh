#!/bin/bash
# Configure Queue Server for Remote Workers
# Run this script on the QUEUE SERVER (172.12.0.132)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

echo "========================================="
echo "GVPOCR Queue Server Configuration"
echo "========================================="
echo ""

# Get current IP
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current IP: $CURRENT_IP"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Check if Docker is running
print_info "Checking Docker services..."
if docker ps | grep -q gvpocr-nsqd; then
    print_success "NSQ services are running"
else
    print_error "NSQ services are not running"
    echo "Start with: docker-compose up -d"
    exit 1
fi

# Step 2: Configure firewall for NSQ
print_info "Configuring firewall for NSQ..."

# Check if ufw is installed
if command -v ufw &> /dev/null; then
    print_info "Configuring UFW firewall..."

    # NSQ Lookupd
    if ufw status | grep -q "4160.*ALLOW"; then
        print_success "Port 4160 (NSQ Lookupd TCP) already allowed"
    else
        ufw allow 4160/tcp comment "NSQ Lookupd TCP"
        print_success "Allowed port 4160 (NSQ Lookupd TCP)"
    fi

    if ufw status | grep -q "4161.*ALLOW"; then
        print_success "Port 4161 (NSQ Lookupd HTTP) already allowed"
    else
        ufw allow 4161/tcp comment "NSQ Lookupd HTTP"
        print_success "Allowed port 4161 (NSQ Lookupd HTTP)"
    fi

    # NSQ Daemon
    if ufw status | grep -q "4150.*ALLOW"; then
        print_success "Port 4150 (NSQ Daemon TCP) already allowed"
    else
        ufw allow 4150/tcp comment "NSQ Daemon TCP"
        print_success "Allowed port 4150 (NSQ Daemon TCP)"
    fi

    if ufw status | grep -q "4151.*ALLOW"; then
        print_success "Port 4151 (NSQ Daemon HTTP) already allowed"
    else
        ufw allow 4151/tcp comment "NSQ Daemon HTTP"
        print_success "Allowed port 4151 (NSQ Daemon HTTP)"
    fi

    # Optional: MongoDB (only if workers need direct access)
    read -p "Allow MongoDB (port 27017) for remote workers? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Allow from specific subnet (e.g., 172.12.0.0/24) or all? [subnet/all] " MONGO_ACCESS
        if [ "$MONGO_ACCESS" == "subnet" ]; then
            read -p "Enter subnet (e.g., 172.12.0.0/24): " SUBNET
            ufw allow from $SUBNET to any port 27017 comment "MongoDB for workers"
            print_success "Allowed MongoDB from $SUBNET"
        else
            ufw allow 27017/tcp comment "MongoDB"
            print_success "Allowed MongoDB from all IPs"
        fi
    fi

    print_success "Firewall configuration complete"
else
    print_error "UFW not found. Please configure firewall manually:"
    echo "  sudo iptables -A INPUT -p tcp --dport 4150 -j ACCEPT"
    echo "  sudo iptables -A INPUT -p tcp --dport 4151 -j ACCEPT"
    echo "  sudo iptables -A INPUT -p tcp --dport 4160 -j ACCEPT"
    echo "  sudo iptables -A INPUT -p tcp --dport 4161 -j ACCEPT"
fi

# Step 3: Test NSQ is accessible
print_info "Testing NSQ accessibility..."
if curl -s http://localhost:4161/ping | grep -q OK; then
    print_success "NSQ Lookupd is accessible"
else
    print_error "NSQ Lookupd is not accessible"
fi

# Step 4: Show current NSQ stats
print_info "Current NSQ Statistics:"
echo ""
docker exec gvpocr-nsqd /nsq_stat --nsqd-http-address=localhost:4151 --status-every=0s 2>/dev/null || echo "No stats available"
echo ""

# Step 5: Setup NFS (optional)
read -p "Setup NFS for shared file access? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Setting up NFS server..."

    # Install NFS server
    if ! command -v exportfs &> /dev/null; then
        apt-get update > /dev/null 2>&1
        apt-get install -y nfs-kernel-server > /dev/null 2>&1
        print_success "NFS server installed"
    else
        print_success "NFS server already installed"
    fi

    # Get uploads directory
    UPLOAD_DIR=$(cd "$(dirname "$0")/../backend/uploads" && pwd)

    # Configure exports
    print_info "Configuring NFS exports..."
    read -p "Enter allowed subnet (e.g., 172.12.0.0/24): " NFS_SUBNET

    EXPORT_LINE="$UPLOAD_DIR $NFS_SUBNET(ro,sync,no_subtree_check)"

    if grep -q "$UPLOAD_DIR" /etc/exports; then
        print_info "Export already exists in /etc/exports"
    else
        echo "$EXPORT_LINE" >> /etc/exports
        print_success "Added export to /etc/exports"
    fi

    # Apply exports
    exportfs -ra
    systemctl restart nfs-kernel-server
    print_success "NFS server configured and restarted"

    # Configure firewall for NFS
    ufw allow from $NFS_SUBNET to any port nfs comment "NFS for workers"
    print_success "Firewall configured for NFS"

    echo ""
    print_info "Workers can mount with:"
    echo "  sudo mount $CURRENT_IP:$UPLOAD_DIR /mnt/gvpocr-uploads"
fi

# Summary
echo ""
echo "========================================="
echo "Configuration Complete!"
echo "========================================="
echo ""
print_success "Queue server is configured for remote workers"
echo ""
echo "Server Information:"
echo "  IP Address: $CURRENT_IP"
echo "  NSQ Lookupd: $CURRENT_IP:4161"
echo "  NSQ Daemon: $CURRENT_IP:4150"
echo "  NSQ Admin UI: http://$CURRENT_IP:4171"
echo ""
echo "Workers should connect with:"
echo "  python run_worker.py --worker-id <worker-id> --nsqlookupd $CURRENT_IP:4161"
echo ""
echo "Monitor workers at: http://$CURRENT_IP:4171"
echo ""
