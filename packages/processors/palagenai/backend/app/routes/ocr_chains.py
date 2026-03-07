"""
OCR Chain routes - Template CRUD and chain execution endpoints
"""

import logging
import os
from flask import Blueprint, jsonify, request, send_file
from app.utils.decorators import token_required
from app.models.ocr_chain_template import OCRChainTemplate
from app.models.bulk_job import BulkJob
from app.services.ocr_chain_service import OCRChainService
from app.config import Config
from bson import ObjectId

logger = logging.getLogger(__name__)

ocr_chains_bp = Blueprint('ocr_chains', __name__, url_prefix='/api/ocr-chains')

ocr_chain_service = OCRChainService()


# ============================================================================
# Helper Functions
# ============================================================================

def validate_chain_config(steps):
    """
    Validate chain configuration
    Returns tuple of (is_valid, error_msg)
    """
    return OCRChainTemplate.validate_chain(steps)


# ============================================================================
# Utility Endpoints
# ============================================================================

@ocr_chains_bp.route('/folders', methods=['GET'])
@token_required
def list_folders(current_user_id):
    """List folders at a given path"""
    try:
        path = request.args.get('path', '')

        # Validate path is provided
        if not path:
            return jsonify({
                'error': 'Path parameter required',
                'success': False
            }), 400

        # Validate path exists
        if not os.path.exists(path):
            return jsonify({
                'error': f'Path does not exist: {path}',
                'success': False
            }), 404

        # Validate path is a directory
        if not os.path.isdir(path):
            return jsonify({
                'error': f'Path is not a directory: {path}',
                'success': False
            }), 400

        # Check read permissions
        if not os.access(path, os.R_OK):
            return jsonify({
                'error': f'Permission denied: {path}',
                'success': False
            }), 403

        # List directories
        folders = []
        try:
            items = os.listdir(path)
            for item in sorted(items):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path) and not item.startswith('.'):
                    try:
                        if os.access(full_path, os.R_OK):
                            folders.append({
                                'name': item,
                                'path': full_path,
                                'is_readable': True
                            })
                    except (OSError, PermissionError):
                        folders.append({
                            'name': item,
                            'path': full_path,
                            'is_readable': False
                        })
        except (OSError, PermissionError) as e:
            logger.error(f"Error listing directories in {path}: {str(e)}")
            return jsonify({
                'error': f'Failed to list directories: {str(e)}',
                'success': False
            }), 500

        return jsonify({
            'success': True,
            'path': path,
            'folders': folders,
            'total': len(folders)
        }), 200

    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


# ============================================================================
# Chain Template CRUD Endpoints
# ============================================================================

@ocr_chains_bp.route('/templates', methods=['GET'])
@token_required
def list_templates(current_user_id):
    """Get list of user's chain templates"""
    try:
        from app.models import mongo

        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 50, type=int)

        templates = OCRChainTemplate.find_by_user(mongo, current_user_id, skip, limit)
        count = OCRChainTemplate.count_by_user(mongo, current_user_id)

        return jsonify({
            'success': True,
            'templates': [OCRChainTemplate.to_dict(t) for t in templates],
            'total': count,
            'skip': skip,
            'limit': limit
        }), 200

    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/templates', methods=['POST'])
