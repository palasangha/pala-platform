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
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

import aiohttp
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

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
CHAT_REFINEMENT_ENABLED = os.getenv("CHAT_REFINEMENT_ENABLED", "true").lower() in ("true", "1", "yes")
CHAT_MIN_RELEVANCE = float(os.getenv("CHAT_MIN_RELEVANCE", "0.75"))
CHAT_HARD_MIN_RELEVANCE = float(os.getenv("CHAT_HARD_MIN_RELEVANCE", "0.65"))
SEARCH_QUERY_STOPWORDS = {
    "a",
    "an",
    "are",
    "be",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "find",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "reference",
    "references",
    "related",
    "show",
    "that",
    "the",
    "there",
    "these",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
    "document",
    "documents",
    "archive",
    "content",
    "mention",
    "mentioned",
    "mentions",
    "place",
    "organization",
    "organizations",
    "person",
    "people",
    "any",
}


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
    logger.debug(f"[CHAT-AGENT] Arguments: {json.dumps(arguments, default=str)[:500]}...")
    
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
    logger.debug(f"[CHAT-AGENT] Tool result: {json.dumps(result, default=str)[:500]}...")
    return result


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group())
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
    return {}


def _normalize_terms(values: list[str]) -> list[str]:
    cleaned = []
    for value in values:
        token = re.sub(r"\s+", " ", str(value)).strip()
        if token and token.lower() not in [item.lower() for item in cleaned]:
            cleaned.append(token)
    return cleaned


def _build_search_query(refined_query: str, keywords: list[str], entities: list[str], must_include: list[str], user_message: str) -> str:
    """Build search query by combining all meaningful candidates into a rich query string."""
    # Start with the refined query (highest priority), then add entities, keywords, must_include
    candidates = [
        refined_query,
        " ".join(entities),
        " ".join(keywords),
        " ".join(must_include),
        user_message,
    ]

    all_tokens = []
    seen = set()
    
    # Collect tokens from all candidates in priority order
    for candidate in candidates:
        if not candidate:
            continue

        for raw_token in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", str(candidate)):
            normalized = raw_token.strip().lower()
            if not normalized or normalized in SEARCH_QUERY_STOPWORDS or normalized in seen:
                continue
            seen.add(normalized)
            all_tokens.append(raw_token.strip())

    # Return up to 10 tokens (increased from 6 to capture more context)
    if all_tokens:
        return " ".join(all_tokens[:10])
    
    return ""

    return user_message.strip()


async def refine_search_query(user_message: str) -> Dict[str, Any]:
    """Use Ollama to refine the user's prompt into search-friendly terms."""
    fallback_tokens = _normalize_terms([
        token for token in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", user_message)
        if len(token) > 2
    ])

    fallback = {
        "refined_query": user_message.strip(),
        "keywords": fallback_tokens,
        "entities": [],
        "must_include": fallback_tokens[:6],
        "exclude_terms": [],
        "intent": "search",
        "minimum_relevance": CHAT_MIN_RELEVANCE,
        "confidence": 0.2,
    }

    if not CHAT_REFINEMENT_ENABLED:
        logger.info(f"[CHAT-AGENT][REFINE] Refinement disabled; using fallback tokens={fallback_tokens[:8]}")
        return fallback

    prompt = """You refine archive search queries.

Return ONLY JSON with this shape:
{
  "refined_query": "short search query for archive retrieval",
    "search_query": "single concise phrase to use for retrieval",
  "keywords": ["keyword1", "keyword2"],
  "entities": ["person", "place", "organization"],
  "must_include": ["terms that should appear if possible"],
  "exclude_terms": ["irrelevant terms to ignore"],
  "intent": "search|summary|comparison|fact_lookup",
  "minimum_relevance": 0.0,
  "confidence": 0.0
}

Rules:
- Keep the refined query short, specific, and retrieval-friendly.
- Prefer exact entities, names, places, and distinctive noun phrases.
- Do not add labels like "place", "organization", or "person" to the query.
- Do not repeat the same term more than once.
- Preserve proper names, dates, places, and document-specific terms.
- If the user asks for something broad, choose the strongest archive terms.
- Never add facts that are not in the user's message.
"""

    try:
        logger.debug(f"[CHAT-AGENT][REFINE] Input query={user_message!r}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"{prompt}\n\nUser query: {user_message}",
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.0, "top_p": 0.9},
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    logger.warning(f"[CHAT-AGENT] Query refinement failed with status {response.status}")
                    return fallback

                payload = await response.json()
                refined = _safe_json_loads(payload.get("response", ""))
                if not refined:
                    logger.warning("[CHAT-AGENT][REFINE] Ollama returned empty or invalid refinement JSON; using fallback")
                    return fallback

                refined_query = str(refined.get("refined_query", user_message)).strip() or user_message.strip()
                keywords = refined.get("keywords", []) if isinstance(refined.get("keywords"), list) else []
                entities = refined.get("entities", []) if isinstance(refined.get("entities"), list) else []
                must_include = refined.get("must_include", []) if isinstance(refined.get("must_include"), list) else []
                exclude_terms = refined.get("exclude_terms", []) if isinstance(refined.get("exclude_terms"), list) else []
                search_query = str(refined.get("search_query", "")).strip()
                search_query = _build_search_query(
                    search_query or refined_query,
                    _normalize_terms([str(item) for item in keywords]),
                    _normalize_terms([str(item) for item in entities]),
                    _normalize_terms([str(item) for item in must_include]),
                    user_message,
                )

                logger.info(
                    "[CHAT-AGENT][REFINE] refined_query=%r search_query=%r keywords=%s entities=%s must_include=%s confidence=%.2f min_relevance=%.2f",
                    refined_query,
                    search_query,
                    _normalize_terms([str(item) for item in keywords])[:6],
                    _normalize_terms([str(item) for item in entities])[:6],
                    _normalize_terms([str(item) for item in must_include])[:6],
                    float(refined.get("confidence", 0.0) or 0.0),
                    float(refined.get("minimum_relevance", CHAT_MIN_RELEVANCE) or CHAT_MIN_RELEVANCE),
                )

                return {
                    "refined_query": refined_query,
                    "keywords": _normalize_terms([str(item) for item in keywords]),
                    "entities": _normalize_terms([str(item) for item in entities]),
                    "must_include": _normalize_terms([str(item) for item in must_include]),
                    "exclude_terms": _normalize_terms([str(item) for item in exclude_terms]),
                    "intent": str(refined.get("intent", "search")),
                    "minimum_relevance": float(refined.get("minimum_relevance", CHAT_MIN_RELEVANCE) or CHAT_MIN_RELEVANCE),
                    "confidence": float(refined.get("confidence", 0.0) or 0.0),
                    "search_query": search_query,
                }
    except Exception as exc:
        logger.warning(f"[CHAT-AGENT] Query refinement unavailable, using fallback terms: {exc}")
        return fallback


