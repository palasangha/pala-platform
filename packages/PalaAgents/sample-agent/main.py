"""
Sample Agent (Python)
---------------------
A minimal JSON-RPC over WebSocket agent that demonstrates how to talk to the
MCP server. It registers a couple of tools and responds to `tools/invoke`
requests with simple deterministic functions.

Additionally, it demonstrates a sophisticated orchestration workflow:
- process_and_store_document: Takes a file, extracts metadata via the
  metadata-extraction-agent, and stores the result via storage-agent.

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
import base64
from typing import Any, Awaitable, Callable, Dict

import websockets

# Global WebSocket connection for cross-agent communication
_ws_global = None

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


async def invoke_remote_tool(agent_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke a tool from another agent via MCP server.
    This enables cross-agent orchestration.
    """
    if _ws_global is None:
        raise RuntimeError("WebSocket connection not initialized")
    
    request_id = f"orchestration-{uuid.uuid4()}"
    request = {
        "jsonrpc": "2.0",
        "method": "tools/invoke",
        "params": {
            "agentId": agent_id,
            "toolName": tool_name,
            "arguments": arguments
        },
        "id": request_id
    }
    
    print(f"[Sample-Agent] Invoking {agent_id}.{tool_name}")
    await _ws_global.send(json.dumps(request))
    
    # Wait for response
    response = None
    async for raw in _ws_global:
        try:
            msg = json.loads(raw)
            if msg.get("id") == request_id:
                response = msg
                break
        except json.JSONDecodeError:
            continue
    
    if response is None:
        raise RuntimeError(f"No response from {agent_id}.{tool_name}")
    
    if "error" in response:
        raise RuntimeError(f"Tool error: {response['error'].get('message', 'Unknown error')}")
    
    return response.get("result", {})


