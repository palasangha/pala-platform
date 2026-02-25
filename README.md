# Pala Platform

Centralized orchestration platform for AI agents using the Model Context Protocol (MCP).

## Quick Start

### One-Command Startup (Recommended)

```bash
# Set your Anthropic API key (required for metadata-extraction-agent)
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Start everything: MCP server, agents, and dashboard
./start-dev.sh
```

**That's it!** This will start:
- ✅ MCP Server (ws://localhost:3000)
- ✅ Sample Agent (echo, sum tools)
- ✅ Metadata Extraction Agent (extract_metadata tool)
- ✅ Web Dashboard (http://localhost:3001)

**Stop everything:**
```bash
./stop-dev.sh
```

**View logs:**
```bash
tail -f logs/*.log
```

See [QUICKSTART.md](QUICKSTART.md) for details.

### Manual Startup (Alternative)

```bash
# 1. Install dependencies
pnpm install

# 2. Terminal 1 - Start MCP server
cd packages/mcp-server && npm run dev

# 3. Terminal 2 - Connect sample agent
cd packages/agents/sample-agent && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python main.py

# 4. Terminal 3 - Connect metadata extraction agent
cd packages/agents/metadata-extraction-agent && source venv/bin/activate && export ANTHROPIC_API_KEY="sk-ant-..." && python main.py

# 5. Terminal 4 - Start web dashboard
cd apps/web && npm run dev
```

**[→ Full Getting Started Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)**

## Features

- **Centralized Agent Management**: Discover, manage, and invoke tools from all connected agents
- **Language-Agnostic**: Agents written in any language via JSON-RPC 2.0 over WebSocket
- **Real-Time Dashboard**: Monitor agents, list tools, and invoke with zero friction
- **Security**: Optional JWT authentication and configurable authorization
- **Observability**: Request tracing with correlation IDs, structured logging
- **Type-Safe**: Full TypeScript implementation with Zod runtime validation
- **Production-Ready**: Comprehensive test suite (127+ tests), error handling, graceful shutdown

## Architecture

```
MCP Server (Node.js + WebSocket)
├── Protocol: JSON-RPC 2.0 message routing
├── Transport: WebSocket with heartbeat, auth hooks
├── Registry: Tool catalog with agent mapping
├── Invoker: Tool execution routing to agents
├── Logging: Structured JSON with Pino
└── Tracing: Request correlation IDs

Agents (Python, JavaScript, Go, etc.)
├── WebSocket client connecting to MCP server
├── Self-registration via tools/register on connect
├── Tool invocation handling via JSON-RPC requests
└── Results routed back via tools/invoke response

Web Dashboard (React + Next.js)
├── Real-time WebSocket client
├── Agent and tool discovery
├── Interactive tool invocation UI
└── Connection status monitoring
```

## Project Structure

```
pala-platform/
├── apps/
│   ├── mobile/     (mobile client, future)
│   └── web/        (React dashboard - start here)
├── packages/
│   ├── agents/
│   │   ├── sample-agent/              (Python reference - echo, sum tools)
│   │   ├── metadata-extraction-agent/ (Claude AI metadata extraction)
│   │   └── ...other agents
│   ├── mcp-server/        (core MCP server)
│   ├── processors/        (data processing pipeline)
│   ├── storage/           (persistence layer)
│   ├── enrichment/        (AI enrichment agents)
│   └── shared/            (shared types/utilities)
├── docs/           (architecture, guides)
├── scripts/        (build, deploy scripts)
├── tests/          (integration tests)
├── start-dev.sh    (one-command startup script)
├── stop-dev.sh     (stop all services)
├── QUICKSTART.md   (quick start guide)
└── turbo.json      (monorepo config)
```

## Stories Implemented

### Completed (Slice 01: MVP Foundation)
- ✅ **Story #7**: JSON-RPC 2.0 Protocol (36 tests)
- ✅ **Story #8**: WebSocket Transport (13 tests)
- ✅ **Story #9**: Tool Registry & Invocation (43 tests)
- ✅ **Story #36**: Structured Logging (25 tests)
- ✅ **Story #37**: Request Tracing (3 tests)
- ✅ **Story #41**: Client Authentication (JWT, optional)
- ✅ **Server Handlers**: Tool/agent discovery RPC methods
- ✅ **Web Dashboard**: Agent management & tool invocation UI

### Test Results
- **Total Tests**: 127 passing
- **Coverage**: Protocol, transport, registry, logging, tracing, handlers, orchestration
- **Framework**: Vitest with comprehensive test suite

### Pending (Future Stories)
- Story #42: Agent-level authorization
- Story #45: TLS/HTTPS configuration
- Story #43: Persistent storage integration

## Key Technologies

- **Server**: TypeScript, Node.js, ws (WebSocket), Pino (logging), Zod (validation)
- **Agent**: Python (reference), any language via JSON-RPC
- **Dashboard**: React, Next.js, TailwindCSS, TypeScript
- **Testing**: Vitest, comprehensive test coverage
- **Monorepo**: pnpm workspaces, Turbo

## Development

### Running Tests
```bash
cd packages/mcp-server
npm test          # Run all tests
npm run test:watch # Watch mode
npm run test:coverage # Coverage report
```

### Development Commands
```bash
# Watch mode for development
npm run dev          # in each package directory

# Build production
npm run build        # from root

# Clean build artifacts
npm run clean
```

### Configuration

| Env Variable | Description | Default |
|---|---|---|
| `PORT` | MCP server WebSocket port | `3000` |
| `MCP_JWT_SECRET` | Enable JWT auth (leave unset for disabled) | `unset` |
| `MCP_AGENT_TOKEN` | Agent auth token (set if server has auth enabled) | `unset` |
| `MCP_SERVER_URL` | Server URL for agent connection | `ws://localhost:3000` |
| `NEXT_PUBLIC_MCP_SERVER_URL` | Server URL for web dashboard | `ws://localhost:3000` |
| `ANTHROPIC_API_KEY` | Claude API key (for metadata extraction agent) | `unset` |

## JSON-RPC Methods

### Server Methods (called by clients)
- `agents/list()` - List connected agents
- `tools/list()` - List all available tools
- `tools/invoke({toolName, agentId, arguments})` - Invoke a tool

### Agent Methods (sent by agents)
- `tools/register({tools})` - Register tools on startup
- `tools/invoke` - Respond to tool invocation

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Port 3000 already in use | Change PORT env var or kill process with `lsof -i :3000` |
| Agent won't connect | Check server URL with `MCP_SERVER_URL=ws://127.0.0.1:3000` |
| Dashboard shows "Disconnected" | Verify server running, check browser console (F12) |
| Tools don't appear | Refresh dashboard, check server logs for agent registration |
| Auth failures | If auth enabled, ensure `MCP_AGENT_TOKEN` matches secret |

## File Quick Reference

| File | Purpose |
|------|---------|
| `src/server.ts` | Main MCPServer class - orchestrates everything |
| `src/protocol/handler.ts` | JSON-RPC request routing |
| `src/transport/websocket.ts` | WebSocket server implementation |
| `src/registry/tool-registry.ts` | Tool storage and search |
| `src/handlers.ts` | RPC method handlers |
| `src/logging/logger.ts` | Structured logging with Pino |
| `src/bin/start.ts` | CLI entry point |
| `apps/web/components/Dashboard.tsx` | React main UI |
| `apps/web/hooks/useWebSocket.ts` | WebSocket client hook |

## Adding a New Agent

1. **In Python** (copy sample-agent pattern):
```python
import websockets
import json

async def main():
    async with websockets.connect('ws://localhost:3000') as ws:
        # Register tools
        await ws.send(json.dumps({
            'jsonrpc': '2.0',
            'method': 'tools/register',
            'params': {'tools': [...]},
            'id': 1
        }))
        
        # Handle invocations
        async for message in ws:
            ...
```

2. **In Go/Node.js/Other**: Same JSON-RPC 2.0 protocol over WebSocket

3. **Start agent**: `python agent.py` (will auto-connect to ws://localhost:3000)

4. **Verify**: Check dashboard or run `agents/list` to see it listed

## Adding a New Tool

In your agent, add to `tools/register` message:

```javascript
{
  name: 'my-tool',
  description: 'What it does',
  agentId: 'my-agent-id',
  inputSchema: {
    type: 'object',
    properties: {
      param1: { type: 'string' },
      param2: { type: 'number' }
    }
  },
  metadata: { /* optional */ }
}
```

Tool automatically appears in web dashboard and is callable via `tools/invoke`.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - One-command startup guide
- **[Getting Started - Setup and Usage Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)** - Complete setup, troubleshooting, and usage
- **[packages/mcp-server/README.md](packages/mcp-server/README.md)** - Server implementation details
- **[packages/agents/sample-agent/README.md](packages/agents/sample-agent/README.md)** - Sample agent guide
- **[packages/agents/metadata-extraction-agent/README.md](packages/agents/metadata-extraction-agent/README.md)** - Metadata extraction agent guide
- **[apps/web/README.md](apps/web/README.md)** - Dashboard implementation

## Contributing

- Follow the project structure and conventions
- Write tests for new features
- Update relevant READMEs
- Submit pull requests with clear descriptions

## License

TBD
