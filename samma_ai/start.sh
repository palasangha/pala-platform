#!/bin/bash
################################################################################
# Samma AI — Unified Start Script
#
# Usage:
#   ./start.sh              Full setup + start (backend & frontend)
#   ./start.sh --backend    Start backend only
#   ./start.sh --frontend   Start frontend only
#   ./start.sh --build      Build frontend for production
#   ./start.sh --stop       Stop running services
#   ./start.sh --status     Check service health
################################################################################

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DATABASE_FILE="$PROJECT_DIR/database/tipitaka_ultimate.db"
PID_FILE="$PROJECT_DIR/.samma_pids"

BACKEND_PORT="${BACKEND_PORT:-5001}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

# ── Utility Functions ─────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
log_success() { echo -e "${GREEN}✓  $1${NC}"; }
log_warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
log_error()   { echo -e "${RED}✗  $1${NC}"; }

header() {
    echo -e "\n${CYAN}━━━  $1  ━━━${NC}"
}

cleanup() {
    echo ""
    log_info "Shutting down…"
    stop_services
    exit 0
}

# ── Stop Services ─────────────────────────────────────────────────────
stop_services() {
    if [ -f "$PID_FILE" ]; then
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null && log_info "Stopped PID $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        log_success "All services stopped"
    else
        # Fallback: kill by port
        local pids
        pids=$(lsof -ti :$BACKEND_PORT 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null && log_info "Killed backend on port $BACKEND_PORT"
        fi
        pids=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null && log_info "Killed frontend on port $FRONTEND_PORT"
        fi
        log_success "Cleanup complete"
    fi
}

# ── Prerequisites ─────────────────────────────────────────────────────
check_prereqs() {
    header "Prerequisites"
    local ok=true

    if command -v python3 &>/dev/null; then
        log_success "Python $(python3 --version 2>&1 | awk '{print $2}')"
    else
        log_error "Python 3 not found"; ok=false
    fi

    if command -v flutter &>/dev/null; then
        log_success "Flutter $(flutter --version 2>&1 | head -1 | awk '{print $2}')"
    else
        log_warn "Flutter not found — frontend won't start"
    fi

    if [ -f "$DATABASE_FILE" ]; then
        log_success "Database $(du -h "$DATABASE_FILE" | awk '{print $1}')"
    else
        log_warn "Database not found at $DATABASE_FILE"
    fi

    if [ "$ok" = false ]; then
        log_error "Missing prerequisites. Aborting."
        exit 1
    fi
}

# ── Backend Setup & Start ─────────────────────────────────────────────
setup_backend() {
    header "Backend Setup"
    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment…"
        python3 -m venv venv
    fi

    source venv/bin/activate
    log_info "Installing dependencies…"
    pip install --upgrade pip -q 2>/dev/null
    pip install -r requirements.txt -q 2>/dev/null
    log_success "Backend dependencies ready"

    # Create .env if missing
    if [ ! -f ".env" ]; then
        log_info "Creating .env with defaults…"
        cat > .env <<ENVEOF
# Samma AI Backend Configuration
FLASK_ENV=development
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
TIPITAKA_DB_PATH=../database/tipitaka_ultimate.db
MONGO_URI=mongodb://localhost:27017/samma_ai
PORT=$BACKEND_PORT
CORS_ORIGINS=http://localhost:$FRONTEND_PORT,http://localhost:3000

# Claude (Anthropic)
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
CLAUDE_MODEL=claude-sonnet-4-20250514

# OpenAI (optional)
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_MODEL=gpt-4o

# Ollama (local, auto-discovered)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2-vision:latest

# Copilot-compatible endpoint (optional)
COPILOT_ENDPOINT=
COPILOT_API_KEY=
ENVEOF
        log_success ".env created"
    fi

    cd "$PROJECT_DIR"
}

start_backend() {
    # Check if backend is already running
    if lsof -ti :$BACKEND_PORT >/dev/null 2>&1; then
        log_warn "Backend already running on port $BACKEND_PORT"
        return 0
    fi

    header "Starting Backend"
    cd "$BACKEND_DIR"
    source venv/bin/activate

    # Source .env if exists
    if [ -f ".env" ]; then
        set -a; source .env; set +a
    fi

    python run.py &
    local pid=$!
    echo "$pid" >> "$PID_FILE"
    log_success "Backend started on port $BACKEND_PORT (PID $pid)"
    cd "$PROJECT_DIR"
}

# ── Frontend Setup & Start ────────────────────────────────────────────
setup_frontend() {
    if ! command -v flutter &>/dev/null; then
        log_warn "Flutter not found — skipping frontend setup"
        return 0
    fi

    header "Frontend Setup"
    cd "$FRONTEND_DIR"
    
    # Clear any stale locks
    rm -f .dart_tool/package_config.json.lock 2>/dev/null || true
    
    log_info "Installing dependencies..."
    if timeout 60 flutter pub get 2>&1 | grep -q "Changed"; then
        log_success "Frontend dependencies ready"
    elif [ -f "pubspec.lock" ]; then
        log_success "Frontend dependencies already cached"
    else
        log_warn "Flutter pub get timed out, but continuing..."
    fi
    
    cd "$PROJECT_DIR"
}

start_frontend() {
    if ! command -v flutter &>/dev/null; then
        log_warn "Flutter not found — start frontend manually"
        return 0
    fi

    # Check if frontend is already running
    if lsof -ti :$FRONTEND_PORT >/dev/null 2>&1; then
        log_warn "Frontend already running on port $FRONTEND_PORT"
        return 0
    fi

    header "Starting Frontend"
    cd "$FRONTEND_DIR"
    flutter run -d chrome --web-port=$FRONTEND_PORT &
    local pid=$!
    echo "$pid" >> "$PID_FILE"
    log_success "Frontend starting on port $FRONTEND_PORT (PID $pid)"
    cd "$PROJECT_DIR"
}

build_frontend() {
    if ! command -v flutter &>/dev/null; then
        log_error "Flutter not found"
        exit 1
    fi

    header "Building Frontend (Production)"
    cd "$FRONTEND_DIR"
    flutter build web --release
    log_success "Built to $FRONTEND_DIR/build/web"
    cd "$PROJECT_DIR"
}

# ── Health Check ──────────────────────────────────────────────────────
health_check() {
    header "Health Check"
    sleep 3

    if curl -sf "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
        log_success "Backend healthy on :$BACKEND_PORT"
    else
        log_warn "Backend not responding yet (may still be starting)"
    fi

    if [ -f "$DATABASE_FILE" ] && command -v sqlite3 &>/dev/null; then
        local count
        count=$(sqlite3 "$DATABASE_FILE" "SELECT COUNT(*) FROM paragraphs;" 2>/dev/null || echo "?")
        log_success "Database: $count paragraphs"
    fi
}

# ── Banner ────────────────────────────────────────────────────────────
print_banner() {
    clear
    cat << 'EOF'
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║          🧘  SAMMA AI — Multi-Agent Platform          ║
║                                                       ║
║   Dhamma-Grounded AI with Multi-Model Support         ║
║   Powered by Pala-Jarvis Orchestration                ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
}

print_ready() {
    cat << EOF

${GREEN}━━━  🎉 ALL SYSTEMS GO  ━━━${NC}

${BLUE}Web App:${NC}  http://localhost:$FRONTEND_PORT
${BLUE}API:${NC}      http://localhost:$BACKEND_PORT/api/health

${CYAN}Agent Dashboard (6 tabs):${NC}
  Status   · View agents with model badges
  Teams    · Chat with team leads
  Direct   · Message individual agents
  Tasks    · Kanban task board
  Collab   · Agent R&D collaboration space
  Live Exec · Real-time execution monitor

${CYAN}Models:${NC} Claude · OpenAI · Ollama (auto-discovered)
${CYAN}Orchestrator:${NC} Pala-Jarvis coordinates all teams

${YELLOW}Press Ctrl+C to stop all services${NC}
EOF
}

# ── Main ──────────────────────────────────────────────────────────────
main() {
    local mode="${1:-all}"

    case "$mode" in
        --stop)
            stop_services
            exit 0
            ;;
        --status)
            health_check
            exit 0
            ;;
        --build)
            print_banner
            check_prereqs
            setup_frontend
            build_frontend
            exit 0
            ;;
        --backend)
            print_banner
            check_prereqs
            setup_backend
            start_backend
            health_check
            trap cleanup SIGINT SIGTERM
            wait
            ;;
        --frontend)
            print_banner
            check_prereqs
            setup_frontend
            start_frontend
            trap cleanup SIGINT SIGTERM
            wait
            ;;
        all|*)
            print_banner
            check_prereqs
            setup_backend
            setup_frontend
            # Clean stale PIDs
            rm -f "$PID_FILE"
            start_backend
            start_frontend
            health_check
            print_ready
            trap cleanup SIGINT SIGTERM
            wait
            ;;
    esac
}

main "$@"
