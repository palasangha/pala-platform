"""
Pala Platform Storage Architecture

Pluggable backend system supporting:
- Local Filesystem
- AWS S3
- Google Cloud Storage (GCS)
- Azure Blob Storage
- Extensible for future backends

Each backend implements the StorageBackend interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
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
    backend_type: str  # local, s3, gcs, azure
    backend_location: str  # path or URI
    metadata: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    signature: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class StorageBackendConfig:
    """Configuration for storage backend"""
    backend_type: str
    name: str  # unique identifier for this backend instance
    enabled: bool = True
    default: bool = False  # Used for new content if no backend specified
    config: Dict[str, Any] = None  # Backend-specific configuration


@dataclass
class StorageStats:
    """Storage statistics aggregated across backends"""
    total_count: int
    total_size: int
    by_type: Dict[str, Dict[str, Any]]  # {content_type: {count, size, backends}}
    by_backend: Dict[str, Dict[str, Any]]  # {backend_name: {count, size}}


class StorageBackend(ABC):
    """
    Abstract base class for storage backends
    
    All backends must implement this interface to support:
    - Reading/writing content
    - Deleting content
    - Checking existence
    - Listing content
    - Backend-specific operations
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize backend
        
        Args:
            name: Unique identifier for this backend instance
            config: Backend-specific configuration
        """
        self.name = name
        self.config = config or {}
        self.backend_type = self.__class__.__name__
    
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
        Check backend health/connectivity
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get backend statistics
        
        Returns:
            Statistics dictionary with count, total_size, etc.
        """
        pass


class StorageBackendFactory:
    """Factory for creating storage backends"""
    
    _backends: Dict[str, type] = {}
    
    @classmethod
    def register(cls, backend_type: str, backend_class: type):
        """Register a storage backend type"""
        cls._backends[backend_type] = backend_class
        logger.info(f"Registered storage backend: {backend_type}")
    
    @classmethod
    def create(cls, backend_type: str, name: str, config: Dict[str, Any]) -> StorageBackend:
        """
        Create a storage backend instance
        
        Args:
            backend_type: Type of backend (local, s3, gcs, etc.)
            name: Unique name for backend instance
            config: Backend configuration
            
        Returns:
            StorageBackend instance
            
        Raises:
            ValueError: If backend type not registered
        """
        if backend_type not in cls._backends:
            raise ValueError(
                f"Unknown backend type: {backend_type}. "
                f"Registered backends: {list(cls._backends.keys())}"
            )
        
        backend_class = cls._backends[backend_type]
        logger.info(f"Creating {backend_type} backend: {name}")
        return backend_class(name, config)
    
    @classmethod
    def get_registered_backends(cls) -> List[str]:
        """Get list of registered backend types"""
        return list(cls._backends.keys())


class StorageBackendManager:
    """
    Manages multiple storage backends
    
    Features:
    - Multiple backend support
    - Content distribution across backends
    - Failover and redundancy
    - Per-content backend tracking
    - Statistics aggregation
    """
    
    def __init__(self):
        """Initialize backend manager"""
        self.backends: Dict[str, StorageBackend] = {}
        self.default_backend: Optional[str] = None
    
    def register_backend(self, backend: StorageBackend, default: bool = False):
        """
        Register a storage backend
        
        Args:
            backend: StorageBackend instance
            default: Use as default for new content
        """
        self.backends[backend.name] = backend
        if default or len(self.backends) == 1:
            self.default_backend = backend.name
        logger.info(f"Backend registered: {backend.name} (default={default})")
    
    async def write(
        self,
        content_id: str,
        content: bytes,
        metadata: Dict[str, Any],
        backend_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Write content to storage
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            backend_name: Specific backend (uses default if not specified)
            
        Returns:
            Tuple of (backend_name, storage_location)
        """
        backend_name = backend_name or self.default_backend
        if not backend_name:
            raise RuntimeError("No default backend configured")
        
        backend = self.backends[backend_name]
        location = await backend.write(content_id, content, metadata)
        logger.info(f"Content {content_id} written to {backend_name}: {location}")
        return backend_name, location
    
    async def read(
        self,
        content_id: str,
        backend_name: str,
        location: str
    ) -> bytes:
        """
        Read content from storage
        
        Args:
            content_id: Content identifier
            backend_name: Backend to read from
            location: Storage location
            
        Returns:
            Binary content
        """
        backend = self.backends[backend_name]
        content = await backend.read(content_id, location)
        logger.info(f"Content {content_id} read from {backend_name}")
        return content
    
    async def delete(
        self,
        content_id: str,
        backend_name: str,
        location: str
    ) -> bool:
        """
        Delete content from storage
        
        Args:
            content_id: Content identifier
            backend_name: Backend to delete from
            location: Storage location
            
        Returns:
            True if deleted
        """
        backend = self.backends[backend_name]
        result = await backend.delete(content_id, location)
        if result:
            logger.info(f"Content {content_id} deleted from {backend_name}")
        return result
    
    async def get_backend_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics from all backends
        
        Returns:
            Dictionary of stats per backend
        """
        stats = {}
        for name, backend in self.backends.items():
            try:
                stats[name] = await backend.get_stats()
            except Exception as e:
                logger.error(f"Error getting stats from {name}: {e}")
                stats[name] = {"error": str(e)}
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all backends
        
        Returns:
            Dictionary of backend health status
        """
        health = {}
        for name, backend in self.backends.items():
            try:
                health[name] = await backend.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health[name] = False
        return health
    
    def get_backend(self, name: str) -> Optional[StorageBackend]:
        """Get specific backend by name"""
        return self.backends.get(name)
    
    def list_backends(self) -> List[str]:
        """List all registered backend names"""
        return list(self.backends.keys())