@token_required
def create_template(current_user_id):
    """Create new chain template"""
    try:
        from app.models import mongo

        data = request.get_json()

        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Template name required'}), 400

        if not data.get('steps') or len(data['steps']) == 0:
            return jsonify({'error': 'Chain must have at least one step'}), 400

        # Validate chain configuration
        is_valid, error_msg = validate_chain_config(data.get('steps', []))
        if not is_valid:
            return jsonify({'error': f'Invalid chain configuration: {error_msg}'}), 400

        # Create template
        template = OCRChainTemplate.create(mongo, current_user_id, {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'steps': data.get('steps', []),
            'is_public': data.get('is_public', False),
        })

        logger.info(f"Created template '{data.get('name')}' for user {current_user_id}")

        return jsonify({
            'success': True,
            'template': OCRChainTemplate.to_dict(template)
        }), 201

    except Exception as e:
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/templates/<template_id>', methods=['GET'])
@token_required
def get_template(current_user_id, template_id):
    """Get template details"""
    try:
        from app.models import mongo

        template = OCRChainTemplate.find_by_id(mongo, template_id, current_user_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        return jsonify({
            'success': True,
            'template': OCRChainTemplate.to_dict(template)
        }), 200

    except Exception as e:
        logger.error(f"Error getting template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/templates/<template_id>', methods=['PUT'])
@token_required
def update_template(current_user_id, template_id):
    """Update template"""
    try:
        from app.models import mongo

        # Verify template exists and belongs to user
        template = OCRChainTemplate.find_by_id(mongo, template_id, current_user_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        data = request.get_json()

        # Validate chain if steps provided
        if data.get('steps'):
            is_valid, error_msg = validate_chain_config(data.get('steps', []))
            if not is_valid:
                return jsonify({'error': f'Invalid chain configuration: {error_msg}'}), 400

        # Prepare update data
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'steps' in data:
            update_data['steps'] = data['steps']
        if 'is_public' in data:
            update_data['is_public'] = data['is_public']

        if not update_data:
            return jsonify({'error': 'No fields to update'}), 400

        # Update template
        OCRChainTemplate.update(mongo, template_id, current_user_id, update_data)

        # Get updated template
        updated_template = OCRChainTemplate.find_by_id(mongo, template_id, current_user_id)

        logger.info(f"Updated template {template_id} for user {current_user_id}")

        return jsonify({
            'success': True,
            'template': OCRChainTemplate.to_dict(updated_template)
        }), 200

    except Exception as e:
        logger.error(f"Error updating template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/templates/<template_id>', methods=['DELETE'])
@token_required
def delete_template(current_user_id, template_id):
    """Delete template"""
    try:
        from app.models import mongo

        # Verify template exists and belongs to user
        template = OCRChainTemplate.find_by_id(mongo, template_id, current_user_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        # Delete template
        OCRChainTemplate.delete(mongo, template_id, current_user_id)

        logger.info(f"Deleted template {template_id} for user {current_user_id}")

        return jsonify({
            'success': True,
            'message': 'Template deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/templates/<template_id>/duplicate', methods=['POST'])
@token_required
def duplicate_template(current_user_id, template_id):
    """Duplicate a template"""
    try:
        from app.models import mongo

        # Verify template exists and belongs to user
        template = OCRChainTemplate.find_by_id(mongo, template_id, current_user_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        data = request.get_json()
        new_name = data.get('name', f"{template.get('name')} (Copy)")

        # Duplicate template
        new_template = OCRChainTemplate.duplicate(mongo, template_id, current_user_id, new_name)

        logger.info(f"Duplicated template {template_id} to {new_template.get('_id')} for user {current_user_id}")

        return jsonify({
            'success': True,
            'template': OCRChainTemplate.to_dict(new_template)
        }), 201

    except Exception as e:
        logger.error(f"Error duplicating template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


# ============================================================================
# Chain Execution Endpoints
# ============================================================================

@ocr_chains_bp.route('/execute', methods=['POST'])
@token_required
def start_chain_job(current_user_id):
    """Start a chain bulk processing job"""
    try:
        from app.models import mongo
        from app.config import Config
        from app.services.nsq_job_coordinator import NSQJobCoordinator
        import uuid
        import os

        data = request.get_json()

        # Validate required fields
        if not data.get('folder_path'):
            return jsonify({'error': 'folder_path required'}), 400

        if not data.get('chain_config'):
            return jsonify({'error': 'chain_config required'}), 400

        folder_path = data.get('folder_path')

        # Validate folder exists and is accessible
        if not os.path.isdir(folder_path):
            return jsonify({'error': f'Folder not found: {folder_path}'}), 400

        if not os.access(folder_path, os.R_OK):
            return jsonify({'error': f'Permission denied: {folder_path}'}), 403

        chain_config = data.get('chain_config', {})
        steps = chain_config.get('steps', [])

        # Validate chain
        is_valid, error_msg = validate_chain_config(steps)
        if not is_valid:
            return jsonify({'error': f'Invalid chain: {error_msg}'}), 400

        # Create bulk job with chain config
        job_id = str(uuid.uuid4())
        job_data = {
            'job_id': job_id,
            'folder_path': folder_path,
            'processing_mode': 'chain',
            'chain_config': {
                'template_id': chain_config.get('template_id'),
                'steps': steps
            },
            'languages': data.get('languages', ['en']),
            'handwriting': data.get('handwriting', False),
            'recursive': data.get('recursive', True),
            'export_formats': data.get('export_formats', ['json', 'csv', 'text']),
            'status': 'processing'
        }

        # Create job in database
        job = BulkJob.create(mongo, current_user_id, job_data)

        logger.info(f"Created chain job {job_id} for user {current_user_id}")

        # Start NSQ coordinator if enabled
        if Config.USE_NSQ:
            try:
                coordinator = NSQJobCoordinator()
                coordinator.start_job(
                    mongo=mongo,
                    job_id=job_id,
                    folder_path=folder_path,
                    provider=None,  # Not used in chain mode
                    languages=data.get('languages', ['en']),
                    handwriting=data.get('handwriting', False),
                    recursive=data.get('recursive', True),
                    processing_mode='chain',
                    chain_config=job_data.get('chain_config')
                )
                file_count = len(coordinator.scan_folder(folder_path, data.get('recursive', True)))
                logger.info(f"Published NSQ chain job {job_id} with {file_count} files to process")
            except Exception as worker_error:
                logger.error(f"Error starting NSQ coordinator: {str(worker_error)}")
                BulkJob.update_status(mongo, job_id, 'error', error=str(worker_error))
                return jsonify({
                    'error': f'Failed to start processing: {str(worker_error)}',
                    'success': False
                }), 500
        else:
            logger.warning("NSQ not enabled - chain processing requires NSQ")
            BulkJob.update_status(mongo, job_id, 'error', error='NSQ not enabled')
            return jsonify({
                'error': 'NSQ must be enabled for chain processing',
                'success': False
            }), 400

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Chain job started',
            'job': BulkJob.to_dict(job)
        }), 201

    except Exception as e:
        logger.error(f"Error starting chain job: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/results/<job_id>', methods=['GET'])
@token_required
def get_chain_results(current_user_id, job_id):
    """Get chain execution results"""
    try:
        from app.models import mongo

        # Get job
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Return job with results
        job_dict = BulkJob.to_dict(job)

        # Generate timeline if job is completed
        if job.get('processing_mode') == 'chain' and job.get('status') == 'completed':
            # Create timeline from results (simplified version)
            timeline_data = {
                'total_time_ms': job.get('progress', {}).get('total_processing_time_ms', 0),
                'images_processed': job.get('consumed_count', 0),
                'success_count': len(job.get('checkpoint', {}).get('results', [])),
                'error_count': len(job.get('checkpoint', {}).get('errors', []))
            }
            job_dict['timeline'] = timeline_data

        return jsonify({
            'success': True,
            'job': job_dict
        }), 200

    except Exception as e:
        logger.error(f"Error getting chain results: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@ocr_chains_bp.route('/export/<job_id>', methods=['GET'])
@token_required
def export_chain_results(current_user_id, job_id):
    """Export chain results as ZIP"""
    try:
        from app.models import mongo
        from app.services.storage import StorageService

        # Get job
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        if job.get('status') != 'completed':
            return jsonify({'error': 'Job must be completed before export'}), 400

        # Export results
        storage_service = StorageService(Config.UPLOAD_FOLDER, Config.ALLOWED_EXTENSIONS)
        file_path = storage_service.export_chain_results(mongo, job_id)

        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Failed to export results'}), 500

        logger.info(f"Exported chain results for job {job_id}")

        # Serve the ZIP file as download
        return send_file(
            file_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'chain_results_{job_id[:8]}.zip'
        )

    except Exception as e:
        logger.error(f"Error exporting chain results: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500
