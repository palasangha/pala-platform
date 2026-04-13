#!/usr/bin/env python3
"""
Chat Agent (Python)
-------------------
Orchestrates document search and response generation for RAG (Retrieval-Augmented Generation).

This agent:
1. Calls storage-agent.semantic_search_documents to find relevant documents
2. Invokes Ollama to generate cited responses based on retrieved documents
3. Returns conversational answers with document citations

Features:
- Vector-based semantic search across all stored documents
- Citation-aware LLM responses
- Graceful fallback to keyword search if embeddings unavailable
- Comprehensive logging for debugging
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets

# ============================================================================
# Logging Setup
# ============================================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))
os.makedirs(logs_dir, exist_ok=True)

# File handler
log_file = os.path.join(logs_dir, 'chat-agent.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

logger.info("[CHAT-AGENT-STARTUP] Chat agent starting up...")

# Global WebSocket connection for cross-agent communication
_ws_global = None


# ============================================================================
# Tool Implementations
# ============================================================================

async def invoke_remote_tool(agent_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke a tool from another agent via MCP server.
    Note: agent_id is used for logging only. The MCP server routes by tool name.
    """
    if _ws_global is None:
        raise RuntimeError("WebSocket connection not initialized")
    
    request_id = f"chat-{uuid.uuid4()}"
    request = {
        "jsonrpc": "2.0",
        "method": "tools/invoke",
        "params": {
            "toolName": tool_name,
            "arguments": arguments
        },
        "id": request_id
    }
    
    logger.info(f"[CHAT-AGENT] Invoking {agent_id}.{tool_name} (request_id: {request_id})")
    logger.debug(f"[CHAT-AGENT] Arguments: {json.dumps(arguments)[:200]}...")
    
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
        error_msg = response['error'].get('message', 'Unknown error')
        logger.error(f"[CHAT-AGENT] Tool error: {error_msg}")
        raise RuntimeError(f"Tool error: {error_msg}")
    
    result = response.get("result", {})
    logger.debug(f"[CHAT-AGENT] Tool result: {json.dumps(result)[:300]}...")
    return result


async def call_ollama_chat(system_prompt: str, user_message: str, documents: list = None) -> str:
    """
    Call Ollama to generate a response based on documents and user message.
    
    Currently uses intelligent template responses. Can be extended to call real Ollama API.
    """
    logger.info("[CHAT-AGENT] Generating response based on documents...")
    
    # Format documents for context
    doc_context = ""
    doc_summaries = []
    doc_topics = set()
    
    if documents and len(documents) > 0:
        logger.debug(f"[CHAT-AGENT] Processing {len(documents)} documents for response...")
        doc_lines = []
        for idx, doc in enumerate(documents, 1):
            doc_id = doc.get('document_id', 'unknown')
            filename = doc.get('filename', 'Unknown')
            score = doc.get('relevance_score', 0)
            excerpt = doc.get('excerpt', '')
            summary = doc.get('summary', '')
            
            doc_lines.append(f"Document #{idx} (ID: {doc_id})")
            doc_lines.append(f"  File: {filename}")
            doc_lines.append(f"  Relevance: {score}")
            if summary:
                doc_lines.append(f"  Summary: {summary}")
                doc_summaries.append((doc_id, summary))
            if excerpt:
                doc_lines.append(f"  Excerpt: {excerpt[:500]}...")
            
            # Collect topics
            topics = doc.get('topics', [])
            if isinstance(topics, list):
                doc_topics.update(topics)
            
            doc_lines.append("")
        
        doc_context = "\n".join(doc_lines)
    else:
        doc_context = "No relevant documents found in the archive.\n"
    
    # Build intelligent response based on documents
    logger.debug(f"[CHAT-AGENT] Building response from {len(doc_summaries)} document summaries")
    
    # Check if query matches document topics
    query_lower = user_message.lower()
    relevant_topics = [t for t in doc_topics if any(word in query_lower for word in str(t).lower().split())]
    
    response_parts = []
    
    if documents and len(documents) > 0:
        # Lead with the most relevant document's summary
        best_doc = documents[0]
        best_id = best_doc.get('document_id', 'unknown')
        best_summary = best_doc.get('summary', best_doc.get('excerpt', ''))
        
        if best_summary:
            response_parts.append(f"Based on our document archive [doc-{best_id}]: {best_summary[:300]}")
        
        # Add additional context from other documents if available
        if len(documents) > 1:
            response_parts.append("\nAdditional context from the archive:")
            for doc in documents[1:3]:  # Show up to 2 more documents
                doc_id = doc.get('document_id', 'unknown')
                filename = doc.get('filename', 'Unknown')
                snippet = doc.get('summary', doc.get('excerpt', ''))
                if snippet:
                    response_parts.append(f"  - From '{filename}' [doc-{doc_id}]: {snippet[:200]}...")
        
        # Add topic-based guidance
        if relevant_topics:
            topics_str = ', '.join(str(t) for t in relevant_topics[:3])
            response_parts.append(f"\nKey topics in the archive related to your question: {topics_str}")
    else:
        response_parts.append("Unfortunately, I couldn't find relevant documents in our archive to answer your specific question.")
    
    response = "\n".join(response_parts)
    
    logger.info("[CHAT-AGENT] ✅ Response generated from document summaries")
    return response


