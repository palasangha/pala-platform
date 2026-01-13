# Getting Started with Pala Platform

Complete guide to running the MCP server, sample agent, and web dashboard.

## Prerequisites

- Node.js 18+ (for MCP server and web app)
- Python 3.10+ (for sample agent)
- pnpm (for monorepo package management)

## 1. Install Dependencies

From the workspace root:

```bash
pnpm install
```

This installs dependencies for the entire monorepo including:
- `packages/mcp-server` - Core MCP server
- `packages/agents/sample-agent` - Python reference agent
- `apps/web` - Next.js web dashboard

## 2. Start the MCP Server

In one terminal:

```bash
cd packages/mcp-server
npm run dev
```

The server will start on `http://localhost:3000` with WebSocket at `ws://localhost:3000`.

Output:
```
{"level":30,"msg":"Starting MCP Server","port":3000,"authEnabled":false}
{"level":30,"msg":"MCP Server started successfully","port":3000}
```

## 3. Connect the Sample Agent

In another terminal:

```bash
cd packages/agents/sample-agent
python main.py
```

The agent will:
1. Connect to the MCP server
2. Self-register its tools (`echo`, `sum`)
3. Wait for invocations

## 4. Start the Web Dashboard

In a third terminal:

```bash
cd apps/web
pnpm install
npm run dev
```

The dashboard will start on `http://localhost:3000` (Next.js uses port 3000 by default; if port 3000 is taken, it will use 3001, 3002, etc.)

Open your browser to the displayed URL (usually `http://localhost:3000`).

## Using the Dashboard

1. **Connection Status**: Top-right indicator shows WebSocket connection state
2. **Connected Agents**: See all agents and their available tools
3. **Available Tools**: Browse all registered tools with descriptions
4. **Invoke Tools**:
   - Select a tool from the list
   - Enter arguments as JSON
   - Click "Invoke"
   - View results

Example tool invocations:
- `echo` with `{"message": "hello"}` → echoes the message back
- `sum` with `{"numbers": [1, 2, 3]}` → returns 6

## Environment Variables

### MCP Server

- `PORT` (default: 3000) - WebSocket server port
- `MCP_AUTH_SECRET` (optional) - Enable JWT auth; if not set, auth is disabled

Example with auth:
```bash
MCP_AUTH_SECRET="your-secret" npm run dev
```

### Sample Agent

- `MCP_AGENT_TOKEN` (optional) - JWT token for authenticated connections
- `MCP_SERVER_URL` (optional, default: `ws://localhost:3000`) - Server address

Example with auth:
```bash
MCP_AGENT_TOKEN="your-token" python main.py
```

### Web Dashboard

- `NEXT_PUBLIC_MCP_SERVER_URL` (optional, default: `ws://localhost:3000`) - Server address

## Architecture

```
┌─────────────────────────────────────────┐
│       Web Dashboard (Next.js)           │
│   - Agent discovery                     │
│   - Tool listing                        │
│   - Tool invocation UI                  │
│   - Real-time connection status         │
└──────────────┬──────────────────────────┘
               │ WebSocket JSON-RPC
               ├──────────────────────────
               ▼
┌─────────────────────────────────────────┐
│       MCP Server (Node.js)              │
│   - WebSocket transport                 │
│   - JSON-RPC 2.0 protocol               │
│   - Tool registry                       │
│   - Request tracing                     │
│   - JWT authentication (optional)       │
└──────────────┬──────────────────────────┘
               │ WebSocket JSON-RPC
      ┌────────┴────────┐
      ▼                 ▼
┌────────────────┐ ┌──────────────────┐
│ Sample Agent   │ │ Other Agents     │
│ (Python)       │ │ (Any Language)   │
│ - echo tool    │ │ - Custom tools   │
│ - sum tool     │ │ - Business logic │
└────────────────┘ └──────────────────┘
```

## Testing

### Run Server Tests

```bash
cd packages/mcp-server
npm test
```

Current test coverage: 127 tests passing
- Protocol & JSON-RPC: 36 tests
- WebSocket transport: 13 tests
- Tool registry & invocation: 43 tests
- Logging: 25 tests
- Server handlers: 7 tests
- Server orchestration: 2 tests
- Request tracing: 3 tests

### Test with cURL

While server and agent are running, test the WebSocket connection:

```bash
# In Node.js or deno:
const ws = new WebSocket('ws://localhost:3000');
ws.onopen = () => {
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    method: 'agents/list',
    params: {},
    id: 1
  }));
};
ws.onmessage = (e) => {
  console.log('Response:', JSON.parse(e.data));
};
```

## Troubleshooting

### Server fails to start
- Check port 3000 is not in use: `lsof -i :3000`
- Verify Node.js version: `node --version` (need v18+)
- Check logs for specific errors

### Agent won't connect
- Verify server is running on ws://localhost:3000
- Check Python version: `python --version` (need 3.10+)
- Verify websockets library: `pip list | grep websockets`
- Try connecting with explicit server URL:
  ```bash
  MCP_SERVER_URL="ws://127.0.0.1:3000" python main.py
  ```

### Dashboard shows "Disconnected"
- Verify server is running and accessible
- Check browser console for WebSocket errors (F12 → Console)
- Verify CORS settings if server is on different host
- Try refreshing the page

### Tools don't appear in dashboard
- Ensure agent is connected (check server logs)
- Verify agent sent tools/register message
- Check tool names and agentId match
- Try refreshing data with "Refresh Data" button

## Next Steps

1. **Modify sample agent**: Edit `packages/agents/sample-agent/main.py` to add custom tools
2. **Create new agents**: Copy sample agent pattern in your preferred language
3. **Extend server**: Add authentication, persistence, custom tool handlers
4. **Deploy**: Build web app with `npm run build`; containerize with Docker

## Architecture Documentation

See `docs/Pala Platform - Architecture & Repository Strategy.md` for:
- Detailed protocol specification
- Tool registration flow
- Authentication design
- Request tracing architecture
- Project structure and conventions
