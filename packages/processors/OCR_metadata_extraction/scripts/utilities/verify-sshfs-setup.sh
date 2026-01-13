#!/bin/bash

# SSHFS Setup Verification Script
# This script verifies that the SSHFS setup is properly configured and ready for deployment
#
# Usage: ./verify-sshfs-setup.sh [options]
#
# Options:
#   --main-server-ip IP     Main server IP to test against (default: 172.12.0.132)
#   --remote-worker IP      Remote worker IP to test
#   --check-ssh             Only check SSH server
#   --check-files           Only check file structure
#   --check-docker          Only check Docker setup
#   --full                  Run all checks
#   --help                  Show this help message

set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
MAIN_SERVER_IP="172.12.0.132"
CHECK_SSH=false
CHECK_FILES=false
CHECK_DOCKER=false
FULL_CHECK=false

# Counters
PASS=0
FAIL=0
WARN=0

# Functions
log_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAIL++))
}

log_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    ((WARN++))
}

log_info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
}

show_help() {
    cat << 'EOF'
SSHFS Setup Verification Script

Usage: ./verify-sshfs-setup.sh [options]

Options:
  --main-server-ip IP     Main server IP to test (default: 172.12.0.132)
  --remote-worker IP      Remote worker IP to test connectivity
  --check-ssh             Check SSH server configuration only
  --check-files           Check file structure only
  --check-docker          Check Docker setup only
  --full                  Run all verification checks
  --help                  Show this help message

Examples:
  # Full verification
  ./verify-sshfs-setup.sh --full

  # Check specific components
  ./verify-sshfs-setup.sh --check-ssh --main-server-ip 192.168.1.100
  ./verify-sshfs-setup.sh --check-files
  ./verify-sshfs-setup.sh --check-docker

  # Test remote worker connectivity
  ./verify-sshfs-setup.sh --remote-worker 192.168.1.50

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --main-server-ip)
            MAIN_SERVER_IP="$2"
            shift 2
            ;;
        --remote-worker)
            REMOTE_WORKER_IP="$2"
            shift 2
            ;;
        --check-ssh)
            CHECK_SSH=true
            shift
            ;;
        --check-files)
            CHECK_FILES=true
            shift
            ;;
        --check-docker)
            CHECK_DOCKER=true
            shift
            ;;
        --full)
            FULL_CHECK=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default to full check if no specific check selected
if [ "$FULL_CHECK" = false ] && [ "$CHECK_SSH" = false ] && [ "$CHECK_FILES" = false ] && [ "$CHECK_DOCKER" = false ]; then
    FULL_CHECK=true
fi

# Expand checks
if [ "$FULL_CHECK" = true ]; then
    CHECK_SSH=true
    CHECK_FILES=true
    CHECK_DOCKER=true
fi

# ============================================================================
# VERIFICATION CHECKS
# ============================================================================

# SSH Server Checks
if [ "$CHECK_SSH" = true ]; then
    log_section "SSH Server Configuration Checks"
    
    # Check if Docker is running
    if ! command -v docker &> /dev/null; then
        log_fail "Docker is not installed"
    else
        log_pass "Docker is installed"
        
        # Check if docker-compose.yml exists
        if [ -f "docker-compose.yml" ]; then
            log_pass "docker-compose.yml exists"
            
            # Check SSH server in docker-compose
            if grep -q "ssh-server:" docker-compose.yml; then
                log_pass "SSH server defined in docker-compose.yml"
                
                # Check SSH port 2222
                if grep -q "2222:22" docker-compose.yml; then
                    log_pass "SSH server port 2222 configured"
                else
                    log_fail "SSH server port 2222 not found in docker-compose.yml"
                fi
                
                # Check volumes for shared data
                if grep -q "Bhushanji:" docker-compose.yml && \
                   grep -q "newsletters:" docker-compose.yml && \
                   grep -q "models:" docker-compose.yml; then
                    log_pass "Shared directories configured in SSH server"
                else
                    log_warn "Some shared directories missing from SSH server volumes"
                fi
                
                # Check SSH server health check
                if grep -A 60 "ssh-server:" docker-compose.yml | grep -q "healthcheck:"; then
                    log_pass "SSH server health check configured"
                else
                    log_warn "SSH server health check not configured"
                fi
            else
                log_fail "SSH server not defined in docker-compose.yml"
            fi
        else
            log_fail "docker-compose.yml not found"
        fi
        
        # Check if SSH server is running
        if docker ps | grep -q "gvpocr-ssh-server"; then
            log_pass "SSH server container is running"
            
            # Try SSH connection
            if ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                   gvpocr@localhost "echo 'SSH connection successful'" &> /dev/null; then
                log_pass "SSH server accepts connections on port 2222"
            else
                log_warn "Could not verify SSH server connectivity (may require password)"
            fi
        else
            log_warn "SSH server container is not running (run: docker-compose up -d ssh-server)"
        fi
    fi
fi

