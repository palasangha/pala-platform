#!/usr/bin/env python3
"""
CLI wrapper for Storage API
Allows MCP server to call storage via subprocess
"""

import sys
import json
import asyncio
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.storage_api import StorageAPI

# Initialize storage
storage_dir = Path(__file__).parent.parent / 'data'
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


async def store_content():
    """Store content from stdin"""
    import sys
    args = sys.argv[2:]  # Skip 'store' command
    
    # Parse arguments
    content_type = None
    metadata = {}
    backend_name = None
    
    i = 0
    while i < len(args):
        if args[i] == '--content-type':
            content_type = args[i + 1]
            i += 2
        elif args[i] == '--metadata':
            metadata = json.loads(args[i + 1])
            i += 2
        elif args[i] == '--backend':
            backend_name = args[i + 1]
            i += 2
        else:
            i += 1
    
    # Read content from stdin
    content = sys.stdin.read()
    content_bytes = content.encode('utf-8')
    
    # Store with deduplication (and optional backend selection)
    stored = await storage_api.store_content(
        content=content_bytes,
        content_type=content_type or 'document',
        metadata=metadata,
        backend_name=backend_name  # Use specified backend or default
    )
    
    # Check if it was deduplicated
    import hashlib
    file_hash = hashlib.sha256(content_bytes).hexdigest()
    
    # If hash matches existing, it was deduplicated
    existing = storage_api._find_by_hash(file_hash)
    is_duplicate = existing and existing.content_id == stored.content_id
    
    result = {
        'content_id': stored.content_id,
        'file_hash': stored.file_hash,
        'provider': 'pala-storage-provider',  # Tool provider (matches MCP agent pattern)
        'backend': stored.backend_name,  # Storage backend implementation (local, s3, gcs, azure)
        'version': stored.version,
        'deduplication': is_duplicate,
        'message': 'Content already exists (deduplicated)' if is_duplicate else 'Content stored successfully'
    }
    
    print(json.dumps(result))


async def retrieve_content():
    """Retrieve content by ID"""
    content_id = sys.argv[2]
    
    stored = await storage_api.retrieve_content(content_id)
    
    result = {
        'content': stored.content.decode('utf-8') if isinstance(stored.content, bytes) else stored.content,
        'metadata': stored.metadata
    }
    
    print(json.dumps(result))


async def list_content():
    """List all stored content"""
    items = await storage_api.list_content(limit=100)
    
    result = {
        'items': [
            {
                'content_id': item.content_id,
                'content_type': item.content_type,
                'file_hash': item.file_hash[:16] + '...',
                'created_at': item.created_at,
                'backend': item.backend_name
            }
            for item in items
        ]
    }
    
    print(json.dumps(result))


async def list_backends():
    """List available storage backends"""
    backends = []
    
    # Get all registered backends from the manager
    for backend_name in storage_api.backend_manager.backends.keys():
        backend = storage_api.backend_manager.backends[backend_name]
        is_default = backend_name == storage_api.backend_manager.default_backend_name
        
        backends.append({
            'name': backend_name,
            'type': backend.__class__.__name__,
            'is_default': is_default,
            'enabled': True
        })
    
    result = {
        'backends': backends,
        'default_backend': storage_api.backend_manager.default_backend_name
    }
    
    print(json.dumps(result))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Command required: store|retrieve|list|backends'}))
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == 'store':
            asyncio.run(store_content())
        elif command == 'retrieve':
            asyncio.run(retrieve_content())
        elif command == 'list':
            asyncio.run(list_content())
        elif command == 'backends':
            asyncio.run(list_backends())
        else:
            print(json.dumps({'error': f'Unknown command: {command}'}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)
