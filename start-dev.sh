#!/bin/bash

# Pala Platform - Development Startup Script
# Starts MCP server, agents, and web dashboard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pala Platform - Starting Development Stack${NC}"
echo -e "${BLUE}================================================${NC}\n"

# Store the root directory
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Set agent venv dir for all agent launches (it's in the project root, not parent)
AGENT_VENV_DIR="$ROOT_DIR/agent-venv"
cd "$ROOT_DIR"

is_python_healthy() {
    local py="$1"
    "$py" -c "import xml.parsers.expat" >/dev/null 2>&1
}

select_python_cmd() {
    local candidates=()
    if [ -n "${PALA_PYTHON:-}" ]; then
        candidates+=("$PALA_PYTHON")
    fi
    candidates+=("python3.12" "python3.11" "python3.10" "python" "python3" "/usr/bin/python3")

    local candidate
    local resolved
    for candidate in "${candidates[@]}"; do
        if [[ "$candidate" == /* ]]; then
            resolved="$candidate"
            [ -x "$resolved" ] || continue
        else
            resolved="$(command -v "$candidate" 2>/dev/null || true)"
            [ -n "$resolved" ] || continue
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
    if [ -x "$venv_dir/bin/python" ]; then
        printf '%s' "$venv_dir/bin/python"
        return 0
    fi
    if [ -x "$venv_dir/Scripts/python.exe" ]; then
        printf '%s' "$venv_dir/Scripts/python.exe"
        return 0
    fi
    return 1
}

ensure_agent_venv() {
    local agent_dir="$1"
    local label="$2"

    if [ ! -d "$agent_dir/venv" ]; then
        echo -e "${YELLOW}[$label] Creating virtual environment with $BOOTSTRAP_PYTHON...${NC}"
        "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" || return 1
    fi

    local venv_python=""
    if venv_python="$(venv_python "$agent_dir/venv")"; then
        if ! "$venv_python" -c "import xml.parsers.expat" >/dev/null 2>&1; then
            echo -e "${YELLOW}[$label] Existing venv uses broken Python; recreating...${NC}"
            rm -rf "$agent_dir/venv"
            "$BOOTSTRAP_PYTHON" -m venv "$agent_dir/venv" || return 1
        fi
    fi
}

get_python_for_agent() {
    local agent_dir="$1"
    local agent_python=""

    # Prefer shared agent venv only if it has a working pip
    if [ -f "$AGENT_VENV_DIR/bin/python" ] && [ -x "$AGENT_VENV_DIR/bin/pip" ] && "$AGENT_VENV_DIR/bin/python" -c "import xml.parsers.expat" >/dev/null 2>&1; then
        agent_python="$AGENT_VENV_DIR/bin/python"
    elif [ -f "$AGENT_VENV_DIR/bin/python3" ] && [ -x "$AGENT_VENV_DIR/bin/pip" ] && "$AGENT_VENV_DIR/bin/python3" -c "import xml.parsers.expat" >/dev/null 2>&1; then
        agent_python="$AGENT_VENV_DIR/bin/python3"
    elif [ -f "$AGENT_VENV_DIR/Scripts/python.exe" ] && [ -x "$AGENT_VENV_DIR/Scripts/pip.exe" ] && "$AGENT_VENV_DIR/Scripts/python.exe" -c "import xml.parsers.expat" >/dev/null 2>&1; then
        agent_python="$AGENT_VENV_DIR/Scripts/python.exe"
    elif [ -f "$agent_dir/venv/bin/python" ]; then
        agent_python="$agent_dir/venv/bin/python"
    elif [ -f "$agent_dir/venv/bin/python3" ]; then
        agent_python="$agent_dir/venv/bin/python3"
    elif [ -f "$agent_dir/venv/Scripts/python.exe" ]; then
        agent_python="$agent_dir/venv/Scripts/python.exe"
    elif command -v python3 >/dev/null 2>&1; then
        agent_python="$(command -v python3)"
    fi

    printf '%s' "$agent_python"
}

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    local pids=()
    local pid

    for pid in "$MCP_PID" "$SAMPLE_PID" "$METADATA_PID" "$STORAGE_PID" "$CHAT_PID" "$WEB_PID" "$OLLAMA_PID"; do
        if [ -n "$pid" ]; then
            pids+=("$pid")
        fi
    done

    while IFS= read -r pid; do
        if [ -n "$pid" ]; then
            pids+=("$pid")
        fi
    done < <(jobs -pr 2>/dev/null || true)

    if [ "${#pids[@]}" -gt 0 ]; then
        printf '%s\n' "${pids[@]}" | sort -u | xargs -r kill 2>/dev/null || true

        for _ in 1 2 3 4 5; do
            if ! printf '%s\n' "${pids[@]}" | sort -u | xargs -r kill -0 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if printf '%s\n' "${pids[@]}" | sort -u | xargs -r kill -0 2>/dev/null; then
            printf '%s\n' "${pids[@]}" | sort -u | xargs -r kill -9 2>/dev/null || true
        fi
    fi

    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

BOOTSTRAP_PYTHON="$(select_python_cmd || true)"
if [ -z "$BOOTSTRAP_PYTHON" ]; then
    echo -e "${RED}No healthy Python interpreter found (expat/ensurepip failed).${NC}"
    echo -e "${YELLOW}Set PALA_PYTHON to a working Python, e.g.:${NC} PALA_PYTHON=$(command -v python3.11) ./start-dev.sh"
    exit 1
fi
echo -e "${GREEN}Using Python interpreter:${NC} $BOOTSTRAP_PYTHON"

# Preflight: clear stale listeners on required ports
clear_port() {
    local port=$1
    local label=$2
    local pids
    
    # Try different tools for cross-platform compatibility
    if command -v lsof >/dev/null 2>&1; then
        # macOS and Linux with lsof installed
        pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    elif command -v ss >/dev/null 2>&1; then
        # Modern Linux with ss (socket statistics)
        pids=$(ss -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}' | grep -oP '(?<=pid=)\d+' | head -1)
    elif command -v netstat >/dev/null 2>&1; then
        # Fallback to netstat (Linux, BSD)
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}' | cut -d'/' -f1)
    else
        echo -e "${YELLOW}⚠ Cannot determine port status (lsof, ss, or netstat required)${NC}"
        return
    fi

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found existing listener(s) on :$port for $label -> $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✓ Cleared port $port${NC}"
    fi
}

npm_cmd() {
    if command -v npm.cmd >/dev/null 2>&1; then
        printf '%s' "$(command -v npm.cmd)"
    elif command -v npm >/dev/null 2>&1; then
        printf '%s' "$(command -v npm)"
    else
        return 1
    fi
}

NPM_CMD="$(npm_cmd || true)"
if [ -z "$NPM_CMD" ]; then
    echo -e "${RED}npm is not available in PATH.${NC}"
    echo -e "${YELLOW}Install Node.js and ensure npm or npm.cmd is available, then rerun:${NC} ./start-dev.sh"
    exit 1
fi

echo -e "${GREEN}[Preflight] Clearing conflicting ports and stopping old agents...${NC}"
clear_port 3010 "MCP Server"
clear_port 3020 "Web Dashboard"

# Kill any running agent processes from previous sessions
echo -e "${YELLOW}Stopping any running agent processes...${NC}"
pkill -f "packages/agents/.*main.py" 2>/dev/null || true
pkill -f "packages/PalaAgents/.*main.py" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Old agent processes stopped${NC}"
echo ""

# 0. Dependency gate
echo -e "${GREEN}[0/6] Validating required dependencies...${NC}"
if ! "$ROOT_DIR/setup-dev.sh"; then
    echo -e "\n${RED}Dependency gate failed. Services were not started.${NC}"
    echo -e "${YELLOW}Fix missing dependencies, then run:${NC} ./start-dev.sh\n"
    exit 1
fi

# Critical: Verify sentence-transformers for question generation quality
echo -e "${GREEN}Verifying sentence-transformers installation...${NC}"
AGENT_PYTHON=""
if [ -d "$AGENT_VENV_DIR" ]; then
    AGENT_PYTHON="$(venv_python "$AGENT_VENV_DIR")" || true
fi

if [ -n "$AGENT_PYTHON" ]; then
    if $AGENT_PYTHON -c "import sentence_transformers; print('[startup] ✓ sentence-transformers v' + sentence_transformers.__version__ + ' is ready')" 2>&1; then
        echo -e "${GREEN}✓ sentence-transformers verified in agent venv${NC}"
    else
        echo -e "${RED}FATAL: sentence-transformers not found in $AGENT_VENV_DIR${NC}"
        echo -e "${YELLOW}sentence-transformers is required for high-quality question generation.${NC}"
        echo -e "${YELLOW}The pip install may have failed. Check output above.${NC}"
        exit 1
    fi
else
    echo -e "${RED}FATAL: Could not find Python in agent venv at $AGENT_VENV_DIR${NC}"
    exit 1
fi
echo ""

if [ ! -d $ROOT_DIR/logs ]; then
    mkdir -p $ROOT_DIR/logs
fi
# Start Ollama server in background if not already running
echo -e "${GREEN}[0.5/6] Starting Ollama Server...${NC}"
if command -v ollama >/dev/null 2>&1; then
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${YELLOW}Starting Ollama server...${NC}"
        ollama serve > "$ROOT_DIR/logs/ollama.log" 2>&1 &
        OLLAMA_PID=$!
        echo -e "${GREEN}✓ Ollama Server started (PID: $OLLAMA_PID)${NC}"
        sleep 3  # Give Ollama time to start
    else
        echo -e "${GREEN}✓ Ollama Server already running${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}⚠ Ollama not found - skipping Ollama startup${NC}"
    echo ""
fi

# Check if ANTHROPIC_API_KEY is set (optional, chat-agent will work without it)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠ ANTHROPIC_API_KEY not set - chat-agent will use Ollama only${NC}"
    echo -e "${YELLOW}To enable Claude responses, set:${NC}"
    echo -e "  export ANTHROPIC_API_KEY=\"sk-ant-api03-your-key-here\"\n"
fi

echo -e "${GREEN}[Preflight] Killing any running storage-agent processes...${NC}"
pkill -f "packages/PalaAgents/storage-agent/main.py" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Old storage-agent processes stopped${NC}"

# 1. Start MCP Server
echo -e "${GREEN}[1/6] Starting MCP Server...${NC}"
cd "$ROOT_DIR/packages/mcp-server"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing MCP Server dependencies...${NC}"
    "$NPM_CMD" install
fi



"$NPM_CMD" run dev > "$ROOT_DIR/logs/mcp-server.log" 2>&1 &
MCP_PID=$!
echo -e "${GREEN}✓ MCP Server started (PID: $MCP_PID)${NC}"
echo -e "  Logs: logs/mcp-server.log\n"
sleep 3

# 2. Start Sample Agent
echo -e "${GREEN}[2/6] Starting Sample Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/sample-agent"
    ensure_agent_venv "$ROOT_DIR/packages/PalaAgents/sample-agent" "sample-agent" || true
    # Determine python interpreter for this agent (prefer per-agent venv if shared venv broken)
    VENV_PYTHON="$(get_python_for_agent "$ROOT_DIR/packages/PalaAgents/sample-agent")"
    if [ -n "$VENV_PYTHON" ]; then
        echo "[sample-agent] Using python: $VENV_PYTHON"
        # Ensure pip is available and show output if installs fail
        if ! $VENV_PYTHON -m pip --version >/dev/null 2>&1; then
            echo "[sample-agent] pip missing in venv, attempting ensurepip..."
            $VENV_PYTHON -m ensurepip --upgrade || true
        fi
        $VENV_PYTHON -m pip install --upgrade pip setuptools wheel || true
        if [ -f requirements.txt ]; then
            $VENV_PYTHON -m pip install -r requirements.txt || echo "[sample-agent] pip install failed (see output)"
        fi
    export MCP_SERVER_URL="ws://localhost:3010"
    export MCP_AGENT_ID="sample-agent"
    $VENV_PYTHON main.py > "$ROOT_DIR/logs/sample-agent.log" 2>&1 &
    SAMPLE_PID=$!
    echo -e "${GREEN}✓ Sample Agent started (PID: $SAMPLE_PID)${NC}"
    echo -e "  Logs: logs/sample-agent.log\n"
else
    echo -e "${RED}Failed to find venv python${NC}"
fi
sleep 2

# 3. Start Metadata Extraction Agent
echo -e "${GREEN}[3/6] Starting Metadata Extraction Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/metadata-extraction-agent"
    ensure_agent_venv "$ROOT_DIR/packages/PalaAgents/metadata-extraction-agent" "metadata-agent" || true
    VENV_PYTHON="$(get_python_for_agent "$ROOT_DIR/packages/PalaAgents/metadata-extraction-agent")"
    if [ -n "$VENV_PYTHON" ]; then
        echo "[metadata-agent] Using python: $VENV_PYTHON"
        if ! $VENV_PYTHON -m pip --version >/dev/null 2>&1; then
            echo "[metadata-agent] pip missing in venv, attempting ensurepip..."
            $VENV_PYTHON -m ensurepip --upgrade || true
        fi
        $VENV_PYTHON -m pip install --upgrade pip setuptools wheel || true
        if [ -f requirements.txt ]; then
            $VENV_PYTHON -m pip install -r requirements.txt || echo "[metadata-agent] pip install failed (see output)"
        fi
    export MCP_SERVER_URL="ws://localhost:3010"
    export MCP_AGENT_ID="metadata-extraction-agent"
    $VENV_PYTHON main.py > "$ROOT_DIR/logs/metadata-agent.log" 2>&1 &
    METADATA_PID=$!
    echo -e "${GREEN}✓ Metadata Extraction Agent started (PID: $METADATA_PID)${NC}"
    echo -e "  Logs: logs/metadata-agent.log\n"
else
    echo -e "${RED}Failed to find venv python${NC}"
fi
sleep 2

# 4. Start Storage Agent
echo -e "${GREEN}[4/6] Starting Storage Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/storage-agent"
    ensure_agent_venv "$ROOT_DIR/packages/PalaAgents/storage-agent" "storage-agent" || true
    VENV_PYTHON="$(get_python_for_agent "$ROOT_DIR/packages/PalaAgents/storage-agent")"
    if [ -n "$VENV_PYTHON" ]; then
        echo "[storage-agent] Using python: $VENV_PYTHON"
        if ! $VENV_PYTHON -m pip --version >/dev/null 2>&1; then
            echo "[storage-agent] pip missing in venv, attempting ensurepip..."
            $VENV_PYTHON -m ensurepip --upgrade || true
        fi
        $VENV_PYTHON -m pip install --upgrade pip setuptools wheel || true
        if [ -f requirements.txt ]; then
            $VENV_PYTHON -m pip install -r requirements.txt || echo "[storage-agent] pip install failed (see output)"
        fi
    export MCP_SERVER_URL="ws://localhost:3010"
    export MCP_AGENT_ID="storage-agent"
    $VENV_PYTHON main.py > "$ROOT_DIR/logs/storage-agent.log" 2>&1 &
    STORAGE_PID=$!
    echo -e "${GREEN}✓ Storage Agent started (PID: $STORAGE_PID)${NC}"
    echo -e "  Logs: logs/storage-agent.log\n"
else
    echo -e "${RED}Failed to find venv python${NC}"
fi
sleep 2

# 5. Start Chat Agent
echo -e "${GREEN}[5/6] Starting Chat Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/chat-agent"
    ensure_agent_venv "$ROOT_DIR/packages/PalaAgents/chat-agent" "chat-agent" || true
    VENV_PYTHON="$(get_python_for_agent "$ROOT_DIR/packages/PalaAgents/chat-agent")"
    if [ -n "$VENV_PYTHON" ]; then
        echo "[chat-agent] Using python: $VENV_PYTHON"
        if ! $VENV_PYTHON -m pip --version >/dev/null 2>&1; then
            echo "[chat-agent] pip missing in venv, attempting ensurepip..."
            $VENV_PYTHON -m ensurepip --upgrade || true
        fi
        $VENV_PYTHON -m pip install --upgrade pip setuptools wheel || true
        if [ -f requirements.txt ]; then
            $VENV_PYTHON -m pip install -r requirements.txt || echo "[chat-agent] pip install failed (see output)"
        fi
    export MCP_SERVER_URL="ws://localhost:3010"
    export MCP_AGENT_ID="chat-agent"
    $VENV_PYTHON main.py > "$ROOT_DIR/logs/chat-agent.log" 2>&1 &
    CHAT_PID=$!
    echo -e "${GREEN}✓ Chat Agent started (PID: $CHAT_PID)${NC}"
    echo -e "  Logs: logs/chat-agent.log\n"
else
    echo -e "${RED}Failed to find venv python${NC}"
fi
sleep 2

# 6. Start Web Dashboard
echo -e "${GREEN}[6/6] Starting Web Dashboard...${NC}"
cd "$ROOT_DIR/apps/web"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Web Dashboard dependencies...${NC}"
    "$NPM_CMD" install
fi
"$NPM_CMD" run dev > "$ROOT_DIR/logs/cd logs" 2>&1 &
WEB_PID=$!
echo -e "${GREEN}✓ Web Dashboard started (PID: $WEB_PID)${NC}"
echo -e "  Logs: logs/web-dashboard.log\n"
sleep 3

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✓ All services running!${NC}"
echo -e "${BLUE}================================================${NC}\n"

echo -e "${YELLOW}Services:${NC}"
echo -e "  • MCP Server:          ws://localhost:3010"
echo -e "  • Sample Agent:        Connected (echo, sum)"
echo -e "  • Metadata Agent:      Connected (extract_metadata)"
echo -e "  • Storage Agent:       Connected (store_document, retrieve_document, list_documents, semantic_search_documents, etc.)"
echo -e "  • Chat Agent:          Connected (chat_with_documents)"
echo -e "  • Web Dashboard:       http://localhost:3020\n"

echo -e "${YELLOW}Logs:${NC}"
echo -e "  • MCP Server:          tail -f logs/mcp-server.log"
echo -e "  • Sample Agent:        tail -f logs/sample-agent.log"
echo -e "  • Metadata Agent:      tail -f logs/metadata-agent.log"
echo -e "  • Storage Agent:       tail -f logs/storage-agent.log"
echo -e "  • Chat Agent:          tail -f logs/chat-agent.log"
echo -e "  • Web Dashboard:       tail -f logs/web-dashboard.log\n"

echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background processes
wait