# File Structure Checks
if [ "$CHECK_FILES" = true ]; then
    log_section "File Structure and Configuration Checks"
    
    # Check documentation files
    docs_files=(
        "SSHFS_IMPLEMENTATION.md"
        "SSHFS_DEPLOYMENT.md"
        "SSHFS_QUICK_START.md"
        "SSHFS_SETUP.md"
        "SSHFS_INDEX.md"
    )
    
    for doc in "${docs_files[@]}"; do
        if [ -f "$doc" ]; then
            log_pass "Documentation file exists: $doc"
        else
            log_fail "Documentation file missing: $doc"
        fi
    done
    
    # Check setup script
    if [ -f "setup-sshfs-remote-worker.sh" ]; then
        log_pass "Setup script exists: setup-sshfs-remote-worker.sh"
        
        if [ -x "setup-sshfs-remote-worker.sh" ]; then
            log_pass "Setup script is executable"
        else
            log_fail "Setup script is not executable (run: chmod +x setup-sshfs-remote-worker.sh)"
        fi
    else
        log_fail "Setup script missing: setup-sshfs-remote-worker.sh"
    fi
    
    # Check configuration files
    config_files=(
        "docker-compose.sshfs-override.yml"
        "sshfs-main-server.service"
        ".env.sshfs.example"
    )
    
    for config in "${config_files[@]}"; do
        if [ -f "$config" ]; then
            log_pass "Configuration file exists: $config"
        else
            log_fail "Configuration file missing: $config"
        fi
    done
    
    # Check shared directories
    if [ -d "shared/Bhushanji" ]; then
        log_pass "Bhushanji directory exists"
    else
        log_warn "Bhushanji directory not found (create with: mkdir -p shared/Bhushanji)"
    fi
    
    if [ -d "shared/newsletters" ]; then
        log_pass "Newsletters directory exists"
    else
        log_warn "Newsletters directory not found (create with: mkdir -p shared/newsletters)"
    fi
    
    if [ -d "models" ]; then
        log_pass "Models directory exists"
    else
        log_warn "Models directory not found (create with: mkdir -p models)"
    fi
fi

# Docker Setup Checks
if [ "$CHECK_DOCKER" = true ]; then
    log_section "Docker and Container Configuration Checks"
    
    # Check Docker running
    if docker ps &> /dev/null; then
        log_pass "Docker daemon is running"
    else
        log_fail "Docker daemon is not running"
        exit 1
    fi
    
    # Check docker-compose
    if command -v docker-compose &> /dev/null; then
        log_pass "Docker Compose is installed"
        docker_compose_version=$(docker-compose --version 2>&1)
        log_info "Version: $docker_compose_version"
    else
        log_fail "Docker Compose is not installed"
    fi
    
    # Validate docker-compose syntax
    if docker-compose config &> /dev/null; then
        log_pass "docker-compose.yml syntax is valid"
    else
        log_fail "docker-compose.yml has syntax errors"
    fi
    
    # Check SSHFS override file syntax
    if [ -f "docker-compose.sshfs-override.yml" ]; then
        if docker-compose -f docker-compose.yml -f docker-compose.sshfs-override.yml config &> /dev/null; then
            log_pass "docker-compose.sshfs-override.yml is compatible"
        else
            log_fail "docker-compose.sshfs-override.yml has compatibility issues"
        fi
    fi
    
    # Check required images
    required_images=(
        "alpine"
        "mongo"
        "nsqio/nsq"
    )
    
    for image in "${required_images[@]}"; do
        if docker images | grep -q "^${image%:*} "; then
            log_pass "Required image exists: $image"
        else
            log_warn "Image may need to be pulled: $image"
        fi
    done
    
    # Check network
    if docker network ls | grep -q "gvpocr-network"; then
        log_pass "gvpocr-network exists"
    else
        log_warn "gvpocr-network doesn't exist (will be created on docker-compose up)"
    fi
fi

# Remote Worker Connectivity Check
if [ -n "$REMOTE_WORKER_IP" ]; then
    log_section "Remote Worker Connectivity Checks"
    
    # Check ping
    if ping -c 1 -W 2 "$REMOTE_WORKER_IP" &> /dev/null; then
        log_pass "Remote worker is reachable ($REMOTE_WORKER_IP)"
    else
        log_fail "Cannot ping remote worker ($REMOTE_WORKER_IP)"
    fi
    
    # Check SSH to main server from remote worker (if we can)
    log_info "To complete remote worker checks, run on the remote worker:"
    log_info "  ssh -p 2222 gvpocr@$MAIN_SERVER_IP echo 'Connected'"
fi

# ============================================================================
# SUMMARY
# ============================================================================

log_section "Verification Summary"

echo ""
echo -e "Results:"
echo -e "  ${GREEN}✓ Passed:  $PASS${NC}"
echo -e "  ${RED}✗ Failed:  $FAIL${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $WARN${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    if [ $WARN -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready for deployment.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Some warnings found, but system should work.${NC}"
        echo "  Review warnings above for optional improvements."
        exit 0
    fi
else
    echo -e "${RED}✗ Some checks failed. Please fix issues above before deployment.${NC}"
    exit 1
fi
