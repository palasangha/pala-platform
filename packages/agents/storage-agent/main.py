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
    Store document with unified schema and automatic deduplication
    
    Params (unified schema):
    - type: Document type (ocr, transcription, metadata, etc) - REQUIRED
    - original_file: Original file name/path - REQUIRED
    - file_format: File format (pdf, txt, json, etc) - REQUIRED
    - processed_data: The actual extracted/processed content (dict or JSON) - REQUIRED
    - metadata: Document metadata (dict) - optional
    - app_data: Application-specific data (dict) - optional
    - created_by: Creator identifier (required)
    - signature: Digital signature (optional)
    - tags: Document tags (optional)
    """
    try:
        # Validate required fields
        doc_type = params.get('type')
        original_file = params.get('original_file')
        file_format = params.get('file_format')
        processed_data = params.get('processed_data')
        created_by = params.get('created_by', 'api')
        
        if not all([doc_type, original_file, file_format, processed_data is not None]):
            raise ValueError('type, original_file, file_format, and processed_data are required')
        
        # Convert processed_data to bytes for hashing
        if isinstance(processed_data, dict):
            content_bytes = json.dumps(processed_data).encode('utf-8')
        else:
            content_bytes = str(processed_data).encode('utf-8')
        
        file_hash = metadata_db.calculate_hash(content_bytes)
        existing = metadata_db.find_by_hash(file_hash)
        
        if existing:
            return {
                'document_id': existing.document_id,
                'type': existing.type,
                'original_file': existing.original_file,
                'file_format': existing.file_format,
                'created_by': existing.created_by,
                'created_at': existing.created_at,
                'version': existing.version,
                'deduplication': True,
                'message': 'Document already exists (deduplicated)'
            }
        
        provider_id = _resolve_provider_id(params)
        provider = providers.get(provider_id)
        if not provider:
            raise ValueError(f'Provider not available: {provider_id}')
        
        # Generate unique document ID
        document_id = f"doc-{uuid.uuid4().hex[:12]}"
        
        # Write to provider
        location = await provider.write(
            content_id=document_id,
            content=content_bytes,
            metadata={
                'type': doc_type,
                'original_file': original_file,
                'file_format': file_format,
            }
        )
        
        # Store in metadata DB
        stored = metadata_db.insert(
            document_id=document_id,
            type=doc_type,
            file_hash=file_hash,
            original_file=original_file,
            file_format=file_format,
            file_size=len(content_bytes),
            processed_data=processed_data,
            metadata=params.get('metadata', {}),
            app_data=params.get('app_data', {}),
            created_by=created_by,
            provider_id=provider_id,
            storage_location=location,
            signature=params.get('signature'),
            tags=params.get('tags'),
        )
        
        return {
            'document_id': stored.document_id,
            'type': stored.type,
            'original_file': stored.original_file,
            'file_format': stored.file_format,
            'created_by': stored.created_by,
            'created_at': stored.created_at,
            'version': stored.version,
            'deduplication': False,
            'message': 'Document stored successfully'
        }
            'deduplication': False,
            'message': 'Content stored successfully'
        }

    except Exception as e:
        logger.error(f"Error in store_document: {e}", exc_info=True)
        raise


async def tool_retrieve_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve document by document ID with unified schema
    
    Params:
    - document_id: Document identifier
    """
    try:
        document_id = params.get('document_id')
        if not document_id:
            raise ValueError('document_id is required')

        metadata = metadata_db.get_metadata(document_id)
        if not metadata:
            raise ValueError(f'Document not found: {document_id}')

        provider = providers.get(metadata.provider_id)
        if not provider:
            raise ValueError(f'Provider not available: {metadata.provider_id}')

        # provider.read returns bytes, processed_data is already in metadata
        return {
            'document_id': metadata.document_id,
            'type': metadata.type,
            'original_file': metadata.original_file,
            'file_format': metadata.file_format,
            'processed_data': metadata.processed_data,
            'metadata': metadata.metadata,
            'app_data': metadata.app_data,
            'created_by': metadata.created_by,
            'created_at': metadata.created_at,
            'version': metadata.version,
        }

    except Exception as e:
        logger.error(f"Error in retrieve_document: {e}", exc_info=True)
        raise


async def tool_list_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List stored documents with unified schema
    
    Params:
    - type: Filter by document type (optional)
    - created_by: Filter by creator (optional)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        items = metadata_db.list_all(
            type=params.get('type'),
            created_by=params.get('created_by'),
            limit=int(params.get('limit', 100)),
            offset=int(params.get('offset', 0))
        )

        return {
            'documents': [
                {
                    'document_id': item.document_id,
                    'type': item.type,
                    'original_file': item.original_file,
                    'file_format': item.file_format,
                    'created_by': item.created_by,
                    'created_at': item.created_at,
                    'version': item.version,
                    'file_hash': item.file_hash[:16] + '...',
                    'metadata': item.metadata,
                    'app_data': item.app_data,
                }
                for item in items
            ],
            'total': len(items)
        }
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


# Tool dispatch table
TOOLS = {
    "store_document": tool_store_document,
    "retrieve_document": tool_retrieve_document,
    "list_documents": tool_list_documents,
    "list_backends": tool_list_backends,
    "list_storage_providers": tool_list_storage_providers,
    "get_stats": tool_get_stats,
    "delete_all_documents": tool_delete_all_documents,
    "answer_content_query": tool_answer_content_query,
}


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
