#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
try:
    from dotenv import load_dotenv
    # Navigate from packages/PalaAgents/storage-agent to pala-platform root
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"[AGENT-STARTUP] Loaded .env from {env_path}")
    else:
        print(f"[AGENT-STARTUP] WARNING: .env not found at {env_path}. S3 config may be missing.")
except ImportError:
    print('[AGENT-STARTUP] WARNING: python-dotenv not installed; .env will not be auto-loaded. S3 config may be missing if not set in environment.')

# Log S3 config at startup and exit if any required variable is missing
required_s3_vars = ["S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET", "S3_REGION"]
s3_config = {k: (os.environ.get(k) if k != "S3_SECRET_KEY" else ("***MASKED***" if os.environ.get(k) else None)) for k in required_s3_vars}
missing_s3 = [k for k in required_s3_vars if not os.environ.get(k)]
print(f"[AGENT-STARTUP] S3 config: " + ", ".join(f"{k}={v}" for k, v in s3_config.items()))
if missing_s3:
    print(f"[AGENT-STARTUP] FATAL: Missing required S3 config: {missing_s3}. Agent will exit.")
    sys.exit(1)
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets
from providers.s3_provider_real import S3ProviderReal

from provider_factory import ProviderFactory, get_provider
from storage_provider import StorageProvider



# Always use DEBUG for development unless overridden by LOGLEVEL env var
loglevel = os.environ.get('LOGLEVEL', 'DEBUG').upper()
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, loglevel, logging.DEBUG))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(console_handler)


# File handler for logs/storage-agent.log (auto-create logs dir)
logfile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))
os.makedirs(logfile_dir, exist_ok=True)
logfile_path = os.path.join(logfile_dir, 'storage-agent.log')
file_handler = logging.FileHandler(logfile_path)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(file_handler)

# Remove duplicate handlers if any
if len(root_logger.handlers) > 2:
    root_logger.handlers = root_logger.handlers[-2:]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Top-level debug log to confirm DEBUG output at import time
logging.getLogger().debug("DEBUG LOG TEST: module import time")

agent_dir = Path(__file__).parent
storage_dir = agent_dir / 'data'
storage_dir.mkdir(exist_ok=True)


# Initialize storage provider and S3 provider with robust logging
try:
    provider: StorageProvider = get_provider()
    logger.info(f"Storage provider initialized: {type(provider).__name__}")
except Exception as e:
    logger.error(f"Failed to initialize storage provider: {e}")
    raise

# S3 Provider initialization with detailed config logging
s3_provider = None
if os.getenv('FILE_STORAGE_PROVIDER', 's3') == 's3':
    s3_env = {
        'S3_ENDPOINT': os.getenv('S3_ENDPOINT'),
        'S3_ACCESS_KEY': os.getenv('S3_ACCESS_KEY'),
        'S3_SECRET_KEY': '***MASKED***' if os.getenv('S3_SECRET_KEY') else None,
        'S3_BUCKET': os.getenv('S3_BUCKET'),
        'S3_REGION': os.getenv('S3_REGION', 'us-east-1'),
    }
    logger.info(f"[S3-INIT] S3 config: "
                f"endpoint={s3_env['S3_ENDPOINT']}, "
                f"access_key={s3_env['S3_ACCESS_KEY']}, "
                f"secret_key={'set' if os.getenv('S3_SECRET_KEY') else 'unset'}, "
                f"bucket={s3_env['S3_BUCKET']}, "
                f"region={s3_env['S3_REGION']}")
    missing = [k for k, v in s3_env.items() if v is None]
    if missing:
        logger.error(f"[S3-INIT] Missing S3 config keys: {missing}. S3ProviderReal will NOT be initialized.")
        s3_provider = None
    else:
        try:
            s3_provider = S3ProviderReal()
            logger.info("S3ProviderReal initialized for file storage.")
        except Exception as e:
            logger.error(f"Failed to initialize S3ProviderReal: {e}")
            s3_provider = None


