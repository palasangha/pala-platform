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

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY not set${NC}"
    echo -e "${YELLOW}Please set it:${NC}"
    echo -e "  export ANTHROPIC_API_KEY=\"sk-ant-api03-your-key-here\"\n"
    exit 1
fi

# Store the root directory
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
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

# 1. Start MCP Server
echo -e "${GREEN}[1/5] Starting MCP Server...${NC}"
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
echo -e "${GREEN}[2/5] Starting Sample Agent...${NC}"
cd "$ROOT_DIR/packages/agents/sample-agent"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
if [ ! -f "venv/bin/websockets" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3000"
export MCP_AGENT_ID="sample-agent"
python main.py > "$ROOT_DIR/logs/sample-agent.log" 2>&1 &
SAMPLE_PID=$!
deactivate
echo -e "${GREEN}✓ Sample Agent started (PID: $SAMPLE_PID)${NC}"
echo -e "  Logs: logs/sample-agent.log\n"
sleep 2

# 3. Start Metadata Extraction Agent
echo -e "${GREEN}[3/5] Starting Metadata Extraction Agent...${NC}"
cd "$ROOT_DIR/packages/agents/metadata-extraction-agent"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
if [ ! -f "venv/bin/anthropic" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3000"
export MCP_AGENT_ID="metadata-extraction-agent"
python main.py > "$ROOT_DIR/logs/metadata-agent.log" 2>&1 &
METADATA_PID=$!
deactivate
echo -e "${GREEN}✓ Metadata Extraction Agent started (PID: $METADATA_PID)${NC}"
echo -e "  Logs: logs/metadata-agent.log\n"
sleep 2

# 4. Start Storage Agent
echo -e "${GREEN}[4/5] Starting Storage Agent...${NC}"
cd "$ROOT_DIR/packages/agents/storage-agent"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
if [ ! -f "venv/bin/websockets" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
export MCP_SERVER_URL="ws://localhost:3000"
export MCP_AGENT_ID="storage-agent"
python main.py > "$ROOT_DIR/logs/storage-agent.log" 2>&1 &
STORAGE_PID=$!
deactivate
echo -e "${GREEN}✓ Storage Agent started (PID: $STORAGE_PID)${NC}"
echo -e "  Logs: logs/storage-agent.log\n"
sleep 2

# 5. Start Web Dashboard
echo -e "${GREEN}[5/5] Starting Web Dashboard...${NC}"
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
echo -e "  • MCP Server:          ws://localhost:3000"
echo -e "  • Sample Agent:        Connected (echo, sum)"
echo -e "  • Metadata Agent:      Connected (extract_metadata)"
echo -e "  • Storage Agent:       Connected (store_document, retrieve_document, list_documents, list_backends, get_stats)"
echo -e "  • Web Dashboard:       http://localhost:3001\n"

echo -e "${YELLOW}Logs:${NC}"
echo -e "  • MCP Server:          tail -f logs/mcp-server.log"
echo -e "  • Sample Agent:        tail -f logs/sample-agent.log"
echo -e "  • Metadata Agent:      tail -f logs/metadata-agent.log"
echo -e "  • Storage Agent:       tail -f logs/storage-agent.log"
echo -e "  • Web Dashboard:       tail -f logs/web-dashboard.log\n"

echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background processes
wait
