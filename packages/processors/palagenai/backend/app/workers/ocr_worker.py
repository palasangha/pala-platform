"""Standalone NSQ consumer worker for OCR processing"""
import gnsq
import json
import logging
import os
import time
import shutil
import requests
from datetime import datetime
from app import create_app
from app.services.ocr_service import OCRService
from app.models.bulk_job import BulkJob
from app.services.inline_enrichment_service import get_inline_enrichment_service

logger = logging.getLogger(__name__)


class OCRWorker:
    """NSQ Consumer worker for distributed OCR processing"""

    def __init__(self, worker_id, nsqlookupd_addresses):
        """
        Initialize OCR worker

        Args:
            worker_id: Unique identifier for this worker
            nsqlookupd_addresses: List of NSQ lookupd HTTP addresses
        """
        self.worker_id = worker_id
        # Ensure HTTP protocol is prepended to addresses
        self.nsqlookupd_addresses = [
            addr if addr.startswith('http://') or addr.startswith('https://')
            else f'http://{addr}'
            for addr in nsqlookupd_addresses
        ]
        self.paused_jobs = set()
        self.cancelled_jobs = set()
        self.processed_count = 0
        self.error_count = 0

        # Initialize Flask app for MongoDB access
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Initialize OCR service
        self.ocr_service = OCRService()

        # Get MongoDB connection directly from models
        from app.models import mongo
        self.mongo = mongo

        # Initialize enrichment service (ALWAYS enabled)
        try:
            self.enrichment_service = get_inline_enrichment_service()
            logger.info(f"Worker {worker_id}: Enrichment service initialized and ENABLED (mandatory)")
        except Exception as e:
            logger.error(f"Worker {worker_id}: Failed to initialize enrichment service: {e}", exc_info=True)
            self.enrichment_service = None

        logger.info(f"Worker {worker_id} initialized")
        logger.info(f"NSQ lookupd addresses (raw): {nsqlookupd_addresses}")
        logger.info(f"NSQ lookupd addresses (processed): {self.nsqlookupd_addresses}")

    def handle_file_task(self, sender, message):
        """
        Process a single file OCR task (single mode) or chain mode

        Args:
            sender: The consumer that received the message
            message: NSQ message containing task data
        """
        try:
            data = json.loads(message.body.decode('utf-8'))
            job_id = data['job_id']
            file_path = data['file_path']
            file_index = data['file_index']
            processing_mode = data.get('processing_mode', 'single')
            languages = data.get('languages', [])
            handwriting = data.get('handwriting', False)
            attempt = data.get('attempt', 0)

            # Extract NSQ message ID for deduplication (prevents redelivery duplicates)
            message_id = message.id.decode('utf-8') if isinstance(message.id, bytes) else str(message.id)
            logger.debug(f"Message ID: {message_id}")

            # Resolve relative file paths to full absolute paths
            if not os.path.isabs(file_path):
                # Handle Bhushanji/ prefixed paths
                if file_path.startswith('Bhushanji/'):
                    gvpocr_path = os.getenv('GVPOCR_PATH', '/app/Bhushanji')
                    relative_part = file_path.replace('Bhushanji/', '', 1)
                    file_path = os.path.join(gvpocr_path, relative_part)
                # Handle newsletters/ prefixed paths
                elif file_path.startswith('newsletters/'):
                    newsletters_path = os.getenv('NEWSLETTERS_PATH', '/data/newsletters')
                    relative_part = file_path.replace('newsletters/', '', 1)
                    file_path = os.path.join(newsletters_path, relative_part)
                # Default: prepend /app/ for generic paths
                else:
                    file_path = os.path.join('/app', file_path)

            # Normalize file path for consistent duplicate detection
            file_path = self._normalize_file_path(file_path)
            logger.debug(f"Normalized file path: {file_path}")

            logger.info(f"Worker {self.worker_id}: Processing file {file_index} for job {job_id} (mode: {processing_mode}): {os.path.basename(file_path)}")

            # Ensure file exists - download from file server if needed
            if not os.path.exists(file_path):
                # Check if the target directory is read-only (mounted from shared storage)
                target_dir = os.path.dirname(file_path)
                if self._is_directory_readonly(target_dir):
                    # Directory is read-only - file should exist but doesn't
                    # This means the file is missing from the shared storage
                    logger.warning(f"File not found in read-only directory: {file_path}")
                    logger.warning(f"Skipping download for read-only mount at {target_dir}")
                    # Continue processing - the file may be in a fallback location or processed differently
                else:
                    # Directory is writable - try to download the file
                    self._download_file_from_server(file_path, data['file_path'])

            # Check if job is paused
            if job_id in self.paused_jobs:
                logger.info(f"Job {job_id} is paused, requeuing message")
                message.requeue()  # Requeue (NSQ handles backoff automatically)
                return

            # Check if job is cancelled
            if job_id in self.cancelled_jobs:
                logger.info(f"Job {job_id} is cancelled, finishing message")
                message.finish()
                return

            # Check if this specific message already processed (prevents NSQ redelivery duplicates)
            if BulkJob.is_message_processed(self.mongo, job_id, message_id):
                logger.info(f"Message {message_id} already processed, skipping (NSQ redelivery)")
                message.finish()
                return

            # Check if already processed (idempotency)
            if BulkJob.is_file_processed(self.mongo, job_id, file_path):
                logger.info(f"File {file_path} already processed, skipping")
                message.finish()
                return

            # Process based on mode
            if processing_mode == 'chain':
                self._handle_chain_task(job_id, file_path, file_index, languages, handwriting, attempt, message, message_id)
            else:
                self._handle_single_task(job_id, file_path, file_index, data.get('provider'), languages, handwriting, attempt, message, message_id)

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error processing file: {e}", exc_info=True)
            self.error_count += 1

            # Handle retry with exponential backoff
            try:
                data = json.loads(message.body.decode('utf-8'))
                attempt = data.get('attempt', 0)
                job_id = data.get('job_id')
                file_path = data.get('file_path')

                if attempt < 3:
                    # Requeue with delay: 2^attempt seconds
                    delay = 2 ** attempt
                    logger.info(f"Requeuing message (attempt {attempt + 1}/3)")

                    # Update attempt count in message
                    data['attempt'] = attempt + 1
                    message.requeue()  # NSQ handles backoff automatically
                else:
                    # Max retries reached, save error atomically
                    logger.error(f"Max retries reached for {file_path}, marking as failed")
                    error_msg = str(e)
                    BulkJob.save_file_error_atomic(self.mongo, job_id, file_path, error_msg)

                    message.finish()
            except Exception as cleanup_error:
                logger.error(f"Error during error handling: {cleanup_error}")
                message.finish()

    def _handle_single_task(self, job_id, file_path, file_index, provider, languages, handwriting, attempt, message, message_id=None):
        """
        Handle single-provider OCR processing

        Args:
            job_id: Job identifier
            file_path: File path to process
            file_index: File index in job
            provider: OCR provider to use
            languages: Languages for OCR
            handwriting: Whether to process handwriting
            attempt: Current attempt number
            message: NSQ message
            message_id: NSQ message ID for deduplication
        """
        try:
            start_time = time.time()
            result = self.ocr_service.process_image(
                file_path,
                provider=provider,
                languages=languages if languages else None,
                handwriting=handwriting,
                job_id=job_id
            )
            processing_time = time.time() - start_time

            # Build result document
            file_result = {
                'file': os.path.basename(file_path),
                'file_path': file_path,
                'file_index': file_index,
                'status': 'success',
                'provider': provider,
                'languages': languages,
                'handwriting': handwriting,
                'text': result.get('text', ''),
                'full_text': result.get('full_text', result.get('text', '')),
                'confidence': result.get('confidence', 0),
                'detected_language': result.get('detected_language'),
                'blocks_count': len(result.get('blocks', [])),
                'words_count': len(result.get('words', [])),
                'pages_processed': result.get('pages_processed', 1),
                'file_info': {
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'extension': os.path.splitext(file_path)[1].lower()
                },
                'metadata': {
                    'processing_time': round(processing_time, 2),
                    'worker_id': self.worker_id
                },
                'processed_at': datetime.utcnow().isoformat(),
                'retry_count': attempt,
                'raw_llm_response': result.get('raw_llm_response')
            }

            # Include intermediate images if available
            if result.get('intermediate_images'):
                file_result['intermediate_images'] = result.get('intermediate_images')

            # MANDATORY ENRICHMENT: Always enrich after successful OCR
            if self.enrichment_service and file_result.get('text'):
                try:
                    logger.info(f"[ENRICHMENT] Starting mandatory enrichment for {os.path.basename(file_path)}")
                    enrichment_start = time.time()

                    # Enrich the OCR result
                    enrichment_result = self.enrichment_service.enrich_ocr_results(
                        [file_result],
                        timeout=900
                    )

                    enrichment_time = time.time() - enrichment_start

                    # Extract enriched data
                    enriched_data = enrichment_result.get('enriched_results', {})
                    filename = os.path.basename(file_path)

                    if filename in enriched_data:
                        # Add enrichment to file result
                        file_result['enrichment'] = enriched_data[filename]
                        logger.info(f"[ENRICHMENT] Successfully enriched {filename} in {enrichment_time:.2f}s")
                    else:
                        logger.warning(f"[ENRICHMENT] No enrichment data returned for {filename}")

                except Exception as enrich_error:
                    logger.error(f"[ENRICHMENT] Failed to enrich {os.path.basename(file_path)}: {enrich_error}", exc_info=True)
                    # Continue with OCR result even if enrichment fails
            else:
                if not self.enrichment_service:
                    logger.warning(f"[ENRICHMENT] Enrichment service not available for {os.path.basename(file_path)}")
                elif not file_result.get('text'):
                    logger.warning(f"[ENRICHMENT] No OCR text to enrich for {os.path.basename(file_path)}")

            # CRITICAL: Double-check idempotency right before save (closes race window)
            # This prevents duplicates when multiple workers pass the initial check simultaneously
            if BulkJob.is_file_processed(self.mongo, job_id, file_path):
                logger.warning(f"File {file_path} was processed during our processing, skipping save")
                message.finish()
                return

            # Save result with message ID for comprehensive deduplication (prevents race condition)
            save_result = BulkJob.save_file_result_atomic(self.mongo, job_id, file_result, message_id)

            # Finish message successfully
            message.finish()

            if save_result is not None:
                self.processed_count += 1
                logger.info(f"Worker {self.worker_id}: Successfully processed {os.path.basename(file_path)} in {processing_time:.2f}s")
            else:
                logger.info(f"Worker {self.worker_id}: File {os.path.basename(file_path)} was already processed by another worker, skipping")

        except Exception as e:
            logger.error(f"Error in single task processing: {e}", exc_info=True)
            raise

    def _handle_chain_task(self, job_id, file_path, file_index, languages, handwriting, attempt, message, message_id=None):
        """
        Handle OCR chain processing for a single file

        Args:
            job_id: Job identifier
            file_path: File path to process
            file_index: File index in job
            languages: Languages for OCR
            handwriting: Whether to process handwriting
            attempt: Current attempt number
            message: NSQ message
            message_id: NSQ message ID for deduplication
        """
        try:
            from app.services.ocr_chain_service import OCRChainService

            # Get job to retrieve chain config
            job = BulkJob.get_by_job_id(self.mongo, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                raise Exception(f"Job {job_id} not found")

            chain_config = job.get('chain_config', {})
            steps = chain_config.get('steps', [])

            if not steps:
                logger.error(f"No steps found in chain config for job {job_id}")
                raise Exception("No chain steps configured")

            # Execute chain
            chain_service = OCRChainService()
            start_time = time.time()
            chain_result = chain_service.execute_chain(
                file_path,
                steps,
                languages=languages if languages else None,
                handwriting=handwriting,
                job_id=job_id
            )
            processing_time = time.time() - start_time

            # Build result document with chain outputs
            file_result = {
                'file': os.path.basename(file_path),
                'file_path': file_path,
                'file_index': file_index,
                'status': 'success' if chain_result.get('success') else 'error',
                'processing_mode': 'chain',
                'languages': languages,
                'handwriting': handwriting,
                'text': chain_result.get('final_output', ''),
                'full_text': chain_result.get('final_output', ''),
                'confidence': 0,  # Average confidence across steps
                'chain_steps': chain_result.get('steps', []),
                'file_info': {
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'extension': os.path.splitext(file_path)[1].lower()
                },
                'metadata': {
                    'processing_time': round(processing_time, 2),
                    'worker_id': self.worker_id,
                    'total_chain_time_ms': chain_result.get('total_processing_time_ms', 0)
                },
                'processed_at': datetime.utcnow().isoformat(),
                'retry_count': attempt
            }

            # CRITICAL: Double-check idempotency right before save (closes race window)
            # This prevents duplicates when multiple workers pass the initial check simultaneously
            if BulkJob.is_file_processed(self.mongo, job_id, file_path):
                logger.warning(f"File {file_path} was processed during our processing, skipping save")
                message.finish()
                return

            # Save result with message ID for comprehensive deduplication
            save_result = BulkJob.save_file_result_atomic(self.mongo, job_id, file_result, message_id)

            # Finish message successfully
            message.finish()

            if save_result is not None:
                self.processed_count += 1
                logger.info(f"Worker {self.worker_id}: Successfully processed chain for {os.path.basename(file_path)} in {processing_time:.2f}s")
            else:
                logger.info(f"Worker {self.worker_id}: File {os.path.basename(file_path)} was already processed by another worker, skipping")

        except Exception as e:
            logger.error(f"Error in chain task processing: {e}", exc_info=True)
            raise

    def _is_directory_readonly(self, directory_path):
        """
        Check if a directory is mounted as read-only by attempting a test write.

        Args:
            directory_path: Path to the directory to check

        Returns:
            True if directory is read-only, False if writable
        """
        # Check if path exists - if not, check parent directory
        check_dir = directory_path
        while not os.path.exists(check_dir) and check_dir != '/':
            check_dir = os.path.dirname(check_dir)
        
        if not os.path.isdir(check_dir):
            return False

        try:
            # Try to create a temporary test file
            test_file = os.path.join(check_dir, '.write_test_delete_me')
            with open(test_file, 'w') as f:
                f.write('test')
            # If we got here, directory is writable - clean up test file
            os.remove(test_file)
            return False
        except (OSError, IOError) as e:
            # If we get permission denied or read-only filesystem, it's read-only
            if e.errno in (30, 13):  # errno 30 = Read-only file system, 13 = Permission denied
                return True
            return False

    def _normalize_file_path(self, file_path):
        """
        Normalize file path to consistent absolute form for duplicate detection.

        This ensures that relative and absolute paths referring to the same file
        are treated identically by the duplicate detection system.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Normalized absolute path with symlinks resolved
        """
        try:
            # Convert to absolute if not already
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)

            # Resolve symlinks and normalize
            normalized_path = os.path.realpath(file_path)
            return normalized_path
        except Exception as e:
            logger.warning(f"Error normalizing path {file_path}: {e}, returning as-is")
            return file_path

    def _download_file_from_server(self, target_path, original_relative_path):
        """
        Download file from main server API endpoint.
        
        Args:
            target_path: Full path where file should be stored
            original_relative_path: Original relative path from the job (e.g., Bhushanji/...)
        """
        try:
            # Create target directory if it doesn't exist
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            
            # Download from API endpoint
            server_url = os.getenv('GVPOCR_SERVER_URL', 'http://gvpocr-api:5000')
            api_endpoint = f"{server_url}/api/files/download"
            
            logger.info(f"Downloading file from API: {api_endpoint}")
            
            response = requests.post(
                api_endpoint,
                json={'file_path': original_relative_path},
                timeout=300
            )
            
            if response.status_code == 200:
                # Write file content to target path
                with open(target_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded file via API to {target_path}")
                return
            else:
                error_msg = f"API download failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}", exc_info=True)
            raise

    def handle_control_message(self, sender, message):
        """
        Handle pause/resume/cancel control messages

        Args:
            sender: The consumer that received the message
            message: NSQ message containing control data
        """
        try:
            data = json.loads(message.body.decode('utf-8'))
            job_id = data['job_id']
            action = data['action']

            logger.info(f"Worker {self.worker_id}: Received control message - job_id={job_id}, action={action}")

            if action == 'pause':
                self.paused_jobs.add(job_id)
                logger.info(f"Job {job_id} added to paused jobs")
            elif action == 'resume':
                self.paused_jobs.discard(job_id)
                logger.info(f"Job {job_id} removed from paused jobs")
            elif action == 'cancel':
                self.cancelled_jobs.add(job_id)
                self.paused_jobs.discard(job_id)
                logger.info(f"Job {job_id} added to cancelled jobs")

            message.finish()

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error handling control message: {e}")
            message.finish()

    def run(self):
        """Start worker event loop"""
        logger.info(f"Worker {self.worker_id} starting...")

        try:
            # Create task consumer with extended timeout for long-running OCR tasks
            # timeout: socket timeout in seconds
            # heartbeat_interval: in seconds to keep connection alive
            task_reader = gnsq.Reader(
                topic='bulk_ocr_file_tasks',
                channel='bulk_ocr_workers',
                lookupd_http_addresses=self.nsqlookupd_addresses,
                max_in_flight=5,  # Process 5 files concurrently per worker
                message_handler=self.handle_file_task,
                timeout=900,  # 15 minutes socket timeout for long OCR processing
                heartbeat_interval=5,  # 5 seconds heartbeat to keep connection alive
                output_buffer_size=16384  # Increase buffer for faster processing
            )

            # Create control message consumer with standard timeout
            control_reader = gnsq.Reader(
                topic='bulk_ocr_control',
                channel='bulk_ocr_control_channel',
                lookupd_http_addresses=self.nsqlookupd_addresses,
                max_in_flight=10,
                message_handler=self.handle_control_message,
                timeout=60,  # 1 minute socket timeout for control messages
                heartbeat_interval=5  # 5 seconds heartbeat
            )

            # Start consumers
            task_reader.start()
            control_reader.start()

            logger.info(f"Worker {self.worker_id} is ready and listening for messages")

            # Keep running
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} shutting down...")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
        finally:
            logger.info(f"Worker {self.worker_id} processed {self.processed_count} files with {self.error_count} errors")
            if hasattr(self, 'app_context'):
                self.app_context.pop()