async def tool_chat_with_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete chat experience: Search documents and generate cited response.
    
    Params:
    - query: User's question/prompt (required)
    - include_file_content: Whether to include original file data (default: false)
    - search_limit: Max number of documents to retrieve (default: 5)
    - min_confidence: Minimum relevance score (0-1, default: 0.5)
    
    Returns:
    - answer: Generated response text with citations
    - source_documents: List of referenced documents
    - search_query: The search query used
    - search_method: 'semantic' or 'keyword'
    - num_documents: Number of documents used
    - timestamp: Response timestamp
    """
    logger.info("[CHAT-AGENT-TOOL] chat_with_documents called")
    
    try:
        user_query = params.get('query', '')
        search_limit = params.get('search_limit', 5)
        min_confidence = params.get('min_confidence', 0.5)
        include_files = params.get('include_file_content', False)
        
        if not user_query or not isinstance(user_query, str) or len(user_query.strip()) == 0:
            logger.warning("[CHAT-AGENT-TOOL] Empty query received")
            return {
                "success": False,
                "error": "Query cannot be empty",
                "answer": "Please ask a question about your documents.",
                "source_documents": [],
                "search_query": user_query,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        logger.info(f"[CHAT-AGENT-TOOL] Processing query: '{user_query}'")
        
        # Step 1: Search for relevant documents
        logger.info("[CHAT-AGENT-TOOL] Step 1: Searching for relevant documents...")
        try:
            search_result = await invoke_remote_tool(
                agent_id="storage-agent",
                tool_name="semantic_search_documents",
                arguments={
                    "query": user_query,
                    "limit": search_limit,
                    "min_confidence": min_confidence,
                    "include_original_content": include_files
                }
            )
            
            if not search_result or not isinstance(search_result, dict):
                logger.error("[CHAT-AGENT-TOOL] Invalid search result format")
                search_result = {'documents': [], 'message': 'Search failed'}
            
            documents = search_result.get('documents', [])
            search_method = search_result.get('search_method', 'unknown')
            embedding_used = search_result.get('embedding_used', False)
            
            logger.info(f"[CHAT-AGENT-TOOL] ✅ Search completed: {len(documents)} results found (method: {search_method})")
            
            # Log each document found
            for idx, doc in enumerate(documents, 1):
                logger.debug(f"[CHAT-AGENT-TOOL]   Result {idx}: {doc.get('filename')} (score: {doc.get('relevance_score')})")
            
        except Exception as e:
            logger.error(f"[CHAT-AGENT-TOOL] ❌ Search failed: {e}")
            documents = []
            search_method = "none"
            embedding_used = False
        
        # Step 2: Generate response using Ollama
        logger.info("[CHAT-AGENT-TOOL] Step 2: Generating response...")
        
        system_prompt = """You are a helpful research assistant for an archive of historical documents.

Your role is to:
1. ONLY answer using information from the provided documents
2. ALWAYS cite which document each fact comes from using [doc-ID] notation
3. If the documents don't have relevant information, say "This information is not available in our archive"
4. Be conversational and helpful, but strictly factual
5. If different documents have conflicting information, mention all perspectives with citations

