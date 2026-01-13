from datetime import datetime
from bson import ObjectId
from pymongo.write_concern import WriteConcern


class BulkJob:
    """BulkJob model for database operations"""

    @staticmethod
    def create(mongo, user_id, job_data):
        """
        Create a new bulk job

        Args:
            mongo: MongoDB connection
            user_id: User ID who initiated the job
            job_data: Dictionary containing:
                - job_id: Unique job identifier (UUID)
                - folder_path: Source folder path
                - provider: OCR provider used (for single mode)
                - languages: List of languages
                - handwriting: Boolean
                - recursive: Boolean
                - export_formats: List of export formats
                - status: Job status (processing, completed, error)
                - processing_mode: "single" or "chain" (default: "single")
                - chain_config: Chain configuration (required if processing_mode is "chain")
        """
        bulk_job = {
            'user_id': ObjectId(user_id),
            'job_id': job_data['job_id'],
            'folder_path': job_data['folder_path'],
            'processing_mode': job_data.get('processing_mode', 'single'),
            'provider': job_data.get('provider', 'tesseract'),
            'languages': job_data.get('languages', ['en']),
            'handwriting': job_data.get('handwriting', False),
            'recursive': job_data.get('recursive', True),
            'export_formats': job_data.get('export_formats', ['json', 'csv', 'text']),
            'status': job_data.get('status', 'processing'),
            'progress': {
                'current': 0,
                'total': 0,
                'percentage': 0,
                'filename': 'Initializing...'
            },
            'results': None,
            'error': None,
            'checkpoint': {
                'processed_count': 0,
                'results': [],
                'errors': [],
                'retry_count': {},
                'consecutive_errors': 0,
                'processed_files': [],  # Track which files have been processed
                'last_checkpoint_at': datetime.utcnow().isoformat()
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'completed_at': None
        }

        # Add chain config if in chain mode
        if job_data.get('processing_mode') == 'chain':
            bulk_job['chain_config'] = {
                'template_id': job_data.get('chain_config', {}).get('template_id'),
                'steps': job_data.get('chain_config', {}).get('steps', [])
            }

        result = mongo.db.bulk_jobs.insert_one(bulk_job)
        bulk_job['_id'] = result.inserted_id
        return bulk_job

    @staticmethod
    def find_by_job_id(mongo, job_id, user_id=None):
        """Find bulk job by job_id"""
        query = {'job_id': job_id}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.bulk_jobs.find_one(query)

    @staticmethod
    def find_by_id(mongo, bulk_job_id, user_id=None):
        """Find bulk job by MongoDB _id"""
        query = {'_id': ObjectId(bulk_job_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.bulk_jobs.find_one(query)

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=50):
        """Find all bulk jobs for a user"""
        return list(mongo.db.bulk_jobs.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def count_by_user(mongo, user_id):
        """Count total bulk jobs for a user"""
        return mongo.db.bulk_jobs.count_documents({'user_id': ObjectId(user_id)})

    @staticmethod
    def update_progress(mongo, job_id, progress_data):
        """Update job progress"""
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    'progress': progress_data,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def update_status(mongo, job_id, status, results=None, error=None):
        """
        Update job status and results

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            status: New status (completed, error, uploading_to_archipelago)
            results: Results dictionary (for completed jobs)
            error: Error message (for failed jobs)
        """
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }

        if status == 'completed':
            update_data['completed_at'] = datetime.utcnow()
            if results:
                update_data['results'] = results

        if status == 'error' and error:
            update_data['error'] = error
            update_data['completed_at'] = datetime.utcnow()

        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {'$set': update_data}
        )

    @staticmethod
    def update_archipelago_result(mongo, job_id, archipelago_result):
        """
        Update job with Archipelago upload result
        
        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            archipelago_result: Result dictionary from AMI Set creation
        """
        update_data = {
            'archipelago_result': archipelago_result,
            'archipelago_uploaded_at': datetime.utcnow(),
            'status': 'completed',
            'updated_at': datetime.utcnow()
        }
        
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {'$set': update_data}
        )

    @staticmethod
    def delete(mongo, bulk_job_id, user_id):
        """Delete bulk job"""
        return mongo.db.bulk_jobs.delete_one({
            '_id': ObjectId(bulk_job_id),
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def delete_by_job_id(mongo, job_id, user_id):
        """Delete bulk job by job_id"""
        return mongo.db.bulk_jobs.delete_one({
            'job_id': job_id,
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def save_checkpoint(mongo, job_id, checkpoint_data):
        """
        Save checkpoint data for job resumption

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            checkpoint_data: Dictionary with checkpoint state
        """
        from datetime import datetime

        checkpoint_data['last_checkpoint_at'] = datetime.utcnow().isoformat()

        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    'checkpoint': checkpoint_data,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def get_checkpoint(mongo, job_id):
        """
        Get checkpoint data for job resumption

        Args:
            mongo: MongoDB connection
            job_id: Job identifier

        Returns:
            Checkpoint data dictionary or None
        """
        job = mongo.db.bulk_jobs.find_one({'job_id': job_id})
        return job.get('checkpoint') if job else None

    @staticmethod
    def find_resumable_jobs(mongo, user_id=None):
        """
        Find jobs that can be resumed (processing or paused)

        Args:
            mongo: MongoDB connection
            user_id: Optional user ID to filter by

        Returns:
            List of resumable job documents
        """
        query = {
            'status': {'$in': ['processing', 'paused']}
        }
        if user_id:
            query['user_id'] = ObjectId(user_id)

        return list(mongo.db.bulk_jobs.find(query).sort('updated_at', -1))

    # NSQ-specific methods

    @staticmethod
    def initialize_nsq_job(mongo, job_id, total_files):
        """
        Initialize NSQ job with tracking fields

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            total_files: Total number of files to process
        """
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    'total_files': total_files,
                    'published_count': 0,
                    'consumed_count': 0,
                    'progress.total': total_files,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def increment_published_count(mongo, job_id):
        """
        Atomically increment published task count

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
        """
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$inc': {'published_count': 1},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )

    @staticmethod
    def increment_consumed_count(mongo, job_id, filename=None):
        """
        Atomically increment consumed task count and update progress

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            filename: Optional filename being processed
        """
        # First increment the count and get the updated value
        result = mongo.db.bulk_jobs.find_one_and_update(
            {'job_id': job_id},
            {
                '$inc': {'consumed_count': 1},
                '$set': {'updated_at': datetime.utcnow()}
            },
            return_document=True
        )

        if result:
            consumed = result.get('consumed_count', 0)
            total = result.get('total_files', 1)
            percentage = int((consumed / total) * 100) if total > 0 else 0

            # Update progress
            progress_update = {
                'progress.current': consumed,
                'progress.percentage': percentage,
                'updated_at': datetime.utcnow()
            }

            if filename:
                progress_update['progress.filename'] = filename

            mongo.db.bulk_jobs.update_one(
                {'job_id': job_id},
                {'$set': progress_update}
            )

    @staticmethod
    def save_file_result(mongo, job_id, result):
        """
        Atomically save file result and add to processed set

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            result: Result dictionary
        """
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$push': {'checkpoint.results': result},
                '$addToSet': {'checkpoint.processed_files': result['file_path']},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )

    @staticmethod
    def save_file_error(mongo, job_id, file_path, error):
        """
        Atomically save file error

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            file_path: Path to failed file
            error: Error message
        """
        import os
        error_doc = {
            'file': os.path.basename(file_path),
            'file_path': file_path,
            'error': error,
            'processed_at': datetime.utcnow().isoformat()
        }

        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$push': {'checkpoint.errors': error_doc},
                '$addToSet': {'checkpoint.processed_files': file_path},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )

    @staticmethod
    def save_file_result_atomic(mongo, job_id, result, message_id=None):
        """
        Atomically save file result AND increment consumed count in single operation.

        Uses a truly atomic check-and-insert operation to prevent race conditions
        where multiple workers might process the same file simultaneously.

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            result: Result dictionary with file processing data
            message_id: Optional NSQ message ID for preventing redelivery duplicates

        Returns:
            MongoDB update result, or None if file was already processed
        """
        import logging
        logger = logging.getLogger(__name__)

        file_path = result['file_path']

        # Get current state to calculate new progress
        job = mongo.db.bulk_jobs.find_one({'job_id': job_id})
        if not job:
            logger.error(f"save_file_result_atomic: Job {job_id} not found!")
            return None

        new_consumed = job.get('consumed_count', 0) + 1
        total_files = job.get('total_files', 0)
        percentage = int((new_consumed / total_files * 100)) if total_files > 0 else 0

        logger.info(f"save_file_result_atomic: Attempting to save result for {result.get('file', 'unknown')} (file {new_consumed}/{total_files})")

        # Use collection with write concern for atomicity
        collection = mongo.db.get_collection('bulk_jobs', write_concern=WriteConcern(w='majority', j=True))

        # Build query conditions
        query_conditions = {
            'job_id': job_id,
            'checkpoint.processed_files': {'$ne': file_path}  # Only update if file NOT already processed
        }

        # Add message ID condition if provided (prevents NSQ redelivery duplicates)
        if message_id:
            query_conditions['checkpoint.processed_message_ids'] = {'$ne': message_id}

        # Build update operations
        update_operations = {
            '$push': {'checkpoint.results': result},
            '$addToSet': {'checkpoint.processed_files': file_path},
            '$inc': {'consumed_count': 1},
            '$set': {
                'updated_at': datetime.utcnow(),
                'progress.current': new_consumed,
                'progress.percentage': percentage,
                'progress.filename': result.get('file', '')
            }
        }

        # Add message ID to update if provided
        if message_id:
            update_operations['$addToSet']['checkpoint.processed_message_ids'] = message_id

        # Atomic operation: Only update if file_path NOT in processed_files array
        # This prevents race conditions where multiple workers process the same file
        update_result = collection.update_one(query_conditions, update_operations)

        if update_result.matched_count == 0:
            logger.warning(f"save_file_result_atomic: File {file_path} was already processed by another worker, skipping duplicate")
            return None

        logger.info(f"save_file_result_atomic: Successfully saved result - matched={update_result.matched_count}, modified={update_result.modified_count}")

        return update_result

    @staticmethod
    def save_file_error_atomic(mongo, job_id, file_path, error):
        """
        Atomically save file error AND increment consumed count in single operation.

        Uses a truly atomic check-and-insert operation to prevent race conditions
        where multiple workers might process the same file simultaneously.

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            file_path: Path to failed file
            error: Error message

        Returns:
            MongoDB update result, or None if file was already processed
        """
        import os
        import logging
        logger = logging.getLogger(__name__)

        error_doc = {
            'file': os.path.basename(file_path),
            'file_path': file_path,
            'error': error,
            'processed_at': datetime.utcnow().isoformat()
        }

        # Get current state to calculate new progress
        job = mongo.db.bulk_jobs.find_one({'job_id': job_id})
        if not job:
            logger.error(f"save_file_error_atomic: Job {job_id} not found!")
            return None

        new_consumed = job.get('consumed_count', 0) + 1
        total_files = job.get('total_files', 0)
        percentage = int((new_consumed / total_files * 100)) if total_files > 0 else 0

        logger.info(f"save_file_error_atomic: Attempting to save error for {os.path.basename(file_path)}")

        # Use collection with write concern for atomicity
        collection = mongo.db.get_collection('bulk_jobs', write_concern=WriteConcern(w='majority', j=True))

        # Atomic operation: Only update if file_path NOT in processed_files array
        # This prevents race conditions where multiple workers process the same file
        update_result = collection.update_one(
            {
                'job_id': job_id,
                'checkpoint.processed_files': {'$ne': file_path}  # Only update if file NOT already processed
            },
            {
                '$push': {'checkpoint.errors': error_doc},
                '$addToSet': {'checkpoint.processed_files': file_path},
                '$inc': {'consumed_count': 1},
                '$set': {
                    'updated_at': datetime.utcnow(),
                    'progress.current': new_consumed,
                    'progress.percentage': percentage,
                    'progress.filename': os.path.basename(file_path)
                }
            }
        )

        if update_result.matched_count == 0:
            logger.warning(f"save_file_error_atomic: File {file_path} was already processed by another worker, skipping duplicate error")
            return None

        logger.info(f"save_file_error_atomic: Successfully saved error - matched={update_result.matched_count}, modified={update_result.modified_count}")

        return update_result

    @staticmethod
    def is_file_processed(mongo, job_id, file_path):
        """
        Check if file already processed (idempotency)

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            file_path: File path to check

        Returns:
            True if file already processed, False otherwise
        """
        job = mongo.db.bulk_jobs.find_one(
            {'job_id': job_id},
            {'checkpoint.processed_files': 1}
        )

        if not job:
            return False

        processed_files = job.get('checkpoint', {}).get('processed_files', [])
        return file_path in processed_files

    @staticmethod
    def is_message_processed(mongo, job_id, message_id):
        """
        Check if NSQ message already processed (prevents redelivery duplicates)

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            message_id: NSQ message ID (hex string)

        Returns:
            True if message already processed, False otherwise
        """
        import logging
        logger = logging.getLogger(__name__)

        job = mongo.db.bulk_jobs.find_one(
            {'job_id': job_id},
            {'checkpoint.processed_message_ids': 1}
        )

        if not job:
            return False

        processed_ids = job.get('checkpoint', {}).get('processed_message_ids', [])
        is_processed = message_id in processed_ids

        if is_processed:
            logger.debug(f"Message {message_id} already in processed_message_ids")

        return is_processed

    @staticmethod
    def find_ready_for_aggregation(mongo):
        """
        Find jobs where consumed_count == published_count and status == 'processing'

        Args:
            mongo: MongoDB connection

        Returns:
            List of job documents ready for aggregation
        """
        return list(mongo.db.bulk_jobs.find({
            '$expr': {'$eq': ['$consumed_count', '$published_count']},
            'status': 'processing',
            'published_count': {'$gt': 0}  # Ensure tasks were published
        }))

    @staticmethod
    def get_by_job_id(mongo, job_id):
        """
        Get job by job_id

        Args:
            mongo: MongoDB connection
            job_id: Job identifier

        Returns:
            Job document or None
        """
        return mongo.db.bulk_jobs.find_one({'job_id': job_id})

    @staticmethod
    def mark_as_completed(mongo, job_id, final_results):
        """
        Mark job as completed with final results

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            final_results: Final results dictionary
        """
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    'status': 'completed',
                    'results': final_results,
                    'completed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def mark_as_error(mongo, job_id, error):
        """
        Mark job as error

        Args:
            mongo: MongoDB connection
            job_id: Job identifier
            error: Error message
        """
        return mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    'status': 'error',
                    'error': error,
                    'completed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def to_dict(bulk_job):
        """Convert bulk job document to dictionary"""
        if not bulk_job:
            return None

        result = {
            'id': str(bulk_job['_id']),
            'user_id': str(bulk_job.get('user_id')),
            'job_id': bulk_job.get('job_id'),
            'folder_path': bulk_job.get('folder_path'),
            'processing_mode': bulk_job.get('processing_mode', 'single'),
            'provider': bulk_job.get('provider'),
            'languages': bulk_job.get('languages', []),
            'handwriting': bulk_job.get('handwriting', False),
            'recursive': bulk_job.get('recursive', True),
            'export_formats': bulk_job.get('export_formats', []),
            'status': bulk_job.get('status'),
            'progress': bulk_job.get('progress', {}),
            'created_at': bulk_job.get('created_at').isoformat() if bulk_job.get('created_at') else None,
            'updated_at': bulk_job.get('updated_at').isoformat() if bulk_job.get('updated_at') else None,
            'completed_at': bulk_job.get('completed_at').isoformat() if bulk_job.get('completed_at') else None
        }

        # Include chain config if present
        if bulk_job.get('chain_config'):
            result['chain_config'] = bulk_job.get('chain_config')

        # Include NSQ tracking fields
        if 'total_files' in bulk_job:
            result['total_files'] = bulk_job.get('total_files')
        if 'published_count' in bulk_job:
            result['published_count'] = bulk_job.get('published_count')
        if 'consumed_count' in bulk_job:
            result['consumed_count'] = bulk_job.get('consumed_count')

        # Include results if available and convert relative URLs to absolute HTTPS URLs
        if bulk_job.get('results'):
            results = bulk_job.get('results')
            result['results'] = BulkJob._convert_urls_to_https(results)

        # Include error if present
        if bulk_job.get('error'):
            result['error'] = bulk_job.get('error')

        return result

    @staticmethod
    def _convert_urls_to_https(results):
        """
        Convert relative image URLs to absolute HTTPS URLs in results

        Args:
            results: List of result dictionaries that may contain intermediate_images

        Returns:
            List of results with updated URLs
        """
        try:
            from flask import request
            # Get base URL from request context
            scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
            host = request.headers.get('X-Forwarded-Host', request.host)
            base_url = f"{scheme}://{host}"
        except (RuntimeError, KeyError):
            # No Flask request context, return results as-is
            return results

        converted_results = []
        for result in results:
            if result.get('intermediate_images'):
                result = dict(result)  # Make a copy to avoid modifying original
                intermediate_images = result.get('intermediate_images', {})

                # Convert each image URL from relative to absolute
                for stage, img_info in intermediate_images.items():
                    if isinstance(img_info, dict) and img_info.get('url'):
                        url = img_info['url']
                        # If URL is relative (starts with /), make it absolute
                        if url.startswith('/'):
                            img_info['url'] = f"{base_url}{url}"

                result['intermediate_images'] = intermediate_images

            converted_results.append(result)

        return converted_results
