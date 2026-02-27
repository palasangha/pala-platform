"""
Pala Platform Storage API

Main entry point for storage operations.

Supports multiple backends:
- Local filesystem
- AWS S3
- Google Cloud Storage (GCS)
- Microsoft Azure Blob Storage
- Extensible for custom backends

Usage:
    from storage.api import StorageAPI
    
    storage = StorageAPI(
        db_path="./pala_storage.db",
        backends_config={
            'local': {
                'enabled': True,
                'default': True,
                'config': {'base_path': './content'}
            },
            's3': {
                'enabled': True,
                'default': False,
                'config': {
                    'aws_access_key_id': '...',
                    'aws_secret_access_key': '...',
                    'bucket_name': 'pala-content'
                }
            }
        }
    )
    
    # Store content
    stored = await storage.store_content(
        content=b'...',
        content_type='document',
        metadata={'source': 'scan.jpg'}
    )
    
    # Retrieve content
    content = await storage.read_content(stored.content_id)
    
    # Get statistics
    stats = await storage.get_stats()
"""

from .storage_api import StorageAPI, StoredContent

__all__ = ['StorageAPI', 'StoredContent']
