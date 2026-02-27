#!/usr/bin/env python3
"""
Storage Agent - Document Storage with Deduplication

Exposes storage operations as MCP tools:
- store_document: Store content with automatic deduplication
- retrieve_document: Retrieve stored content by ID
- list_documents: List stored documents
- list_backends: List available storage backends
- get_stats: Get storage statistics

Uses the storage package backend with SHA-256 deduplication.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import websockets
from pathlib import Path
from typing import Dict, Any, Callable, Awaitable

# Add storage package to path
storage_path = Path(__file__).parent.parent.parent / 'storage'
sys.path.insert(0, str(storage_path))

from api.storage_api import StorageAPI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize storage API
storage_dir = storage_path / 'data'
storage_dir.mkdir(exist_ok=True)

db_path = storage_dir / 'pala_storage.db'
content_path = storage_dir / 'content'

storage_api = StorageAPI(
    db_path=str(db_path),
    backends_config={
        'local': {
            'enabled': True,
            'default': True,
            'config': {
                'base_path': str(content_path)
            }
        }
    }
)

logger.info(f"Storage initialized - DB: {db_path}, Content: {content_path}")


# Tool implementations
async def tool_store_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store document with automatic deduplication
    
    Params:
    - job_id: Job identifier
    - file_index: File index in job
    - ocr_text: Extracted text content
    - content_type: Type of content (default: document)
    - original_file_path: Original file path
    - enriched_metadata: Metadata from extraction
    - document_metadata: Additional document metadata
    - backend: Storage backend name (optional)
    - signature: Digital signature (optional)
    - tags: Document tags (optional)
    """
    try:
        ocr_text = params.get('ocr_text', params.get('content', ''))
        if not ocr_text:
            raise ValueError('ocr_text or content is required')
        
        content_bytes = ocr_text.encode('utf-8')
        
        # Calculate hash for deduplication check
        import hashlib
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        existing = storage_api._find_by_hash(file_hash)
        
        # Store content
        stored = await storage_api.store_content(
            content=content_bytes,
            content_type=params.get('content_type', 'document'),
            metadata={
                'job_id': params.get('job_id'),
                'file_index': params.get('file_index', 0),
                'original_file_path': params.get('original_file_path'),
                'enriched_metadata': params.get('enriched_metadata', {}),
                'document_metadata': params.get('document_metadata', {}),
            },
            signature=params.get('signature'),
            tags=params.get('tags', {}),
            backend_name=params.get('backend')
        )
        
        is_duplicate = existing is not None
        
        return {
            'content_id': stored.content_id,
            'provider': 'pala-storage-provider',
            'backend': stored.backend_name,
            'path': stored.backend_location,
            'version': stored.version,
            'file_hash': stored.file_hash,
            'size': stored.file_size,
            'created_at': stored.created_at,
            'deduplication': is_duplicate,
            'message': 'Content already exists (deduplicated)' if is_duplicate else 'Content stored successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in store_document: {e}", exc_info=True)
        raise


async def tool_retrieve_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve document by content ID
    
    Params:
    - content_id: Content identifier
    """
    try:
        content_id = params.get('content_id')
        if not content_id:
            raise ValueError('content_id is required')
        
        content = await storage_api.read_content(content_id)
        metadata = storage_api.get_content_metadata(content_id)
        
        if not metadata:
            raise ValueError(f'Content not found: {content_id}')
        
        return {
            'content': content.decode('utf-8') if isinstance(content, bytes) else content,
            'metadata': metadata.metadata,
            'content_id': metadata.content_id,
            'backend': metadata.backend_name,
            'version': metadata.version,
            'file_hash': metadata.file_hash,
            'created_at': metadata.created_at
        }
        
    except Exception as e:
        logger.error(f"Error in retrieve_document: {e}", exc_info=True)
        raise


async def tool_list_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List stored documents
    
    Params:
    - content_type: Filter by content type (optional)
    - backend: Filter by backend (optional)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        items = storage_api.list_content(
            content_type=params.get('content_type'),
            backend_name=params.get('backend'),
            limit=params.get('limit', 100),
            offset=params.get('offset', 0)
        )
        
        return {
            'items': [
                {
                    'content_id': item.content_id,
                    'backend': item.backend_name,
                    'content_type': item.content_type,
                    'file_hash': item.file_hash[:16] + '...',
                    'size': item.file_size,
                    'version': item.version,
                    'created_at': item.created_at,
                    'metadata': item.metadata
                }
                for item in items
            ],
            'count': len(items)
        }
        
    except Exception as e:
        logger.error(f"Error in list_documents: {e}", exc_info=True)
        raise


async def tool_list_backends(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List available storage backends
    
    No parameters required
    """
    try:
        backends = []
        
        for backend_name in storage_api.backend_manager.backends.keys():
            backend = storage_api.backend_manager.backends[backend_name]
            is_default = backend_name == storage_api.backend_manager.default_backend_name
            
            backends.append({
                'name': backend_name,
                'type': backend.__class__.__name__,
                'is_default': is_default,
                'enabled': True
            })
        
        return {
            'backends': backends,
            'default_backend': storage_api.backend_manager.default_backend_name
        }
        
    except Exception as e:
        logger.error(f"Error in list_backends: {e}", exc_info=True)
        raise


async def tool_get_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get storage statistics
    
    No parameters required
    """
    try:
        stats = await storage_api.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_stats: {e}", exc_info=True)
        raise


# Tool registry
TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "store_document": tool_store_document,
    "retrieve_document": tool_retrieve_document,
    "list_documents": tool_list_documents,
    "list_backends": tool_list_backends,
    "get_stats": tool_get_stats,
}


# JSON-RPC helpers
def make_request(method: str, params: Any = None, id: str = None) -> str:
    """Create JSON-RPC request"""
    payload = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if id is not None:
        payload["id"] = id
    return json.dumps(payload)


def make_response(result: Any, id: str) -> str:
    """Create JSON-RPC response"""
    return json.dumps({"jsonrpc": "2.0", "result": result, "id": id})


def make_error(message: str, id: str = None, code: int = -32000) -> str:
    """Create JSON-RPC error"""
    return json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id})


# Agent client
async def register_tools(ws: websockets.WebSocketClientProtocol, agent_id: str) -> None:
    """Register storage tools with MCP server"""
    tool_defs = [
        {
            "name": "store_document",
            "description": "Store document content with automatic SHA-256 deduplication",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "file_index": {"type": "number"},
                    "ocr_text": {"type": "string"},
                    "content_type": {"type": "string"},
                    "original_file_path": {"type": "string"},
                    "enriched_metadata": {"type": "object"},
                    "document_metadata": {"type": "object"},
                    "backend": {"type": "string"},
                    "signature": {"type": "string"},
                    "tags": {"type": "object"}
                },
                "required": ["ocr_text"]
            }
        },
        {
            "name": "retrieve_document",
            "description": "Retrieve stored document by content ID",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content_id": {"type": "string"}
                },
                "required": ["content_id"]
            }
        },
        {
            "name": "list_documents",
            "description": "List stored documents with optional filters",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content_type": {"type": "string"},
                    "backend": {"type": "string"},
                    "limit": {"type": "number"},
                    "offset": {"type": "number"}
                }
            }
        },
        {
            "name": "list_backends",
            "description": "List available storage backends",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object"
            }
        },
        {
            "name": "get_stats",
            "description": "Get storage statistics across all backends",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object"
            }
        }
    ]
    
    await ws.send(
        make_request(
            method="tools/register",
            params={"tools": tool_defs},
            id=f"reg-{uuid.uuid4()}"
        )
    )
    logger.info(f"Registered {len(tool_defs)} storage tools")


async def handle_invoke(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool invocation"""
    name = params.get("name")
    arguments = params.get("arguments", {})
    
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    
    logger.info(f"Invoking tool: {name}")
    result = await TOOLS[name](arguments)
    return {"result": result}


async def run_agent():
    """Main agent loop"""
    server_url = os.getenv("MCP_SERVER_URL", "ws://localhost:3000")
    agent_id = os.getenv("MCP_AGENT_ID", "storage-agent")
    
    logger.info(f"Starting Storage Agent - connecting to {server_url}")
    
    while True:
        try:
            async with websockets.connect(server_url) as ws:
                logger.info(f"Connected to MCP server as {agent_id}")
                
                # Register tools
                await register_tools(ws, agent_id)
                
                # Message loop
                async for message in ws:
                    try:
                        msg = json.loads(message)
                        method = msg.get("method")
                        params = msg.get("params", {})
                        msg_id = msg.get("id")
                        
                        if method == "tools/invoke":
                            result = await handle_invoke(method, params)
                            await ws.send(make_response(result, msg_id))
                        else:
                            logger.warning(f"Unknown method: {method}")
                            
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
                        if msg_id:
                            await ws.send(make_error(str(e), msg_id))
                            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed, reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_agent())
