# Pala Platform - Quick Reference

## Quick Start (TL;DR)

```bash
# Install dependencies
pnpm install

# Terminal 1: Start server
cd packages/mcp-server && npm run dev

# Terminal 2: Start sample agent
cd packages/agents/sample-agent && python main.py

# Terminal 3: Start web dashboard
cd apps/web && npm run dev

# → Open http://localhost:3000
```

## Key Commands

### Development

```bash
# Watch mode for development
npm run dev          # in each package directory

# Build production
npm run build        # from root

# Run tests
npm test             # in packages/mcp-server
npm test:watch       # with auto-reload
npm test:coverage    # with coverage report

# Clean build artifacts
npm run clean
```

### Configuration

| Env Variable | Description | Default |
|---|---|---|
| `PORT` | MCP server WebSocket port | `3000` |
| `MCP_AUTH_SECRET` | Enable JWT auth (leave unset for disabled) | `unset` |
| `MCP_AGENT_TOKEN` | Agent auth token (set if server has auth enabled) | `unset` |
| `MCP_SERVER_URL` | Server URL for agent connection | `ws://localhost:3000` |
| `NEXT_PUBLIC_MCP_SERVER_URL` | Server URL for web dashboard | `ws://localhost:3000` |

## Architecture at a Glance

```
┌─────────────────────────────────────┐
│        Web Dashboard (React)         │ Port 3000/3001
│  • Agent listing                    │
│  • Tool discovery                   │
│  • Real-time invocation             │
└─────────────┬───────────────────────┘
              │ WebSocket JSON-RPC
              │
┌─────────────▼───────────────────────┐
│   MCP Server (Node.js)              │ Port 3000
│  • JSON-RPC 2.0 protocol            │
│  • WebSocket transport               │
│  • Tool registry                    │
│  • Agent orchestration              │
└──────────────────┬────────────────────┘
                   │ WebSocket JSON-RPC
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ Sample │ │ Custom │ │ Custom │
   │ Agent  │ │ Agent  │ │ Agent  │
   │Python  │ │  Go    │ │Node.js │
   └────────┘ └────────┘ └────────┘
```

## Project Structure

```
pala-platform/
├── apps/
│   └── web/              # Next.js dashboard
├── packages/
│   ├── mcp-server/       # Core MCP server (START HERE)
│   ├── agents/
│   │   └── sample-agent/ # Python reference agent
│   ├── shared/           # Shared types
│   └── ...other packages
├── docs/                 # Architecture & guides
├── GETTING_STARTED.md    # Complete setup guide
├── COMPLETION_SUMMARY.md # Feature & test summary
└── README.md             # Overview
```

## Testing

```bash
cd packages/mcp-server

# Run all tests (129 tests)
npm test

# Run specific test file
npm test test/handlers.test.ts

# Watch mode with auto-reload
npm test:watch

# Coverage report
npm test:coverage
```

**Test Breakdown:**
- Protocol: 36 tests
- Transport: 13 tests  
- Registry: 26 tests
- Logging: 25 tests
- Handlers: 7 tests
- Server: 2 tests
- Integration: 2 tests
- Tracing: 3 tests

## JSON-RPC Methods

All methods are bidirectional but most are server-provided:

### Server Methods (called by clients)

```javascript
// List connected agents
agents/list(params: {}) → { agents: Agent[] }

// List all available tools
tools/list(params: {}) → { tools: ToolDefinition[] }

// Invoke a tool
tools/invoke({
  toolName: string,
  agentId: string,
  arguments: Record<string, any>
}) → result (tool-specific)
```

### Agent Methods (sent by agents)

```javascript
// Register tools on startup
tools/register({
  tools: ToolDefinition[]
}) → { registered: number }

// Respond to tool/invoke
tools/invoke → result (routed back to client)
```

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

## Performance Notes

- **Message parsing**: < 1ms per message
- **Tool invocation**: Depends on tool execution time (no server overhead)
- **Heartbeat**: 30-second ping/pong for connection health
- **Timeout**: 10-second default for tool invocation responses

## Security

- **Auth**: Optional JWT on WebSocket upgrade (disable by not setting `MCP_AUTH_SECRET`)
- **Validation**: Zod runtime schema validation for all inputs
- **Logging**: All requests/responses logged with request IDs
- **Tracing**: Correlation IDs for debugging across layers

## Next Steps

1. Run the quick start commands above
2. Read GETTING_STARTED.md for detailed setup
3. Explore sample agent in packages/agents/sample-agent/
4. Try invoking tools via web dashboard
5. Modify sample agent to add your own tools
6. Read COMPLETION_SUMMARY.md for architecture details

---

**Need Help?**
- Check GETTING_STARTED.md for troubleshooting
- Review docs/ folder for architecture decisions
- Run tests to verify setup: `npm test` in packages/mcp-server
