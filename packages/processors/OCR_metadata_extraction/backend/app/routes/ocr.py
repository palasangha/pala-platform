from flask import Blueprint, request, jsonify, send_file, current_app
from app.models import mongo
from app.models.image import Image
from app.models.project import Project
from app.utils.decorators import token_required
from app.services.ocr_service import OCRService
from app.services.storage import StorageService
from app.config import Config
import os
import mimetypes

ocr_bp = Blueprint('ocr', __name__)

# Initialize services
ocr_service = OCRService()
storage_service = StorageService(Config.UPLOAD_FOLDER, Config.ALLOWED_EXTENSIONS)

@ocr_bp.route('/providers', methods=['GET'])
@token_required
def get_providers(current_user_id):
    """Get available OCR providers"""
    try:
        providers = ocr_service.get_available_providers()
        return jsonify({'providers': providers}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/process/<image_id>', methods=['POST'])
@token_required
def process_image(current_user_id, image_id):
    """Process an image with OCR"""
    try:
        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Verify user owns the project
        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get processing options
        data = request.get_json() or {}
        languages = data.get('languages', ['en', 'hi'])  # Default: English and Hindi
        handwriting = data.get('handwriting', False)
        provider = data.get('provider', None)  # OCR provider to use
        custom_prompt = data.get('custom_prompt', None)  # Custom prompt for AI providers

        # Update status to processing
        Image.update_status(mongo, image_id, 'processing')

        try:
            # Process image with selected provider
            result = ocr_service.process_image(
                image['filepath'],
                languages=languages,
                handwriting=handwriting,
                provider=provider,
                custom_prompt=custom_prompt
            )

            # Update image with OCR text
            Image.update_ocr_text(mongo, image_id, result['text'], 'completed')

            return jsonify({
                'message': 'OCR processing completed',
                'image_id': image_id,
                'text': result['text'],
                'confidence': result.get('confidence', 0),
                'blocks': result.get('blocks', []),
                'provider': result.get('provider', 'unknown')
            }), 200

        except Exception as e:
            # Update status to failed
            Image.update_status(mongo, image_id, 'failed')
            return jsonify({'error': f'OCR processing failed: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/image/<image_id>', methods=['GET'])
@token_required
def get_image(current_user_id, image_id):
    """Get image file"""
    try:
        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Verify user owns the project
        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        # Check if file exists
        filepath = image.get('filepath')
        if not filepath:
            return jsonify({'error': 'File path not stored in database'}), 400
        
        # Try multiple path resolution strategies
        full_path = None
        
        # Strategy 1: If it's an absolute path, use it directly
        if os.path.isabs(filepath):
            if os.path.exists(filepath):
                full_path = filepath
        else:
            # Strategy 2: Try prepending /app/
            candidate = os.path.join('/app', filepath)
            if os.path.exists(candidate):
                full_path = candidate
            
            # Strategy 3: Try relative to uploads folder
            if not full_path:
                candidate = os.path.join(Config.UPLOAD_FOLDER, filepath)
                if os.path.exists(candidate):
                    full_path = candidate
            
            # Strategy 4: Try relative to current working directory
            if not full_path:
                if os.path.exists(filepath):
                    full_path = filepath
            
            # Strategy 5: Try relative to app root directory
            if not full_path:
                app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                candidate = os.path.join(app_root, filepath)
                if os.path.exists(candidate):
                    full_path = candidate
        
        if not full_path:
            return jsonify({'error': f'File not found at any path. Database path: {filepath}'}), 404
        
        filepath = full_path

        # Guess mimetype from file extension; fall back to sensible defaults
        mimetype, _ = mimetypes.guess_type(filepath)
        if not mimetype:
            # If filename ends with .pdf assume PDF, otherwise image/jpeg
            if filepath.lower().endswith('.pdf') or image.get('original_filename', '').lower().endswith('.pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = 'image/jpeg'

        # Log for debugging: file path and detected mimetype
        try:
            current_app.logger.info(f"Serving file {filepath} with mimetype {mimetype}")
        except Exception:
            # If current_app isn't available for some reason, silently ignore logging
            pass

        return send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=False
        )

    except Exception as e:
        import traceback
        try:
            current_app.logger.error(f"Error serving image {image_id}: {str(e)}\n{traceback.format_exc()}")
        except:
            print(f"Error serving image {image_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Error serving image: {str(e)}'}), 500

@ocr_bp.route('/image/<image_id>/details', methods=['GET'])
@token_required
def get_image_details(current_user_id, image_id):
    """Get image details including OCR text"""
    try:
        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Verify user owns the project
        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        return jsonify({
            'image': Image.to_dict(image)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/image/<image_id>/text', methods=['PUT'])
@token_required
def update_image_text(current_user_id, image_id):
    """Update OCR text for an image (manual correction)"""
    try:
        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Verify user owns the project
        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get new text
        data = request.get_json()
        new_text = data.get('text')

        if new_text is None:
            return jsonify({'error': 'Text is required'}), 400

        # Update text
        Image.update_ocr_text(mongo, image_id, new_text, 'completed')

        # Get updated image
        updated_image = Image.find_by_id(mongo, image_id)

        return jsonify({
            'message': 'Text updated successfully',
            'image': Image.to_dict(updated_image)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/batch-process', methods=['POST'])
@token_required
def batch_process_images(current_user_id):
    """Process multiple images with OCR"""
    try:
        data = request.get_json()
        image_ids = data.get('image_ids', [])
        languages = data.get('languages', ['en', 'hi'])
        handwriting = data.get('handwriting', False)
        provider = data.get('provider', None)  # OCR provider to use
        custom_prompt = data.get('custom_prompt', None)  # Custom prompt for AI providers

        if not image_ids:
            return jsonify({'error': 'No image IDs provided'}), 400

        results = []
        for image_id in image_ids:
            # Get image
            image = Image.find_by_id(mongo, image_id)
            if not image:
                results.append({
                    'image_id': image_id,
                    'status': 'error',
                    'error': 'Image not found'
                })
                continue

            # Verify user owns the project
            project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
            if not project:
                results.append({
                    'image_id': image_id,
                    'status': 'error',
                    'error': 'Unauthorized'
                })
                continue

            # Update status to processing
            Image.update_status(mongo, image_id, 'processing')

            try:
                # Process image with selected provider
                result = ocr_service.process_image(
                    image['filepath'],
                    languages=languages,
                    handwriting=handwriting,
                    provider=provider,
                    custom_prompt=custom_prompt
                )

                # Update image with OCR text
                Image.update_ocr_text(mongo, image_id, result['text'], 'completed')

                results.append({
                    'image_id': image_id,
                    'status': 'completed',
                    'text': result['text'],
                    'provider': result.get('provider', 'unknown')
                })

            except Exception as e:
                # Update status to failed
                Image.update_status(mongo, image_id, 'failed')
                results.append({
                    'image_id': image_id,
                    'status': 'failed',
                    'error': str(e)
                })

        return jsonify({
            'message': 'Batch processing completed',
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/add-to-project', methods=['POST'])
@token_required
def add_image_to_project(current_user_id):
    """Add an image with OCR text to a project from bulk job results"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        filename = data.get('filename')
        file_path = data.get('file_path')
        ocr_text = data.get('ocr_text')
        confidence = data.get('confidence', 0)
        language = data.get('language', 'en')
        provider = data.get('provider', 'bulk')

        if not project_id or not filename:
            return jsonify({'error': 'project_id and filename are required'}), 400

        # Verify user owns the project
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found or unauthorized'}), 404

        # Create image record
        image = Image.create(mongo, project_id, filename, file_path, filename)
        
        # Update with OCR text
        if ocr_text:
            Image.update_ocr_text(mongo, image['_id'], ocr_text, 'completed')

        return jsonify({
            'message': 'Image added to project',
            'image': Image.to_dict(image)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
