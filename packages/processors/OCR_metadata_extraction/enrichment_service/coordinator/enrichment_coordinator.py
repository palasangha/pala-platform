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
import gnsq
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
        # Build MongoDB URI with authentication if credentials provided
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr')
        mongo_username = os.getenv('MONGO_USERNAME')
        mongo_password = os.getenv('MONGO_PASSWORD')

        # If URI doesn't have auth but credentials are provided, build authenticated URI
        if mongo_username and mongo_password and '@' not in mongo_uri:
            # URL-encode the password to handle special characters like @, :, etc.
            from urllib.parse import quote_plus
            encoded_username = quote_plus(mongo_username)
            encoded_password = quote_plus(mongo_password)
            # Extract host and database from URI
            # mongodb://host:port/db -> mongodb://user:pass@host:port/db?authSource=admin
            mongo_uri = mongo_uri.replace('mongodb://', f'mongodb://{encoded_username}:{encoded_password}@')
            # Add authSource=admin parameter if not already present
            if '?authSource=' not in mongo_uri:
                mongo_uri = mongo_uri + '?authSource=admin'

        # Parse NSQD_ADDRESS if provided (format: "host:port"), otherwise use separate host/port
        nsqd_address = os.getenv('NSQD_ADDRESS', '')
        if ':' in nsqd_address:
            nsqd_host, nsqd_port = nsqd_address.rsplit(':', 1)
            nsqd_port = int(nsqd_port)
        else:
            nsqd_host = os.getenv('NSQD_HOST', 'nsqd')
            nsqd_port = int(os.getenv('NSQD_PORT', '4150'))

        return {
            'MONGO_URI': mongo_uri,
            'DB_NAME': os.getenv('DB_NAME', 'gvpocr'),
            'NSQD_HOST': nsqd_host,
            'NSQD_PORT': nsqd_port,
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
            ocr_job = self.db.bulk_jobs.find_one({'job_id': ocr_job_id})
            if not ocr_job:
                logger.error(f"OCR job {ocr_job_id} not found")
                return None

            # Check job status
            if ocr_job.get('status') != 'completed':
                logger.warning(f"OCR job {ocr_job_id} not completed, skipping enrichment")
                return None

            # Get list of processed documents from job checkpoint
            checkpoint = ocr_job.get('checkpoint', {})
            ocr_results = checkpoint.get('results', [])
            if not ocr_results:
                logger.warning(f"No OCR results found in checkpoint for job {ocr_job_id}")
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
                # Get document ID from result (use file path as unique identifier)
                doc_id = result.get('_id') or result.get('file', f"doc_{published_count}")
                
                # Build enrichment task
                task = {
                    'task_id': f"task_{enrichment_job_id}_{doc_id}",
                    'enrichment_job_id': enrichment_job_id,
                    'ocr_job_id': result.get('ocr_job_id', ''),
                    'document_id': str(doc_id),
                    'ocr_data': {
                        'text': result.get('text', ''),
                        'full_text': result.get('full_text', ''),
                        'confidence': result.get('confidence', 0.0),
                        'detected_language': result.get('detected_language', 'en'),
                        'blocks_count': result.get('blocks_count', 0),
                        'words_count': result.get('words_count', 0),
                        'provider': result.get('provider', 'unknown'),
                        'file': result.get('file', ''),
                        'file_path': result.get('file_path', ''),
                        'file_index': result.get('file_index', 0),
                        'status': result.get('status', 'success')
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
                logger.error(f"Error publishing task for document {result.get('file', 'unknown')}: {e}")
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
                # Use HTTP API on port 4151 (NSQ admin/HTTP port)
                nsq_http_url = f"http://{self.nsq_host}:4151/pub"
                params = {'topic': self.enrichment_topic}
                
                response = requests.post(
                    nsq_http_url,
                    params=params,
                    data=task_json.encode('utf-8'),
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.debug(f"Published task {task['task_id']} to NSQ (HTTP)")
                    return True
                else:
                    logger.error(f"NSQ HTTP publish failed: {response.status_code} - URL: {nsq_http_url}")
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
            
            # Trigger ZIP regeneration with enrichment data
            self._trigger_zip_regeneration(enrichment_job_id)
            
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Error marking job completed: {e}")
            return False

    def _trigger_zip_regeneration(self, enrichment_job_id: str):
        """
        Trigger ZIP file regeneration to include enrichment data
        
        Args:
            enrichment_job_id: Enrichment job ID
        """
        try:
            # Get enrichment job details
            job = self.db.enrichment_jobs.find_one({'_id': enrichment_job_id})
            if not job:
                logger.error(f"Enrichment job {enrichment_job_id} not found")
                return
            
            ocr_job_id = job.get('ocr_job_id')
            if not ocr_job_id:
                logger.error(f"No OCR job ID found for enrichment job {enrichment_job_id}")
                return
            
            logger.info(f"Triggering ZIP regeneration for OCR job {ocr_job_id}")
            
            # Publish ZIP regeneration task to NSQ
            zip_regen_task = {
                'task_type': 'regenerate_zip',
                'ocr_job_id': ocr_job_id,
                'enrichment_job_id': enrichment_job_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Publish to a separate topic or use the same enrichment topic
            import requests
            nsq_http_url = f"http://{self.nsq_host}:4151/pub"
            params = {'topic': 'zip_regeneration'}
            
            response = requests.post(
                nsq_http_url,
                params=params,
                data=json.dumps(zip_regen_task).encode('utf-8'),
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"ZIP regeneration task published for job {ocr_job_id}")
            else:
                logger.error(f"Failed to publish ZIP regeneration task: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error triggering ZIP regeneration: {e}", exc_info=True)


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
    # Simple test and keep-alive for Docker container
    import time
    logging.basicConfig(level=logging.INFO)
    coordinator = EnrichmentCoordinator()
    print("EnrichmentCoordinator initialized successfully")

    # Keep-alive loop (Docker service mode)
    logger.info("Coordinator service started - keeping alive...")
    try:
        while True:
            time.sleep(60)  # Check every minute
            # Can add monitoring tasks here if needed
    except KeyboardInterrupt:
        logger.info("Coordinator service stopped")
