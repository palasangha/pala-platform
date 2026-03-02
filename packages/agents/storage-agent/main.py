#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

import websockets

from metadata_db import MetadataDB
from providers import (
    build_provider_catalog,
    build_provider_instances,
    resolve_provider_id_from_params,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

agent_dir = Path(__file__).parent
storage_dir = agent_dir / 'data'
storage_dir.mkdir(exist_ok=True)

metadata_db = MetadataDB(str(storage_dir / 'pala_storage_metadata.db'))
providers = build_provider_instances(storage_dir)
provider_catalog = build_provider_catalog(providers)

default_provider_id = next(
    (provider_id for provider_id, info in provider_catalog.items() if info.get('is_default')),
    'local-provider',
)


def _resolve_provider_id(params: Dict[str, Any]) -> str:
    return resolve_provider_id_from_params(
        params=params,
        catalog=provider_catalog,
        default_provider_id=default_provider_id,
    )


def _backend_name(provider_id: str) -> str:
    return provider_catalog.get(provider_id, {}).get('backend_name', provider_id)


def _build_content_id(file_hash: str) -> str:
    ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f"content-{ts}-{abs(hash(file_hash)) % 1000000:06d}"


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
        file_hash = metadata_db.calculate_hash(content_bytes)
        existing = metadata_db.find_by_hash(file_hash)

        if existing:
            return {
                'content_id': existing.content_id,
                'provider': 'pala-storage-provider',
                'storage_provider': existing.provider_id,
                'backend': _backend_name(existing.provider_id),
                'path': existing.storage_location,
                'version': existing.version,
                'file_hash': existing.file_hash,
                'size': existing.file_size,
                'created_at': existing.created_at,
                'deduplication': True,
                'message': 'Content already exists (deduplicated)'
            }

        provider_id = _resolve_provider_id(params)
        provider = providers.get(provider_id)
        if not provider:
            raise ValueError(f'Provider not available: {provider_id}')

        content_id = _build_content_id(file_hash)
        content_type = params.get('content_type', 'document')
        timestamp = datetime.now(timezone.utc).isoformat()

        document_metadata = {
            'job_id': params.get('job_id'),
            'file_index': params.get('file_index', 0),
            'original_file_path': params.get('original_file_path'),
            'enriched_metadata': params.get('enriched_metadata', {}),
            'document_metadata': params.get('document_metadata', {}),
        }

        location = await provider.write(
            content_id=content_id,
            content=content_bytes,
            metadata={
                'content_type': content_type,
                'created_at': timestamp,
                'file_hash': file_hash,
                'metadata': document_metadata,
            }
        )

        stored = metadata_db.insert(
            content_id=content_id,
            content_type=content_type,
            file_hash=file_hash,
            file_size=len(content_bytes),
            provider_id=provider_id,
            storage_location=location,
            metadata=document_metadata,
            signature=params.get('signature'),
            tags=params.get('tags', {}),
        )

        return {
            'content_id': stored.content_id,
            'provider': 'pala-storage-provider',
            'storage_provider': stored.provider_id,
            'backend': _backend_name(stored.provider_id),
            'path': stored.storage_location,
            'version': stored.version,
            'file_hash': stored.file_hash,
            'size': stored.file_size,
            'created_at': stored.created_at,
            'deduplication': False,
            'message': 'Content stored successfully'
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

        metadata = metadata_db.get_metadata(content_id)
        if not metadata:
            raise ValueError(f'Content not found: {content_id}')

        provider = providers.get(metadata.provider_id)
        if not provider:
            raise ValueError(f'Provider not available: {metadata.provider_id}')

        content = await provider.read(content_id, metadata.storage_location)

        return {
            'content': content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else str(content),
            'metadata': metadata.metadata,
            'content_id': metadata.content_id,
            'backend': _backend_name(metadata.provider_id),
            'storage_provider': metadata.provider_id,
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
        provider_filter = None
        if params.get('provider') or params.get('provider_id') or params.get('backend'):
            provider_filter = _resolve_provider_id(params)

        items = metadata_db.list_all(
            content_type=params.get('content_type'),
            provider_id=provider_filter,
            limit=int(params.get('limit', 100)),
            offset=int(params.get('offset', 0))
        )

        return {
            'items': [
                {
                    'content_id': item.content_id,
                    'backend': _backend_name(item.provider_id),
                    'storage_provider': item.provider_id,
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
        for provider_id, info in provider_catalog.items():
            backends.append({
                'name': info['backend_name'],
                'type': info['provider_type'],
                'is_default': info.get('is_default', False),
                'enabled': info.get('enabled', False),
                'provider_id': provider_id,
            })

        return {
            'backends': backends,
            'default_backend': _backend_name(default_provider_id)
        }

    except Exception as e:
        logger.error(f"Error in list_backends: {e}", exc_info=True)
        raise


async def tool_list_storage_providers(params: Dict[str, Any]) -> Dict[str, Any]:
    """List logical storage providers and whether they are enabled in this deployment."""
    try:
        return {
            "providers": list(provider_catalog.values()),
            "default_backend": _backend_name(default_provider_id),
            "default_provider": default_provider_id,
        }
    except Exception as e:
        logger.error(f"Error in list_storage_providers: {e}", exc_info=True)
        raise


async def tool_get_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get storage statistics
    
    No parameters required
    """
    try:
        metadata_stats = metadata_db.get_stats()
        provider_stats: Dict[str, Any] = {}
        for provider_id, provider in providers.items():
            try:
                provider_stats[provider_id] = await provider.get_stats()
            except Exception as provider_error:
                provider_stats[provider_id] = {'error': str(provider_error)}

        return {
            'metadata': metadata_stats,
            'providers': provider_stats,
            'total_count': metadata_stats.get('total_count', 0),
            'total_size': metadata_stats.get('total_size', 0),
            'by_type': metadata_stats.get('by_type', {}),
            'by_backend': metadata_stats.get('by_provider', {}),
        }

    except Exception as e:
        logger.error(f"Error in get_stats: {e}", exc_info=True)
        raise


async def tool_delete_all_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete all documents from metadata DB and provider storage.
    """
    del params
    try:
        all_items = metadata_db.list_all(limit=1_000_000, offset=0)
        for item in all_items:
            provider = providers.get(item.provider_id)
            if not provider:
                continue
            try:
                await provider.delete(item.content_id, item.storage_location)
            except Exception as provider_error:
                logger.warning(f"Failed to delete blob for {item.content_id}: {provider_error}")

        deleted_count = metadata_db.delete_all()
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": "All documents deleted.",
        }
    except Exception as e:
        logger.error(f"Error deleting all documents: {e}", exc_info=True)
        raise


async def tool_answer_content_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Answer a natural-language query using stored documents with citations.

    Params:
    - query: User question (required)
    - limit: Max references to return (default: 5)
    - include_web: Whether to include separate web/OpenAI section (default: True)
    """
    try:
        query = str(params.get('query', '')).strip()
        if not query:
            raise ValueError('query is required')

        limit = int(params.get('limit', 5))
        include_web = bool(params.get('include_web', True))

        tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9]+", query)
            if len(token) > 2
        ]

        provider_filter = None
        if params.get('provider') or params.get('provider_id') or params.get('backend'):
            provider_filter = _resolve_provider_id(params)

        items = metadata_db.list_all(provider_id=provider_filter, limit=500, offset=0)
        ranked: list[Dict[str, Any]] = []

        for item in items:
            metadata = item.metadata or {}
            document_meta = metadata.get('document_metadata', {}) if isinstance(metadata, dict) else {}
            content_meta = metadata.get('enriched_metadata', {}) if isinstance(metadata, dict) else {}

            title = (
                document_meta.get('title')
                or metadata.get('original_file_path')
                or item.content_id
            )

            summary = content_meta.get('summary') if isinstance(content_meta, dict) else ''

            try:
                provider = providers.get(item.provider_id)
                if not provider:
                    continue
                raw_content = await provider.read(item.content_id, item.storage_location)
                content_text = raw_content.decode('utf-8', errors='ignore') if isinstance(raw_content, bytes) else str(raw_content)
            except Exception:
                content_text = ''

            haystack = f"{title}\n{summary}\n{content_text}".lower()

            score = 0
            if tokens:
                for token in tokens:
                    score += haystack.count(token)
            else:
                score = 1

            if score <= 0:
                continue

            snippet_source = content_text or str(summary or '')
            snippet = snippet_source.strip().replace('\n', ' ')
            if len(snippet) > 320:
                snippet = snippet[:320].rstrip() + '…'

            ranked.append({
                'content_id': item.content_id,
                'title': title,
                'snippet': snippet,
                'score': score,
                'created_at': item.created_at,
                'backend': _backend_name(item.provider_id),
                'storage_provider': item.provider_id,
            })

        ranked.sort(key=lambda row: (row['score'], row['created_at']), reverse=True)
        top_refs = ranked[:max(1, limit)]

        if top_refs:
            lines = []
            for index, ref in enumerate(top_refs[:3], start=1):
                lines.append(f"{ref['snippet']} [L{index}]")
            local_answer = "Based on your stored documents, here are the most relevant findings:\n\n" + "\n\n".join(lines)
        else:
            local_answer = "I could not find relevant evidence in your stored documents for that question."

        references_local = [
            {
                'id': f"L{index}",
                'source_type': 'local',
                'content_id': ref['content_id'],
                'title': ref['title'],
                'snippet': ref['snippet'],
                'score': ref['score'],
                'backend': ref['backend'],
                'storage_provider': ref['storage_provider'],
                'created_at': ref['created_at'],
            }
            for index, ref in enumerate(top_refs, start=1)
        ]

        web_section = {
            'enabled': include_web,
            'answer': '',
            'references': [],
            'note': 'OpenAI/web search can be plugged in here; currently disabled in this MVP.' if include_web else 'Web search not requested.',
        }

        return {
            'query': query,
            'answer_local': local_answer,
            'references_local': references_local,
            'web_section': web_section,
            'reference_count': len(references_local),
            'provider_filter': provider_filter or 'all',
        }
    except Exception as e:
        logger.error(f"Error in answer_content_query: {e}", exc_info=True)
        raise


# Tool registry
TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "store_document": tool_store_document,
    "retrieve_document": tool_retrieve_document,
    "list_documents": tool_list_documents,
    "list_backends": tool_list_backends,
    "list_storage_providers": tool_list_storage_providers,
    "get_stats": tool_get_stats,
    "delete_all_documents": tool_delete_all_documents,
    "answer_content_query": tool_answer_content_query,
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
                    "provider": {"type": "string"},
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
                    "provider": {"type": "string"},
                    "limit": {"type": "number"},
                    "offset": {"type": "number"}
                }
            }
        },
        {
            "name": "list_storage_providers",
            "description": "List storage providers by backend type (local/s3/gcs/azure) and enabled status",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object"
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
        },
        {
            "name": "delete_all_documents",
            "description": "Delete all stored documents and reset storage state",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object"
            }
        },
        {
            "name": "answer_content_query",
            "description": "Answer user question from stored content with local citations and optional separate web section",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "provider": {"type": "string"},
                    "backend": {"type": "string"},
                    "limit": {"type": "number"},
                    "include_web": {"type": "boolean"}
                },
                "required": ["query"]
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
