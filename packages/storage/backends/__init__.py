"""
Pala Platform Storage Backends

Pluggable storage backends for multiple cloud and local storage providers.

Available Backends:
- Local: Local filesystem storage
- S3: Amazon S3
- GCS: Google Cloud Storage
- Azure: Microsoft Azure Blob Storage

Each backend implements the StorageBackend interface and can be used
interchangeably through the StorageBackendManager.

Usage:
    from storage.backends import StorageBackendFactory, StorageBackendManager
    from storage.backends.local import LocalStorageBackend
    from storage.backends.s3 import S3StorageBackend
    
    # Create manager
    manager = StorageBackendManager()
    
    # Register local backend
    local_backend = LocalStorageBackend('local-primary', {
        'base_path': './content',
        'organize_by_type': True,
        'organize_by_date': True
    })
    manager.register_backend(local_backend, default=True)
    
    # Register S3 backend
    s3_backend = S3StorageBackend('s3-backup', {
        'aws_access_key_id': '...',
        'aws_secret_access_key': '...',
        'bucket_name': 'pala-content'
    })
    manager.register_backend(s3_backend)
    
    # Write content
    backend_name, location = await manager.write(
        content_id='doc-123',
        content=b'...',
        metadata={'content_type': 'document'}
    )
    
    # Read content
    content = await manager.read(
        content_id='doc-123',
        backend_name=backend_name,
        location=location
    )
"""

from .base import (
    StorageBackend,
    StorageBackendConfig,
    StorageBackendFactory,
    StorageBackendManager,
    StorageMetadata,
    StorageStats
)
from .local import LocalStorageBackend
from .sqlite import SQLiteStorageBackend
from .s3 import S3StorageBackend
from .gcs import GCSStorageBackend
from .azure import AzureStorageBackend

# Register all backends
StorageBackendFactory.register('local', LocalStorageBackend)
StorageBackendFactory.register('sqlite', SQLiteStorageBackend)
StorageBackendFactory.register('s3', S3StorageBackend)
StorageBackendFactory.register('gcs', GCSStorageBackend)
StorageBackendFactory.register('azure', AzureStorageBackend)

__all__ = [
    'StorageBackend',
    'StorageBackendConfig',
    'StorageBackendFactory',
    'StorageBackendManager',
    'StorageMetadata',
    'StorageStats',
    'LocalStorageBackend',
    'SQLiteStorageBackend',
    'S3StorageBackend',
    'GCSStorageBackend',
    'AzureStorageBackend'
]
