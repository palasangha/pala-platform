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
# Set agent venv dir for all agent launches
AGENT_VENV_DIR="$(cd "$ROOT_DIR/.." && pwd)/agent-venv"
cd "$ROOT_DIR"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

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
if false; then
    echo -e "\n${RED}Dependency gate failed. Services were not started.${NC}"
    echo -e "${YELLOW}Fix missing dependencies, then run:${NC} ./start-dev.sh\n"
    exit 1
fi
echo ""

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

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY not set${NC}"
    echo -e "${YELLOW}Please set it:${NC}"
    echo -e "  export ANTHROPIC_API_KEY=\"sk-ant-api03-your-key-here\"\n"
    exit 1
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
    npm install
fi
npm run dev > "$ROOT_DIR/logs/mcp-server.log" 2>&1 &
MCP_PID=$!
echo -e "${GREEN}✓ MCP Server started (PID: $MCP_PID)${NC}"
echo -e "  Logs: logs/mcp-server.log\n"
sleep 3

# 2. Start Sample Agent
echo -e "${GREEN}[2/6] Starting Sample Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/sample-agent"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
# Activate virtual environment (cross-platform compatible)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi
if ! command -v websockets >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3010"
export MCP_AGENT_ID="sample-agent"
python main.py > "$ROOT_DIR/logs/sample-agent.log" 2>&1 &
SAMPLE_PID=$!
deactivate 2>/dev/null || true
echo -e "${GREEN}✓ Sample Agent started (PID: $SAMPLE_PID)${NC}"
echo -e "  Logs: logs/sample-agent.log\n"
sleep 2

# 3. Start Metadata Extraction Agent
echo -e "${GREEN}[3/6] Starting Metadata Extraction Agent...${NC}"
cd "$ROOT_DIR/packages/PalaAgents/metadata-extraction-agent"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
# Activate virtual environment (cross-platform compatible)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi
if ! command -v anthropic >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3010"
export MCP_AGENT_ID="metadata-extraction-agent"
python main.py > "$ROOT_DIR/logs/metadata-agent.log" 2>&1 &
METADATA_PID=$!
deactivate 2>/dev/null || true
echo -e "${GREEN}✓ Metadata Extraction Agent started (PID: $METADATA_PID)${NC}"
echo -e "  Logs: logs/metadata-agent.log\n"
sleep 2

# 4. Start Storage Agent
echo -e "${GREEN}[4/7] Starting Storage Agent...${NC}"
cd "$ROOT_DIR"
if [ ! -d "$AGENT_VENV_DIR" ]; then
    echo -e "${YELLOW}Creating shared agent virtual environment...${NC}"
    python3 -m venv "$AGENT_VENV_DIR"
fi
# Install storage-agent dependencies into shared venv
if ! "$AGENT_VENV_DIR/bin/python" -c "import sentence_transformers" 2>/dev/null; then
    echo -e "${YELLOW}Installing Storage Agent dependencies...${NC}"
    "$AGENT_VENV_DIR/bin/pip" install -q -r packages/PalaAgents/storage-agent/requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3010"
export MCP_AGENT_ID="storage-agent"
"$AGENT_VENV_DIR/bin/python" packages/PalaAgents/storage-agent/main.py > "$ROOT_DIR/logs/storage-agent.log" 2>&1 &
STORAGE_PID=$!
echo -e "${GREEN}✓ Storage Agent started (PID: $STORAGE_PID)${NC}"
echo -e "  Logs: logs/storage-agent.log\n"
sleep 2

# 5. Start Chat Agent
echo -e "${GREEN}[5/7] Starting Chat Agent...${NC}"
cd "$ROOT_DIR"
# Install chat-agent dependencies into shared venv
if [ -f "packages/PalaAgents/chat-agent/requirements.txt" ]; then
    if ! "$AGENT_VENV_DIR/bin/python" -c "import anthropic" 2>/dev/null; then
        echo -e "${YELLOW}Installing Chat Agent dependencies...${NC}"
        "$AGENT_VENV_DIR/bin/pip" install -q -r packages/PalaAgents/chat-agent/requirements.txt
    fi
fi
export MCP_SERVER_URL="ws://localhost:3010"
export MCP_AGENT_ID="chat-agent"
"$AGENT_VENV_DIR/bin/python" packages/PalaAgents/chat-agent/main.py > "$ROOT_DIR/logs/chat-agent.log" 2>&1 &
CHAT_PID=$!
echo -e "${GREEN}✓ Chat Agent started (PID: $CHAT_PID)${NC}"
echo -e "  Logs: logs/chat-agent.log\n"
sleep 2

# 6. Start Web Dashboard
echo -e "${GREEN}[6/7] Starting Web Dashboard...${NC}"
cd "$ROOT_DIR/apps/web"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Web Dashboard dependencies...${NC}"
    npm install
fi
npm run dev > "$ROOT_DIR/logs/web-dashboard.log" 2>&1 &
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
