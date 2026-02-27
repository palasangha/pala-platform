"""
Azure Blob Storage Backend

Stores content on Microsoft Azure for enterprise deployments.

Configuration:
{
    'connection_string': 'DefaultEndpointsProtocol=https;...',
    'account_name': 'myaccount',
    'account_key': '...',
    'container_name': 'pala-content',
    'organize_by_type': True,
    'organize_by_date': True,
    'storage_tier': 'Hot'  # Hot, Cool, Archive
}
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base import StorageBackend

logger = logging.getLogger(__name__)


class AzureStorageBackend(StorageBackend):
    """Microsoft Azure Blob Storage backend"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Azure storage backend
        
        Args:
            name: Backend name (e.g., 'azure-primary')
            config: Configuration dict with Azure credentials and container info
        """
        super().__init__(name, config)
        
        # Check for azure-storage-blob
        try:
            from azure.storage.blob import BlobServiceClient
            
            # Initialize Azure client
            connection_string = config.get('connection_string')
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
            else:
                self.blob_service_client = BlobServiceClient(
                    account_url=f"https://{config.get('account_name')}.blob.core.windows.net",
                    credential=config.get('account_key')
                )
            
            self.container_client = self.blob_service_client.get_container_client(
                config.get('container_name')
            )
            self.azure_available = True
        except ImportError:
            logger.warning("azure-storage-blob not installed. Azure operations will use mock data.")
            self.azure_available = False
            self.blob_service_client = None
            self.container_client = None
        
        self.container_name = config.get('container_name', 'pala-content')
        self.organize_by_type = config.get('organize_by_type', True)
        self.organize_by_date = config.get('organize_by_date', True)
        self.storage_tier = config.get('storage_tier', 'Hot')
        
        logger.info(f"AzureStorageBackend initialized: container={self.container_name}")
    
    def _get_blob_name(
        self,
        content_id: str,
        content_type: str,
        created_at: Optional[str] = None
    ) -> str:
        """
        Calculate Azure blob name
        
        Args:
            content_id: Content identifier
            content_type: Type of content
            created_at: Creation timestamp
            
        Returns:
            Azure blob name
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
        Write content to Azure
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            
        Returns:
            Azure blob name
        """
        try:
            content_type = metadata.get('content_type', 'unknown')
            created_at = metadata.get('created_at', datetime.now(timezone.utc).isoformat())
            
            blob_name = self._get_blob_name(content_id, content_type, created_at)
            
            if not self.azure_available:
                logger.warning(f"azure-storage-blob not available, using mock write for {content_id}")
                return blob_name
            
            # Upload to Azure
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.upload_blob(content, overwrite=True)
            
            # Set metadata
            blob_client.set_blob_metadata({
                'content-id': content_id,
                'content-type': content_type,
                'created-at': created_at
            })
            
            logger.info(f"Content {content_id} uploaded to Azure: {blob_name}")
            return blob_name
        except Exception as e:
            logger.error(f"Error writing content {content_id} to Azure: {e}")
            raise
    
    async def read(
        self,
        content_id: str,
        location: str
    ) -> bytes:
        """
        Read content from Azure
        
        Args:
            content_id: Content identifier
            location: Azure blob name
            
        Returns:
            Binary content
        """
        try:
            if not self.azure_available:
                logger.warning(f"azure-storage-blob not available, using mock read for {content_id}")
                return b"Mock Azure content for " + content_id.encode()
            
            blob_client = self.container_client.get_blob_client(location)
            content = blob_client.download_blob().readall()
            
            logger.info(f"Content {content_id} read from Azure: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id} from Azure: {e}")
            raise
    
    async def delete(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Delete content from Azure
        
        Args:
            content_id: Content identifier
            location: Azure blob name
            
        Returns:
            True if deleted
        """
        try:
            if not self.azure_available:
                logger.warning(f"azure-storage-blob not available, using mock delete for {content_id}")
                return True
            
            blob_client = self.container_client.get_blob_client(location)
            blob_client.delete_blob()
            
            logger.info(f"Content {content_id} deleted from Azure")
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id} from Azure: {e}")
            raise
    
    async def exists(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Check if content exists in Azure
        
        Args:
            content_id: Content identifier
            location: Azure blob name
            
        Returns:
            True if exists
        """
        try:
            if not self.azure_available:
                return True  # Mock: assume exists
            
            blob_client = self.container_client.get_blob_client(location)
            return blob_client.exists()
        except Exception as e:
            logger.error(f"Error checking existence in Azure: {e}")
            return False
    
    async def get_size(
        self,
        content_id: str,
        location: str
    ) -> int:
        """
        Get content size from Azure
        
        Args:
            content_id: Content identifier
            location: Azure blob name
            
        Returns:
            Size in bytes
        """
        try:
            if not self.azure_available:
                return 1024  # Mock size
            
            blob_client = self.container_client.get_blob_client(location)
            properties = blob_client.get_blob_properties()
            return properties.size
        except Exception as e:
            logger.error(f"Error getting size from Azure: {e}")
            return 0
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content in Azure
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of content IDs
        """
        try:
            if not self.azure_available:
                return []  # Mock
            
            content_ids = []
            blobs = self.container_client.list_blobs(name_starts_with=prefix or '')
            
            for blob in blobs:
                # Extract content-id from blob name
                name_parts = blob.name.split('/')
                filename = name_parts[-1]  # Last part
                content_id = filename.replace('.bin', '')
                content_ids.append(content_id)
            
            logger.info(f"Listed {len(content_ids)} content items from Azure")
            return content_ids
        except Exception as e:
            logger.error(f"Error listing content in Azure: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check Azure backend health
        
        Returns:
            True if backend is healthy
        """
        try:
            if not self.azure_available:
                logger.warning("azure-storage-blob not available")
                return False
            
            # Try to check container
            _ = self.container_client.get_container_properties()
            logger.debug(f"Health check passed for {self.name}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Azure backend statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            if not self.azure_available:
                return {'error': 'azure-storage-blob not available'}
            
            total_size = 0
            total_count = 0
            by_type = {}
            
            blobs = self.container_client.list_blobs()
            
            for blob in blobs:
                total_count += 1
                total_size += blob.size
                
                # Count by content type (first path component)
                name_parts = blob.name.split('/')
                content_type = name_parts[0] if name_parts else 'unknown'
                
                if content_type not in by_type:
                    by_type[content_type] = {'count': 0, 'size': 0}
                
                by_type[content_type]['count'] += 1
                by_type[content_type]['size'] += blob.size
            
            stats = {
                'backend_type': self.backend_type,
                'backend_name': self.name,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'container_name': self.container_name,
                'storage_tier': self.storage_tier
            }
            
            logger.debug(f"Stats for {self.name}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