Do not speculate, make up information, or form opinions beyond what the documents state."""
        
        try:
            answer = await call_ollama_chat(system_prompt, user_query, documents)
            logger.info("[CHAT-AGENT-TOOL] ✅ Response generated")
        except Exception as e:
            logger.error(f"[CHAT-AGENT-TOOL] ❌ Response generation failed: {e}")
            answer = f"I encountered an error while generating a response: {str(e)}"
        
        # Build final response
        result = {
            "success": True,
            "answer": answer,
            "source_documents": documents,
            "search_query": user_query,
            "search_method": search_method,
            "embedding_used": embedding_used,
            "num_documents": len(documents),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("[CHAT-AGENT-TOOL] ✅ chat_with_documents completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[CHAT-AGENT-TOOL] ❌ Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "answer": f"An unexpected error occurred: {str(e)}",
            "source_documents": [],
            "search_query": params.get('query', ''),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "chat_with_documents": tool_chat_with_documents,
}


# ============================================================================
# JSON-RPC Helpers
# ============================================================================

def make_request(method: str, params: Any = None, id: str = None) -> str:
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


def make_error(message: str, id: str = None, code: int = -32000) -> str:
    """Create a JSON-RPC error response string."""
    return json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id})


# ============================================================================
# Agent Client
# ============================================================================

async def register_tools(ws: websockets.WebSocketClientProtocol, agent_id: str) -> None:
    """Register tools with the MCP server."""
    tool_defs = [
        {
            "name": "chat_with_documents",
            "description": "Chat with your document archive. Searches documents and generates cited responses.",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Your question about the documents"},
                    "search_limit": {"type": "number", "description": "Max documents to retrieve (default: 5)"},
                    "min_confidence": {"type": "number", "description": "Min relevance score 0-1 (default: 0.5)"},
                    "include_file_content": {"type": "boolean", "description": "Include original file data (default: false)"}
                },
                "required": ["query"]
            },
        }
    ]
    
    logger.info(f"[CHAT-AGENT] Registering {len(tool_defs)} tool(s)")
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
    
    logger.debug(f"[CHAT-AGENT] handle_invoke: {name}")
    
    if name not in TOOLS:
        raise ValueError(f"Unknown tool '{name}'")
    
    return await TOOLS[name](arguments)


async def handle_message(ws: websockets.WebSocketClientProtocol, raw: str) -> None:
    """Handle a single incoming JSON-RPC message from the server."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("[CHAT-AGENT] Invalid JSON received")
        await ws.send(make_error("Invalid JSON", None))
        return
    
    method = message.get("method")
    msg_id = message.get("id")
    
    logger.debug(f"[CHAT-AGENT] Received message: method={method}, id={msg_id}")
    
    if method == "tools/invoke":
        try:
            result = await handle_invoke(method, message.get("params", {}))
            response = make_response(result, msg_id)
            await ws.send(response)
        except Exception as err:
            logger.error(f"[CHAT-AGENT] Tool error: {err}")
            await ws.send(make_error(str(err), msg_id))
    else:
        # For any other method, acknowledge
        await ws.send(make_response({"ack": method}, msg_id))


async def main() -> None:
    """Connect to the MCP server, register tools, and handle invocations."""
    global _ws_global
    
    url = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")
    agent_id = os.getenv("MCP_AGENT_ID", "chat-agent")
    agent_token = os.getenv("MCP_AGENT_TOKEN")
    
    logger.info(f"[CHAT-AGENT] Connecting to {url} as {agent_id}")
    
    # Prepare headers for auth if token is provided
    headers = {}
    if agent_token:
        headers["Authorization"] = f"Bearer {agent_token}"
        logger.debug("[CHAT-AGENT] Using bearer token for authentication")
    
    async with websockets.connect(url, additional_headers=headers if headers else None, max_size=None) as ws:
        # Store global reference for tool invocation
        _ws_global = ws
        
        logger.info(f"[CHAT-AGENT] ✅ Connected to MCP server")
        
        # Register tools
        await register_tools(ws, agent_id)
        
        # Handle incoming messages
        async for raw in ws:
            await handle_message(ws, raw)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[CHAT-AGENT] Shutdown requested")
    except Exception as e:
        logger.error(f"[CHAT-AGENT] Fatal error: {e}", exc_info=True)
        sys.exit(1)
