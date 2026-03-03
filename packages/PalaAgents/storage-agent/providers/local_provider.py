"""
Local Filesystem Storage Provider

Stores content on local disk with organized directory structure.
Best for development and small-scale deployments.

Directory structure:
content/
  ├── document/
  │   ├── 2026/02/26/
  │   │   ├── content-id-1.bin
  │   │   └── content-id-2.bin
  │   └── 2026/02/27/
  ├── audio/
  ├── video/
  └── ...
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class LocalProvider(BaseStorageProvider):
    """Local filesystem storage provider"""
    
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        """
        Initialize local storage provider
        
        Args:
            provider_id: Provider identifier (e.g., 'local-provider')
            config: Configuration dict with:
                - base_path: Root directory for storage (default: ./content)
                - organize_by_type: Organize by content type (default: True)
                - organize_by_date: Organize by date subdirs (default: True)
        """
        super().__init__(provider_id, config)
        
        self.base_path = Path(config.get('base_path', './content'))
        self.organize_by_type = config.get('organize_by_type', True)
        self.organize_by_date = config.get('organize_by_date', True)
        
        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalProvider initialized: {self.base_path}")
    
    def _get_storage_path(
        self,
        content_id: str,
        content_type: str,
        created_at: Optional[str] = None
    ) -> Path:
        """
        Calculate storage path based on content type and date
        
        Args:
            content_id: Content identifier
            content_type: Type of content
            created_at: Creation timestamp (ISO format)
            
        Returns:
            Full storage path
        """
        path = self.base_path
        
        # Organize by content type
        if self.organize_by_type:
            path = path / content_type
        
        # Organize by date
        if self.organize_by_date and created_at:
            # Parse ISO timestamp: 2026-02-26T...
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            path = path / dt.strftime('%Y/%m/%d')
        
        # Create directory
        path.mkdir(parents=True, exist_ok=True)
        
        return path / f"{content_id}.bin"
    
    async def write(
        self,
        content_id: str,
        content: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Write content to local filesystem
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            
        Returns:
            Relative storage path
        """
        try:
            content_type = metadata.get('content_type', 'unknown')
            created_at = metadata.get('created_at', datetime.now(timezone.utc).isoformat())
            
            storage_path = self._get_storage_path(content_id, content_type, created_at)
            
            # Write content
            storage_path.write_bytes(content)
            
            # Return relative path for consistency
            relative_path = str(storage_path.relative_to(self.base_path))
            logger.info(f"Content {content_id} written to {relative_path}")
            
            return relative_path
        except Exception as e:
            logger.error(f"Error writing content {content_id}: {e}")
            raise
    
    async def read(
        self,
        content_id: str,
        location: str
    ) -> bytes:
        """
        Read content from local filesystem
        
        Args:
            content_id: Content identifier
            location: Relative storage path
            
        Returns:
            Binary content
        """
        try:
            storage_path = self.base_path / location
            
            if not storage_path.exists():
                raise FileNotFoundError(f"Content not found: {location}")
            
            content = storage_path.read_bytes()
            logger.info(f"Content {content_id} read from {location} ({len(content)} bytes)")
            
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id}: {e}")
            raise
    
    async def delete(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Delete content from local filesystem
        
        Args:
            content_id: Content identifier
            location: Relative storage path
            
        Returns:
            True if deleted, False if not found
        """
        try:
            storage_path = self.base_path / location
            
            if not storage_path.exists():
                return False
            
            storage_path.unlink()
            logger.info(f"Content {content_id} deleted from {location}")
            
            # Clean up empty directories
            try:
                parent = storage_path.parent
                while parent != self.base_path and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
            except OSError:
                pass  # Directory not empty, that's fine
            
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id}: {e}")
            raise
    
    async def exists(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Check if content exists
        
        Args:
            content_id: Content identifier
            location: Relative storage path
            
        Returns:
            True if exists
        """
        try:
            storage_path = self.base_path / location
            return storage_path.exists()
        except Exception as e:
            logger.error(f"Error checking existence of {content_id}: {e}")
            return False
    
    async def get_size(
        self,
        content_id: str,
        location: str
    ) -> int:
        """
        Get content size
        
        Args:
            content_id: Content identifier
            location: Relative storage path
            
        Returns:
            Size in bytes
        """
        try:
            storage_path = self.base_path / location
            
            if not storage_path.exists():
                return 0
            
            return storage_path.stat().st_size
        except Exception as e:
            logger.error(f"Error getting size of {content_id}: {e}")
            return 0
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content identifiers
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of content IDs
        """
        try:
            content_ids = []
            
            for file_path in self.base_path.rglob('*.bin'):
                # Extract content-id from filename
                content_id = file_path.stem  # Remove .bin extension
                
                if prefix is None or content_id.startswith(prefix):
                    content_ids.append(content_id)
            
            logger.info(f"Listed {len(content_ids)} content items")
            return content_ids
        except Exception as e:
            logger.error(f"Error listing content: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check provider health
        
        Returns:
            True if provider is healthy
        """
        try:
            # Check write permission
            test_file = self.base_path / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            
            logger.debug(f"Health check passed for {self.provider_id}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get provider statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            total_size = 0
            total_count = 0
            by_type = {}
            
            for file_path in self.base_path.rglob('*.bin'):
                total_count += 1
                file_size = file_path.stat().st_size
                total_size += file_size
                
                # Count by content type (first directory level)
                try:
                    rel_path = file_path.relative_to(self.base_path)
                    content_type = rel_path.parts[0] if rel_path.parts else 'unknown'
                    
                    if content_type not in by_type:
                        by_type[content_type] = {'count': 0, 'size': 0}
                    
                    by_type[content_type]['count'] += 1
                    by_type[content_type]['size'] += file_size
                except Exception:
                    pass
            
            stats = {
                'provider_type': self.provider_type,
                'provider_id': self.provider_id,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'base_path': str(self.base_path),
                'available_space': self._get_available_space()
            }
            
            logger.debug(f"Stats for {self.provider_id}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def _get_available_space(self) -> int:
        """Get available disk space"""
        try:
            stat = os.statvfs(self.base_path)
            available = stat.f_bavail * stat.f_frsize
            return available
        except Exception:
            return 0
