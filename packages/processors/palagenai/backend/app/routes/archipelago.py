"""
Routes for Archipelago Commons integration
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from app.services.archipelago_service import ArchipelagoService
from app.utils.decorators import token_required
from app.models import mongo
from app.models.bulk_job import BulkJob
from app.models.image import Image
from app.models.project import Project

logger = logging.getLogger(__name__)

archipelago_bp = Blueprint('archipelago', __name__, url_prefix='/api/archipelago')


@archipelago_bp.route('/check-connection', methods=['GET'])
@token_required
def check_connection(current_user_id):
    """Check if Archipelago Commons is configured and reachable"""
    try:
        service = ArchipelagoService()

        if not service.enabled:
            return jsonify({
                'success': False,
                'enabled': False,
                'message': 'Archipelago integration is not enabled. Set ARCHIPELAGO_ENABLED=true in environment variables.'
            }), 200

        is_connected = service.check_connection()

        return jsonify({
            'success': is_connected,
            'enabled': True,
            'base_url': service.base_url,
            'message': 'Connected successfully' if is_connected else 'Connection failed'
        }), 200

    except Exception as e:
        logger.error(f"Error checking Archipelago connection: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/diagnose', methods=['GET'])
@token_required
def diagnose_archipelago(current_user_id):
    """Run comprehensive diagnostics on Archipelago endpoints"""
    try:
        from app.services.ami_service import AMIService
        service = AMIService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        logger.info("Running Archipelago diagnostics...")
        report = service.diagnose_archipelago_endpoints()

        return jsonify({
            'success': True,
            'report': report
        }), 200

    except Exception as e:
        logger.error(f"Error running Archipelago diagnostics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/push-document', methods=['POST'])
@token_required
def push_document(current_user_id):
    """
    Push a single processed document to Archipelago Commons

    Expected JSON:
    {
        "image_id": "mongodb_image_id",
        "title": "Document Title",
        "tags": ["tag1", "tag2"],
        "custom_metadata": {}
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        image_id = data.get('image_id')
        if not image_id:
            return jsonify({'error': 'image_id is required'}), 400

        # Get image from database
        image = Image.find_by_id(mongo, image_id, current_user_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404

        # Check if OCR text is available
        if not image.get('ocr_text'):
            return jsonify({'error': 'Image has not been processed with OCR yet'}), 400

        service = ArchipelagoService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        # Prepare metadata
        title = data.get('title', image.get('original_filename', 'Untitled Document'))
        tags = data.get('tags', [])
        custom_metadata = data.get('custom_metadata', {})

        metadata = {
            'filename': image.get('filename'),
            'original_filename': image.get('original_filename'),
            'file_type': image.get('file_type'),
            'provider': 'OCR Processing',
            'confidence': 0.0,  # Add if available in image metadata
            'language': 'en',  # Add if available
            'description': custom_metadata.get('description', f'OCR processed document: {title}'),
            'custom_fields': custom_metadata
        }

        # Create digital object in Archipelago
        result = service.create_digital_object(
            title=title,
            file_path=image.get('filepath'),
            ocr_text=image.get('ocr_text'),
            metadata=metadata,
            tags=tags
        )

        if result:
            return jsonify({
                'success': True,
                'archipelago_node_id': result['node_id'],
                'archipelago_url': result['url'],
                'message': 'Document successfully pushed to Archipelago Commons'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to create digital object in Archipelago',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error pushing document to Archipelago: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/push-raw-metadata', methods=['POST'])
@token_required
def push_raw_metadata(current_user_id):
    """
    Push a single document with raw metadata to Archipelago Commons
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        metadata = data.get('metadata')
        if not metadata:
            return jsonify({'error': 'metadata is required'}), 400

        service = ArchipelagoService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        result = service.create_digital_object_from_raw(metadata)

        if result:
            return jsonify(result), 200
        else:
            return jsonify({
                'error': 'Failed to create digital object in Archipelago',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error pushing raw metadata to Archipelago: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/push-bulk-job', methods=['POST'])
@token_required
def push_bulk_job(current_user_id):
    """
    Push entire bulk processing job results to Archipelago as a collection

    Expected JSON:
    {
        "job_id": "bulk_job_id",
        "collection_title": "Collection Title",
        "collection_description": "Description",
        "tags": ["tag1", "tag2"],
        "include_failed": false
    }
    """
    logger.info("push_bulk_job method called.")
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        job_id = data.get('job_id')
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400

        # Get bulk job from database
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not job:
            return jsonify({'error': 'Bulk job not found'}), 404

        # Check if job is completed
        if job.get('status') != 'completed':
            return jsonify({'error': 'Bulk job is not completed yet'}), 400

        # Check if results are available
        if not job.get('results'):
            return jsonify({'error': 'No results available for this job'}), 400

        service = ArchipelagoService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        # Get auto-generated collection metadata from job results
        results = job.get('results', {})
        auto_collection = results.get('archipelago_collection', {})

        # Use auto-generated metadata, allow user override
        collection_title = data.get('collection_title', auto_collection.get('title', f"Bulk OCR - {job.get('folder_path')}"))
        collection_description = data.get('collection_description', auto_collection.get('description', f"Bulk OCR processing results from {job.get('folder_path')}"))

        # Merge tags: auto-generated + user-provided
        auto_tags = auto_collection.get('tags', [])
        user_tags = data.get('tags', [])
        merged_tags = list(set(auto_tags + user_tags))  # Remove duplicates

        include_failed = data.get('include_failed', False)

        successful_samples = results.get('results_preview', {}).get('successful_samples', [])

        if not successful_samples:
            return jsonify({'error': 'No successful results to push'}), 400

        collection_metadata = {
            'description': collection_description,
            'summary': results.get('summary', {}),
            'tags': merged_tags,
            'job_id': job_id,
            'processing_date': job.get('completed_at')
        }

        # Create collection with documents
        result = service.create_bulk_collection(
            collection_title=collection_title,
            document_results=successful_samples,
            collection_metadata=collection_metadata
        )

        if result:
            return jsonify({
                'success': True,
                'collection_id': result['collection_id'],
                'collection_url': result['collection_url'],
                'created_documents': result['created_documents'],
                'total_documents': result['total_documents'],
                'message': f"Successfully created collection with {result['created_documents']} documents"
            }), 200
        else:
            return jsonify({
                'error': 'Failed to create collection in Archipelago',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error pushing bulk job to Archipelago: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/push-project', methods=['POST'])
@token_required
def push_project(current_user_id):
    """
    Push all images from a project to Archipelago as a collection

    Expected JSON:
    {
        "project_id": "mongodb_project_id",
        "collection_title": "Collection Title (optional)",
        "collection_description": "Description (optional)",
        "tags": ["tag1", "tag2"]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        project_id = data.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400

        # Get project from database
        project = Project.find_by_id(mongo, project_id, current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Get all images from project
        images = Image.find_by_project(mongo, project_id)
        if not images:
            return jsonify({'error': 'No images found in this project'}), 404

        # Filter images that have OCR text
        processed_images = [img for img in images if img.get('ocr_text')]
        if not processed_images:
            return jsonify({'error': 'No processed images with OCR text found in this project'}), 400

        service = ArchipelagoService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        # Prepare collection metadata
        collection_title = data.get('collection_title', project.get('name', 'Untitled Collection'))
        collection_description = data.get('collection_description', project.get('description', ''))

        # Convert images to document results format
        document_results = []
        for img in processed_images:
            document_results.append({
                'file': img.get('original_filename', img.get('filename')),
                'file_path': img.get('filepath'),
                'text': img.get('ocr_text', ''),
                'provider': 'OCR Processing',
                'confidence': 0.0,
                'detected_language': 'en'
            })

        collection_metadata = {
            'description': collection_description,
            'summary': {
                'total_files': len(document_results),
                'successful': len(document_results),
                'failed': 0
            },
            'tags': data.get('tags', []),
            'project_id': project_id,
            'project_name': project.get('name')
        }

        # Create collection
        result = service.create_bulk_collection(
            collection_title=collection_title,
            document_results=document_results,
            collection_metadata=collection_metadata
        )

        if result:
            return jsonify({
                'success': True,
                'collection_id': result['collection_id'],
                'collection_url': result['collection_url'],
                'created_documents': result['created_documents'],
                'total_documents': result['total_documents'],
                'message': f"Successfully created collection with {result['created_documents']} documents"
            }), 200
        else:
            return jsonify({
                'error': 'Failed to create collection in Archipelago',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error pushing project to Archipelago: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/node/<node_uuid>/metadata', methods=['PUT', 'POST'])
@token_required
def update_node_metadata(current_user_id, node_uuid):
    """
    Update the descriptive metadata of a digital object in Archipelago.

    The request body should be the raw JSON for the 'field_descriptive_metadata'.
    """
    try:
        # Use get_data() to get the raw request body as a string
        metadata_json = request.get_data(as_text=True)
        if not metadata_json:
            return jsonify({'error': 'No metadata provided in request body'}), 400

        service = ArchipelagoService()
        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        success = service.update_descriptive_metadata(node_uuid, metadata_json)

        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully updated metadata for node {node_uuid}'
            }), 200
        else:
            return jsonify({
                'error': f'Failed to update metadata for node {node_uuid}',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error updating metadata for node {node_uuid}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500



def _push_bulk_ami_background(job_id, collection_title, collection_id, user_id):
    """Background task for pushing bulk job to Archipelago via AMI"""
    import time
    from app.services.ami_service import AMIService
    
    try:
        logger.info(f"Background: Starting AMI Set creation for job {job_id}")
        
        # Get bulk job from database
        job = BulkJob.find_by_job_id(mongo, job_id, user_id)
        if not job:
            logger.error(f"Background: Job {job_id} not found")
            BulkJob.update_status(mongo, job_id, 'error', 'Job not found')
            return
        
        # Get results
        results = job.get('results', {})
        successful_samples = results.get('results_preview', {}).get('successful_samples', [])
        
        if not successful_samples:
            logger.error(f"Background: No successful samples for job {job_id}")
            BulkJob.update_status(mongo, job_id, 'error', 'No successful samples')
            return
        
        # Update status to "uploading_to_archipelago"
        BulkJob.update_status(mongo, job_id, 'uploading_to_archipelago', 'Uploading to Archipelago...')
        
        # Transform successful_samples to ocr_data format
        ocr_data_list = []
        for sample in successful_samples:
            ocr_data = {
                'name': sample.get('file', 'Unknown'),
                'label': sample.get('file', 'Unknown'),
                'text': sample.get('text', ''),
                'description': f"OCR processed document: {sample.get('file')}",
                'file_info': {
                    'filename': sample.get('file'),
                    'file_path': sample.get('file_path'),
                },
                'ocr_metadata': {
                    'provider': sample.get('provider'),
                    'confidence': sample.get('confidence'),
                    'language': sample.get('language'),
                    'processing_date': job.get('completed_at'),
                }
            }
            ocr_data_list.append(ocr_data)
        
        # Create AMI Set
        logger.info(f"Background: Creating AMI Set for {len(ocr_data_list)} documents")
        service = AMIService()
        
        if not service.enabled:
            BulkJob.update_status(mongo, job_id, 'error', 'Archipelago integration not enabled')
            return
        
        # Add retry logic for network errors
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            try:
                result = service.create_bulk_via_ami(
                    ocr_data_list=ocr_data_list,
                    collection_name=collection_title,
                    collection_id=collection_id,
                    job_id=job_id
                )
                
                if result and result.get('success'):
                    # Update job with Archipelago info
                    BulkJob.update_archipelago_result(mongo, job_id, result)
                    logger.info(f"Background: AMI Set created successfully: {result.get('ami_set_id')}")
                    return
                elif result:
                    # Handle specific errors
                    error = result.get('error', 'Unknown error')
                    logger.error(f"Background: AMI creation failed - {error}")
                    BulkJob.update_status(mongo, job_id, 'error', f'Archipelago upload failed: {error}')
                    return
                else:
                    raise Exception('create_bulk_via_ami returned None')
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Background: Attempt {attempt} failed: {str(e)}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
    except Exception as e:
        logger.error(f"Background: Error in _push_bulk_ami_background: {str(e)}", exc_info=True)
        BulkJob.update_status(mongo, job_id, 'error', f'Archipelago upload error: {str(e)}')


@archipelago_bp.route('/push-bulk-ami', methods=['POST'])
@token_required
def push_bulk_ami(current_user_id):
    """
    Push bulk OCR results to Archipelago using AMI Sets workflow
    
    Returns immediately (202 Accepted), processing happens in background

    Request body:
    {
        "job_id": "bulk_job_id",
        "collection_title": "Optional collection title",
        "collection_id": 123  // Optional existing collection ID
    }
    """
    try:
        data = request.get_json()
        job_id = data.get('job_id')

        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400

        # Get bulk job from database
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not job:
            return jsonify({'error': 'Bulk job not found'}), 404

        # Check if job is completed
        if job.get('status') != 'completed':
            return jsonify({'error': 'Bulk job is not completed yet'}), 400

        # Check if results are available
        if not job.get('results'):
            return jsonify({'error': 'No results available for this job'}), 400

        from app.services.ami_service import AMIService
        service = AMIService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        # Check if already uploading
        if job.get('status') == 'uploading_to_archipelago':
            return jsonify({
                'success': False,
                'error': 'Upload already in progress for this job'
            }), 409

        # Get collection info
        collection_title = data.get('collection_title')
        collection_id = data.get('collection_id')

        # Start background task
        import threading
        thread = threading.Thread(
            target=_push_bulk_ami_background,
            args=(job_id, collection_title, collection_id, current_user_id),
            daemon=True
        )
        thread.start()

        logger.info(f"Started background AMI upload for job {job_id}")

        return jsonify({
            'success': True,
            'message': 'AMI Set creation started. Processing in background...',
            'job_id': job_id,
            'status': 'uploading_to_archipelago'
        }), 202  # 202 Accepted

    except Exception as e:
        logger.error(f"Error initiating bulk job AMI upload: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/amiset/add', methods=['POST'])
@token_required
def add_amiset(current_user_id):
    """
    Add and upload OCR data to Archipelago as an AMI Set
    
    This endpoint creates an AMI Set in Archipelago directly from OCR data,
    without requiring a pre-existing bulk job.

    Request body (JSON):
    {
        "ocr_data": [
            {
                "name": "document_name",
                "label": "Display Label",
                "text": "Full OCR extracted text...",
                "description": "Optional description",
                "file_info": {
                    "filename": "document.pdf",
                    "file_path": "/path/to/file.pdf"
                },
                "ocr_metadata": {
                    "provider": "tesseract",
                    "confidence": 0.95,
                    "language": "en",
                    "processing_date": "2025-12-08T06:20:19.158Z"
                }
            }
        ],
        "collection_title": "Optional Collection Name",
        "collection_id": null
    }

    Returns:
    {
        "success": true,
        "ami_set_id": "123",
        "ami_set_name": "Collection Name",
        "csv_fid": "456",
        "zip_fid": "789",
        "message": "AMI Set created successfully...",
        "total_documents": 5
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        ocr_data_list = data.get('ocr_data', [])
        if not ocr_data_list:
            return jsonify({'error': 'ocr_data array is required'}), 400

        if not isinstance(ocr_data_list, list):
            return jsonify({'error': 'ocr_data must be an array'}), 400

        if len(ocr_data_list) == 0:
            return jsonify({'error': 'ocr_data array cannot be empty'}), 400

        from app.services.ami_service import AMIService
        service = AMIService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        collection_title = data.get('collection_title')
        collection_id = data.get('collection_id')

        logger.info(f"Creating AMI Set for {len(ocr_data_list)} documents via /amiset/add endpoint")

        try:
            result = service.create_bulk_via_ami(
                ocr_data_list=ocr_data_list,
                collection_name=collection_title,
                collection_id=collection_id
            )

            if result:
                if result.get('success') is False:
                    return jsonify(result), 400

                return jsonify({
                    'success': True,
                    'ami_set_id': result.get('ami_set_id'),
                    'ami_set_name': result.get('name'),
                    'csv_fid': result.get('csv_fid'),
                    'zip_fid': result.get('zip_fid'),
                    'message': result.get('message'),
                    'total_documents': len(ocr_data_list)
                }), 200
            else:
                return jsonify({
                    'error': 'Failed to create AMI Set - check logs for details',
                    'success': False
                }), 500

        except Exception as ami_error:
            logger.error(f"Exception in create_bulk_via_ami: {str(ami_error)}", exc_info=True)
            return jsonify({
                'error': f'AMI Set creation failed: {str(ami_error)}',
                'success': False
            }), 500

    except Exception as e:
        logger.error(f"Error in add_amiset endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/amiset/status/<ami_set_id>', methods=['GET'])
@token_required
def get_amiset_status(current_user_id, ami_set_id):
    """
    Get the status of an AMI Set in Archipelago
    
    Returns information about the AMI Set processing status and results.
    """
    try:
        from app.services.ami_service import AMIService
        service = AMIService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        if not service.csrf_token:
            if not service._login():
                return jsonify({'error': 'Failed to authenticate with Archipelago'}), 401

        session = service._get_session() if hasattr(service, '_get_session') else service.session
        
        try:
            # Attempt to fetch AMI Set details from Archipelago
            response = session.get(
                f"{service.base_url}/jsonapi/ami_set_entity/ami_set_entity/{ami_set_id}"
            )

            if response.status_code == 404:
                return jsonify({'error': 'AMI Set not found'}), 404

            if response.status_code != 200:
                return jsonify({
                    'error': 'Failed to fetch AMI Set status',
                    'status_code': response.status_code
                }), 500

            result = response.json()
            ami_data = result.get('data', {})
            attributes = ami_data.get('attributes', {})

            return jsonify({
                'success': True,
                'ami_set_id': ami_set_id,
                'name': attributes.get('name'),
                'status': attributes.get('status', 'unknown'),
                'created': attributes.get('created'),
                'updated': attributes.get('changed'),
                'messages': attributes.get('ami_messages', []),
                'url': f"{service.base_url}/amiset/{ami_set_id}"
            }), 200

        except Exception as fetch_error:
            logger.error(f"Error fetching AMI Set status: {str(fetch_error)}")
            return jsonify({
                'error': 'Failed to retrieve AMI Set status',
                'details': str(fetch_error)
            }), 500

    except Exception as e:
        logger.error(f"Error in get_amiset_status endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@archipelago_bp.route('/amiset/process/<ami_set_id>', methods=['POST'])
@token_required
def process_amiset(current_user_id, ami_set_id):
    """
    Trigger processing of an AMI Set in Archipelago
    
    This endpoint initiates the ingestion process for a previously created AMI Set.
    The Archipelago server will process the CSV and ZIP files to create digital objects.

    Returns:
    {
        "success": true,
        "message": "AMI Set processing initiated",
        "ami_set_url": "http://archipelago.example.com/amiset/123"
    }
    """
    try:
        from app.services.ami_service import AMIService
        service = AMIService()

        if not service.enabled:
            return jsonify({
                'error': 'Archipelago integration is not enabled',
                'enabled': False
            }), 400

        if not service.csrf_token:
            if not service._login():
                return jsonify({'error': 'Failed to authenticate with Archipelago'}), 401

        session = service.session
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'X-CSRF-Token': service.csrf_token
        }

        try:
            # Send process request to Archipelago
            # This triggers the AMI ingestion workflow
            response = session.post(
                f"{service.base_url}/amiset/{ami_set_id}/process",
                headers=headers
            )

            if response.status_code == 404:
                return jsonify({'error': 'AMI Set not found'}), 404

            if response.status_code not in [200, 201, 202]:
                logger.error(f"AMI Set processing failed: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return jsonify({
                    'error': 'Failed to process AMI Set',
                    'status_code': response.status_code,
                    'details': response.text[:200]
                }), 500

            return jsonify({
                'success': True,
                'message': 'AMI Set processing initiated',
                'ami_set_id': ami_set_id,
                'ami_set_url': f"{service.base_url}/amiset/{ami_set_id}"
            }), 200

        except Exception as process_error:
            logger.error(f"Error processing AMI Set: {str(process_error)}")
            return jsonify({
                'error': 'Failed to process AMI Set',
                'details': str(process_error)
            }), 500

    except Exception as e:
        logger.error(f"Error in process_amiset endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
