# Quick Start

**→ [See Full Getting Started Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)**

## One-Command Startup

```bash
# Clone the repository (first time only)
git clone https://github.com/palasangha/pala-platform.git
cd pala-platform

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Start everything
./start-dev.sh
```

This will start:
- ✓ MCP Server (ws://localhost:3000)
- ✓ Sample Agent (echo, sum tools)
- ✓ Metadata Extraction Agent (extract_metadata tool)
- ✓ Web Dashboard (http://localhost:3001)

**View logs:**
```bash
tail -f logs/*.log
```

**Stop everything:**
```bash
./stop-dev.sh
```

For detailed setup, manual startup, troubleshooting, and usage, see [Getting Started Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md).
