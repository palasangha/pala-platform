"""
AWS S3 Storage Backend

Stores content on Amazon S3 for scalability and durability.
Supports bucket organization, lifecycle policies, and versioning.

Configuration:
{
    'aws_access_key_id': '...',
    'aws_secret_access_key': '...',
    'bucket_name': 'pala-content',
    'region': 'us-east-1',
    'organize_by_type': True,
    'organize_by_date': True,
    'storage_class': 'STANDARD'  # STANDARD, INTELLIGENT_TIERING, GLACIER, etc.
}
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base import StorageBackend

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize S3 storage backend
        
        Args:
            name: Backend name (e.g., 's3-primary')
            config: Configuration dict with AWS credentials and bucket info
        """
        super().__init__(name, config)
        
        # Check for boto3
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.get('aws_access_key_id'),
                aws_secret_access_key=config.get('aws_secret_access_key'),
                region_name=config.get('region', 'us-east-1')
            )
            self.boto3_available = True
        except ImportError:
            logger.warning("boto3 not installed. S3 operations will use mock data.")
            self.boto3_available = False
            self.s3_client = None
        
        self.bucket_name = config.get('bucket_name', 'pala-content')
        self.organize_by_type = config.get('organize_by_type', True)
        self.organize_by_date = config.get('organize_by_date', True)
        self.storage_class = config.get('storage_class', 'STANDARD')
        
        logger.info(f"S3StorageBackend initialized: bucket={self.bucket_name}, region={config.get('region', 'us-east-1')}")
    
    def _get_object_key(
        self,
        content_id: str,
        content_type: str,
        created_at: Optional[str] = None
    ) -> str:
        """
        Calculate S3 object key
        
        Args:
            content_id: Content identifier
            content_type: Type of content
            created_at: Creation timestamp
            
        Returns:
            S3 object key
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
        Write content to S3
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            
        Returns:
            S3 object key
        """
        try:
            content_type = metadata.get('content_type', 'unknown')
            created_at = metadata.get('created_at', datetime.now(timezone.utc).isoformat())
            
            object_key = self._get_object_key(content_id, content_type, created_at)
            
            if not self.boto3_available:
                logger.warning(f"boto3 not available, using mock write for {content_id}")
                return object_key
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=content,
                ContentType='application/octet-stream',
                StorageClass=self.storage_class,
                Metadata={
                    'content-id': content_id,
                    'content-type': content_type,
                    'created-at': created_at
                }
            )
            
            logger.info(f"Content {content_id} uploaded to S3: s3://{self.bucket_name}/{object_key}")
            return object_key
        except Exception as e:
            logger.error(f"Error writing content {content_id} to S3: {e}")
            raise
    
    async def read(
        self,
        content_id: str,
        location: str
    ) -> bytes:
        """
        Read content from S3
        
        Args:
            content_id: Content identifier
            location: S3 object key
            
        Returns:
            Binary content
        """
        try:
            if not self.boto3_available:
                logger.warning(f"boto3 not available, using mock read for {content_id}")
                return b"Mock S3 content for " + content_id.encode()
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=location
            )
            
            content = response['Body'].read()
            logger.info(f"Content {content_id} read from S3: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id} from S3: {e}")
            raise
    
    async def delete(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Delete content from S3
        
        Args:
            content_id: Content identifier
            location: S3 object key
            
        Returns:
            True if deleted
        """
        try:
            if not self.boto3_available:
                logger.warning(f"boto3 not available, using mock delete for {content_id}")
                return True
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=location
            )
            
            logger.info(f"Content {content_id} deleted from S3")
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id} from S3: {e}")
            raise
    
    async def exists(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Check if content exists in S3
        
        Args:
            content_id: Content identifier
            location: S3 object key
            
        Returns:
            True if exists
        """
        try:
            if not self.boto3_available:
                return True  # Mock: assume exists
            
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=location
            )
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"Error checking existence in S3: {e}")
            return False
    
    async def get_size(
        self,
        content_id: str,
        location: str
    ) -> int:
        """
        Get content size from S3
        
        Args:
            content_id: Content identifier
            location: S3 object key
            
        Returns:
            Size in bytes
        """
        try:
            if not self.boto3_available:
                return 1024  # Mock size
            
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=location
            )
            return response['ContentLength']
        except Exception as e:
            logger.error(f"Error getting size from S3: {e}")
            return 0
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content in S3
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of content IDs
        """
        try:
            if not self.boto3_available:
                return []  # Mock
            
            content_ids = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix or ''
            )
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    # Extract content-id from key
                    key_parts = obj['Key'].split('/')
                    filename = key_parts[-1]  # Last part
                    content_id = filename.replace('.bin', '')
                    content_ids.append(content_id)
            
            logger.info(f"Listed {len(content_ids)} content items from S3")
            return content_ids
        except Exception as e:
            logger.error(f"Error listing content in S3: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check S3 backend health
        
        Returns:
            True if backend is healthy
        """
        try:
            if not self.boto3_available:
                logger.warning("boto3 not available")
                return False
            
            # Try to list bucket (minimal operation)
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"Health check passed for {self.name}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get S3 backend statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            if not self.boto3_available:
                return {'error': 'boto3 not available'}
            
            total_size = 0
            total_count = 0
            by_type = {}
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    total_count += 1
                    total_size += obj['Size']
                    
                    # Count by content type (first path component)
                    key_parts = obj['Key'].split('/')
                    content_type = key_parts[0] if key_parts else 'unknown'
                    
                    if content_type not in by_type:
                        by_type[content_type] = {'count': 0, 'size': 0}
                    
                    by_type[content_type]['count'] += 1
                    by_type[content_type]['size'] += obj['Size']
            
            stats = {
                'backend_type': self.backend_type,
                'backend_name': self.name,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'bucket_name': self.bucket_name,
                'region': self.s3_client.meta.region_name
            }
            
            logger.debug(f"Stats for {self.name}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
