#!/usr/bin/env bash
# =============================================================================
# Production Setup Script — pala-platform
# Run this as the prod user AFTER rsync completes.
#
# Usage:
#   chmod +x prod_setup.sh
#   ./prod_setup.sh
# =============================================================================

set -euo pipefail

PROD_ROOT="/mnt/sda1/prod/pala-platform"
PYTHON=${PYTHON:-python3}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ─── Preflight ────────────────────────────────────────────────────────────────
echo ""
echo "======================================================="
echo "  pala-platform  Production Setup"
echo "======================================================="
echo ""

[[ -d "$PROD_ROOT" ]] || error "Directory $PROD_ROOT not found. Run rsync first."

command -v docker        &>/dev/null || error "docker not installed"
command -v docker compose &>/dev/null 2>&1 || \
  command -v docker-compose &>/dev/null   || error "docker compose not installed"
command -v "$PYTHON"     &>/dev/null || error "$PYTHON not found"

info "Python: $($PYTHON --version)"
info "Docker: $(docker --version)"

# ─── Helper: create venv + install requirements ───────────────────────────────
setup_venv() {
  local dir="$1"
  local req="$2"
  local label="$3"

  info "Setting up venv: $label"
  if [[ ! -d "$dir/venv" ]]; then
    "$PYTHON" -m venv "$dir/venv"
  fi
  # shellcheck disable=SC1091
  source "$dir/venv/bin/activate"
  pip install --quiet --upgrade pip
  pip install --quiet -r "$req"
  deactivate
  success "$label venv ready"
}

# ─── Helper: copy .env.example → .env (skip if .env already exists) ──────────
init_env() {
  local dir="$1"
  local example="$2"
  local target="$dir/.env"

  if [[ -f "$target" ]]; then
    warn ".env already exists at $target — skipping (edit manually if needed)"
  elif [[ -f "$example" ]]; then
    cp "$example" "$target"
    warn "Created $target from example. EDIT IT before starting services!"
  else
    warn "No .env.example found in $dir — create $target manually"
  fi
}

# =============================================================================
# 1. SAMMA AI
# =============================================================================
echo ""
echo "-------------------------------------------------------"
echo "  1/2  Samma AI"
echo "-------------------------------------------------------"

SAMMA="$PROD_ROOT/samma_ai"

# 1a. .env files
init_env "$SAMMA/backend" "$SAMMA/backend/.env.example"

# 1b. Backend venv
setup_venv "$SAMMA/backend" "$SAMMA/backend/requirements.txt" "samma_ai/backend"

# 1c. Check Tipitaka DB
if [[ -f "$SAMMA/database/tipitaka_ultimate.db" ]]; then
  success "Tipitaka DB found ($(du -sh "$SAMMA/database/tipitaka_ultimate.db" | cut -f1))"
else
  warn "tipitaka_ultimate.db NOT found at $SAMMA/database/ — backend will start but Tipitaka search will fail"
fi

success "Samma AI setup complete"

# =============================================================================
# 2. OCR METADATA EXTRACTION (palagenai)
# =============================================================================
echo ""
echo "-------------------------------------------------------"
echo "  2/2  OCR Metadata Extraction"
echo "-------------------------------------------------------"

OCR="$PROD_ROOT/packages/processors/OCR_metadata_extraction"

# 2a. .env files
init_env "$OCR" "$OCR/.env.example"
init_env "$OCR/backend" "$OCR/backend/.env.example"
init_env "$OCR/frontend" "$OCR/frontend/.env.example"

# 2b. Backend venv
setup_venv "$OCR/backend" "$OCR/backend/requirements.txt" "OCR/backend"

success "OCR Metadata Extraction setup complete"

# =============================================================================
# 3. DOCKER SERVICES — Samma AI
# =============================================================================
echo ""
echo "-------------------------------------------------------"
echo "  Starting Docker services — Samma AI"
echo "-------------------------------------------------------"

cd "$SAMMA"

if [[ ! -f ".env" && -f "backend/.env" ]]; then
  # docker-compose.yml reads from root .env; copy backend one if root missing
  cp "backend/.env" ".env"
  warn "Copied backend/.env → .env for docker-compose. Check CORS_ORIGINS & SECRET_KEY."
fi

info "Pulling latest Docker images..."
docker compose pull 2>/dev/null || true

info "Building & starting Samma AI services (mongodb, qdrant, backend, frontend)..."
docker compose up -d --build

info "Waiting for services to be healthy (up to 60s)..."
sleep 10
docker compose ps

success "Samma AI Docker services started"

# =============================================================================
# 4. DOCKER SERVICES — OCR Metadata Extraction
# =============================================================================
echo ""
echo "-------------------------------------------------------"
echo "  Starting Docker services — OCR Metadata Extraction"
echo "-------------------------------------------------------"

cd "$OCR"

if docker compose -f docker-compose.prod.yml config &>/dev/null 2>&1; then
  COMPOSE_FILE="docker-compose.prod.yml"
else
  COMPOSE_FILE="docker-compose.yml"
fi

info "Using compose file: $COMPOSE_FILE"
info "Pulling latest Docker images..."
docker compose -f "$COMPOSE_FILE" pull 2>/dev/null || true

info "Building & starting OCR services..."
docker compose -f "$COMPOSE_FILE" up -d --build

info "Waiting for services to be healthy (up to 60s)..."
sleep 10
docker compose -f "$COMPOSE_FILE" ps

success "OCR services started"

# =============================================================================
# 5. SUMMARY
# =============================================================================
echo ""
echo "======================================================="
echo "  Setup Complete — Service Endpoints"
echo "======================================================="
echo ""
echo "  Samma AI"
echo "    Frontend   : http://localhost:8080"
echo "    Backend API: http://localhost:5001/api/health"
echo "    MongoDB    : localhost:27018"
echo "    Qdrant     : localhost:6334"
echo ""
echo "  OCR Metadata Extraction"
echo "    Backend API: http://localhost:5000"
echo "    (Check docker-compose for frontend port)"
echo ""
echo "  Useful commands:"
echo "    docker compose -f $OCR/$COMPOSE_FILE ps"
echo "    docker compose -C $SAMMA ps"
echo "    docker compose logs -f --tail=50"
echo ""
warn "IMPORTANT: Edit all .env files with real secrets before going live:"
warn "  - SECRET_KEY (must not be the default dev key)"
warn "  - ANTHROPIC_API_KEY"
warn "  - CORS_ORIGINS (set to your actual domain)"
warn "  - MONGO_URI, QDRANT_API_KEY (if changed from defaults)"
echo ""
