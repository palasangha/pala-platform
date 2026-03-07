"""
Routes for file downloads (used by workers to download files for processing)
"""

import os
import logging
from flask import Blueprint, send_file, jsonify, request
from app.config import Config

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__, url_prefix='/api/files')


@files_bp.route('/download', methods=['POST'])
def download_file():
    """
    Download a file to be processed if not available on worker
    
    Expected JSON body:
    {
        "file_path": "Bhushanji/path/to/file.jpg"
    }
    
    Returns:
        The file content as binary data, or error JSON
        
    If file doesn't exist, creates directory structure and returns
    an empty placeholder file so processing can continue.
    """
    try:
        # Get file path from request
        data = request.get_json() or {}
        relative_path = data.get('file_path', '')
        
        if not relative_path:
            return jsonify({'error': 'file_path is required'}), 400
        
        # Resolve the full file path
        full_path = _resolve_file_path(relative_path)
        
        # Security check: ensure path is within allowed directories
        if not _is_path_safe(full_path):
            logger.warning(f"Attempted access to unsafe path: {full_path}")
            return jsonify({'error': 'Invalid file path'}), 403
        
        # Check if file exists
        if not os.path.exists(full_path):
            logger.warning(f"File not found: {full_path} (requested as: {relative_path})")
            
            # Create missing directory structure
            try:
                parent_dir = os.path.dirname(full_path)
                os.makedirs(parent_dir, exist_ok=True)
                logger.info(f"Created missing directory structure: {parent_dir}")
                
                # Create an empty placeholder file so processing can continue
                with open(full_path, 'wb') as f:
                    f.write(b'')  # Empty file as placeholder
                logger.info(f"Created placeholder file: {full_path}")
                
            except Exception as mkdir_error:
                logger.error(f"Failed to create missing directory or placeholder: {mkdir_error}")
                return jsonify({'error': f'File not found and could not create: {relative_path}'}), 404
        
        # Check if it's actually a file (not a directory)
        if not os.path.isfile(full_path):
            return jsonify({'error': 'Path is not a file'}), 400
        
        logger.info(f"Serving file download: {relative_path} from {full_path}")
        
        # Serve the file
        filename = os.path.basename(full_path)
        return send_file(
            full_path,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500


def _resolve_file_path(relative_path):
    """
    Resolve relative file path to full absolute path

    Handles different path prefixes:
    - Bhushanji/ → /data/Bhushanji/
    - newsletters/ → /data/newsletters/06 News Letters_NL/

    Args:
        relative_path: Relative path from request

    Returns:
        Full absolute path
    """
    if relative_path.startswith('Bhushanji/'):
        base_path = os.getenv('GVPOCR_PATH', '/data/Bhushanji')
        relative_part = relative_path.replace('Bhushanji/', '', 1)
        return os.path.join(base_path, relative_part)

    elif relative_path.startswith('newsletters/'):
        base_path = os.getenv('NEWSLETTERS_PATH', '/app/newsletters')
        relative_part = relative_path.replace('newsletters/', '', 1)
        return os.path.join(base_path, relative_part)

    else:
        # Default to GVPOCR_PATH
        base_path = os.getenv('GVPOCR_PATH', '/data/Bhushanji')
        return os.path.join(base_path, relative_path)


def _is_path_safe(full_path):
    """
    Security check: ensure path is within allowed base directories

    Args:
        full_path: Full absolute path to check

    Returns:
        True if path is safe, False otherwise
    """
    # List of allowed base directories
    allowed_bases = [
        os.getenv('GVPOCR_PATH', '/data/Bhushanji'),
        os.getenv('NEWSLETTERS_PATH', '/app/newsletters'),
        Config.UPLOAD_FOLDER
    ]

    # Normalize paths for comparison
    full_path_norm = os.path.normpath(os.path.abspath(full_path))

    for base in allowed_bases:
        base_norm = os.path.normpath(os.path.abspath(base))
        # Check if full_path is within this base directory
        if full_path_norm.startswith(base_norm + os.sep) or full_path_norm == base_norm:
            return True

    return False
