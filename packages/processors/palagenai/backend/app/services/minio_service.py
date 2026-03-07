"""
MinIO S3 Storage Service for Archipelago file uploads
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote
from minio import Minio
from minio.error import S3Error
from app.config import Config

logger = logging.getLogger(__name__)


class MinIOService:
    """Service for uploading files to MinIO S3 storage"""

    def __init__(self):
        self.endpoint = Config.MINIO_ENDPOINT  # Internal endpoint for MinIO client
        self.public_endpoint = Config.MINIO_PUBLIC_ENDPOINT  # Public endpoint for browser access
        self.access_key = Config.MINIO_ACCESS_KEY
        self.secret_key = Config.MINIO_SECRET_KEY
        self.bucket_name = Config.MINIO_BUCKET
        self.secure = Config.MINIO_SECURE  # For internal endpoint
        self.public_secure = Config.MINIO_PUBLIC_SECURE  # For public endpoint
        self.enabled = Config.MINIO_ENABLED
        self.client = None

    def _get_client(self) -> Optional[Minio]:
        """Get or create MinIO client"""
        if not self.enabled:
            logger.warning("MinIO is disabled")
            return None

        if self.client is None:
            try:
                self.client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure
                )
                logger.info(f"Connected to MinIO at {self.endpoint}")
            except Exception as e:
                logger.error(f"Failed to create MinIO client: {str(e)}")
                return None

        return self.client

    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        Ensure the bucket exists, create if it doesn't

        Args:
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if bucket exists or was created, False otherwise
        """
        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return False

        try:
            bucket_created = False
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                bucket_created = True
                logger.info(f"Created MinIO bucket: {bucket_name}")
            else:
                logger.debug(f"MinIO bucket already exists: {bucket_name}")

            # Set bucket policy to allow public read access (download)
            # This is needed for Archipelago to access files
            if bucket_created or bucket_name == self.bucket_name:
                try:
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                            }
                        ]
                    }
                    import json
                    client.set_bucket_policy(bucket_name, json.dumps(policy))
                    logger.info(f"Set public read policy on bucket: {bucket_name}")
                except Exception as e:
                    logger.warning(f"Could not set bucket policy (files may not be publicly accessible): {str(e)}")

            return True
        except S3Error as e:
            logger.error(f"Error checking/creating bucket {bucket_name}: {str(e)}")
            return False

    def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a file to MinIO

        Args:
            file_path: Path to the file to upload
            object_name: Name for the object in MinIO (uses filename if not provided)
            bucket_name: Bucket name (uses default if not provided)
            content_type: MIME type of the file (auto-detected if not provided)

        Returns:
            Dictionary with upload info or None if failed
        """
        if not self.enabled:
            logger.warning("MinIO is disabled, skipping file upload")
            return None

        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return None

        # Resolve file path
        if not os.path.isabs(file_path):
            gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')
            gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))

            if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                file_path = file_path[len(gvpocr_basename) + 1:]

            file_path = os.path.join(gvpocr_path, file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        # Get object name
        if not object_name:
            object_name = os.path.basename(file_path)

        # Auto-detect content type if not provided
        if not content_type:
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists(bucket_name):
                return None

            # Get file size
            file_size = os.path.getsize(file_path)

            # Upload file
            logger.info(f"Uploading file to MinIO: {object_name} ({file_size} bytes)")
            result = client.fput_object(
                bucket_name,
                object_name,
                file_path,
                content_type=content_type
            )

            # Generate the S3 URL
            s3_url = f"s3://{bucket_name}/{object_name}"

            # Generate HTTP URL using public endpoint (for browser access)
            # URL-encode the object name to handle spaces and special characters
            encoded_object_name = quote(object_name, safe='')
            http_url = f"{'https' if self.public_secure else 'http'}://{self.public_endpoint}/{bucket_name}/{encoded_object_name}"

            logger.info(f"Successfully uploaded file to MinIO: {s3_url}")
            logger.info(f"Public HTTP URL: {http_url}")

            return {
                'success': True,
                'bucket': bucket_name,
                'object_name': object_name,
                's3_url': s3_url,
                'http_url': http_url,
                'etag': result.etag,
                'size': file_size,
                'content_type': content_type
            }

        except S3Error as e:
            logger.error(f"S3 error uploading file to MinIO: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to MinIO: {str(e)}", exc_info=True)
            return None

    def upload_file_data(
        self,
        file_data: bytes,
        object_name: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload file data (bytes) to MinIO

        Args:
            file_data: File data as bytes
            object_name: Name for the object in MinIO
            bucket_name: Bucket name (uses default if not provided)
            content_type: MIME type of the file

        Returns:
            Dictionary with upload info or None if failed
        """
        if not self.enabled:
            logger.warning("MinIO is disabled, skipping file upload")
            return None

        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return None

        if not content_type:
            content_type = 'application/octet-stream'

        try:
            # Ensure bucket exists
            if not self.ensure_bucket_exists(bucket_name):
                return None

            # Upload file data
            from io import BytesIO
            file_size = len(file_data)

            logger.info(f"Uploading file data to MinIO: {object_name} ({file_size} bytes)")
            result = client.put_object(
                bucket_name,
                object_name,
                BytesIO(file_data),
                length=file_size,
                content_type=content_type
            )

            # Generate the S3 URL
            s3_url = f"s3://{bucket_name}/{object_name}"

            # Generate HTTP URL using public endpoint (for browser access)
            # URL-encode the object name to handle spaces and special characters
            encoded_object_name = quote(object_name, safe='')
            http_url = f"{'https' if self.public_secure else 'http'}://{self.public_endpoint}/{bucket_name}/{encoded_object_name}"

            logger.info(f"Successfully uploaded file data to MinIO: {s3_url}")
            logger.info(f"Public HTTP URL: {http_url}")

            return {
                'success': True,
                'bucket': bucket_name,
                'object_name': object_name,
                's3_url': s3_url,
                'http_url': http_url,
                'etag': result.etag,
                'size': file_size,
                'content_type': content_type
            }

        except S3Error as e:
            logger.error(f"S3 error uploading file data to MinIO: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file data to MinIO: {str(e)}", exc_info=True)
            return None

    def file_exists(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Check if a file exists in MinIO

        Args:
            object_name: Name of the object in MinIO
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if file exists, False otherwise
        """
        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return False

        try:
            client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence in MinIO: {str(e)}")
            return False

    def get_file_info(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get file information from MinIO

        Args:
            object_name: Name of the object in MinIO
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            Dictionary with file info or None if not found
        """
        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return None

        try:
            stat = client.stat_object(bucket_name, object_name)

            s3_url = f"s3://{bucket_name}/{object_name}"
            # Use public endpoint for external access
            # URL-encode the object name to handle spaces and special characters
            encoded_object_name = quote(object_name, safe='')
            http_url = f"{'https' if self.public_secure else 'http'}://{self.public_endpoint}/{bucket_name}/{encoded_object_name}"

            return {
                'object_name': object_name,
                'bucket': bucket_name,
                's3_url': s3_url,
                'http_url': http_url,
                'size': stat.size,
                'etag': stat.etag,
                'content_type': stat.content_type,
                'last_modified': stat.last_modified.isoformat() if stat.last_modified else None
            }

        except S3Error as e:
            logger.error(f"File not found in MinIO: {object_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info from MinIO: {str(e)}")
            return None

    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Delete a file from MinIO

        Args:
            object_name: Name of the object in MinIO
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if deleted successfully, False otherwise
        """
        bucket_name = bucket_name or self.bucket_name
        client = self._get_client()

        if not client:
            return False

        try:
            client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted file from MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file from MinIO: {str(e)}")
            return False

    def check_connection(self) -> bool:
        """
        Test connection to MinIO

        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled:
            return False

        client = self._get_client()

        if not client:
            return False

        try:
            # Try to list buckets as a connection test
            client.list_buckets()
            logger.info("Successfully connected to MinIO")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {str(e)}")
            return False