# Tool implementations
async def tool_store_document(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] store_document called with params: {json.dumps(params)[:500]}")
    print(f"[TOOL-DEBUG] store_document params: {json.dumps(params)[:500]}")
    logger.debug(f"[TOOL-DEBUG] Params preview: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    logger.debug(f"[TOOL-DEBUG] store_document full params: {json.dumps(params)}")
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
        logger.debug(f"[TOOL-DEBUG] Extracting processed_data and required fields")
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

        # Handle file content (base64) from dashboard
        original_file_data = params.get('original_file_data')
        original_file_mime = params.get('original_file_mime', '')
        file_blob = None
        s3_result = None
        logger.debug(f"[TOOL-DEBUG] original_file_data present: {bool(original_file_data)}")
        if original_file_data:
            import base64
            # Debug log: print length and preview of actual data received
            logger.debug(f"[TOOL-DEBUG] About to decode original_file_data: length={len(original_file_data)}, preview={original_file_data[:40]}...")
            try:
                file_blob = base64.b64decode(original_file_data)
                logger.info(f"[TOOL-DEBUG] Decoded file_blob, size: {len(file_blob)} bytes, mime: {original_file_mime}")
                if s3_provider:
                    logger.info(f"[TOOL-DEBUG] S3 provider config: endpoint={getattr(s3_provider, 'endpoint_url', None)}, bucket={getattr(s3_provider, 'bucket', None)}")
                    s3_object_name = original_file or f"file-{uuid.uuid4()}"
                    logger.info(f"[TOOL-DEBUG] Uploading to S3: object_name={s3_object_name}, content_type={original_file_mime}")
                    try:
                        s3_result = s3_provider.upload_file_data(file_blob, s3_object_name, content_type=original_file_mime)
                        logger.info(f"[TOOL-DEBUG] S3 upload result: {s3_result}")
                    except Exception as s3e:
                        logger.error(f"[TOOL-ERROR] S3 upload failed: {s3e}", exc_info=True)
                        s3_result = {'success': False, 'error': str(s3e)}
                else:
                    logger.error("[TOOL-DEBUG] S3 provider is not initialized. S3 upload will not occur. Check S3 config and logs.")
                    s3_result = {'success': False, 'error': 'S3 provider not initialized. Check S3 config.'}
            except Exception as e:
                logger.error(f"[TOOL-ERROR] Failed to decode original_file_data: {e}", exc_info=True)
                s3_result = {'success': False, 'error': f'Failed to decode original_file_data: {e}'}
                raise ValueError('Failed to decode original_file_data')
        else:
            logger.warning("[TOOL-DEBUG] No original_file_data provided in params")
            s3_result = None

        logger.debug(f"[TOOL-DEBUG] Storing document with type={doc_type}, original_file={original_file}, file_format={file_format}, created_by={created_by}, metadata={metadata}, app_data={app_data}, file_hash={file_hash}, file_blob={'present' if file_blob else 'absent'}, s3_result={s3_result}")
        # Store metadata in DB and replicate file_blob to SQLite for backup
        logger.info(f"[REPLICATION] Storing to SQLite: file_blob={'present' if file_blob else 'absent'}, mime={original_file_mime}")
        
        # Build replication status before storing document
        # s3_result structure: { success: bool, primary: {...}, replica: {...} }
        s3_primary = s3_result.get('primary') if s3_result else None
        s3_replica = s3_result.get('replica') if s3_result else None
        s3_success = s3_result.get('success') if s3_result else False
        
        replication_status = {
            'file_content': {
                's3_primary': {**s3_primary, 'success': True} if s3_primary else {'success': False},
                's3_replica': s3_replica if s3_replica else {'success': False, 'reason': 'Not configured'},
            },
            'metadata': {
                'sqlite_primary': {
                    'success': True,
                    'provider': 'sqlite-primary',
                    'db_path': getattr(provider, 'db_path', None),
                    'file_blob_stored': file_blob is not None,
                },
                'sqlite_replica': {
                    'success': True,
                    'provider': 'sqlite-replica',
                    'db_path': getattr(provider, 'replica_db_path', None),
                    'file_blob_stored': file_blob is not None,
                } if getattr(provider, 'replica_enabled', False) else {'success': False, 'reason': 'Not configured'},
            }
        }
        
        doc, duplicate = await provider.store_document(
            type=doc_type,
            original_file=original_file,
            file_format=file_format,
            processed_data=processed_data,
            metadata=metadata,
            app_data=app_data,
            created_by=created_by,
            file_hash=file_hash,
            file_blob=file_blob,  # Store file blob in SQLite for dual replication (backup)
            file_mime=original_file_mime,
            replication=replication_status,
            s3_result=s3_result,
            message=None  # Will be set after we know if it's a duplicate
        )
        
        result = {
            'document_id': doc.id,
            'type': doc.type,
            'original_file': doc.original_file,
            'file_format': doc.file_format,
            'created_by': doc.created_by,
            'created_at': doc.created_at,
            'version': doc.version,
            'db_storage_location': getattr(doc, 'storage_location', None),
            'db_provider_id': getattr(doc, 'provider_id', None),
            'replication': replication_status,
            's3_result': s3_result,  # Keep for backward compatibility
            'duplicate': duplicate,
            'message': 'Document updated (duplicate)' if duplicate else 'Document stored successfully'
        }
        logger.info(f"[TOOL-RETURN] store_document returned: {json.dumps(result)[:500]}")
        print(f"[TOOL-DEBUG] store_document result: {json.dumps(result)[:500]}")
        logger.debug(f"[TOOL-DEBUG] Full store_document result: {json.dumps(result)}")
        return result

    except Exception as e:
        logger.error(f"[TOOL-ERROR] store_document exception: {e}", exc_info=True)
        raise


async def tool_store_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] store_extraction called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
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
        
        result = {
            'extraction_id': extraction.id,
            'source_type': extraction.source_type,
            'source_id': extraction.source_id,
            'data_type': extraction.data_type,
            'provider': extraction.provider,
            'confidence': extraction.confidence,
            'created_at': extraction.created_at,
            'message': 'Extraction stored successfully'
        }
        logger.info(f"[TOOL-RETURN] store_extraction returned: {json.dumps(result)[:500]}")
        return result
    except Exception as e:
        logger.error(f"Error in store_extraction: {e}", exc_info=True)
        raise


