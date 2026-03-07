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
import subprocess

ocr_bp = Blueprint('ocr', __name__)

# Initialize services
ocr_service = OCRService()
storage_service = StorageService(Config.UPLOAD_FOLDER, Config.ALLOWED_EXTENSIONS)

# TagGUI configuration
TAGGUI_PATH = os.environ.get(
    'TAGGUI_PATH',
    '/mnt/sda1/mango1_home/Downloads/taggui-v1.32.2-linux/taggui'
)
TAGGUI_WORK_ROOT = '/tmp/palagenai_taggui'


def _resolve_filepath(image):
    """Resolve the actual filesystem path for an image record (5-strategy lookup).

    Returns the resolved path string, or None if the file cannot be found.
    """
    filepath = image.get('filepath')
    if not filepath:
        return None

    # Strategy 1: absolute path used directly
    if os.path.isabs(filepath):
        if os.path.exists(filepath):
            return filepath
        return None

    # Strategy 2: prepend /app/
    candidate = os.path.join('/app', filepath)
    if os.path.exists(candidate):
        return candidate

    # Strategy 3: relative to uploads folder
    candidate = os.path.join(Config.UPLOAD_FOLDER, filepath)
    if os.path.exists(candidate):
        return candidate

    # Strategy 4: relative to current working directory
    if os.path.exists(filepath):
        return filepath

    # Strategy 5: relative to app root directory
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    candidate = os.path.join(app_root, filepath)
    if os.path.exists(candidate):
        return candidate

    return None

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
        if not image.get('filepath'):
            return jsonify({'error': 'File path not stored in database'}), 400

        filepath = _resolve_filepath(image)
        if not filepath:
            return jsonify({'error': f'File not found at any path. Database path: {image.get("filepath")}'}), 404

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
    """Add an image with OCR text and enrichment to a project from bulk job results"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        filename = data.get('filename')
        file_path = data.get('file_path')
        ocr_text = data.get('ocr_text')
        enrichment = data.get('enrichment')  # NEW: Accept enrichment data
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

        # Update with enrichment data (NEW)
        if enrichment:
            Image.update_enrichment(mongo, image['_id'], enrichment)

        return jsonify({
            'message': 'Image added to project',
            'image': Image.to_dict(image)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/image/<image_id>/enrichment', methods=['GET'])
@token_required
def get_image_enrichment(current_user_id, image_id):
    """Get enrichment data for a project image"""
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
            'success': True,
            'enrichment': image.get('enrichment_data'),
            'enrichment_status': image.get('enrichment_status', 'pending'),
            'enriched_at': image['enriched_at'].isoformat() if image.get('enriched_at') else None,
            'enrichment_edited_at': image['enrichment_edited_at'].isoformat() if image.get('enrichment_edited_at') else None,
            'enrichment_edited_by': str(image['enrichment_edited_by']) if image.get('enrichment_edited_by') else None
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/image/<image_id>/enrichment', methods=['PUT'])
@token_required
def update_image_enrichment(current_user_id, image_id):
    """
    Update enrichment data for a project image

    Request Body:
    {
        "enrichment": {
            "filename": "doc.pdf",
            "ocr_text": "...",
            "raw_mcp_responses": {...},
            "merged_result": {...}
        }
    }
    """
    try:
        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Verify user owns the project
        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get enrichment data from request
        data = request.get_json()
        enrichment_data = data.get('enrichment')

        if not enrichment_data:
            return jsonify({'error': 'enrichment data is required'}), 400

        # Update enrichment
        Image.update_enrichment(mongo, image_id, enrichment_data, edited_by=current_user_id)

        # Get updated image
        updated_image = Image.find_by_id(mongo, image_id)

        return jsonify({
            'success': True,
            'message': 'Enrichment data updated successfully',
            'image': Image.to_dict(updated_image)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/image/<image_id>/taggui/open', methods=['POST'])
@token_required
def open_in_taggui(current_user_id, image_id):
    """Prepare a work directory and launch TagGUI for annotation"""
    try:
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        project = Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Unauthorized'}), 403

        filepath = _resolve_filepath(image)
        if not filepath:
            return jsonify({'error': f'File not found. Database path: {image.get("filepath")}'}), 404

        # Create per-image work dir
        work_dir = os.path.join(TAGGUI_WORK_ROOT, image_id)
        os.makedirs(work_dir, exist_ok=True)

        # Symlink image into work dir (avoid copying large files)
        img_basename = os.path.basename(filepath)
        dest_img = os.path.join(work_dir, img_basename)
        if not os.path.exists(dest_img):
            os.symlink(filepath, dest_img)

        # Write current OCR text as .txt file (TagGUI annotation format)
        txt_basename = os.path.splitext(img_basename)[0] + '.txt'
        txt_path = os.path.join(work_dir, txt_basename)
        ocr_text = image.get('ocr_text') or ''
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(ocr_text)

        # Launch TagGUI (non-blocking)
        env = {**os.environ, 'DISPLAY': os.environ.get('DISPLAY', ':0')}
        subprocess.Popen([TAGGUI_PATH], env=env)

        return jsonify({'work_dir': work_dir, 'txt_file': txt_basename, 'status': 'launched'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/image/<image_id>/taggui/sync', methods=['GET'])
@token_required
def sync_from_taggui(current_user_id, image_id):
    """Read annotation .txt back from the TagGUI work directory"""
    try:
        image = Image.find_by_id(mongo, image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        Project.find_by_id(mongo, str(image['project_id']), user_id=current_user_id)

        filepath = _resolve_filepath(image)
        if not filepath:
            return jsonify({'error': f'File not found. Database path: {image.get("filepath")}'}), 404

        img_basename = os.path.basename(filepath)
        txt_basename = os.path.splitext(img_basename)[0] + '.txt'
        txt_path = os.path.join(TAGGUI_WORK_ROOT, image_id, txt_basename)

        if not os.path.exists(txt_path):
            return jsonify({'error': 'No TagGUI annotation file found. Open in TagGUI first.'}), 404

        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()

        return jsonify({'text': text}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
