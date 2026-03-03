# Pala Platform

Centralized orchestration platform for AI agents using the Model Context Protocol (MCP).

## Quick Start

### First-Time Setup (One-Time)

```bash
# Set up all required dependencies (Node, Python, Tesseract, Ollama, LM Studio)
# Idempotent: only installs what's missing where possible
./setup-dev.sh

# Set your Anthropic API key (required for metadata-extraction-agent)
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

### Start Development Stack

```bash
# Runs dependency gate first, then starts MCP server, all agents, and dashboard
# If anything required is missing, startup aborts and shows install instructions
./start-dev.sh
```

**Services Started:**
- ✅ MCP Server (ws://localhost:4000)
- ✅ Sample Agent (echo, sum tools)
- ✅ Metadata Extraction Agent (extract_metadata tool)
- ✅ Storage Agent (unified document storage with store_document, retrieve_document, list_documents)
- ✅ Web Dashboard (http://localhost:4001)

**Note:** Pala Platform provides core infrastructure (MCP + Storage + Metadata extraction). Domain-specific applications (OCR, transcription, etc.) are separate web apps that use the Storage Agent as their integration point.

**Stop everything:**
```bash
./stop-dev.sh
```

**View logs:**
```bash
tail -f logs/*.log
```

**[→ Full Getting Started Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)** for detailed setup, manual startup, and troubleshooting.

## Features

- **Centralized Agent Management**: Discover, manage, and invoke tools from all connected agents
- **Language-Agnostic**: Agents written in any language via JSON-RPC 2.0 over WebSocket
- **Real-Time Dashboard**: Monitor agents, list tools, and invoke with zero friction
- **Security**: Optional JWT authentication and configurable authorization
- **Observability**: Request tracing with correlation IDs, structured logging
- **Type-Safe**: Full TypeScript implementation with Zod runtime validation
- **Production-Ready**: Comprehensive test suite (127+ tests), error handling, graceful shutdown

## Architecture

**Pala Platform Core:**
- **MCP Server**: Central communication hub using JSON-RPC 2.0 over WebSocket
- **Storage Agent**: Unified database layer with `store_document()`, `retrieve_document()`, `list_documents()` tools
- **Metadata Extractor Agent**: Optional service for enriching content with AI-powered metadata
- **Web Dashboard**: Real-time monitoring and tool invocation UI

**External Applications:**
- Domain-specific web apps (OCR, transcription, document conversion, etc.) run independently
- Each app has its own business logic, UI, and local storage
- Apps connect to MCP Server and use Storage Agent as the integration point
- All extracted data flows into Pala Platform's unified database (single source of truth)
- Apps can optionally use Metadata Extractor for enrichment

```
┌─────────────────────────────────────────────────────────┐
│                    Pala Platform Core                    │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐ │
│  │  MCP Server  │◄──►│Storage Agent │   │ Metadata   │ │
│  │  (WS Hub)    │    │ (Unified DB) │   │ Extractor  │ │
│  └──────────────┘    └──────────────┘   └────────────┘ │
│         ▲                    ▲                  ▲        │
└─────────┼────────────────────┼──────────────────┼────────┘
          │                    │                  │
          │                    │                  │
┌─────────▼────────┐  ┌────────▼──────┐  ┌───────▼────────┐
│   OCR Web App    │  │ Transcription │  │  Doc Convert   │
│  (own logic/DB)  │  │  (own logic)  │  │  (own logic)   │
│  Calls:          │  │  Calls:       │  │  Calls:        │
│  store_extraction│  │  store_extract│  │  store_extract │
└──────────────────┘  └───────────────┘  └────────────────┘
```

## Project Structure

```
pala-platform/
├── apps/
│   ├── mobile/     (future mobile client)
│   └── web/        (React dashboard for monitoring MCP + agents)
├── packages/
│   ├── mcp-server/                   (Core: MCP Server)
│   ├── PalaAgents/
│   │   ├── metadata-extraction-agent/(Core: Claude AI metadata extraction)
│   │   └── storage-agent/            (Core: Unified database layer)
│   ├── agents/
│   │   └── sample-agent/             (Example: echo, sum tools)
│   ├── processors/
│   │   └── OCR_metadata_extraction/  (Example: External OCR web app)
│   ├── storage/                      (Persistence utilities)
│   ├── enrichment/                   (AI enrichment services)
│   └── shared/                       (Shared types/utilities)
├── docs/           (architecture, guides)
├── scripts/        (build, deploy scripts)
├── tests/          (integration tests)
├── start-dev.sh    (one-command startup for core services)
└── turbo.json      (monorepo config)
```

**Note:** `packages/processors/OCR_metadata_extraction` is an example of an external web app that uses Pala Platform. It has its own business logic and calls `storage-agent` to persist data.

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
| `PORT` | MCP server WebSocket port | `4000` |
| `MCP_JWT_SECRET` | Enable JWT auth (leave unset for disabled) | `unset` |
| `MCP_AGENT_TOKEN` | Agent auth token (set if server has auth enabled) | `unset` |
| `MCP_SERVER_URL` | Server URL for agent connection | `ws://localhost:4000` |
| `NEXT_PUBLIC_MCP_SERVER_URL` | Server URL for web dashboard | `ws://localhost:4000` |
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
| Port 4000 already in use | Change PORT env var or kill process with `lsof -i :4000` |
| Agent won't connect | Check server URL with `MCP_SERVER_URL=ws://127.0.0.1:4000` |
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
    async with websockets.connect('ws://localhost:4000') as ws:
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

3. **Start agent**: `python agent.py` (will auto-connect to ws://localhost:4000)

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

- **[Getting Started - Setup and Usage Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)** - Complete setup, troubleshooting, and usage
- **[packages/mcp-server/README.md](packages/mcp-server/README.md)** - Server implementation details
- **[packages/agents/sample-agent/README.md](packages/agents/sample-agent/README.md)** - Sample agent guide
- **[packages/PalaAgents/metadata-extraction-agent/README.md](packages/PalaAgents/metadata-extraction-agent/README.md)** - Metadata extraction agent guide
- **[apps/web/README.md](apps/web/README.md)** - Dashboard implementation

## Contributing

- Follow the project structure and conventions
- Write tests for new features
- Update relevant READMEs
- Submit pull requests with clear descriptions

## License

TBD
