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
            [[ -d "$HOME/AppData/Local/LM Studio" ]] || command_exists lm-studio
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

    if ollama_model_installed "$model"; then
        echo -e "${GREEN}✓ Ollama model '$model' already installed${NC}"
        return
    fi

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
                    python3 -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                fi
                if [[ -d "$agent_dir/venv" ]]; then
                    source "$agent_dir/venv/bin/activate" >/dev/null 2>&1 || true
                    pip install -q -r "$agent_dir/requirements.txt" >/dev/null 2>&1 || true
                    deactivate >/dev/null 2>&1 || true
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
                    python3 -m venv "$agent_dir/venv" >/dev/null 2>&1 || true
                fi
                if [[ -d "$agent_dir/venv" ]]; then
                    source "$agent_dir/venv/bin/activate" >/dev/null 2>&1 || true
                    pip install -q -r "$agent_dir/requirements.txt" >/dev/null 2>&1 || true
                    deactivate >/dev/null 2>&1 || true
                fi
            fi
        done
    fi
}

OS=$(get_os)
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MISSING=()
OLLAMA_MODEL_REQUIRED="${OLLAMA_MODEL:-minicpm-v}"

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
    exit 2
fi

echo -e "${GREEN}✓ All required dependencies are installed${NC}"
echo -e "${BLUE}Phase 2/2: Prepare local workspace deps${NC}"
prepare_workspace

echo -e "${GREEN}✓ Setup gate passed${NC}"
exit 0
