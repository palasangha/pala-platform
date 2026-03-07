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
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets

from provider_factory import ProviderFactory, get_provider
from storage_provider import StorageProvider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

agent_dir = Path(__file__).parent
storage_dir = agent_dir / 'data'
storage_dir.mkdir(exist_ok=True)

# Initialize storage provider
try:
    provider: StorageProvider = get_provider()
    logger.info(f"Storage provider initialized: {type(provider).__name__}")
except Exception as e:
    logger.error(f"Failed to initialize storage provider: {e}")
    raise


# Tool implementations
async def tool_store_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store document using unified schema with automatic deduplication
    
    Params:
    - type: Document type (ocr, transcription, metadata, etc)
    - original_file: Path/name of original file
    - file_format: File format (pdf, txt, json, etc)
    - processed_data: Processed/extracted content (object)
    - metadata: Document metadata (object)
    - app_data: App-specific data (object)
    - created_by: User/app that created this (required)
    """
    try:
        # Get content from new or old parameter names for backward compatibility
        processed_data = params.get('processed_data', {})
        if not processed_data and params.get('content'):
            processed_data = {'text': params.get('content')}
        if not processed_data and params.get('ocr_text'):
            processed_data = {'text': params.get('ocr_text')}
        
        if not processed_data:
            raise ValueError('processed_data or content/ocr_text is required')

        # Get required fields
        doc_type = params.get('type', params.get('content_type', 'document'))
        original_file = params.get('original_file', params.get('original_file_path', 'unknown'))
        file_format = params.get('file_format', 'txt')
        created_by = params.get('created_by', 'api')
        
        metadata = params.get('metadata', {})
        app_data = params.get('app_data', {})
        file_hash = params.get('file_hash')

        # For backwards compatibility, include old fields in app_data
        if not file_hash and params.get('job_id'):
            app_data['job_id'] = params.get('job_id')
            app_data['file_index'] = params.get('file_index', 0)

        # Store the document
        doc = await provider.store_document(
            type=doc_type,
            original_file=original_file,
            file_format=file_format,
            processed_data=processed_data,
            metadata=metadata,
            app_data=app_data,
            created_by=created_by,
            file_hash=file_hash
        )

        return {
            'document_id': doc.id,
            'type': doc.type,
            'original_file': doc.original_file,
            'file_format': doc.file_format,
            'created_by': doc.created_by,
            'created_at': doc.created_at,
            'version': doc.version,
            'message': 'Document stored successfully'
        }

    except Exception as e:
        logger.error(f"Error in store_document: {e}", exc_info=True)
        raise


async def tool_store_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store a generic extraction result to unified table
    
    Params:
    - source_type: Type of extraction (ocr, transcription, translation, custom, etc)
    - source_id: ID of the source file/input
    - data: The actual extracted content (string or object)
    - data_type: Type of data (text, json, binary)
    - metadata: Additional metadata about the extraction (optional)
    - provider: Which model/service performed extraction (optional)
    - confidence: Confidence score if applicable (optional)
    - created_by: Which UI/service stored this (optional)
    """
    try:
        source_type = params.get('source_type')
        source_id = params.get('source_id')
        data = params.get('data')
        data_type = params.get('data_type', 'text')
        metadata = params.get('metadata', {})
        extraction_provider = params.get('provider', 'unknown')
        confidence = params.get('confidence')
        created_by = params.get('created_by', 'api')
        
        if not source_type or not source_id or data is None:
            raise ValueError('source_type, source_id, and data are required')
        
        extraction = await provider.store_extraction(
            source_type=source_type,
            source_id=source_id,
            data=data,
            data_type=data_type,
            metadata=metadata,
            provider=extraction_provider,
            confidence=confidence,
            created_by=created_by
        )
        
        return {
            'extraction_id': extraction.id,
            'source_type': extraction.source_type,
            'source_id': extraction.source_id,
            'data_type': extraction.data_type,
            'provider': extraction.provider,
            'confidence': extraction.confidence,
            'created_at': extraction.created_at,
            'message': 'Extraction stored successfully'
        }
    except Exception as e:
        logger.error(f"Error in store_extraction: {e}", exc_info=True)
        raise