async def tool_retrieve_extraction(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] retrieve_extraction called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    """Retrieve a single extraction by ID"""
    try:
        extraction_id = params.get('extraction_id')
        if not extraction_id:
            raise ValueError('extraction_id is required')
        
        extraction = await provider.retrieve_extraction(extraction_id)
        if not extraction:
            return {'error': f'Extraction not found: {extraction_id}'}
        
        result = {
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
        logger.info(f"[TOOL-RETURN] retrieve_extraction returned: {json.dumps(result)[:500]}")
        return result
    except Exception as e:
        logger.error(f"Error in retrieve_extraction: {e}", exc_info=True)
        raise


async def tool_list_extractions(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] list_extractions called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
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
        
        result = {
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
        logger.info(f"[TOOL-RETURN] list_extractions returned: {json.dumps(result)[:500]}")
        return result
    except Exception as e:
        logger.error(f"Error in list_extractions: {e}", exc_info=True)
        raise


async def tool_retrieve_document(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] retrieve_document called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    """
    Retrieve document by document ID with optional original file content
    
    Params:
    - document_id: Document identifier
    - include_original_file: If true, include original file as base64 (default: false)
    """
    try:
        document_id = params.get('document_id') or params.get('content_id')
        if not document_id:
            raise ValueError('document_id is required')
        
        include_original_file = params.get('include_original_file', False)
        logger.debug(f"[TOOL-DEBUG] retrieve_document: document_id={document_id}, include_original_file={include_original_file}")

        doc = await provider.retrieve_document(document_id)
        if not doc:
            logger.warning(f"[TOOL-WARNING] Document not found: {document_id}")
            raise ValueError(f'Document not found: {document_id}')

        logger.debug(f"[TOOL-DEBUG] Document retrieved: doc.id={doc.id}, storage_location={getattr(doc, 'storage_location', None)}, provider_id={getattr(doc, 'provider_id', None)}")
        
        # Compute message based on duplicate status
        duplicate_status = getattr(doc, 'duplicate', False)
        message = 'Document updated (duplicate)' if duplicate_status else 'Document stored successfully'
        
        result = {
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
            'version': doc.version,
            'storage_location': getattr(doc, 'storage_location', None),
            'provider_id': getattr(doc, 'provider_id', None),
            'file_hash': getattr(doc, 'file_hash', None),
            'replication': getattr(doc, 'replication', None),
            's3_result': getattr(doc, 's3_result', None),
            'message': message,
            'duplicate': duplicate_status
        }
        
        # Retrieve original file if requested
        original_file_data = None
        if include_original_file:
            try:
                logger.info(f"[TOOL-DEBUG] Retrieving original file for document_id={document_id}")
                # Try to retrieve from SQLite BLOB storage first
                if hasattr(provider, 'retrieve_document_file'):
                    original_file_data = await provider.retrieve_document_file(document_id)
                    if original_file_data:
                        import base64
                        original_file_b64 = base64.b64encode(original_file_data).decode('utf-8')
                        result['original_file_data'] = original_file_b64
                        result['original_file_size'] = len(original_file_data)
                        logger.info(f"[TOOL-SUCCESS] Original file retrieved from storage: size={len(original_file_data)} bytes")
                    else:
                        logger.warning(f"[TOOL-WARNING] Original file not found in storage for document_id={document_id}")
                        result['original_file_data'] = None
                        result['original_file_size'] = 0
            except Exception as e:
                logger.error(f"[TOOL-ERROR] Failed to retrieve original file: {e}", exc_info=True)
                result['original_file_error'] = str(e)
        
        logger.info(f"[TOOL-RETURN] retrieve_document returned: {json.dumps({k: v for k, v in result.items() if k != 'original_file_data'})[:500]}")
        return result

    except Exception as e:
        logger.error(f"[TOOL-ERROR] Error in retrieve_document: {e}", exc_info=True)
        raise


async def tool_list_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] list_documents called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
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

        documents = []
        for doc in result['documents']:
            doc_info = {
                'document_id': doc.id,
                'type': doc.type,
                'original_file': doc.original_file,
                'file_format': doc.file_format,
                'created_by': doc.created_by,
                'created_at': doc.created_at,
                'version': doc.version,
                'storage_location': getattr(doc, 'storage_location', None),
                'provider_id': getattr(doc, 'provider_id', None)
            }
            logger.debug(f"tool_list_documents: doc.id={doc.id}, storage_location={doc_info['storage_location']}, provider_id={doc_info['provider_id']}")
            documents.append(doc_info)
        result_dict = {
            'count': result['count'],
            'total': result['total'],
            'limit': result['limit'],
            'offset': result['offset'],
            'documents': documents
        }
        logger.info(f"[TOOL-RETURN] list_documents returned: {json.dumps(result_dict)[:500]}")
        return result_dict

    except Exception as e:
        logger.error(f"Error in list_documents: {e}", exc_info=True)
        raise


async def tool_get_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] get_stats called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    """
    Get storage statistics
    
    No parameters required
    """
    try:
        stats = await provider.get_stats()
        logger.info(f"[TOOL-RETURN] get_stats returned: {json.dumps(stats)[:500]}")
        return stats

    except Exception as e:
        logger.error(f"Error in get_stats: {e}", exc_info=True)
        raise