def _extract_result_documents(search_result: Dict[str, Any]) -> list:
    # Normalize possible nested result wrappers coming from remote agents/JSON-RPC
    def _unwrap(result: Any, depth: int = 0) -> Any:
        if depth > 6 or not isinstance(result, dict):
            return result
        # If top-level contains 'documents', we're at the payload
        if 'documents' in result:
            return result
        # Otherwise, if there is a nested 'result' key, dive in
        if 'result' in result and isinstance(result['result'], dict):
            return _unwrap(result['result'], depth + 1)
        return result

    normalized = _unwrap(search_result)
    documents = normalized.get("documents", []) if isinstance(normalized, dict) else []
    if not isinstance(documents, list):
        return []
    return [doc for doc in documents if isinstance(doc, dict)]


def _filter_documents(documents: list, threshold: float) -> list:
    filtered = []
    for doc in documents:
        score = float(doc.get("relevance_score", 0.0) or 0.0)
        if score >= threshold:
            filtered.append(doc)
    filtered.sort(key=lambda item: float(item.get("relevance_score", 0.0) or 0.0), reverse=True)
    return filtered


def _build_extractive_answer(query: str, refined_query: str, documents: list, search_method: str, embedding_used: bool) -> str:
    if not documents:
        return "No relevant documents found in the archive for that query."

    lines = [
        f"Refined search query: {refined_query}",
        f"Search method: {search_method} (embeddings={'yes' if embedding_used else 'no'})",
        "Matched documents:",
    ]

    for idx, doc in enumerate(documents[:5], start=1):
        doc_id = doc.get("document_id", "unknown")
        filename = doc.get("filename", "Unknown")
        score = float(doc.get("relevance_score", 0.0) or 0.0)
        excerpt = doc.get("excerpt") or doc.get("summary") or ""
        lines.append(f"{idx}. {filename} [doc-{doc_id}] — relevance {score:.2f}")
        if excerpt:
            lines.append(f"   {excerpt[:280]}")

    logger.info(
        "[CHAT-AGENT][ANSWER] query=%r refined_query=%r search_method=%s embedding_used=%s num_documents=%d top_document=%s",
        query,
        refined_query,
        search_method,
        embedding_used,
        len(documents),
        documents[0].get("filename") if documents else None,
    )

    return "\n".join(lines)


