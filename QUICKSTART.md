# Pala Platform - Quick Start

## One-Command Startup

### Prerequisites
1. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

2. Install Node.js and Python 3.10+ if not already installed

### Start Everything
```bash
cd /Users/vijayaraghavanvedantham/Documents/GitHub/pala-platform
./start-dev.sh
```

This will:
- ✓ Start MCP Server (port 3000)
- ✓ Start Sample Agent (echo, sum tools)
- ✓ Start Metadata Extraction Agent (extract_metadata tool)
- ✓ Start Web Dashboard (port 3001)

### Stop Everything
```bash
./stop-dev.sh
```

### View Logs
All logs are stored in `logs/` directory:
```bash
# Watch all logs in real-time
tail -f logs/*.log

# Or individually:
tail -f logs/mcp-server.log
tail -f logs/sample-agent.log
tail -f logs/metadata-agent.log
tail -f logs/web-dashboard.log
```

### Access Dashboard
Open: http://localhost:3001

You should see:
- **Agents**: sample-agent, metadata-extraction-agent
- **Tools**: echo, sum, extract_metadata

### Troubleshooting

**API Key Error?**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
./start-dev.sh
```

**Port Conflict?**
```bash
./stop-dev.sh  # Kill all services
./start-dev.sh  # Restart
```

**Service Failed?**
```bash
# Check logs
cat logs/metadata-agent.log  # or other service log
```

**Clean Restart?**
```bash
./stop-dev.sh
rm -rf logs/*.log
./start-dev.sh
```
