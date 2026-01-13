"""Coordinates NSQ-based bulk processing jobs"""
import os
import logging
from pathlib import Path
from app.services.nsq_service import NSQService
from app.models.bulk_job import BulkJob

logger = logging.getLogger(__name__)


class NSQJobCoordinator:
    """Coordinates NSQ-based bulk processing jobs"""

    # Supported image extensions
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp',
        '.pdf'  # Also support PDFs
    }

    def __init__(self):
        self.nsq_service = NSQService()

    def scan_folder(self, folder_path: str, recursive: bool = True):
        """
        Scan folder for image files

        Args:
            folder_path: Root folder to scan
            recursive: Whether to scan subfolders (default: True)

        Returns:
            List of image file paths found
        """
        if not os.path.isdir(folder_path):
            raise ValueError(f"Invalid folder path: {folder_path}")

        image_files = []
        folder_path = Path(folder_path)

        # Use glob pattern for recursion
        pattern = "**/*" if recursive else "*"

        for file_path in folder_path.glob(pattern):
            if file_path.is_file():
                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    image_files.append(str(file_path))

        # Sort for consistent ordering
        return sorted(image_files)

    def start_job(self, mongo, job_id, folder_path, provider, languages, handwriting, recursive=True, processing_mode='single', chain_config=None):
        """
        Start a new NSQ-based bulk processing job

        Args:
            mongo: MongoDB connection
            job_id: Unique job identifier
            folder_path: Path to folder containing images
            provider: OCR provider to use (single mode)
            languages: List of languages for OCR
            handwriting: Whether to optimize for handwriting
            recursive: Whether to scan subfolders
            processing_mode: "single" or "chain"
            chain_config: Chain configuration (required for chain mode)

        Returns:
            Dictionary with job information
        """
        logger.info(f"Starting NSQ job {job_id}: folder={folder_path}, provider={provider}, mode={processing_mode}")

        try:
            # Scan folder for files
            image_files = self.scan_folder(folder_path, recursive)
            total_files = len(image_files)

            logger.error(f"NSQ Coordinator: Scanned folder {folder_path}, found {total_files} files")
            if image_files:
                logger.error(f"NSQ Coordinator: Files found: {image_files[:5]}..." if len(image_files) > 5 else f"NSQ Coordinator: Files found: {image_files}")

            if total_files == 0:
                raise ValueError(f"No supported files found in {folder_path}")

            logger.error(f"NSQ Coordinator: Found {total_files} files to process in job {job_id}")

            # Initialize job in MongoDB with NSQ tracking
            BulkJob.initialize_nsq_job(mongo, job_id, total_files)

            # Publish tasks to NSQ
            published_count = 0
            for idx, file_path in enumerate(image_files):
                logger.error(f"NSQ Coordinator: Publishing file {idx+1}/{total_files}: {file_path}")

                # Prepare task data based on mode
                task_data = {
                    'job_id': job_id,
                    'file_path': file_path,
                    'file_index': idx,
                    'total_files': total_files,
                    'processing_mode': processing_mode,
                    'languages': languages,
                    'handwriting': handwriting
                }

                if processing_mode == 'chain':
                    task_data['chain_config'] = chain_config
                else:
                    task_data['provider'] = provider

                self.nsq_service.publish_file_task(**task_data)

                # Increment published count in MongoDB
                BulkJob.increment_published_count(mongo, job_id)
                published_count += 1

            logger.error(f"NSQ Coordinator: Published {published_count} tasks to NSQ for job {job_id}")

            return {
                "job_id": job_id,
                "total_files": total_files,
                "status": "processing"
            }

        except Exception as e:
            logger.error(f"Failed to start NSQ job {job_id}: {e}")
            # Update job status to error
            try:
                BulkJob.update_status(mongo, job_id, 'error', str(e))
            except:
                pass
            raise

    def pause_job(self, job_id):
        """
        Pause a running job

        Args:
            job_id: Unique job identifier
        """
        logger.info(f"Pausing job {job_id}")
        self.nsq_service.publish_control_message(job_id, "pause")

    def resume_job(self, job_id):
        """
        Resume a paused job

        Args:
            job_id: Unique job identifier
        """
        logger.info(f"Resuming job {job_id}")
        self.nsq_service.publish_control_message(job_id, "resume")

    def cancel_job(self, job_id):
        """
        Cancel a running job

        Args:
            job_id: Unique job identifier
        """
        logger.info(f"Cancelling job {job_id}")
        self.nsq_service.publish_control_message(job_id, "cancel")