async def tool_process_and_store_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestration tool: Process a file through metadata extraction and store with metadata.
    
    Workflow:
    1. Take original file (base64-encoded) and extract text via OCR
    2. Extract metadata from text using metadata-extraction-agent
    3. Store document with extracted metadata using storage-agent
    
    Fails fast: If any step fails, the pipeline stops and returns error.
    
    Input params:
    - original_file: base64-encoded file content
    - original_file_name: original filename
    - file_format: file format/extension
    - document_type: type of document (e.g., 'ocr', 'metadata', etc.)
    - created_by: who created this (default: 'sample-agent')
    - ocr_text: optional OCR-extracted text (if already extracted)
    """
    try:
        original_file_b64 = params.get("original_file")
        original_file_name = params.get("original_file_name", "document")
        file_format = params.get("file_format", "pdf")
        document_type = params.get("document_type", "ocr")
        created_by = params.get("created_by", "sample-agent")
        ocr_text = params.get("ocr_text", "")
        
        if not original_file_b64:
            raise ValueError("original_file (base64-encoded) is required")
        
        print(f"[Sample-Agent] Processing file: {original_file_name}")
        
        # Step 1: Extract metadata using metadata-extraction-agent
        # If no OCR text provided, use a placeholder indicating file was processed
        print(f"[Sample-Agent] Step 1: Extracting metadata...")
        text_for_extraction = ocr_text or f"Document: {original_file_name}\nFormat: {file_format}\n(Original file data provided as base64 binary)"
        
        try:
            metadata_result = await invoke_remote_tool(
                agent_id="metadata-extraction-agent",
                tool_name="extract_metadata",
                arguments={
                    "text": text_for_extraction,
                    "model": "ollama",
                    "output_type": "combined",
                    "document_context": "document_archive"
                }
            )
        except Exception as e:
            print(f"[Sample-Agent] Step 1 FAILED: Metadata extraction error: {e}")
            return {
                "success": False,
                "error": f"Metadata extraction failed: {str(e)}",
                "step_failed": "extract_metadata",
                "message": f"Failed to extract metadata from {original_file_name}: {str(e)}"
            }
        
        # Verify metadata extraction was successful
        if not metadata_result or not isinstance(metadata_result, dict):
            print(f"[Sample-Agent] Step 1 FAILED: Invalid metadata result")
            return {
                "success": False,
                "error": "Metadata extraction returned invalid result",
                "step_failed": "extract_metadata",
                "message": f"Invalid response from metadata extraction"
            }
        
        print(f"[Sample-Agent] Step 1 SUCCESS: Metadata extraction completed")
        
        # Step 2: Store document with extracted metadata using storage-agent
        print(f"[Sample-Agent] Step 2: Storing document with metadata...")
        try:
            store_result = await invoke_remote_tool(
                agent_id="storage-agent",
                tool_name="store_document",
                arguments={
                    "type": document_type,
                    "original_file": original_file_name,
                    "file_format": file_format,
                    "original_file_data": original_file_b64,
                    "processed_data": metadata_result,  # Store full metadata extraction result
                    "metadata": {
                        "extraction_model": metadata_result.get("extraction_metadata", {}).get("model_used", "ollama"),
                        "schema_version": metadata_result.get("schema_version", "1.0.0"),
                        "processing_time_ms": metadata_result.get("extraction_metadata", {}).get("processing_time_ms", 0),
                    },
                    "app_data": {"pipeline": "sample-agent-orchestration", "with_metadata_extraction": True},
                    "created_by": created_by
                }
            )
        except Exception as e:
            print(f"[Sample-Agent] Step 2 FAILED: Storage error: {e}")
            return {
                "success": False,
                "error": f"Document storage failed: {str(e)}",
                "step_failed": "store_document",
                "metadata_extraction": metadata_result,
                "message": f"Failed to store {original_file_name}: {str(e)}"
            }
        
        # Verify storage was successful
        if not store_result or not isinstance(store_result, dict):
            print(f"[Sample-Agent] Step 2 FAILED: Invalid storage result")
            return {
                "success": False,
                "error": "Document storage returned invalid result",
                "step_failed": "store_document",
                "metadata_extraction": metadata_result,
                "message": f"Invalid response from storage"
            }
        
        print(f"[Sample-Agent] Step 2 SUCCESS: Document stored with ID {store_result.get('document_id')}")
        
        # All steps successful
        return {
            "success": True,
            "document_id": store_result.get("document_id"),
            "metadata_extraction": metadata_result,
            "storage_result": store_result,
            "message": f"Successfully processed and stored {original_file_name} with metadata extraction"
        }
        
    except Exception as e:
        print(f"[Sample-Agent] Orchestration FAILED: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Pipeline failed: {str(e)}"
        }


TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "echo": tool_echo,
    "sum": tool_sum,
    "process_and_store_document": tool_process_and_store_document,
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
    tool_descriptions = {
        "echo": "Echo back provided text",
        "sum": "Sum a list of numbers with validation",
        "process_and_store_document": "Orchestration tool: Extract metadata from a file and store it. Chains metadata-extraction-agent and storage-agent."
    }
    
    tool_defs = []
    for name in TOOLS.keys():
        tool_defs.append(
            {
                "name": name,
                "description": tool_descriptions.get(name, f"Sample tool: {name}"),
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
    # The server sends arguments nested in params.arguments
    arguments = params.get("arguments", {})
    if name not in TOOLS:
        raise ValueError(f"Unknown tool '{name}'")
    return await TOOLS[name](arguments)


async def handle_message(ws: websockets.WebSocketClientProtocol, raw: str) -> None:
    """Handle a single incoming JSON-RPC message from the server."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        print("[Agent-DEBUG] Failed to parse JSON")
        await ws.send(make_error("Invalid JSON", None))
        return

    method = message.get("method")
    msg_id = message.get("id")

    # Ignore responses/errors from the server (they have result/error but no method)
    if not method:
        print(f"[Agent-DEBUG] Received response/non-request message: {json.dumps(message)[:100]}")
        return

    print(f"[Agent-DEBUG] Processing method: {method}")

    if method == "tools/invoke":
        try:
            result = await handle_invoke(method, message.get("params", {}))
            response = make_response(result, msg_id)
            await ws.send(response)
        except Exception as err:
            print(f"[Agent-ERROR] Error invoking tool: {err}")
            await ws.send(make_error(str(err), msg_id))
    else:
        # For any other method, acknowledge to keep things simple
        print(f"[Agent-DEBUG] Acknowledging method: {method}")
        await ws.send(make_response({"ack": method}, msg_id))


async def main() -> None:
    """Connect to the MCP server, register tools, and handle invocations."""
    global _ws_global
    
    url = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")
    agent_id = os.getenv("MCP_AGENT_ID", "sample-agent")
    agent_token = os.getenv("MCP_AGENT_TOKEN")

    # Prepare headers for auth if token is provided
    headers = {}
    if agent_token:
        headers["Authorization"] = f"Bearer {agent_token}"

    async with websockets.connect(url, additional_headers=headers if headers else None, max_size=None) as ws:
        # Store global reference for cross-agent tool invocation
        _ws_global = ws
        
        print(f"Connected to MCP server at {url} as {agent_id}")

        # Optional: send registration (server-side handling pending)
        await register_tools(ws, agent_id)

        async for raw in ws:
            await handle_message(ws, raw)


if __name__ == "__main__":
    asyncio.run(main())