async def tool_delete_all_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"[TOOL-INVOKE] delete_all_documents called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
    """
    Delete all documents from storage.
    """
    try:
        deleted_count = await provider.delete_all_documents()
        result = {
            "success": True,
            "deleted_count": deleted_count,
            "message": "All documents deleted."
        }
        logger.info(f"[TOOL-RETURN] delete_all_documents returned: {json.dumps(result)[:500]}")
        print(f"[TOOL-DEBUG] delete_all_documents result: {json.dumps(result)[:500]}")
        return result
    except Exception as e:
        logger.error(f"[TOOL-ERROR] delete_all_documents exception: {e}", exc_info=True)
        raise


async def tool_answer_content_query(params: Dict[str, Any]) -> Dict[str, Any]:
    log = logging.getLogger()
    logger.info(f"[TOOL-INVOKE] answer_content_query called with params: {json.dumps(params)[:500]}")
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass
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

        result = {
            'query': query,
            'answer_local': local_answer,
            'references_local': references_local,
            'web_section': web_section,
            'reference_count': len(references_local),
        }
        logger.info(f"[TOOL-RETURN] answer_content_query returned: {json.dumps(result)[:500]}")
        return result
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
    logger.info(f"TESTETS [AGENT-REGISTER] Registering tools from __file__={__file__} cwd={os.getcwd()} agent_id={agent_id}")
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
    
    logger.info(f"[AGENT-START] __file__={__file__} cwd={os.getcwd()}")
    print("PRINT TEST LINE - AGENT-START")
    logger.info(f"Starting Storage Agent - connecting to {server_url}")
    

    while True:
        try:
            async with websockets.connect(server_url) as ws:
                logger.info(f"Connected to MCP server as {agent_id}")

                # Register tools
                await register_tools(ws, agent_id)

                # Message loop
                async for message in ws:
                    logger.info(f"[AGENT-RECV] Raw message: {message}")
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
