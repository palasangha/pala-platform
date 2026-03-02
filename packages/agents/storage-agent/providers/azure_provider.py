"""
Azure Blob Storage Provider

Stores content on Azure Blob Storage for enterprise scalability.

TODO: Implement full Azure provider with azure-storage-blob
"""

import logging
from typing import Dict, Any, List, Optional

from .base_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class AzureProvider(BaseStorageProvider):
    """Azure Blob Storage provider (stub implementation)"""
    
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        super().__init__(provider_id, config)
        logger.warning("AzureProvider is not fully implemented yet")
    
    async def write(self, content_id: str, content: bytes, metadata: Dict[str, Any]) -> str:
        raise NotImplementedError("AzureProvider.write() not implemented")
    
    async def read(self, content_id: str, location: str) -> bytes:
        raise NotImplementedError("AzureProvider.read() not implemented")
    
    async def delete(self, content_id: str, location: str) -> bool:
        raise NotImplementedError("AzureProvider.delete() not implemented")
    
    async def exists(self, content_id: str, location: str) -> bool:
        raise NotImplementedError("AzureProvider.exists() not implemented")
    
    async def get_size(self, content_id: str, location: str) -> int:
        raise NotImplementedError("AzureProvider.get_size() not implemented")
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        raise NotImplementedError("AzureProvider.list_content() not implemented")
    
    async def health_check(self) -> bool:
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        return {'provider_type': 'azure', 'status': 'not_implemented'}