async def call_ollama_chat(system_prompt: str, user_message: str, documents: list = None) -> str:
    """Build an extractive response from matched documents."""
    logger.info("[CHAT-AGENT] Generating extractive response from documents...")
    return _build_extractive_answer(user_message, user_message, documents or [], "semantic", True)


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
        
        logger.info(
            "[CHAT-AGENT-TOOL] Processing query=%r search_limit=%s min_confidence=%s include_file_content=%s",
            user_query,
            search_limit,
            min_confidence,
            include_files,
        )

        query_terms = [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", user_query)
            if len(token) > 2
        ]
        short_query_mode = len(query_terms) <= 2

        refinement = {
            "refined_query": user_query.strip(),
            "keywords": query_terms,
            "entities": [],
            "must_include": query_terms[:4],
            "exclude_terms": [],
            "intent": "search",
            "minimum_relevance": CHAT_MIN_RELEVANCE,
            "confidence": 1.0,
            "search_query": user_query.strip(),
        } if short_query_mode else await refine_search_query(user_query)

        if short_query_mode:
            logger.info("[CHAT-AGENT-TOOL] Short query detected; using verbatim search without refinement")
        refined_query = refinement.get("refined_query", user_query)
        effective_min_confidence = max(
            float(min_confidence or 0.0),
            float(refinement.get("minimum_relevance", CHAT_MIN_RELEVANCE) or CHAT_MIN_RELEVANCE),
            CHAT_HARD_MIN_RELEVANCE,
        )
        search_query = refinement.get("search_query") or refined_query

        logger.info(
            "[CHAT-AGENT-TOOL] Query refined: user_query=%r refined_query=%r search_query=%r threshold=%.2f refinement=%s",
            user_query,
            refined_query,
            search_query,
            effective_min_confidence,
            {k: refinement.get(k) for k in ("intent", "confidence", "minimum_relevance", "keywords", "entities", "must_include")},
        )
        
        # Step 1: Search for relevant documents
        logger.info("[CHAT-AGENT-TOOL] Step 1: Searching for relevant documents...")
        try:
            logger.debug(
                "[CHAT-AGENT-TOOL] Search payload: query=%r limit=%s min_confidence=%.2f include_original_content=%s",
                search_query,
                search_limit,
                effective_min_confidence,
                include_files,
            )
            search_result = await invoke_remote_tool(
                agent_id="storage-agent",
                tool_name="semantic_search_documents",
                arguments={
                    "query": search_query,
                    "limit": search_limit,
                    "min_confidence": effective_min_confidence,
                    "include_original_content": include_files
                }
            )
            
            if not search_result or not isinstance(search_result, dict):
                logger.error("[CHAT-AGENT-TOOL] Invalid search result format")
                search_result = {'documents': [], 'message': 'Search failed'}
            
            documents = _extract_result_documents(search_result)
            search_method = search_result.get('search_method', 'unknown')
            embedding_used = search_result.get('embedding_used', False)

            logger.info(
                "[CHAT-AGENT-TOOL] Raw search response: search_method=%s embedding_used=%s result_count=%d keys=%s",
                search_method,
                embedding_used,
                len(documents),
                sorted(list(search_result.keys())) if isinstance(search_result, dict) else [],
            )

            # Enforce strict relevance gating so weak matches do not become chat answers.
            documents = _filter_documents(documents, effective_min_confidence)
            
            logger.info(f"[CHAT-AGENT-TOOL] ✅ Search completed: {len(documents)} results found (method: {search_method})")
            
            # Log each document found
            for idx, doc in enumerate(documents, 1):
                logger.debug(
                    "[CHAT-AGENT-TOOL]   Result %d: document_id=%s filename=%s score=%.3f match_method=%s excerpt=%r",
                    idx,
                    doc.get('document_id'),
                    doc.get('filename'),
                    float(doc.get('relevance_score', 0.0) or 0.0),
                    doc.get('match_method'),
                    (doc.get('excerpt') or doc.get('summary') or '')[:180],
                )
            if not documents:
                logger.warning(
                    "[CHAT-AGENT-TOOL] No documents after gating: query=%r refined_query=%r search_query=%r threshold=%.2f search_result_message=%r",
                    user_query,
                    refined_query,
                    search_query,
                    effective_min_confidence,
                    search_result.get('message') if isinstance(search_result, dict) else None,
                )
            
        except Exception as e:
            logger.error(f"[CHAT-AGENT-TOOL] ❌ Search failed: {e}", exc_info=True)
            documents = []
            search_method = "none"
            embedding_used = False
        
        # Step 2: Build an extractive response only; no generative answer when no strong evidence exists.
        logger.info("[CHAT-AGENT-TOOL] Step 2: Building extractive response...")

        if documents:
            answer = _build_extractive_answer(
                user_query,
                refined_query,
                documents,
                search_method,
                embedding_used,
            )
            logger.info("[CHAT-AGENT-TOOL] ✅ Extractive response built")
        else:
            answer = "No relevant documents found in the archive for that query."
            logger.info(
                "[CHAT-AGENT-TOOL] No relevant documents after gating: query=%r refined_query=%r search_query=%r threshold=%.2f",
                user_query,
                refined_query,
                search_query,
                effective_min_confidence,
            )
        
        # Build final response
        result = {
            "success": True,
            "answer": answer,
            "source_documents": documents,
            "refined_query": refined_query,
            "query_refinement": refinement,
            "search_query": search_query,
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
    
    async with websockets.connect(url, additional_headers=headers if headers else None) as ws:
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
