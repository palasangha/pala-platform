"""
Google Cloud Storage (GCS) Backend

Stores content on Google Cloud Storage for global distribution and reliability.

Configuration:
{
    'project_id': 'my-project',
    'bucket_name': 'pala-content',
    'credentials_path': '/path/to/service-account.json',
    'organize_by_type': True,
    'organize_by_date': True,
    'storage_class': 'STANDARD'  # STANDARD, NEARLINE, COLDLINE, ARCHIVE
}
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base import StorageBackend

logger = logging.getLogger(__name__)


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize GCS storage backend
        
        Args:
            name: Backend name (e.g., 'gcs-primary')
            config: Configuration dict with GCS credentials and bucket info
        """
        super().__init__(name, config)
        
        # Check for google-cloud-storage
        try:
            from google.cloud import storage
            
            # Initialize GCS client
            credentials_path = config.get('credentials_path')
            if credentials_path:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
            self.gcs_client = storage.Client(
                project=config.get('project_id')
            )
            self.bucket = self.gcs_client.bucket(config.get('bucket_name'))
            self.gcs_available = True
        except ImportError:
            logger.warning("google-cloud-storage not installed. GCS operations will use mock data.")
            self.gcs_available = False
            self.gcs_client = None
            self.bucket = None
        
        self.bucket_name = config.get('bucket_name', 'pala-content')
        self.organize_by_type = config.get('organize_by_type', True)
        self.organize_by_date = config.get('organize_by_date', True)
        self.storage_class = config.get('storage_class', 'STANDARD')
        
        logger.info(f"GCSStorageBackend initialized: bucket={self.bucket_name}")
    
    def _get_object_name(
        self,
        content_id: str,
        content_type: str,
        created_at: Optional[str] = None
    ) -> str:
        """
        Calculate GCS object name
        
        Args:
            content_id: Content identifier
            content_type: Type of content
            created_at: Creation timestamp
            
        Returns:
            GCS object name
        """
        parts = []
        
        # Organize by content type
        if self.organize_by_type:
            parts.append(content_type)
        
        # Organize by date
        if self.organize_by_date and created_at:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            parts.extend(dt.strftime('%Y/%m/%d').split('/'))
        
        # Content ID as filename
        parts.append(f"{content_id}.bin")
        
        return '/'.join(parts)
    
    async def write(
        self,
        content_id: str,
        content: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Write content to GCS
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            
        Returns:
            GCS object name
        """
        try:
            content_type = metadata.get('content_type', 'unknown')
            created_at = metadata.get('created_at', datetime.now(timezone.utc).isoformat())
            
            object_name = self._get_object_name(content_id, content_type, created_at)
            
            if not self.gcs_available:
                logger.warning(f"google-cloud-storage not available, using mock write for {content_id}")
                return object_name
            
            # Upload to GCS
            blob = self.bucket.blob(object_name)
            blob.upload_from_string(
                content,
                content_type='application/octet-stream'
            )
            
            # Set metadata
            blob.metadata = {
                'content-id': content_id,
                'content-type': content_type,
                'created-at': created_at
            }
            blob.patch()
            
            logger.info(f"Content {content_id} uploaded to GCS: gs://{self.bucket_name}/{object_name}")
            return object_name
        except Exception as e:
            logger.error(f"Error writing content {content_id} to GCS: {e}")
            raise
    
    async def read(
        self,
        content_id: str,
        location: str
    ) -> bytes:
        """
        Read content from GCS
        
        Args:
            content_id: Content identifier
            location: GCS object name
            
        Returns:
            Binary content
        """
        try:
            if not self.gcs_available:
                logger.warning(f"google-cloud-storage not available, using mock read for {content_id}")
                return b"Mock GCS content for " + content_id.encode()
            
            blob = self.bucket.blob(location)
            content = blob.download_as_bytes()
            
            logger.info(f"Content {content_id} read from GCS: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id} from GCS: {e}")
            raise
    
    async def delete(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Delete content from GCS
        
        Args:
            content_id: Content identifier
            location: GCS object name
            
        Returns:
            True if deleted
        """
        try:
            if not self.gcs_available:
                logger.warning(f"google-cloud-storage not available, using mock delete for {content_id}")
                return True
            
            blob = self.bucket.blob(location)
            blob.delete()
            
            logger.info(f"Content {content_id} deleted from GCS")
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id} from GCS: {e}")
            raise
    
    async def exists(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Check if content exists in GCS
        
        Args:
            content_id: Content identifier
            location: GCS object name
            
        Returns:
            True if exists
        """
        try:
            if not self.gcs_available:
                return True  # Mock: assume exists
            
            blob = self.bucket.blob(location)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking existence in GCS: {e}")
            return False
    
    async def get_size(
        self,
        content_id: str,
        location: str
    ) -> int:
        """
        Get content size from GCS
        
        Args:
            content_id: Content identifier
            location: GCS object name
            
        Returns:
            Size in bytes
        """
        try:
            if not self.gcs_available:
                return 1024  # Mock size
            
            blob = self.bucket.blob(location)
            blob.reload()
            return blob.size or 0
        except Exception as e:
            logger.error(f"Error getting size from GCS: {e}")
            return 0
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content in GCS
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of content IDs
        """
        try:
            if not self.gcs_available:
                return []  # Mock
            
            content_ids = []
            blobs = self.bucket.list_blobs(prefix=prefix or '')
            
            for blob in blobs:
                # Extract content-id from object name
                name_parts = blob.name.split('/')
                filename = name_parts[-1]  # Last part
                content_id = filename.replace('.bin', '')
                content_ids.append(content_id)
            
            logger.info(f"Listed {len(content_ids)} content items from GCS")
            return content_ids
        except Exception as e:
            logger.error(f"Error listing content in GCS: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check GCS backend health
        
        Returns:
            True if backend is healthy
        """
        try:
            if not self.gcs_available:
                logger.warning("google-cloud-storage not available")
                return False
            
            # Try to check bucket
            _ = self.bucket.reload()
            logger.debug(f"Health check passed for {self.name}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get GCS backend statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            if not self.gcs_available:
                return {'error': 'google-cloud-storage not available'}
            
            total_size = 0
            total_count = 0
            by_type = {}
            
            blobs = self.bucket.list_blobs()
            
            for blob in blobs:
                total_count += 1
                total_size += blob.size or 0
                
                # Count by content type (first path component)
                name_parts = blob.name.split('/')
                content_type = name_parts[0] if name_parts else 'unknown'
                
                if content_type not in by_type:
                    by_type[content_type] = {'count': 0, 'size': 0}
                
                by_type[content_type]['count'] += 1
                by_type[content_type]['size'] += blob.size or 0
            
            stats = {
                'backend_type': self.backend_type,
                'backend_name': self.name,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'bucket_name': self.bucket_name
            }
            
            logger.debug(f"Stats for {self.name}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
