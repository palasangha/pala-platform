# Sample Agent (Python)

A minimal Python agent that speaks JSON-RPC over WebSocket to the MCP server.
It registers simple tools and handles `tools/invoke` requests.

## Prerequisites
- Python 3.10+
- `websockets` library (`pip install -r requirements.txt`)
- Running MCP server WebSocket endpoint (default: `ws://localhost:3000`)

## Quick start
```bash
cd packages/agents/sample-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure MCP server is running on ws://localhost:3000
python main.py
```

Environment variables:
- `MCP_SERVER_URL` (default `ws://localhost:3000`)
- `MCP_AGENT_ID` (default `sample-agent`)

## Tools implemented
- `echo`: returns the provided `text`
- `sum`: sums a list of numbers (`numbers` array)

## Notes
- Tool registration payload is sent via `tools/register`; server-side handling
  will be wired to the registry in a future story.
- The agent responds to `tools/invoke` with JSON-RPC responses and handles
  errors gracefully (invalid JSON, unknown tools, bad arguments).
- Keep this example minimal and deterministic for easy testing and extension.
