"""
Storage Provider Base Classes

Abstract interfaces for storage providers in the storage-agent.
Each provider implements complete storage operations for a specific backend type.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


@dataclass
class StorageMetadata:
    """Standardized storage metadata"""
    content_id: str
    content_type: str  # document, audio, video, etc.
    file_hash: str
    file_size: int
    provider_type: str  # local, s3, gcs, azure, sqlite
    storage_location: str  # path or URI
    metadata: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    signature: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class BaseStorageProvider(ABC):
    """
    Abstract base class for storage providers
    
    All providers must implement this interface to support:
    - Reading/writing content
    - Deleting content
    - Checking existence
    - Listing content
    - Provider-specific operations
    """
    
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        """
        Initialize provider
        
        Args:
            provider_id: Unique identifier for this provider instance
            config: Provider-specific configuration
        """
        self.provider_id = provider_id
        self.config = config or {}
        self.provider_type = self.__class__.__name__.replace('Provider', '').lower()
    
    @abstractmethod
    async def write(self, content_id: str, content: bytes, metadata: Dict[str, Any]) -> str:
        """
        Write content to storage
        
        Args:
            content_id: Unique identifier for content
            content: Binary content to store
            metadata: Content metadata
            
        Returns:
            Storage location (path, URI, etc.)
        """
        pass
    
    @abstractmethod
    async def read(self, content_id: str, location: str) -> bytes:
        """
        Read content from storage
        
        Args:
            content_id: Content identifier
            location: Storage location returned by write()
            
        Returns:
            Binary content
        """
        pass
    
    @abstractmethod
    async def delete(self, content_id: str, location: str) -> bool:
        """
        Delete content from storage
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, content_id: str, location: str) -> bool:
        """
        Check if content exists
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_size(self, content_id: str, location: str) -> int:
        """
        Get content size
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            Size in bytes
        """
        pass
    
    @abstractmethod
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content identifiers in storage
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of content IDs
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check provider health/connectivity
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get provider statistics
        
        Returns:
            Statistics dictionary with count, total_size, etc.
        """
        pass