async def tool_retrieve_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve a single extraction by ID"""
    try:
        extraction_id = params.get('extraction_id')
        if not extraction_id:
            raise ValueError('extraction_id is required')
        
        extraction = await provider.retrieve_extraction(extraction_id)
        if not extraction:
            return {'error': f'Extraction not found: {extraction_id}'}
        
        return {
            'extraction_id': extraction.id,
            'source_type': extraction.source_type,
            'source_id': extraction.source_id,
            'data': extraction.data,
            'data_type': extraction.data_type,
            'metadata': extraction.metadata,
            'provider': extraction.provider,
            'confidence': extraction.confidence,
            'created_by': extraction.created_by,
            'created_at': extraction.created_at
        }
    except Exception as e:
        logger.error(f"Error in retrieve_extraction: {e}", exc_info=True)
        raise


async def tool_list_extractions(params: Dict[str, Any]) -> Dict[str, Any]:
    """List extractions with optional filters"""
    try:
        source_type = params.get('source_type')
        source_id = params.get('source_id')
        limit = params.get('limit', 100)
        offset = params.get('offset', 0)
        
        result = await provider.list_extractions(
            source_type=source_type,
            source_id=source_id,
            limit=limit,
            offset=offset
        )
        
        return {
            'count': result['count'],
            'total': result['total'],
            'limit': result['limit'],
            'offset': result['offset'],
            'extractions': [
                {
                    'id': ext.id,
                    'source_type': ext.source_type,
                    'source_id': ext.source_id,
                    'data_type': ext.data_type,
                    'provider': ext.provider,
                    'confidence': ext.confidence,
                    'created_at': ext.created_at
                }
                for ext in result['extractions']
            ]
        }
    except Exception as e:
        logger.error(f"Error in list_extractions: {e}", exc_info=True)
        raise


async def tool_retrieve_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve document by document ID
    
    Params:
    - document_id: Document identifier
    """
    try:
        document_id = params.get('document_id') or params.get('content_id')
        if not document_id:
            raise ValueError('document_id is required')

        doc = await provider.retrieve_document(document_id)
        if not doc:
            raise ValueError(f'Document not found: {document_id}')

        return {
            'document_id': doc.id,
            'type': doc.type,
            'original_file': doc.original_file,
            'file_format': doc.file_format,
            'processed_data': doc.processed_data,
            'metadata': doc.metadata,
            'app_data': doc.app_data,
            'created_by': doc.created_by,
            'created_at': doc.created_at,
            'updated_at': doc.updated_at,
            'version': doc.version
        }

    except Exception as e:
        logger.error(f"Error in retrieve_document: {e}", exc_info=True)
        raise


async def tool_list_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List stored documents
    
    Params:
    - type: Filter by document type (optional)
    - created_by: Filter by creator (optional)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        doc_type = params.get('type') or params.get('content_type')
        created_by = params.get('created_by')
        limit = int(params.get('limit', 100))
        offset = int(params.get('offset', 0))

        result = await provider.list_documents(
            doc_type=doc_type,
            created_by=created_by,
            limit=limit,
            offset=offset
        )

        return {
            'count': result['count'],
            'total': result['total'],
            'limit': result['limit'],
            'offset': result['offset'],
            'documents': [
                {
                    'document_id': doc.id,
                    'type': doc.type,
                    'original_file': doc.original_file,
                    'file_format': doc.file_format,
                    'created_by': doc.created_by,
                    'created_at': doc.created_at,
                    'version': doc.version
                }
                for doc in result['documents']
            ]
        }

    except Exception as e:
        logger.error(f"Error in list_documents: {e}", exc_info=True)
        raise


