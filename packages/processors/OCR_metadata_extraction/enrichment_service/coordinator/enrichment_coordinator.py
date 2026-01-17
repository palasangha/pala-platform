"""
EnrichmentCoordinator - Monitors OCR completion and creates enrichment tasks in NSQ

Triggered from ResultAggregator after OCR job completion.
Creates enrichment tasks in NSQ topic "enrichment" for each OCR document.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import nsq
import time

logger = logging.getLogger(__name__)


class EnrichmentCoordinator:
    """
    Monitors MongoDB for completed OCR jobs and publishes enrichment tasks to NSQ
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize EnrichmentCoordinator

        Args:
            config: Optional configuration dict, otherwise uses environment variables
        """
        self.config = config or self._load_config()

        # MongoDB connection
        try:
            self.mongo_client = MongoClient(
                self.config['MONGO_URI'],
                serverSelectionTimeoutMS=5000
            )
            # Verify connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.config['DB_NAME']]
            logger.info("✓ MongoDB connected")
        except ConnectionFailure as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            self.db = None

        # NSQ connection
        self.nsq_host = self.config['NSQD_HOST']
        self.nsq_port = self.config['NSQD_PORT']
        self.enrichment_topic = self.config['ENRICHMENT_TOPIC']

        logger.info(f"EnrichmentCoordinator initialized - NSQ: {self.nsq_host}:{self.nsq_port}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'MONGO_URI': os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr'),
            'DB_NAME': os.getenv('DB_NAME', 'gvpocr'),
            'NSQD_HOST': os.getenv('NSQD_HOST', 'localhost'),
            'NSQD_PORT': int(os.getenv('NSQD_PORT', '4150')),
            'ENRICHMENT_TOPIC': os.getenv('ENRICHMENT_TOPIC', 'enrichment'),
            'BATCH_SIZE': int(os.getenv('ENRICHMENT_BATCH_SIZE', '50')),
            'ENRICHMENT_ENABLED': os.getenv('ENRICHMENT_ENABLED', 'true').lower() == 'true'
        }

    def create_enrichment_job(
        self,
        ocr_job_id: str,
        collection_id: str,
        collection_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create enrichment job and publish tasks to NSQ

        Called from ResultAggregator after OCR job completion

        Args:
            ocr_job_id: ID of completed OCR job
            collection_id: Collection containing the documents
            collection_metadata: Optional metadata about collection

        Returns:
            enrichment_job_id
        """
        if not self.config['ENRICHMENT_ENABLED'] or self.db is None:
            logger.warning("Enrichment disabled or MongoDB unavailable, skipping")
            return None

        try:
            # Fetch OCR job details
            ocr_job = self.db.bulk_jobs.find_one({'_id': ocr_job_id})
            if not ocr_job:
                logger.error(f"OCR job {ocr_job_id} not found")
                return None

            # Check job status
            if ocr_job.get('status') != 'completed':
                logger.warning(f"OCR job {ocr_job_id} not completed, skipping enrichment")
                return None

            # Get list of processed documents
            ocr_results = list(self.db.ocr_results.find({'ocr_job_id': ocr_job_id}))
            if not ocr_results:
                logger.warning(f"No OCR results found for job {ocr_job_id}")
                return None

            logger.info(f"Creating enrichment job for {len(ocr_results)} documents")

            # Create enrichment job record
            enrichment_job_id = f"enrich_{ocr_job_id}_{int(time.time())}"
            enrichment_job = {
                '_id': enrichment_job_id,
                'ocr_job_id': ocr_job_id,
                'collection_id': collection_id,
                'collection_metadata': collection_metadata or {},
                'status': 'created',
                'created_at': datetime.utcnow(),
                'total_documents': len(ocr_results),
                'processed_count': 0,
                'success_count': 0,
                'error_count': 0,
                'review_count': 0,
                'cost_summary': {
                    'total_usd': 0.0,
                    'ollama_cost': 0.0,
                    'claude_sonnet_cost': 0.0,
                    'claude_opus_cost': 0.0
                },
                'started_at': None,
                'completed_at': None
            }
            self.db.enrichment_jobs.insert_one(enrichment_job)
            logger.info(f"Created enrichment job: {enrichment_job_id}")

            # Publish enrichment tasks to NSQ
            published_count = self._publish_tasks(
                enrichment_job_id,
                ocr_results,
                collection_id,
                collection_metadata
            )

            # Mark job as published
            self.db.enrichment_jobs.update_one(
                {'_id': enrichment_job_id},
                {'$set': {'status': 'published', 'started_at': datetime.utcnow()}}
            )

            logger.info(f"Published {published_count}/{len(ocr_results)} enrichment tasks")
            return enrichment_job_id

        except Exception as e:
            logger.error(f"Error creating enrichment job: {e}", exc_info=True)
            return None

    def _publish_tasks(
        self,
        enrichment_job_id: str,
        ocr_results: list,
        collection_id: str,
        collection_metadata: Optional[Dict[str, Any]]
    ) -> int:
        """
        Publish individual enrichment tasks to NSQ

        Args:
            enrichment_job_id: Parent enrichment job ID
            ocr_results: List of OCR result documents
            collection_id: Collection ID
            collection_metadata: Collection metadata

        Returns:
            Number of tasks successfully published
        """
        published_count = 0

        for result in ocr_results:
            try:
                # Build enrichment task
                task = {
                    'task_id': f"task_{enrichment_job_id}_{result['_id']}",
                    'enrichment_job_id': enrichment_job_id,
                    'ocr_job_id': result['ocr_job_id'],
                    'document_id': str(result['_id']),
                    'ocr_data': {
                        'text': result.get('text', ''),
                        'full_text': result.get('full_text', ''),
                        'confidence': result.get('confidence', 0.0),
                        'detected_language': result.get('detected_language', 'en'),
                        'blocks': result.get('blocks', []),
                        'words': result.get('words', []),
                        'provider': result.get('provider', 'unknown'),
                        'ocr_job_id': result.get('ocr_job_id', ''),
                        'file_path': result.get('file_path', ''),
                        'file_metadata': result.get('file_metadata', {})
                    },
                    'enrichment_config': {
                        'enable_ollama': os.getenv('ENABLE_OLLAMA', 'true').lower() == 'true',
                        'enable_claude': os.getenv('ENABLE_CLAUDE', 'true').lower() == 'true',
                        'enable_context_agent': os.getenv('ENABLE_CONTEXT_AGENT', 'true').lower() == 'true',
                        'cost_limit_usd': float(os.getenv('MAX_COST_PER_DOC', '0.50')),
                        'completeness_threshold': float(os.getenv('COMPLETENESS_THRESHOLD', '0.95'))
                    },
                    'collection_metadata': collection_metadata or {
                        'collection_id': collection_id,
                        'collection_name': 'Unknown',
                        'archive_name': 'Unknown'
                    },
                    'enqueued_at': datetime.utcnow().isoformat(),
                    'priority': 'normal',
                    'attempt': 0,
                    'max_retries': 3
                }

                # Publish to NSQ
                self._publish_to_nsq(task)
                published_count += 1

            except Exception as e:
                logger.error(f"Error publishing task for document {result.get('_id')}: {e}")
                continue

        return published_count

    def _publish_to_nsq(self, task: Dict[str, Any]) -> bool:
        """
        Publish single task to NSQ

        Args:
            task: Enrichment task dict

        Returns:
            True if published successfully
        """
        try:
            # Serialize task
            task_json = json.dumps(task)

            # Connect to NSQ and publish
            # Using nsq-py library's publish function
            from nsq_py import publish_message

            publish_message(
                self.enrichment_topic,
                task_json,
                nsqd_tcp_addresses=[f"{self.nsq_host}:{self.nsq_port}"]
            )

            logger.debug(f"Published task {task['task_id']} to NSQ")
            return True

        except ImportError:
            # Fallback: Use direct HTTP publishing
            import requests
            try:
                response = requests.post(
                    f"http://{self.nsq_host}:4151/pub",
                    params={'topic': self.enrichment_topic},
                    data=task_json.encode('utf-8'),
                    timeout=5
                )
                if response.status_code == 200:
                    logger.debug(f"Published task {task['task_id']} to NSQ (HTTP)")
                    return True
                else:
                    logger.error(f"NSQ HTTP publish failed: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Error publishing to NSQ: {e}")
                return False

    def get_job_status(self, enrichment_job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of enrichment job

        Args:
            enrichment_job_id: Job ID to query

        Returns:
            Job document or None
        """
        if self.db is None:
            return None

        return self.db.enrichment_jobs.find_one({'_id': enrichment_job_id})

    def update_job_progress(
        self,
        enrichment_job_id: str,
        increment: Dict[str, int] = None,
        status: Optional[str] = None
    ) -> bool:
        """
        Update job progress counters

        Args:
            enrichment_job_id: Job ID to update
            increment: Dict with counters to increment (e.g., {'processed_count': 1})
            status: Optional new status

        Returns:
            True if updated successfully
        """
        if self.db is None or increment is None:
            return False

        try:
            update_dict = {'$inc': increment}
            if status:
                update_dict['$set'] = {'status': status}

            result = self.db.enrichment_jobs.update_one(
                {'_id': enrichment_job_id},
                update_dict
            )
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Error updating job progress: {e}")
            return False

    def mark_job_completed(self, enrichment_job_id: str) -> bool:
        """
        Mark enrichment job as completed

        Args:
            enrichment_job_id: Job ID to complete

        Returns:
            True if updated successfully
        """
        if self.db is None:
            return False

        try:
            result = self.db.enrichment_jobs.update_one(
                {'_id': enrichment_job_id},
                {'$set': {
                    'status': 'completed',
                    'completed_at': datetime.utcnow()
                }}
            )
            logger.info(f"Enrichment job {enrichment_job_id} marked as completed")
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Error marking job completed: {e}")
            return False


# Integration function to be called from ResultAggregator
def trigger_enrichment_after_ocr(ocr_job_id: str, collection_id: str, collection_metadata: Optional[Dict] = None) -> Optional[str]:
    """
    Trigger enrichment after OCR job completion

    This function should be called from ResultAggregator.mark_as_completed()
    after the OCR job is successfully completed.

    Example usage in result_aggregator.py:
        if config.get('ENRICHMENT_ENABLED'):
            enrichment_job_id = trigger_enrichment_after_ocr(
                ocr_job_id=job_id,
                collection_id=metadata.get('collection_id'),
                collection_metadata=metadata
            )

    Args:
        ocr_job_id: ID of completed OCR job
        collection_id: Collection ID
        collection_metadata: Optional collection metadata

    Returns:
        enrichment_job_id or None if enrichment disabled/failed
    """
    coordinator = EnrichmentCoordinator()
    return coordinator.create_enrichment_job(ocr_job_id, collection_id, collection_metadata)


if __name__ == '__main__':
    # Simple test
    logging.basicConfig(level=logging.INFO)
    coordinator = EnrichmentCoordinator()
    print("EnrichmentCoordinator initialized successfully")
