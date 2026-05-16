#!/bin/bash

# Pala Platform - Development Environment Setup Gate
# Idempotent: safe to run repeatedly. Installs only missing deps where possible.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

is_python_healthy() {
    local py="$1"
    "$py" -c "import xml.parsers.expat, ensurepip" >/dev/null 2>&1
}

select_python_cmd() {
    local candidates=()
    if [[ -n "${PALA_PYTHON:-}" ]]; then
        candidates+=("$PALA_PYTHON")
    fi
    candidates+=("python3.12" "python3.11" "python3.10" "python" "python3" "/usr/bin/python3")

    local candidate
    local resolved
    for candidate in "${candidates[@]}"; do
        if [[ "$candidate" == /* ]]; then
            resolved="$candidate"
            [[ -x "$resolved" ]] || continue
        else
            resolved="$(command -v "$candidate" 2>/dev/null || true)"
            [[ -n "$resolved" ]] || continue
        fi

        if is_python_healthy "$resolved"; then
            printf '%s' "$resolved"
            return 0
        fi
    done

    return 1
}

venv_python() {
    local venv_dir="$1"
    if [[ -x "$venv_dir/bin/python" ]]; then
        printf '%s' "$venv_dir/bin/python"
        return 0
    fi
    if [[ -x "$venv_dir/Scripts/python.exe" ]]; then
        printf '%s' "$venv_dir/Scripts/python.exe"
        return 0
    fi
    return 1
}

setup_shared_agent_venv() {
    AGENT_VENV_DIR="$ROOT_DIR/agent-venv"
    echo "[setup-dev] Setting up Python venv for agent at $AGENT_VENV_DIR..."

    if [[ ! -d "$AGENT_VENV_DIR" ]]; then
        "$BOOTSTRAP_PYTHON" -m venv "$AGENT_VENV_DIR" || true
        echo "[setup-dev] Created venv at $AGENT_VENV_DIR"
    fi

    local AGENT_PYTHON=""
    if AGENT_PYTHON="$(venv_python "$AGENT_VENV_DIR")"; then
        if ! "$AGENT_PYTHON" -c "import xml.parsers.expat" >/dev/null 2>&1; then
            echo "[setup-dev] WARNING: shared venv uses broken Python; recreating..."
            rm -rf "$AGENT_VENV_DIR"
            "$BOOTSTRAP_PYTHON" -m venv "$AGENT_VENV_DIR" || true
            AGENT_PYTHON="$(venv_python "$AGENT_VENV_DIR")" || true
        fi
    fi

    if [[ -n "${AGENT_PYTHON:-}" && -x "$AGENT_PYTHON" ]]; then
        "$AGENT_PYTHON" -m ensurepip --upgrade || true
        "$AGENT_PYTHON" -m pip install --upgrade pip setuptools wheel || true
    fi

    echo "[setup-dev] Installing agent Python dependencies (python-dotenv, boto3, websockets, sentence-transformers)..."
    if [[ -n "${AGENT_PYTHON:-}" && -x "$AGENT_PYTHON" ]]; then
        if "$AGENT_PYTHON" -m pip install python-dotenv boto3 websockets sentence-transformers; then
            echo "[setup-dev] ✓ Python dependencies installed in shared venv."
            # Verify sentence-transformers was actually installed (CRITICAL for quality gate)
            if "$AGENT_PYTHON" -c "import sentence_transformers; print('[setup-dev] ✓ sentence-transformers verified')" 2>/dev/null; then
                echo "[setup-dev] SUCCESS: sentence-transformers is ready"
            else
                echo "[setup-dev] FATAL: sentence-transformers import failed even after pip install"
                return 1
            fi
        else
            echo "[setup-dev] FATAL: Could not install one or more dependencies into $AGENT_VENV_DIR"
            echo "[setup-dev] Pip output above shows the root cause."
            return 1
        fi
    else
        echo "[setup-dev] FATAL: shared venv python missing; cannot proceed"
        return 1
    fi
}

ollama_model_installed() {
    local model="$1"
    if ! command_exists ollama; then
        return 1
    fi

    local installed
    installed=$(ollama list 2>/dev/null | awk 'NR>1 {print $1}')

    for entry in $installed; do
        if [[ "$entry" == "$model" || "$entry" == "$model:"* ]]; then
            return 0
        fi
    done

    return 1
}

get_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

lmstudio_installed() {
    case "$OS" in
        macos)
            [[ -d "/Applications/LM Studio.app" || -d "$HOME/Applications/LM Studio.app" ]]
            ;;
        linux)
            [[ -x "$HOME/.local/bin/lm-studio" || -d "$HOME/.cache/lm-studio" ]] || command_exists lm-studio
            ;;
        windows)
            [[ -d "C:/Program Files/LM Studio" ]] || command_exists lm-studio
            ;;
        *)
            return 1
            ;;
    esac
}

install_system_deps() {
    case "$OS" in
        macos)
            if ! command_exists brew; then
                echo -e "${YELLOW}Homebrew missing. Install it first:${NC} https://brew.sh"
                MISSING+=("homebrew")
                return
            fi

            command_exists node || brew install node || true
            command_exists python3 || brew install python@3.11 || true
            command_exists tesseract || brew install tesseract || true
            ;;
        linux)
            if command_exists apt-get; then
                sudo apt-get update -y >/dev/null 2>&1 || true
                command_exists node || sudo apt-get install -y nodejs npm >/dev/null 2>&1 || true
                command_exists python3 || sudo apt-get install -y python3 python3-pip python3-venv >/dev/null 2>&1 || true
                command_exists tesseract || sudo apt-get install -y tesseract-ocr >/dev/null 2>&1 || true
            elif command_exists yum; then
                command_exists node || sudo yum install -y nodejs npm >/dev/null 2>&1 || true
                command_exists python3 || sudo yum install -y python3 python3-pip >/dev/null 2>&1 || true
                command_exists tesseract || sudo yum install -y tesseract >/dev/null 2>&1 || true
            else
                echo -e "${YELLOW}No supported Linux package manager (apt/yum) found.${NC}"
            fi
            ;;
        windows)
            :
            ;;
    esac
}

install_ollama() {
    case "$OS" in
        macos)
            if command_exists brew; then
                brew install ollama || brew upgrade ollama || true
            fi
            ;;
        linux)
            if command_exists curl; then
                curl -fsSL https://ollama.com/install.sh | sh || true
            fi
            ;;
        windows)
            :
            ;;
    esac
}

install_ollama_model() {
    local model="$1"

    if ! command_exists ollama; then
        return
    fi

    ensure_ollama_running() {
        if ! command_exists ollama; then
            return 1
        fi

        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            return 0
        fi

        echo -e "${YELLOW}Starting Ollama server for model setup...${NC}"
        ollama serve > "$ROOT_DIR/logs/ollama.log" 2>&1 &
        local ollama_pid=$!

        local attempt
        for attempt in $(seq 1 20); do
            if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Ollama server is ready (PID: $ollama_pid)${NC}"
                return 0
            fi
            sleep 1
        done

        echo -e "${YELLOW}Ollama server did not become ready in time. Check $ROOT_DIR/logs/ollama.log${NC}"
        return 1
    }

    if ollama_model_installed "$model"; then
        echo -e "${GREEN}✓ Ollama model '$model' already installed${NC}"
        return
    fi

    ensure_ollama_running || true

    echo -e "${YELLOW}Installing Ollama model '$model'...${NC}"
    if ! ollama pull "$model"; then
        echo -e "${YELLOW}Could not auto-install model '$model'.${NC}"
        echo -e "${YELLOW}Try manually:${NC} ollama pull $model"
        echo -e "${YELLOW}If needed, start server first:${NC} ollama serve"
    fi
}

install_lmstudio() {
    case "$OS" in
        macos)
            if command_exists brew; then
                brew install --cask lm-studio || true
            fi
            ;;
        linux|windows)
            :
            ;;
    esac
}

check_required() {
    MISSING=()

    command_exists node || MISSING+=("node")
    command_exists npm || MISSING+=("npm")
    command_exists python3 || MISSING+=("python3")
    command_exists tesseract || MISSING+=("tesseract")
    command_exists ollama || MISSING+=("ollama")
    if command_exists ollama && ! ollama_model_installed "$OLLAMA_MODEL_REQUIRED"; then
        MISSING+=("ollama-model:$OLLAMA_MODEL_REQUIRED")
    fi
    lmstudio_installed || MISSING+=("lm-studio")

    if command_exists npm && ! command_exists pnpm; then
        npm install -g pnpm >/dev/null 2>&1 || true
    fi
    command_exists pnpm || MISSING+=("pnpm")
}

prepare_workspace() {
    if command_exists pnpm; then
        if [[ ! -d "$ROOT_DIR/node_modules" ]]; then
            (cd "$ROOT_DIR" && pnpm install >/dev/null 2>&1 || true)
        fi
    fi

    # Setup PalaAgents (core agents)
    local pala_agents_dir="$ROOT_DIR/packages/PalaAgents"
    if [[ -d "$pala_agents_dir" ]]; then
        for agent_dir in "$pala_agents_dir"/*; do
            if [[ -d "$agent_dir" && -f "$agent_dir/requirements.txt" ]]; then
                if [[ ! -d "$agent_dir/venv" ]]; then
                    "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                fi
                local AGENT_PYTHON=""
                if AGENT_PYTHON="$(venv_python "$agent_dir/venv")" && [[ -x "$AGENT_PYTHON" ]] && ! "$AGENT_PYTHON" -c "import xml.parsers.expat" >/dev/null 2>&1; then
                    echo "[setup-dev] WARNING: Recreating broken venv for $agent_dir"
                    rm -rf "$agent_dir/venv"
                    "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                    AGENT_PYTHON="$(venv_python "$agent_dir/venv")" || true
                fi
                if [[ -n "${AGENT_PYTHON:-}" && -x "$AGENT_PYTHON" ]]; then
                    "$AGENT_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
                    "$AGENT_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
                    if ! "$AGENT_PYTHON" -m pip install -r "$agent_dir/requirements.txt"; then
                        echo "[setup-dev] WARNING: Failed to install requirements for $agent_dir. See pip output above."
                    fi
                fi
            fi
        done
    fi

    # Setup other agents (sample agents, etc)
    local agents_dir="$ROOT_DIR/packages/agents"
    if [[ -d "$agents_dir" ]]; then
        for agent_dir in "$agents_dir"/*; do
            if [[ -d "$agent_dir" && -f "$agent_dir/requirements.txt" ]]; then
                if [[ ! -d "$agent_dir/venv" ]]; then
                    "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                fi
                local AGENT_PYTHON=""
                if AGENT_PYTHON="$(venv_python "$agent_dir/venv")" && [[ -x "$AGENT_PYTHON" ]] && ! "$AGENT_PYTHON" -c "import xml.parsers.expat" >/dev/null 2>&1; then
                    echo "[setup-dev] WARNING: Recreating broken venv for $agent_dir"
                    rm -rf "$agent_dir/venv"
                    "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                    AGENT_PYTHON="$(venv_python "$agent_dir/venv")" || true
                fi
                if [[ -n "${AGENT_PYTHON:-}" && -x "$AGENT_PYTHON" ]]; then
                    "$AGENT_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
                    "$AGENT_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
                    if ! "$AGENT_PYTHON" -m pip install -r "$agent_dir/requirements.txt"; then
                        echo "[setup-dev] WARNING: Failed to install requirements for $agent_dir. See pip output above."
                    fi
                fi
            fi
        done
    fi
}

OS=$(get_os)
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MISSING=()
BOOTSTRAP_PYTHON="$(select_python_cmd || true)"

if [[ -z "$BOOTSTRAP_PYTHON" ]]; then
    echo -e "${RED}No healthy Python interpreter found (expat/ensurepip failed).${NC}"
    echo -e "${YELLOW}Set PALA_PYTHON to a working interpreter, e.g.:${NC} PALA_PYTHON=$(command -v python3.11) ./setup-dev.sh"
    exit 1
fi

echo -e "${GREEN}[setup-dev] Using Python interpreter:${NC} $BOOTSTRAP_PYTHON"
# Ollama model for metadata extraction agent (can be overridden with OLLAMA_MODEL env var)
# Recommended models: mistral, neural-chat, or other instruction-tuned models
OLLAMA_MODEL_REQUIRED="${OLLAMA_MODEL:-mistral}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pala Platform - Dependency Gate${NC}"
echo -e "${BLUE}  OS: ${OS}${NC}"
echo -e "${BLUE}================================================${NC}\n"

echo -e "${BLUE}Phase 1/2: Ensure required dependencies${NC}"
install_system_deps
install_ollama
install_ollama_model "$OLLAMA_MODEL_REQUIRED"
install_lmstudio
check_required

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo -e "\n${RED}Missing required dependencies:${NC} ${MISSING[*]}"
    echo -e "${YELLOW}Install missing items, then rerun:${NC} ./start-dev.sh"
    echo -e "\n${YELLOW}Manual install help:${NC}"
    echo -e "  • Ollama: https://ollama.com/download"
    echo -e "  • Ollama model: ollama pull $OLLAMA_MODEL_REQUIRED"
    echo -e "  • LM Studio: https://lmstudio.ai/download"
    echo -e "  • Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html"
    echo -e "\n${YELLOW}After installing, run:${NC} ./start-dev.sh"
    exit 2
fi

echo -e "${GREEN}✓ All required dependencies are installed${NC}"
echo -e "${BLUE}Phase 2/2: Prepare local workspace deps${NC}"
setup_shared_agent_venv
prepare_workspace


# --- S3/MinIO & Storage Agent Automation ---


# 1. Ensure .env exists (copy from .env.example if missing)
if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo -e "${GREEN}✓ .env created from .env.example${NC}"
fi

# 1b. Print info about local S3/MinIO usage for dev
echo -e "${BLUE}Local development uses MinIO (local S3) and SQLite by default.${NC}"
echo -e "${BLUE}To use production S3, edit .env and set S3_* variables accordingly.${NC}"

# Print current S3 config for developer clarity
echo -e "${YELLOW}S3/MinIO config in use:${NC}"
grep -E '^(S3_|FILE_STORAGE_PROVIDER|STORAGE_PROVIDER)' "$ROOT_DIR/.env" | grep -v '^#' || echo "(No S3 config found in .env)"

# 2. Install boto3 in storage-agent venv
STORAGE_AGENT_DIR="$ROOT_DIR/packages/PalaAgents/storage-agent"
if [[ -d "$STORAGE_AGENT_DIR/venv" ]]; then
    # Use venv python directly instead of sourcing activate
    if AGENT_PYTHON="$(venv_python "$STORAGE_AGENT_DIR/venv")" && [[ -x "$AGENT_PYTHON" ]]; then
        "$AGENT_PYTHON" -m pip install -q boto3 >/dev/null 2>&1 || true
        echo -e "${GREEN}✓ boto3 installed in storage-agent venv${NC}"
    fi
fi

# 3. Check/start MinIO server on a free port (3900-4000) if not running
MINIO_PORT=3900
MINIO_BIN=$(command -v minio || true)
if [[ -z "$MINIO_BIN" ]]; then
    echo -e "${YELLOW}MinIO not found. Installing MinIO...${NC}"
    if [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            brew install minio/stable/minio || brew upgrade minio || true
        else
            curl -O https://dl.min.io/server/minio/release/darwin-amd64/minio && chmod +x minio && sudo mv minio /usr/local/bin/
        fi
    elif [[ "$OS" == "linux" ]]; then
        curl -O https://dl.min.io/server/minio/release/linux-amd64/minio && chmod +x minio && sudo mv minio /usr/local/bin/
    fi
    MINIO_BIN=$(command -v minio || true)
fi

# Install MinIO Client (mc) if missing
MC_BIN=$(command -v mc || true)
if [[ -z "$MC_BIN" ]]; then
    echo -e "${YELLOW}MinIO Client (mc) not found. Installing...${NC}"
    if [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            brew install minio/stable/mc || brew upgrade mc || true
        else
            curl -O https://dl.min.io/client/mc/release/darwin-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/
        fi
    elif [[ "$OS" == "linux" ]]; then
        curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/
    fi
    MC_BIN=$(command -v mc || true)
fi

if [[ -n "$MINIO_BIN" ]]; then
    # Find a free port for MinIO
    while lsof -i :$MINIO_PORT >/dev/null 2>&1; do
        ((MINIO_PORT++))
        if [[ $MINIO_PORT -gt 4000 ]]; then
            echo -e "${RED}No free port for MinIO in 3900-4000 range${NC}"
            MINIO_PORT=0
            break
        fi
    done
    if [[ $MINIO_PORT -ne 0 ]]; then
        # Check if MinIO is already running on this port
        if ! lsof -i :$MINIO_PORT >/dev/null 2>&1; then
            MINIO_DATA_DIR="$ROOT_DIR/.minio-data"
            mkdir -p "$MINIO_DATA_DIR"
            nohup "$MINIO_BIN" server --address ":$MINIO_PORT" "$MINIO_DATA_DIR" >/dev/null 2>&1 &
            sleep 2
            echo -e "${GREEN}✓ MinIO started on port $MINIO_PORT${NC}"
        else
            echo -e "${GREEN}✓ MinIO already running on port $MINIO_PORT${NC}"
        fi

        # Print endpoint for developer
        echo -e "${BLUE}MinIO S3 endpoint: http://localhost:$MINIO_PORT${NC}"

        # Auto-create buckets if needed (requires mc CLI)
        BUCKET_NAME="pala-local"
        REPLICA_BUCKET_NAME="pala-local-replica"
        MC_BIN=$(command -v mc || true)
        if [[ -n "$MC_BIN" ]]; then
            "$MC_BIN" alias set localminio "http://localhost:$MINIO_PORT" minioadmin minioadmin >/dev/null 2>&1 || true
            
            # Create primary bucket
            if ! "$MC_BIN" ls localminio/$BUCKET_NAME >/dev/null 2>&1; then
                "$MC_BIN" mb localminio/$BUCKET_NAME >/dev/null 2>&1 && \
                echo -e "${GREEN}✓ MinIO bucket '$BUCKET_NAME' created${NC}"
            else
                echo -e "${GREEN}✓ MinIO bucket '$BUCKET_NAME' already exists${NC}"
            fi
            
            # Create replica bucket
            if ! "$MC_BIN" ls localminio/$REPLICA_BUCKET_NAME >/dev/null 2>&1; then
                "$MC_BIN" mb localminio/$REPLICA_BUCKET_NAME >/dev/null 2>&1 && \
                echo -e "${GREEN}✓ MinIO replica bucket '$REPLICA_BUCKET_NAME' created${NC}"
            else
                echo -e "${GREEN}✓ MinIO replica bucket '$REPLICA_BUCKET_NAME' already exists${NC}"
            fi
        else
            echo -e "${YELLOW}MinIO Client (mc) not found. Please install from https://min.io/download#/mc to auto-create buckets.${NC}"
        fi
    fi
fi


echo -e "${GREEN}✓ Setup gate passed${NC}"
exit 0