async def tool_get_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get storage statistics
    
    No parameters required
    """
    try:
        stats = await provider.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Error in get_stats: {e}", exc_info=True)
        raise


async def tool_delete_all_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete all documents from storage.
    """
    try:
        deleted_count = await provider.delete_all_documents()
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

        # Search documents
        results = await provider.search_full_text(query, limit=500)
        ranked: list[Dict[str, Any]] = []

        for doc in results:
            title = doc.original_file or doc.id
            
            # Try to extract text from processed_data
            content_text = ""
            if isinstance(doc.processed_data, dict):
                content_text = doc.processed_data.get('text', str(doc.processed_data))
            else:
                content_text = str(doc.processed_data)

            # Calculate relevance score
            haystack = f"{title}\n{content_text}".lower()
            score = 0
            if tokens:
                for token in tokens:
                    score += haystack.count(token)
            else:
                score = 1

            if score <= 0:
                continue

            snippet = content_text.strip().replace('\n', ' ')
            if len(snippet) > 320:
                snippet = snippet[:320].rstrip() + '…'

            ranked.append({
                'document_id': doc.id,
                'title': title,
                'snippet': snippet,
                'score': score,
                'created_at': doc.created_at,
                'type': doc.type,
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
                'document_id': ref['document_id'],
                'title': ref['title'],
                'snippet': ref['snippet'],
                'score': ref['score'],
                'type': ref['type'],
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
        }
    except Exception as e:
        logger.error(f"Error in answer_content_query: {e}", exc_info=True)
        raise



# Tool registry
TOOLS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "store_document": tool_store_document,
    "retrieve_document": tool_retrieve_document,
    "list_documents": tool_list_documents,
    "store_extraction": tool_store_extraction,
    "retrieve_extraction": tool_retrieve_extraction,
    "list_extractions": tool_list_extractions,
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
            "description": "Store document with automatic deduplication using unified schema",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Document type (ocr, transcription, metadata, etc)"},
                    "original_file": {"type": "string", "description": "Path/name of original file"},
                    "file_format": {"type": "string", "description": "File format (pdf, txt, json, etc)"},
                    "processed_data": {"type": "object", "description": "Processed/extracted content"},
                    "metadata": {"type": "object", "description": "Document metadata"},
                    "app_data": {"type": "object", "description": "App-specific data"},
                    "created_by": {"type": "string", "description": "User/app that created this"},
                    "file_hash": {"type": "string", "description": "SHA-256 file hash (optional)"},
                },
                "required": ["created_by"]
            }
        },
        {
            "name": "retrieve_document",
            "description": "Retrieve document by document ID",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"}
                },
                "required": ["document_id"]
            }
        },
        {
            "name": "list_documents",
            "description": "List stored documents with optional filters",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Filter by document type"},
                    "created_by": {"type": "string", "description": "Filter by creator"},
                    "limit": {"type": "number", "default": 100},
                    "offset": {"type": "number", "default": 0}
                }
            }
        },
        {
            "name": "store_extraction",
            "description": "Store extraction result (OCR, transcription, translation, etc) to unified table",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_type": {"type": "string", "description": "Type of extraction (ocr, transcription, translation, custom, etc)"},
                    "source_id": {"type": "string", "description": "ID of the source file/input"},
                    "data": {"description": "The actual extracted content (string or object)"},
                    "data_type": {"type": "string", "description": "Type of data (text, json, binary)", "default": "text"},
                    "metadata": {"type": "object", "description": "Additional metadata about the extraction"},
                    "provider": {"type": "string", "description": "Which model/service performed extraction"},
                    "confidence": {"type": "number", "description": "Confidence score if applicable"},
                    "created_by": {"type": "string", "description": "Which UI/service stored this", "default": "api"}
                },
                "required": ["source_type", "source_id", "data"]
            }
        },
        {
            "name": "retrieve_extraction",
            "description": "Retrieve a single extraction by ID from unified table",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "extraction_id": {"type": "string"}
                },
                "required": ["extraction_id"]
            }
        },
        {
            "name": "list_extractions",
            "description": "List extractions from unified table with optional filters",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_type": {"type": "string", "description": "Filter by extraction type"},
                    "source_id": {"type": "string", "description": "Filter by source file ID"},
                    "limit": {"type": "number", "default": 100},
                    "offset": {"type": "number", "default": 0}
                }
            }
        },
        {
            "name": "get_stats",
            "description": "Get storage statistics",
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
            "description": "Answer user question from stored content with local citations",
            "agentId": agent_id,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "number", "default": 5},
                    "include_web": {"type": "boolean", "default": True}
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
    import time
    name = params.get("name")
    arguments = params.get("arguments", {})
    
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    
    start_time = time.time()
    logger.info(f"[TOOL-START] {name}")
    
    try:
        result = await TOOLS[name](arguments)
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[TOOL-SUCCESS] {name} completed in {duration_ms}ms")
        return {"result": result}
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[TOOL-FAILED] {name} failed after {duration_ms}ms: {e}")
        raise


async def run_agent():
    """Main agent loop"""
    server_url = os.getenv("MCP_SERVER_URL", "ws://localhost:4000")
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
