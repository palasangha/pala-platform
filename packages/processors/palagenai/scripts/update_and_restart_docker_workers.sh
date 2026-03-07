#!/bin/bash
# Update and Restart Docker Workers
# This script pulls the latest code and restarts the Docker worker containers

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

# Get the script directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

clear
print_header "========================================="
print_header "  GVPOCR Docker Workers - Update & Restart"
print_header "========================================="
echo ""

# Configuration - allow override via environment variables
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-nsq-implementation}"
REBUILD_WORKERS="${REBUILD_WORKERS:-false}"

print_info "Project Root: $PROJECT_ROOT"
print_info "Git Remote: $GIT_REMOTE"
print_info "Git Branch: $GIT_BRANCH"
print_info "Rebuild Workers: $REBUILD_WORKERS"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Check git status
print_info "Checking git status..."
if ! git status &>/dev/null; then
    print_error "Not a git repository"
    exit 1
fi

# Stash any local changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_info "Stashing local changes..."
    git stash save "Auto-stash before update $(date '+%Y-%m-%d %H:%M:%S')"
    print_success "Local changes stashed"
fi

# Step 2: Fetch latest code
print_info "Fetching latest code from $GIT_REMOTE/$GIT_BRANCH..."
if ! git fetch "$GIT_REMOTE" "$GIT_BRANCH"; then
    print_error "Failed to fetch from remote"
    exit 1
fi
print_success "Fetched latest code"

# Step 3: Get current and latest commit hashes
CURRENT_COMMIT=$(git rev-parse HEAD)
LATEST_COMMIT=$(git rev-parse "$GIT_REMOTE/$GIT_BRANCH")

if [ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]; then
    print_success "Already up to date ($(git rev-parse --short HEAD))"
else
    print_info "Current: $(git rev-parse --short $CURRENT_COMMIT)"
    print_info "Latest:  $(git rev-parse --short $LATEST_COMMIT)"

    # Pull latest changes
    print_info "Pulling latest changes..."
    if ! git pull "$GIT_REMOTE" "$GIT_BRANCH"; then
        print_error "Failed to pull latest changes"
        print_info "You may need to resolve conflicts manually"
        exit 1
    fi
    print_success "Updated to latest code ($(git rev-parse --short HEAD))"
fi

# Step 4: Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found"
    echo "Please install docker-compose first"
    exit 1
fi

# Step 5: Rebuild or restart workers
if [ "$REBUILD_WORKERS" == "true" ]; then
    print_info "Rebuilding worker images..."
    if ! docker-compose build ocr-worker; then
        print_error "Failed to build worker images"
        exit 1
    fi
    print_success "Worker images rebuilt"

    print_info "Restarting workers with new images..."
    if ! docker-compose up -d ocr-worker; then
        print_error "Failed to start workers"
        exit 1
    fi
else
    print_info "Restarting workers..."
    if ! docker-compose restart ocr-worker; then
        print_error "Failed to restart workers"
        exit 1
    fi
fi

print_success "Workers restarted"

# Step 6: Check worker status
sleep 3
print_info "Checking worker status..."
WORKER_COUNT=$(docker-compose ps ocr-worker | grep -c "Up" || true)
print_success "$WORKER_COUNT worker(s) running"

# Show worker logs (last 10 lines)
echo ""
print_info "Recent worker logs:"
docker-compose logs --tail=10 ocr-worker 2>/dev/null | sed 's/^/  /'

echo ""
print_header "========================================="
print_header "  Update Complete!"
print_header "========================================="
echo ""
print_success "Workers are running on latest code"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f ocr-worker"
echo "  Check status:  docker-compose ps ocr-worker"
echo "  Restart:       docker-compose restart ocr-worker"
echo "  Rebuild:       REBUILD_WORKERS=true $0"
echo ""
