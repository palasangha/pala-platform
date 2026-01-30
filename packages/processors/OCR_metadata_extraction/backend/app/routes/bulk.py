"""
Routes for bulk image processing
"""

import os
import json
import tempfile
import threading
import uuid
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import zipfile
import logging

from app.services.ocr_service import OCRService
from app.services.bulk_processor import BulkProcessor
from app.services.nsq_job_coordinator import NSQJobCoordinator
from app.config import Config
from app.utils.decorators import token_required
from app.models import mongo
from app.models.bulk_job import BulkJob

logger = logging.getLogger(__name__)

bulk_bp = Blueprint('bulk', __name__, url_prefix='/api/bulk')

# Store processing jobs progress in memory
processing_jobs = {}
# Store processor instances for pause/resume control
active_processors = {}


def generate_collection_metadata(folder_path, results_summary, languages, provider):
    """
    Generate collection title and description based on folder structure and processing results

    Args:
        folder_path: Path to the processed folder
        results_summary: Summary dict with file counts and statistics
        languages: List of languages used for OCR
        provider: OCR provider name

    Returns:
        dict with 'title', 'description', and 'tags'
    """
    from datetime import datetime
    import os

    # Extract meaningful parts from folder path
    path_parts = folder_path.strip('./').split('/')

    # Use the last folder name as base for collection name
    folder_name = path_parts[-1] if path_parts else 'Documents'

    # Try to make folder name more readable
    # e.g., "hin-typed" → "Hindi Typed"
    readable_name = folder_name.replace('-', ' ').replace('_', ' ').title()

    # If there's a parent folder, include it
    if len(path_parts) > 1:
        parent_name = path_parts[-2].replace('-', ' ').replace('_', ' ').title()
        title = f"{parent_name} - {readable_name}"
    else:
        title = readable_name

    # Append "Collection" to make it clear
    title = f"{title} Collection"

    # Generate description
    total_files = results_summary.get('total_files', 0)
    successful = results_summary.get('successful', 0)
    failed = results_summary.get('failed', 0)

    statistics = results_summary.get('statistics', {})
    total_chars = statistics.get('total_characters', 0)
    avg_confidence = statistics.get('average_confidence', 0)
    detected_languages = statistics.get('languages', languages)

    # Format date
    processed_date = datetime.utcnow().strftime('%B %d, %Y')

    description = f"""OCR processed collection from folder: {folder_path}

Processed on: {processed_date}
Total documents: {total_files}
Successfully processed: {successful}
Failed: {failed}

OCR Statistics:
- Provider: {provider}
- Languages: {', '.join(detected_languages)}
- Total characters extracted: {total_chars:,}
- Average confidence: {avg_confidence:.1%}

This collection contains digitized documents with full-text OCR content, making them searchable and accessible."""

    # Generate tags
    tags = ['ocr', 'digitized']

    # Add language tags
    for lang in detected_languages:
        if lang and lang != 'unknown':
            tags.append(lang.split('-')[0])  # e.g., 'en-hi' → 'en'

    # Add folder-based tags
    for part in path_parts:
        if part and len(part) > 2:  # Skip very short parts
            tag = part.replace('-', '_').replace(' ', '_').lower()
            if tag not in tags:
                tags.append(tag)

    # Add provider tag
    provider_tag = provider.replace('_', '').lower()
    if provider_tag not in tags:
        tags.append(provider_tag)

    return {
        'title': title,
        'description': description,
        'tags': tags[:10]  # Limit to 10 most relevant tags
    }


def _get_progress_callback(job_id: str):
    """Create a progress callback that stores progress in memory and database"""

    def callback(current, total, filename):
        progress_data = {
            'current': current,
            'total': total,
            'filename': filename,
            'percentage': int((current / total) * 100) if total > 0 else 0,
            'status': 'processing'
        }
        processing_jobs[job_id]['progress'] = progress_data

        # Also update database
        try:
            BulkJob.update_progress(mongo, job_id, progress_data)
        except Exception as e:
            logger.error(f"Error updating progress in database: {str(e)}")

        logger.info(f"Job {job_id} Progress: {current}/{total} - {filename}")

    return callback


def _get_checkpoint_callback(job_id: str):
    """Create a checkpoint callback that saves checkpoint to database"""

    def callback(checkpoint_data):
        try:
            BulkJob.save_checkpoint(mongo, job_id, checkpoint_data)
            logger.info(f"Checkpoint saved for job {job_id}")
        except Exception as e:
            logger.error(f"Error saving checkpoint for job {job_id}: {str(e)}")

    return callback


