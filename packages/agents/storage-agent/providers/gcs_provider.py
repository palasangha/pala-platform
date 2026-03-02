"""
Google Cloud Storage Provider

Stores content on Google Cloud Storage for scalability and global access.

TODO: Implement full GCS provider with google-cloud-storage
"""

import logging
from typing import Dict, Any, List, Optional

from .base_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class GCSProvider(BaseStorageProvider):
    """Google Cloud Storage provider (stub implementation)"""
    
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        super().__init__(provider_id, config)
        logger.warning("GCSProvider is not fully implemented yet")
    
    async def write(self, content_id: str, content: bytes, metadata: Dict[str, Any]) -> str:
        raise NotImplementedError("GCSProvider.write() not implemented")
    
    async def read(self, content_id: str, location: str) -> bytes:
        raise NotImplementedError("GCSProvider.read() not implemented")
    
    async def delete(self, content_id: str, location: str) -> bool:
        raise NotImplementedError("GCSProvider.delete() not implemented")
    
    async def exists(self, content_id: str, location: str) -> bool:
        raise NotImplementedError("GCSProvider.exists() not implemented")
    
    async def get_size(self, content_id: str, location: str) -> int:
        raise NotImplementedError("GCSProvider.get_size() not implemented")
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        raise NotImplementedError("GCSProvider.list_content() not implemented")
    
    async def health_check(self) -> bool:
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        return {'provider_type': 'gcs', 'status': 'not_implemented'}
