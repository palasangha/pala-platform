# Pala Platform

Centralized orchestration platform for AI agents using the Model Context Protocol (MCP).

## Quick Start

To get the MCP server, sample agent, and web dashboard running in minutes:

```bash
# 1. Install dependencies
pnpm install

# 2. Terminal 1 - Start MCP server
cd packages/mcp-server && npm run dev

# 3. Terminal 2 - Connect sample agent
cd packages/agents/sample-agent && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python main.py

# 4. Terminal 3 - Start web dashboard
cd apps/web && npm run dev
```

Then open your browser to `http://localhost:3000` and start invoking tools!

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
│   │   ├── sample-agent/  (Python reference implementation)
│   │   └── ...other agents
│   ├── mcp-server/        (core MCP server)
│   ├── processors/        (data processing pipeline)
│   ├── storage/           (persistence layer)
│   ├── enrichment/        (AI enrichment agents)
│   └── shared/            (shared types/utilities)
├── docs/           (architecture, guides)
├── scripts/        (build, deploy scripts)
├── tests/          (integration tests)
├── GETTING_STARTED.md
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

### Development Mode
```bash
cd packages/mcp-server
npm run dev       # Auto-reload on changes
```

### Building
```bash
npm run build     # Build all packages
npm run clean     # Clean dist/coverage
```

## Documentation

- **[Getting Started - Setup and Usage Guide](docs/Getting%20Started%20-%20Setup%20and%20Usage%20Guide.md)** - Complete setup, troubleshooting, and usage
- **[Quick Reference - Developer Cheat Sheet](docs/Quick%20Reference%20-%20Developer%20Cheat%20Sheet.md)** - TL;DR commands and API reference
- **[Slice 01 - MVP Foundation Completion Summary](docs/Slice%2001%20-%20MVP%20Foundation%20Completion%20Summary.md)** - Implementation details and test coverage
- **[Pala Platform - Architecture & Repository Strategy](docs/Pala%20Platform%20-%20Architecture%20%26%20Repository%20Strategy.md)** - Overall architecture
- **[Pala Platform - Project Management Guide](docs/Pala%20Platform%20-%20Project%20Management%20Guide.md)** - Development workflow
- **[packages/mcp-server/README.md](packages/mcp-server/README.md)** - Server details
- **[packages/agents/sample-agent/README.md](packages/agents/sample-agent/README.md)** - Agent guide
- **[apps/web/README.md](apps/web/README.md)** - Dashboard details

## Contributing

See [docs/Pala Platform - Project Management Guide.md](docs/Pala%20Platform%20-%20Project%20Management%20Guide.md) for:
- Development workflow
- Commit conventions
- Story/epic structure
- Code review process

## License

TBD