@bulk_bp.route('/browse-folders', methods=['POST'])
@token_required
def browse_folders(current_user_id):
    """
    Browse folders on the server
    
    Expected JSON:
    {
        "path": "/path/to/browse" or "" for root browsable paths
    }
    """
    try:
        data = request.get_json()
        browse_path = data.get('path', '') if data else ''
        
        # Define allowed root paths for browsing
        allowed_roots = [
            '/mnt/sda1/mango1_home',
            '/home',
            './uploads',  # Relative to app directory
        ]
        
        # If no path specified, return allowed root paths
        if not browse_path:
            folders = []
            for root in allowed_roots:
                if os.path.isdir(root):
                    try:
                        # Get immediate subfolders only
                        items = os.listdir(root)
                        for item in items:
                            full_path = os.path.join(root, item)
                            if os.path.isdir(full_path) and not item.startswith('.'):
                                try:
                                    # Count files in folder
                                    file_count = len([f for f in os.listdir(full_path) 
                                                    if os.path.isfile(os.path.join(full_path, f))])
                                    folders.append({
                                        'name': item,
                                        'path': full_path,
                                        'file_count': file_count,
                                        'is_dir': True
                                    })
                                except PermissionError:
                                    pass
                    except PermissionError:
                        pass
            
            return jsonify({
                'success': True,
                'current_path': 'Server Root',
                'folders': sorted(folders, key=lambda x: x['name']),
                'parent_path': None
            }), 200
        
        # Validate the path is accessible
        if not os.path.isdir(browse_path):
            return jsonify({'error': f'Path not found: {browse_path}'}), 400
        
        if not os.access(browse_path, os.R_OK):
            return jsonify({'error': f'Permission denied: {browse_path}'}), 403
        
        # Get subfolders and files
        try:
            items = os.listdir(browse_path)
            folders = []
            files = []
            
            for item in items:
                full_path = os.path.join(browse_path, item)
                if item.startswith('.'):
                    continue
                
                try:
                    if os.path.isdir(full_path):
                        file_count = len([f for f in os.listdir(full_path) 
                                        if os.path.isfile(os.path.join(full_path, f))])
                        folders.append({
                            'name': item,
                            'path': full_path,
                            'file_count': file_count,
                            'is_dir': True
                        })
                    else:
                        # Only show image files
                        if item.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.pdf')):
                            file_size = os.path.getsize(full_path)
                            files.append({
                                'name': item,
                                'path': full_path,
                                'size': file_size,
                                'is_dir': False
                            })
                except (PermissionError, OSError):
                    pass
            
            # Get parent path
            parent_path = os.path.dirname(browse_path) if browse_path != '/' else None
            
            return jsonify({
                'success': True,
                'current_path': browse_path,
                'folders': sorted(folders, key=lambda x: x['name']),
                'files': sorted(files, key=lambda x: x['name']),
                'parent_path': parent_path,
                'folder_count': len(folders),
                'file_count': len(files)
            }), 200
            
        except PermissionError:
            return jsonify({'error': f'Permission denied: {browse_path}'}), 403
            
    except Exception as e:
        logger.error(f"Error browsing folders: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _process_in_background(app, job_id, folder_path, recursive, provider, languages, handwriting, export_formats, parallel=True, max_workers=None):
    """Background function to process bulk images"""
    with app.app_context():
        try:
            from app.config import Config

            logger.info(f"Starting background processing for job {job_id}")

            # Determine max workers from config if not specified
            if max_workers is None:
                max_workers = Config.BULK_PARALLEL_JOBS

            # Ensure max_workers doesn't exceed limit
            max_workers = min(max_workers, Config.BULK_MAX_PARALLEL_JOBS)

            # Initialize services
            ocr_service = OCRService()
            progress_callback = _get_progress_callback(job_id)
            checkpoint_callback = _get_checkpoint_callback(job_id)
            processor = BulkProcessor(
                ocr_service,
                progress_callback,
                max_workers=max_workers,
                job_id=job_id,
                checkpoint_callback=checkpoint_callback,
                enable_enrichment=True
            )

            # Check if there's a checkpoint to restore from
            checkpoint = BulkJob.get_checkpoint(mongo, job_id)
            if checkpoint and checkpoint.get('processed_files'):
                logger.info(f"Restoring job {job_id} from checkpoint with {len(checkpoint.get('processed_files', []))} files already processed")
                processor.restore_from_checkpoint(checkpoint)

            # Store processor instance for pause/resume control
            active_processors[job_id] = processor

            logger.info(f"Using {'parallel' if parallel else 'sequential'} processing with {max_workers} workers")

            # Process folder
            results = processor.process_folder(
                folder_path=folder_path,
                provider=provider,
                languages=languages,
                handwriting=handwriting,
                recursive=recursive,
                parallel=parallel
            )

            # Create output folder
            output_folder = tempfile.mkdtemp(prefix='ocr_bulk_')

            # Export reports
            exported_files = {}
            for fmt in export_formats:
                if fmt.lower() in ['json', 'csv', 'text']:
                    try:
                        if fmt.lower() == 'json':
                            exported_files['json'] = processor.export_to_json(
                                os.path.join(output_folder, 'report')
                            )
                        elif fmt.lower() == 'csv':
                            exported_files['csv'] = processor.export_to_csv(
                                os.path.join(output_folder, 'report')
                            )
                        elif fmt.lower() == 'text':
                            exported_files['text'] = processor.export_to_text(
                                os.path.join(output_folder, 'report')
                            )
                    except Exception as e:
                        logger.error(f"Error exporting {fmt}: {str(e)}")

            # Save result.json in the output folder
            try:
                source_result_json = os.path.join(output_folder, 'result.json')
                processor.export_to_json(source_result_json.replace('.json', ''))
                logger.info(f"Saved result.json to output folder: {source_result_json}")
            except Exception as e:
                logger.error(f"Error saving result.json to output folder: {str(e)}")

            # Create individual JSON files for each processed file
            individual_json_folder = os.path.join(output_folder, 'individual_files')
            os.makedirs(individual_json_folder, exist_ok=True)

            individual_json_files = []
            try:
                for result in results['results']:
                    # Get original filename without extension
                    original_filename = result.get('file', 'unknown')
                    base_name = os.path.splitext(original_filename)[0]

                    # Create JSON filename
                    json_filename = f"{base_name}.json"
                    json_filepath = os.path.join(individual_json_folder, json_filename)

                    # Write individual JSON file
                    with open(json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)

                    individual_json_files.append(json_filepath)
                    logger.debug(f"Created individual JSON: {json_filename}")

                logger.info(f"Created {len(individual_json_files)} individual JSON files")
            except Exception as e:
                logger.error(f"Error creating individual JSON files: {str(e)}")

            # Create zip file with all reports AND individual JSON files
            zip_path = os.path.join(output_folder, 'reports.zip')
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add main report files
                    for file_path in exported_files.values():
                        if os.path.exists(file_path):
                            zipf.write(file_path, arcname=os.path.basename(file_path))
                            logger.debug(f"Added to zip: {os.path.basename(file_path)}")

                    # Add individual JSON files in a subfolder
                    for json_file in individual_json_files:
                        if os.path.exists(json_file):
                            # Store in 'individual_files/' folder within zip
                            arcname = os.path.join('individual_files', os.path.basename(json_file))
                            zipf.write(json_file, arcname=arcname)
                            logger.debug(f"Added to zip: {arcname}")

                # Verify the zip file was created successfully
                if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                    logger.error(f"ZIP file creation failed for job {job_id}: file is empty or missing")
                    raise Exception("ZIP file creation resulted in empty file")

                logger.info(f"ZIP archive created successfully for job {job_id}")
            except Exception as zip_error:
                logger.error(f"Error creating ZIP archive for job {job_id}: {str(zip_error)}", exc_info=True)
                raise

            # Generate collection metadata for Archipelago
            collection_metadata = generate_collection_metadata(
                folder_path=folder_path,
                results_summary=results['summary'],
                languages=languages,
                provider=provider
            )

            # Prepare response data with downloadable zip path
            response_data = {
                'success': True,
                'job_id': job_id,
                'summary': results['summary'],
                'report_files': {
                    'json': os.path.basename(exported_files.get('json', '')),
                    'csv': os.path.basename(exported_files.get('csv', '')),
                    'text': os.path.basename(exported_files.get('text', '')),
                    'zip': 'reports.zip',
                    'individual_json_count': len(individual_json_files)
                },
                'download_url': f'/api/bulk/download/{job_id}',  # Use job_id for download
                'zip_path': zip_path,  # Store actual zip file path
                'output_folder': output_folder,  # Store output folder
                'individual_json_folder': individual_json_folder,  # Store individual JSON folder
                'results_preview': {
                    'total_results': len(results['results']),
                    'successful_samples': [
                        {
                            'file': r['file'],
                            'file_path': r['file_path'],
                            'confidence': r['confidence'],
                            'text': r['text'],  # Include full OCR text
                            'text_length': len(r['text']),
                            'language': r['detected_language'],
                            'provider': r['provider']
                        }
                        for r in results['results']  # All successful files
                    ],
                    'error_samples': [
                        {
                            'file': e['file'],
                            'error': e['error']
                        }
                        for e in results['errors']  # All failed files
                    ]
                },
                'archipelago_collection': collection_metadata  # Auto-generated collection metadata
            }

            # Store output files for download using job_id as key
            current_app.bulk_processing_outputs = getattr(current_app, 'bulk_processing_outputs', {})
            current_app.bulk_processing_outputs[job_id] = {
                'folder': output_folder,
                'files': exported_files,
                'zip': zip_path,
                'job_id': job_id
            }

            # Update job status to completed
            processing_jobs[job_id]['status'] = 'completed'
            processing_jobs[job_id]['results'] = response_data
            processing_jobs[job_id]['progress'] = {
                'current': results['summary']['total_files'],
                'total': results['summary']['total_files'],
                'percentage': 100,
                'filename': 'Completed'
            }

            # Save results to database
            try:
                BulkJob.update_status(mongo, job_id, 'completed', results=response_data)
            except Exception as db_error:
                logger.error(f"Error saving results to database: {str(db_error)}")

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Error in background processing for job {job_id}: {str(e)}", exc_info=True)
            processing_jobs[job_id]['status'] = 'error'
            processing_jobs[job_id]['error'] = str(e)

            # Save error to database
            try:
                BulkJob.update_status(mongo, job_id, 'error', error=str(e))
            except Exception as db_error:
                logger.error(f"Error saving error to database: {str(db_error)}")

        finally:
            # Cleanup: Remove processor instance after completion
            if job_id in active_processors:
                del active_processors[job_id]
                logger.info(f"Cleaned up processor for job {job_id}")


@bulk_bp.route('/progress/<job_id>', methods=['GET'])
@token_required
def get_progress(current_user_id, job_id):
    """
    Get the progress of a bulk processing job

    Returns:
    {
        "status": "processing" | "completed" | "error" | "not_found",
        "progress": {
            "current": 5,
            "total": 10,
            "percentage": 50,
            "filename": "current_file.jpg"
        },
        "results": {...}  // Only present when status is "completed"
    }
    """
    # Always check database first for NSQ jobs, fall back to in-memory for threading jobs
    try:
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if db_job:
            job = {
                'status': db_job.get('status', 'unknown'),
                'progress': db_job.get('progress', {}),
                'results': db_job.get('results'),
                'error': db_job.get('error')
            }
        else:
            # Fall back to in-memory cache for threading-based jobs
            job = processing_jobs.get(job_id)
            if not job:
                return jsonify({'status': 'not_found', 'error': 'Job not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching job from database: {str(e)}")
        # Fall back to in-memory cache
        job = processing_jobs.get(job_id)
        if not job:
            return jsonify({'status': 'not_found', 'error': 'Job not found'}), 404

    response = {
        'status': job.get('status', 'unknown'),
        'progress': job.get('progress', {
            'current': 0,
            'total': 0,
            'percentage': 0,
            'filename': ''
        })
    }

    # If completed, include results
    if job.get('status') == 'completed':
        response['results'] = job.get('results')

    # If error, include error message
    if job.get('status') == 'error':
        response['error'] = job.get('error', 'Unknown error occurred')

    return jsonify(response), 200


@bulk_bp.route('/pause/<job_id>', methods=['POST'])
@token_required
def pause_job(current_user_id, job_id):
    """Pause a running bulk processing job"""
    try:
        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Check if processor is active
        if job_id in active_processors:
            processor = active_processors[job_id]
            # Pause the processor
            processor.pause()
            msg = 'Job paused successfully'
            state = processor.get_state()
        elif Config.USE_NSQ:
            # Use NSQ-based pausing
            coordinator = NSQJobCoordinator()
            coordinator.pause_job(job_id)
            msg = 'Job pause request sent to NSQ'
            state = 'pausing'
        else:
            return jsonify({'error': 'Job is not currently running or already completed'}), 400

        # Update job status
        if job_id in processing_jobs:
            processing_jobs[job_id]['status'] = 'paused'
        BulkJob.update_status(mongo, job_id, 'paused')

        logger.info(f"Job {job_id} paused by user {current_user_id}")

        return jsonify({
            'success': True,
            'message': msg,
            'job_id': job_id,
            'state': state
        }), 200

    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/resume/<job_id>', methods=['POST'])
@token_required
def resume_job(current_user_id, job_id):
    """Resume a paused bulk processing job"""
    try:
        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Check if processor is active
        if job_id in active_processors:
            processor = active_processors[job_id]
            # Resume the processor
            processor.resume()
            msg = 'Job resumed successfully'
            state = processor.get_state()
        elif Config.USE_NSQ:
            # Use NSQ-based resumption
            coordinator = NSQJobCoordinator()
            coordinator.resume_job(job_id)
            msg = 'Job resume request sent to NSQ'
            state = 'resuming'
        else:
            return jsonify({'error': 'Job is not currently running'}), 400

        # Update job status
        if job_id in processing_jobs:
            processing_jobs[job_id]['status'] = 'processing'
        BulkJob.update_status(mongo, job_id, 'processing')

        logger.info(f"Job {job_id} resumed by user {current_user_id}")

        return jsonify({
            'success': True,
            'message': msg,
            'job_id': job_id,
            'state': state
        }), 200

    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/stop/<job_id>', methods=['POST'])
@token_required
def stop_job(current_user_id, job_id):
    """Stop/cancel a bulk processing job"""
    try:
        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Check if processor is active
        if job_id in active_processors:
            processor = active_processors[job_id]
            # Stop the processor
            processor.stop()
            msg = 'Job cancelled successfully'
            state = processor.get_state()
        elif Config.USE_NSQ:
            # Use NSQ-based cancellation
            coordinator = NSQJobCoordinator()
            coordinator.cancel_job(job_id)
            msg = 'Job cancellation request sent to NSQ'
            state = 'cancelled'
        else:
            return jsonify({'error': 'Job is not currently running'}), 400

        # Update job status
        if job_id in processing_jobs:
            processing_jobs[job_id]['status'] = 'cancelled'
        BulkJob.update_status(mongo, job_id, 'cancelled')

        logger.info(f"Job {job_id} stopped by user {current_user_id}")

        return jsonify({
            'success': True,
            'message': msg,
            'job_id': job_id,
            'state': state
        }), 200

    except Exception as e:
        logger.error(f"Error stopping job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/state/<job_id>', methods=['GET'])
@token_required
def get_job_state(current_user_id, job_id):
    """Get the current state of a job (running, paused, stopped)"""
    try:
        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Check if processor is active
        if job_id in active_processors:
            processor = active_processors[job_id]
            checkpoint = processor.get_checkpoint_data()

            return jsonify({
                'job_id': job_id,
                'state': processor.get_state(),
                'is_paused': processor.is_paused(),
                'is_stopped': processor.is_stopped(),
                'checkpoint': checkpoint
            }), 200
        else:
            # Job not active, return database status
            return jsonify({
                'job_id': job_id,
                'state': db_job.get('status', 'unknown'),
                'is_paused': False,
                'is_stopped': True
            }), 200

    except Exception as e:
        logger.error(f"Error getting job state {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/process', methods=['POST'])
@token_required
def process_bulk_images(current_user_id):
    """
    Process bulk images from a folder

    Expected JSON:
    {
        "folder_path": "/path/to/folder",
        "recursive": true,
        "provider": "tesseract",
        "languages": ["en"],
        "handwriting": false,
        "export_formats": ["json", "csv", "text"],
        "parallel": true,
        "max_workers": 4
    }
    """
    try:
        from app.config import Config

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        folder_path = data.get('folder_path')
        if not folder_path:
            return jsonify({'error': 'folder_path is required'}), 400

        # Validate folder exists and is accessible
        if not os.path.isdir(folder_path):
            # Try to provide helpful error message
            parent = os.path.dirname(folder_path)
            if os.path.isdir(parent):
                try:
                    contents = os.listdir(parent)
                    error_msg = f'Folder not found: {folder_path}\n\nAvailable in {parent}:\n' + '\n'.join(contents[:10])
                except PermissionError:
                    error_msg = f'Permission denied accessing: {folder_path}'
            else:
                error_msg = f'Folder not found: {folder_path}'

            logger.warning(f"Folder access error: {error_msg}")
            return jsonify({'error': error_msg}), 400

        # Check if folder is readable
        if not os.access(folder_path, os.R_OK):
            logger.error(f"Permission denied: {folder_path}")
            return jsonify({'error': f'Permission denied accessing: {folder_path}'}), 403

        # Get parameters
        recursive = data.get('recursive', True)
        provider = data.get('provider', 'tesseract')
        languages = data.get('languages', ['en'])
        handwriting = data.get('handwriting', False)
        export_formats = data.get('export_formats', ['json', 'csv', 'text'])

        # Parallel processing parameters
        parallel = data.get('parallel', True)
        max_workers = data.get('max_workers', None)

        # Validate and constrain max_workers
        if max_workers is not None:
            max_workers = int(max_workers)
            if max_workers < 1:
                max_workers = 1
            if max_workers > Config.BULK_MAX_PARALLEL_JOBS:
                logger.warning(f"Requested {max_workers} workers, limiting to {Config.BULK_MAX_PARALLEL_JOBS}")
                max_workers = Config.BULK_MAX_PARALLEL_JOBS

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Initialize job in processing_jobs dictionary
        processing_jobs[job_id] = {
            'status': 'processing',
            'progress': {
                'current': 0,
                'total': 0,
                'percentage': 0,
                'filename': 'Initializing...'
            },
            'folder_path': folder_path,
            'provider': provider
        }

        # Save job to database
        try:
            BulkJob.create(mongo, current_user_id, {
                'job_id': job_id,
                'folder_path': folder_path,
                'provider': provider,
                'languages': languages,
                'handwriting': handwriting,
                'recursive': recursive,
                'export_formats': export_formats,
                'parallel': parallel,
                'max_workers': max_workers or Config.BULK_PARALLEL_JOBS,
                'status': 'processing'
            })
        except Exception as db_error:
            logger.error(f"Error saving job to database: {str(db_error)}")

        logger.info(f"Starting bulk processing job {job_id} from: {folder_path} (parallel={parallel}, workers={max_workers or Config.BULK_PARALLEL_JOBS})")

        # Check if NSQ is enabled
        if Config.USE_NSQ:
            # Use NSQ-based processing
            logger.info(f"Using NSQ-based processing for job {job_id}")
            coordinator = NSQJobCoordinator()
            coordinator.start_job(
                mongo=mongo,
                job_id=job_id,
                folder_path=folder_path,
                provider=provider,
                languages=languages,
                handwriting=handwriting,
                recursive=recursive
            )
            file_count = len(coordinator.scan_folder(folder_path, recursive))
            logger.info(f"Published NSQ job {job_id} with {file_count} files to process")
        else:
            # Use traditional threading-based processing
            logger.info(f"Using threading-based processing for job {job_id}")
            # Get the current app instance for background thread
            app = current_app._get_current_object()

            # Start processing in background thread
            thread = threading.Thread(
                target=_process_in_background,
                args=(app, job_id, folder_path, recursive, provider, languages, handwriting, export_formats, parallel, max_workers),
                daemon=True
            )
            thread.start()
            logger.info(f"Started background thread for job {job_id}")

        # Return job ID immediately
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Processing started. Use the job_id to poll for progress.',
            'progress_url': f'/api/bulk/progress/{job_id}'
        }), 202  # 202 Accepted
        
    except Exception as e:
        logger.error(f"Error in bulk processing: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/file/<path:filename>', methods=['GET'])
@token_required
def get_file_from_folder(current_user_id, filename):
    """
    Get a specific file from a folder for uploading to a project

    Query params:
    - folder: The folder path where the file is located
    """
    try:
        folder_path = request.args.get('folder')
        if not folder_path:
            return jsonify({'error': 'folder parameter is required'}), 400

        # Resolve relative paths (e.g., ./data/documents -> /app/data/documents)
        if folder_path.startswith('./'):
            # Remove './' prefix and prepend '/app/' (where volumes are mounted)
            folder_path = '/app/' + folder_path[2:]

        # Construct full file path
        file_path = os.path.join(folder_path, filename)

        # Security: Validate the file path
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': f'File not found: {filename}'}), 404

        if not os.path.isfile(file_path):
            return jsonify({'error': 'Path is not a file'}), 400

        # Security: Ensure the file is within the allowed folder
        real_file_path = os.path.realpath(file_path)
        real_folder_path = os.path.realpath(folder_path)

        if not real_file_path.startswith(real_folder_path):
            return jsonify({'error': 'Access denied'}), 403

        # Determine mimetype
        from mimetypes import guess_type
        mimetype, _ = guess_type(file_path)
        if not mimetype:
            mimetype = 'application/octet-stream'

        logger.info(f"Sending file: {file_path}")
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error fetching file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/download/<job_id>', methods=['GET'])
@token_required
def download_reports(current_user_id, job_id):
    """Download processed reports as ZIP"""
    try:
        zip_path = None

        # First check in-memory storage
        current_app.bulk_processing_outputs = getattr(current_app, 'bulk_processing_outputs', {})

        if job_id in current_app.bulk_processing_outputs:
            output_info = current_app.bulk_processing_outputs[job_id]
            zip_path = output_info['zip']
        else:
            # Check database for completed jobs
            job = BulkJob.find_by_job_id(mongo, job_id, user_id=current_user_id)

            if not job:
                logger.warning(f"Download attempt for non-existent or unauthorized job: {job_id}")
                return jsonify({'error': 'Job not found or access denied'}), 404

            # Check job status
            job_status = job.get('status')
            if job_status != 'completed':
                logger.info(f"Download attempt for job {job_id} with status: {job_status}")
                error_msg = f'Job is still {job_status}'
                if job_status == 'error':
                    error_msg = f'Job failed: {job.get("error", "Unknown error")}'
                return jsonify({'error': error_msg}), 400

            # Get zip path from job results
            results = job.get('results', {})
            if not results:
                logger.error(f"Job {job_id} has no results object")
                return jsonify({'error': 'Reports not yet generated. Please wait for processing to complete.'}), 400

            if not results.get('zip_path'):
                logger.error(f"Job {job_id} results missing zip_path. Results keys: {list(results.keys())}")
                return jsonify({'error': 'Report file path not found. Reports may still be generating.'}), 400

            zip_path = results['zip_path']

        # Verify file exists
        if not zip_path:
            logger.error(f"Download endpoint called with empty zip_path for job {job_id}")
            return jsonify({'error': 'Report file path is empty'}), 400

        if not os.path.exists(zip_path):
            logger.error(f"Report file not found at path: {zip_path} (job: {job_id})")
            return jsonify({'error': f'Report file not found on disk. Path: {zip_path}'}), 404

        # Verify file is a valid zip
        try:
            if not zipfile.is_zipfile(zip_path):
                logger.error(f"Invalid ZIP file at path: {zip_path} (job: {job_id})")
                return jsonify({'error': 'Report file is corrupted or invalid'}), 400

            # Try to open and read the zip file to ensure it's not corrupted
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Test zip file integrity
                bad_file = zipf.testzip()
                if bad_file is not None:
                    logger.error(f"ZIP file corruption detected - bad file: {bad_file} (job: {job_id})")
                    return jsonify({'error': f'Report file is corrupted (bad file: {bad_file})'}), 400
        except Exception as e:
            logger.error(f"Error validating ZIP file: {str(e)} (job: {job_id})")
            return jsonify({'error': f'Report file validation failed: {str(e)}'}), 400

        # Check file size
        file_size = os.path.getsize(zip_path)
        if file_size == 0:
            logger.error(f"ZIP file is empty at path: {zip_path} (job: {job_id})")
            return jsonify({'error': 'Report file is empty'}), 400

        logger.info(f"Download started for job {job_id} (file size: {file_size} bytes)")
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'ocr_reports_{job_id}.zip'
        )

    except Exception as e:
        logger.error(f"Error downloading reports for job {job_id}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@bulk_bp.route('/status/<job_id>', methods=['GET'])
@token_required
def get_job_status(current_user_id, job_id):
    """
    Get status of a bulk processing job including Archipelago upload results
    
    Args:
        job_id: Bulk job identifier
        
    Returns:
        JSON with job status, progress, and results (including archipelago_result if uploaded)
    """
    try:
        logger.info(f"Status request for job {job_id} by user {current_user_id}")
        
        # Get job from database
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        
        if not job:
            logger.warning(f"Job {job_id} not found for user {current_user_id}")
            return jsonify({'error': 'Job not found'}), 404
        
        logger.info(f"Found job {job_id}, status: {job.get('status')}")
        
        # Return job status with all relevant fields
        response = {
            'success': True,
            'job_id': job_id,
            'status': job.get('status'),
            'updated_at': str(job.get('updated_at', '')),
            'archipelago_result': job.get('archipelago_result'),
            'archipelago_uploaded_at': str(job.get('archipelago_uploaded_at', '')) if job.get('archipelago_uploaded_at') else None,
            'progress': {
                'total_files': job.get('total_files'),
                'processed_count': job.get('processed_count', 0),
                'failed_count': job.get('failed_count', 0)
            },
            'error': job.get('error')
        }
        
        logger.debug(f"Returning status response: {response}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}', 'success': False}), 500

@bulk_bp.route('/history', methods=['GET'])
@token_required
def get_job_history(current_user_id):
    """
    Get bulk processing job history for the current user

    Query params:
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    """
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        skip = (page - 1) * limit

        logger.info(f"[JOB_HISTORY] Fetching jobs for user: {current_user_id}, page: {page}, limit: {limit}")

        # Get jobs from database
        jobs = BulkJob.find_by_user(mongo, current_user_id, skip=skip, limit=limit)
        total_count = BulkJob.count_by_user(mongo, current_user_id)

        logger.info(f"[JOB_HISTORY] Found {len(jobs)} jobs out of {total_count} total for user {current_user_id}")

        # Convert to dictionaries
        jobs_list = [BulkJob.to_dict(job) for job in jobs]

        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Error fetching job history: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/job/<job_id>', methods=['GET'])
@token_required
def get_job_details(current_user_id, job_id):
    """Get detailed information about a specific bulk job"""
    try:
        job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify({
            'success': True,
            'job': BulkJob.to_dict(job)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching job details: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/job/<job_id>', methods=['DELETE'])
@token_required
def delete_job(current_user_id, job_id):
    """Delete a bulk job from history"""
    try:
        result = BulkJob.delete_by_job_id(mongo, job_id, current_user_id)

        if result.deleted_count == 0:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Job deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/resumable-jobs', methods=['GET'])
@token_required
def get_resumable_jobs(current_user_id):
    """
    Get all jobs that can be resumed (status: processing or paused)

    Returns jobs that were interrupted and can be restored from checkpoint
    """
    try:
        jobs = BulkJob.find_resumable_jobs(mongo, current_user_id)

        jobs_list = []
        for job in jobs:
            job_dict = BulkJob.to_dict(job)
            # Add checkpoint info
            if job.get('checkpoint'):
                job_dict['checkpoint_info'] = {
                    'processed_count': job['checkpoint'].get('processed_count', 0),
                    'processed_files': len(job['checkpoint'].get('processed_files', [])),
                    'last_checkpoint': job['checkpoint'].get('last_checkpoint_at'),
                    'consecutive_errors': job['checkpoint'].get('consecutive_errors', 0)
                }
            jobs_list.append(job_dict)

        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'count': len(jobs_list)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching resumable jobs: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/sample-results/<job_id>', methods=['GET'])
@token_required
def get_sample_results(current_user_id, job_id):
    """
    Download sample results from a currently processing job

    Query params:
    - sample_size: Number of results to include (default: all processed so far)

    This allows users to verify OCR quality while the job is still running
    """
    try:
        import tempfile

        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Get sample size from query params
        sample_size = request.args.get('sample_size', type=int)

        # Check if processor is active (job is running)
        if job_id in active_processors:
            processor = active_processors[job_id]

            # Create temp folder for sample results
            output_folder = tempfile.mkdtemp(prefix='sample_results_')

            try:
                # Generate sample results zip
                zip_path = processor.generate_sample_results(output_folder, sample_size)

                # Send the zip file
                return send_file(
                    zip_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f'sample_results_{job_id}.zip'
                )
            except ValueError as e:
                # No files processed yet
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Error generating sample results for job {job_id}: {str(e)}")
                return jsonify({'error': str(e)}), 500
        else:
            # Job is not currently running, check if it has checkpoint data
            checkpoint = BulkJob.get_checkpoint(mongo, job_id)
            if not checkpoint or not checkpoint.get('results'):
                return jsonify({
                    'error': 'Job is not currently running and has no checkpoint data. Sample results are only available for active jobs.'
                }), 400

            # Generate sample from checkpoint data
            try:
                output_folder = tempfile.mkdtemp(prefix='sample_results_')

                # Create a temporary processor just to use the export method
                from app.services.ocr_service import OCRService
                temp_processor = BulkProcessor(
                    OCRService(),
                    job_id=job_id,
                    enable_enrichment=True
                )

                # Restore results from checkpoint
                temp_processor.results = checkpoint.get('results', [])
                temp_processor.errors = checkpoint.get('errors', [])

                # Generate sample
                zip_path = temp_processor.generate_sample_results(output_folder, sample_size)

                return send_file(
                    zip_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f'sample_results_{job_id}.zip'
                )
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Error generating sample results from checkpoint for job {job_id}: {str(e)}")
                return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error getting sample results for job {job_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bulk_bp.route('/restore/<job_id>', methods=['POST'])
@token_required
def restore_job(current_user_id, job_id):
    """
    Restore and restart a crashed or interrupted job from checkpoint

    This will create a new background processor and restore from the last checkpoint
    """
    try:
        from app.config import Config

        # Check if job exists and belongs to user
        db_job = BulkJob.find_by_job_id(mongo, job_id, current_user_id)
        if not db_job:
            return jsonify({'error': 'Job not found or unauthorized'}), 404

        # Check if job is already running
        if job_id in active_processors:
            return jsonify({'error': 'Job is already running'}), 400

        # Check if job can be resumed
        job_status = db_job.get('status')
        if job_status not in ['processing', 'paused']:
            return jsonify({
                'error': f'Job cannot be restored. Current status: {job_status}. Only jobs with status "processing" or "paused" can be restored.'
            }), 400

        # Get checkpoint
        checkpoint = BulkJob.get_checkpoint(mongo, job_id)
        if not checkpoint:
            return jsonify({'error': 'No checkpoint found for this job'}), 404

        # Get job parameters
        folder_path = db_job.get('folder_path')
        provider = db_job.get('provider', 'tesseract')
        languages = db_job.get('languages', ['en'])
        handwriting = db_job.get('handwriting', False)
        recursive = db_job.get('recursive', True)
        export_formats = db_job.get('export_formats', ['json', 'csv', 'text'])
        max_workers = db_job.get('max_workers', Config.BULK_PARALLEL_JOBS)
        parallel = db_job.get('parallel', True)

        # Update job status to processing
        processing_jobs[job_id] = {
            'status': 'processing',
            'progress': db_job.get('progress', {
                'current': 0,
                'total': 0,
                'percentage': 0,
                'filename': 'Restoring from checkpoint...'
            }),
            'folder_path': folder_path,
            'provider': provider
        }

        BulkJob.update_status(mongo, job_id, 'processing')

        logger.info(f"Restoring job {job_id} from checkpoint. Processed files: {len(checkpoint.get('processed_files', []))}")

        # Get the current app instance for background thread
        app = current_app._get_current_object()

        # Start processing in background thread (will automatically restore from checkpoint)
        thread = threading.Thread(
            target=_process_in_background,
            args=(app, job_id, folder_path, recursive, provider, languages, handwriting, export_formats, parallel, max_workers),
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job restoration started. Processing will continue from last checkpoint.',
            'checkpoint_info': {
                'processed_files': len(checkpoint.get('processed_files', [])),
                'processed_count': checkpoint.get('processed_count', 0),
                'last_checkpoint': checkpoint.get('last_checkpoint_at')
            },
            'progress_url': f'/api/bulk/progress/{job_id}'
        }), 200

    except Exception as e:
        logger.error(f"Error restoring job {job_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
