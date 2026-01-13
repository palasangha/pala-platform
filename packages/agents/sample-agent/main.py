"""
Sample Agent (Python)
---------------------
A minimal JSON-RPC over WebSocket agent that demonstrates how to talk to the
MCP server. It registers a couple of tools and responds to `tools/invoke`
requests with simple deterministic functions.

Notes:
- This is a reference example, not production-ready.
- The MCP server currently exposes a WebSocket endpoint (default ws://localhost:3000).
- Tool registration payloads may evolve as the server's tool registry endpoint
  is finalized; this agent shows the intended shape for future integration.
"""

import asyncio
import json
import os
import uuid
from typing import Any, Awaitable, Callable, Dict

import websockets

# Simple tool implementations -------------------------------------------------

async def tool_echo(params: Dict[str, Any]) -> Dict[str, Any]:
    """Echo back provided text."""
    return {"echo": params.get("text", "")}


async def tool_sum(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sum a list of numbers with simple validation."""
    numbers = params.get("numbers", [])
    if not isinstance(numbers, list):
        raise ValueError("'numbers' must be a list")
    if not all(isinstance(n, (int, float)) for n in numbers):
        raise ValueError("all numbers must be int or float")
    return {"sum": float(sum(numbers))}

TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "echo": tool_echo,
    "sum": tool_sum,
}

# JSON-RPC helpers ------------------------------------------------------------

def make_request(method: str, params: Any | None = None, id: str | None = None) -> str:
    """Create a JSON-RPC request string."""
    payload = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if id is not None:
        payload["id"] = id
    return json.dumps(payload)


def make_response(result: Any, id: str) -> str:
    """Create a JSON-RPC success response string."""
    return json.dumps({"jsonrpc": "2.0", "result": result, "id": id})


def make_error(message: str, id: str | None = None, code: int = -32000) -> str:
    """Create a JSON-RPC error response string."""
    return json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id})


# Agent client ----------------------------------------------------------------

async def register_tools(ws: websockets.WebSocketClientProtocol, agent_id: str) -> None:
    """
    Demonstrates a hypothetical tool registration flow.
    The server-side endpoint will be wired to the registry in a future story.
    """
    tool_defs = []
    for name in TOOLS.keys():
        tool_defs.append(
            {
                "name": name,
                "description": f"Sample tool: {name}",
                "agentId": agent_id,
                "inputSchema": {
                    "type": "object",
                    "additionalProperties": True,
                },
            }
        )

    # Send registration so the server can discover this agent's tools
    await ws.send(
        make_request(
            method="tools/register",
            params={"tools": tool_defs},
            id=f"reg-{uuid.uuid4()}",
        )
    )


async def handle_invoke(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a tools/invoke request to the local tool map."""
    name = params.get("name")
    arguments = params.get("arguments", {})
    if name not in TOOLS:
        raise ValueError(f"Unknown tool '{name}'")
    return await TOOLS[name](arguments)


async def handle_message(ws: websockets.WebSocketClientProtocol, raw: str) -> None:
    """Handle a single incoming JSON-RPC message from the server."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        await ws.send(make_error("Invalid JSON", None))
        return

    method = message.get("method")
    msg_id = message.get("id")

    if method == "tools/invoke":
        try:
            result = await handle_invoke(method, message.get("params", {}))
            await ws.send(make_response(result, msg_id))
        except Exception as err:
            await ws.send(make_error(str(err), msg_id))
    else:
        # For any other method, acknowledge to keep things simple
        await ws.send(make_response({"ack": method}, msg_id))


async def main() -> None:
    """Connect to the MCP server, register tools, and handle invocations."""
    url = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")
    agent_id = os.getenv("MCP_AGENT_ID", "sample-agent")

    async with websockets.connect(url) as ws:
        print(f"Connected to MCP server at {url} as {agent_id}")

        # Optional: send registration (server-side handling pending)
        await register_tools(ws, agent_id)

        async for raw in ws:
            await handle_message(ws, raw)


if __name__ == "__main__":
    asyncio.run(main())
