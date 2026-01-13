"""NSQ integration service for publishing and consuming messages"""
import gnsq
import json
import logging
from datetime import datetime
from app.config import Config

logger = logging.getLogger(__name__)


class NSQService:
    """Service for interacting with NSQ message queue"""

    def __init__(self):
        self.nsqd_address = Config.NSQD_ADDRESS  # "nsqd:4150"
        self.nsqlookupd_addresses = Config.NSQLOOKUPD_ADDRESSES  # ["nsqlookupd:4161"]
        logger.info(f"NSQ Service initialized: nsqd={self.nsqd_address}, lookupd={self.nsqlookupd_addresses}")

    def publish_file_task(self, job_id, file_path, file_index, total_files, provider=None, languages=None, handwriting=False, processing_mode='single', chain_config=None):
        """
        Publish a file processing task to NSQ

        Args:
            job_id: Unique job identifier
            file_path: Path to the file to process
            file_index: Index of this file in the job
            total_files: Total number of files in the job
            provider: OCR provider to use (single mode)
            languages: List of languages for OCR
            handwriting: Whether to optimize for handwriting
            processing_mode: "single" or "chain"
            chain_config: Chain configuration (required for chain mode)
        """
        message = {
            "job_id": job_id,
            "file_path": file_path,
            "file_index": file_index,
            "total_files": total_files,
            "processing_mode": processing_mode,
            "languages": languages or [],
            "handwriting": handwriting,
            "attempt": 0,
            "enqueued_at": datetime.utcnow().isoformat()
        }

        # Add provider or chain_config depending on mode
        if processing_mode == 'chain':
            message['chain_config'] = chain_config
        else:
            message['provider'] = provider

        try:
            logger.error(f"NSQService: Creating producer for {self.nsqd_address}")
            producer = gnsq.Producer(self.nsqd_address)
            producer.start()
            logger.error(f"NSQService: Publishing to topic 'bulk_ocr_file_tasks': job_id={job_id}, file={file_path}")
            producer.publish('bulk_ocr_file_tasks', json.dumps(message).encode('utf-8'))
            producer.close()
            logger.error(f"NSQService: Successfully published file task: job_id={job_id}, file={file_path}")
        except Exception as e:
            logger.error(f"NSQService: FAILED to publish file task: {e}", exc_info=True)
            raise

    def publish_control_message(self, job_id, action):
        """
        Publish pause/resume/cancel control message

        Args:
            job_id: Unique job identifier
            action: Control action ('pause', 'resume', 'cancel')
        """
        message = {
            "job_id": job_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            producer = gnsq.Producer(self.nsqd_address)
            producer.start()
            producer.publish('bulk_ocr_control', json.dumps(message).encode('utf-8'))
            producer.close()
            logger.info(f"Published control message: job_id={job_id}, action={action}")
        except Exception as e:
            logger.error(f"Failed to publish control message: {e}")
            raise

    def get_topic_stats(self, topic):
        """
        Get statistics for a topic from NSQ

        Args:
            topic: Topic name

        Returns:
            Dictionary with topic statistics
        """
        try:
            import requests
            # Query nsqd HTTP API for stats
            nsqd_host = self.nsqd_address.replace(':4150', ':4151')
            response = requests.get(f"http://{nsqd_host}/stats?format=json&topic={topic}")

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get topic stats: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting topic stats: {e}")
            return None
