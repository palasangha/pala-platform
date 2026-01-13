"""
Image Storage Service using MongoDB GridFS

Stores intermediate images (preprocessed, cropped, enhanced) generated during OCR processing
and provides URLs for retrieval.
"""
import os
import logging
from datetime import datetime
from gridfs import GridFS
from bson import ObjectId

logger = logging.getLogger(__name__)


class ImageStorageService:
    """Service for storing and retrieving images in MongoDB GridFS"""

    def __init__(self, mongo):
        """
        Initialize ImageStorageService

        Args:
            mongo: MongoDB connection (Flask-PyMongo instance)
        """
        self.mongo = mongo
        self.fs = GridFS(mongo.db)

    def store_image(self, image_path, metadata=None):
        """
        Store an image in GridFS

        Args:
            image_path: Path to the image file to store
            metadata: Optional dictionary of metadata to store with the image
                     (e.g., job_id, file_path, processing_stage, dimensions)

        Returns:
            str: GridFS file ID as string, or None if storage failed
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image file does not exist: {image_path}")
                return None

            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # Get file size and extension
            file_size = len(image_data)
            filename = os.path.basename(image_path)
            file_ext = os.path.splitext(filename)[1].lower()

            # Prepare metadata
            storage_metadata = {
                'filename': filename,
                'original_path': image_path,
                'content_type': self._get_content_type(file_ext),
                'size': file_size,
                'uploaded_at': datetime.utcnow(),
            }

            # Merge with provided metadata
            if metadata:
                storage_metadata.update(metadata)

            # Store in GridFS
            file_id = self.fs.put(
                image_data,
                filename=filename,
                metadata=storage_metadata,
                content_type=storage_metadata['content_type']
            )

            logger.info(f"Image stored in GridFS: {filename} (ID: {file_id}, Size: {file_size:,} bytes)")
            return str(file_id)

        except Exception as e:
            logger.error(f"Failed to store image in GridFS: {str(e)}", exc_info=True)
            return None

    def get_image_url(self, file_id, absolute=False, base_url=None):
        """
        Generate URL for retrieving an image from GridFS

        Args:
            file_id: GridFS file ID (string or ObjectId)
            absolute: If True, return absolute HTTPS URL; if False, return relative path
            base_url: Base URL for absolute URLs (e.g., 'https://example.com')
                     If not provided and absolute=True, will use request context

        Returns:
            str: URL to retrieve the image
                 Relative: /api/images/{file_id}
                 Absolute: https://example.com/api/images/{file_id}
        """
        path = f"/api/images/{file_id}"

        if not absolute:
            return path

        # Build absolute URL
        if base_url:
            # Use provided base_url
            return f"{base_url}{path}"

        # Try to get from Flask request context
        try:
            from flask import request
            # Build from request context
            scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
            host = request.headers.get('X-Forwarded-Host', request.host)
            return f"{scheme}://{host}{path}"
        except (RuntimeError, KeyError):
            # No Flask request context, return relative path
            logger.warning("Cannot build absolute URL - no Flask request context available")
            return path

    def retrieve_image(self, file_id):
        """
        Retrieve an image from GridFS

        Args:
            file_id: GridFS file ID (string or ObjectId)

        Returns:
            tuple: (image_data: bytes, metadata: dict) or (None, None) if not found
        """
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)

            # Retrieve from GridFS
            grid_out = self.fs.get(file_id)

            image_data = grid_out.read()
            metadata = {
                'filename': grid_out.filename,
                'content_type': grid_out.content_type,
                'length': grid_out.length,
                'upload_date': grid_out.upload_date,
                'metadata': grid_out.metadata
            }

            logger.info(f"Retrieved image from GridFS: {grid_out.filename} (ID: {file_id})")
            return image_data, metadata

        except Exception as e:
            logger.error(f"Failed to retrieve image from GridFS: {str(e)}", exc_info=True)
            return None, None

    def delete_image(self, file_id):
        """
        Delete an image from GridFS

        Args:
            file_id: GridFS file ID (string or ObjectId)

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)

            self.fs.delete(file_id)
            logger.info(f"Deleted image from GridFS: {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete image from GridFS: {str(e)}", exc_info=True)
            return False

    def delete_images_by_job(self, job_id):
        """
        Delete all images associated with a job

        Args:
            job_id: Job ID to delete images for

        Returns:
            int: Number of images deleted
        """
        try:
            deleted_count = 0

            # Find all files with this job_id in metadata
            cursor = self.fs.find({'metadata.job_id': job_id})

            for grid_out in cursor:
                self.fs.delete(grid_out._id)
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} images for job {job_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete images for job {job_id}: {str(e)}", exc_info=True)
            return 0

    def _get_content_type(self, file_ext):
        """
        Get MIME content type from file extension

        Args:
            file_ext: File extension (e.g., '.jpg', '.png')

        Returns:
            str: MIME content type
        """
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.webp': 'image/webp'
        }
        return content_types.get(file_ext.lower(), 'application/octet-stream')

    def get_image_info(self, file_id, absolute=False, base_url=None):
        """
        Get metadata about an image without retrieving the full content

        Args:
            file_id: GridFS file ID (string or ObjectId)
            absolute: If True, return absolute HTTPS URL; if False, return relative path
            base_url: Base URL for absolute URLs (e.g., 'https://example.com')

        Returns:
            dict: Image metadata or None if not found
        """
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)

            grid_out = self.fs.get(file_id)

            return {
                'file_id': str(file_id),
                'filename': grid_out.filename,
                'content_type': grid_out.content_type,
                'size': grid_out.length,
                'upload_date': grid_out.upload_date,
                'metadata': grid_out.metadata,
                'url': self.get_image_url(file_id, absolute=absolute, base_url=base_url)
            }

        except Exception as e:
            logger.error(f"Failed to get image info: {str(e)}", exc_info=True)
            return None
