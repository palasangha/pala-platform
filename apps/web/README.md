# Pala Platform Web Dashboard

Next.js application for managing MCP agents and invoking tools.

## Features

- **Agent Discovery**: List all connected agents and their tools
- **Tool Invocation**: Execute tools with custom JSON arguments
- **Real-time Connection Status**: WebSocket connection indicator
- **Error Handling**: User-friendly error messages and timeouts

## Quick Start

```bash
# Install dependencies
pnpm install

# Development
pnpm dev

# Production build
pnpm build
pnpm start
```

## Architecture

- **useWebSocket Hook**: Manages WebSocket connection and JSON-RPC communication
- **Dashboard Component**: Main UI for agent/tool management and invocation
- **Tailwind CSS**: Responsive styling
- **TypeScript**: Full type safety

## API Integration

The web app connects to the MCP server at `ws://localhost:3000` and uses JSON-RPC 2.0 to:
- Query `agents/list` to fetch connected agents
- Query `tools/list` to fetch available tools
- Invoke `tools/invoke` with tool name, agent ID, and arguments

## Environment

Ensure the MCP server is running:

```bash
cd packages/mcp-server
npm run dev
```

And at least one agent is connected:

```bash
cd packages/agents/sample-agent
python main.py
``` Portal

Next.js-based web application for the Pala Platform.

## Features

- Document upload and management
- OCR processing interface
- Metadata viewing and editing
- User authentication
- Search and filtering
- **Job management with cancellation support** ✨

## Demo

A working demonstration of the job cancellation feature is available in the `demo/` directory.

To view the demo:

```bash
cd demo
# Open index.html in your browser or serve with a local HTTP server
python3 -m http.server 8000
```

Then navigate to http://localhost:8000

See [demo/README.md](demo/README.md) for more details.

## Tech Stack

- Next.js 14+
- React
- TypeScript
- Tailwind CSS
- shadcn/ui components

## Status

🚧 Under development
