"""
Image API Routes

Provides endpoints for retrieving intermediate images stored in GridFS
"""
from flask import Blueprint, send_file, jsonify, request
from io import BytesIO
import logging

from app.services.image_storage_service import ImageStorageService
from app.models import mongo

logger = logging.getLogger(__name__)

images_bp = Blueprint('images', __name__)


@images_bp.route('/api/images/<file_id>', methods=['GET'])
def get_image(file_id):
    """
    Retrieve an image from GridFS

    Args:
        file_id: GridFS file ID

    Returns:
        Image file with appropriate content type
    """
    try:
        # Initialize image storage service
        image_storage = ImageStorageService(mongo)

        # Retrieve image
        image_data, metadata = image_storage.retrieve_image(file_id)

        if image_data is None:
            return jsonify({'error': 'Image not found'}), 404

        # Create BytesIO object from image data
        image_io = BytesIO(image_data)
        image_io.seek(0)

        # Send file with appropriate content type
        return send_file(
            image_io,
            mimetype=metadata.get('content_type', 'image/jpeg'),
            as_attachment=False,
            download_name=metadata.get('filename', f'{file_id}.jpg')
        )

    except Exception as e:
        logger.error(f"Error retrieving image {file_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to retrieve image'}), 500


@images_bp.route('/api/images/<file_id>/info', methods=['GET'])
def get_image_info(file_id):
    """
    Get metadata about an image without downloading it

    Args:
        file_id: GridFS file ID

    Returns:
        JSON with image metadata
    """
    try:
        # Initialize image storage service
        image_storage = ImageStorageService(mongo)

        # Get image info
        info = image_storage.get_image_info(file_id)

        if info is None:
            return jsonify({'error': 'Image not found'}), 404

        return jsonify(info), 200

    except Exception as e:
        logger.error(f"Error getting image info {file_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get image info'}), 500


@images_bp.route('/api/images/<file_id>', methods=['DELETE'])
def delete_image(file_id):
    """
    Delete an image from GridFS

    Args:
        file_id: GridFS file ID

    Returns:
        JSON confirmation
    """
    try:
        # Initialize image storage service
        image_storage = ImageStorageService(mongo)

        # Delete image
        success = image_storage.delete_image(file_id)

        if not success:
            return jsonify({'error': 'Failed to delete image'}), 500

        return jsonify({'message': 'Image deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting image {file_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to delete image'}), 500
