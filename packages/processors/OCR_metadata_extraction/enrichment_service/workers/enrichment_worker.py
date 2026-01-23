"""
EnrichmentWorker - NSQ consumer that processes enrichment tasks

Consumes enrichment tasks from NSQ topic "enrichment"
Orchestrates 5 MCP agents through 3-phase pipeline
Validates schema completeness and routes to review queue if needed
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import gnsq

# Handle event loop conflicts by allowing nested event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    # nest_asyncio not available, use fallback approach
    pass

# Import our enrichment components
from enrichment_service.workers.agent_orchestrator import AgentOrchestrator
from enrichment_service.mcp_client.client import MCPClient
from enrichment_service.schema.validator import SchemaValidator
from enrichment_service.models.enrichment_job import EnrichmentJob
from enrichment_service.models.enriched_document import EnrichedDocument
from enrichment_service.review.review_queue import ReviewQueue
from enrichment_service.coordinator.enrichment_coordinator import EnrichmentCoordinator

logger = logging.getLogger(__name__)


class EnrichmentWorker:
    """
    NSQ consumer for enrichment tasks
    Orchestrates enrichment pipeline and saves results
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize EnrichmentWorker

        Args:
            config: Optional configuration dict
        """
        self.config = config or self._load_config()

        # MongoDB connection
        try:
            self.mongo_client = MongoClient(
                self.config['MONGO_URI'],
                serverSelectionTimeoutMS=5000
            )
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.config['DB_NAME']]
            logger.info("✓ MongoDB connected")
        except ConnectionFailure as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            self.db = None

        # Initialize MCP client for agents
        self.mcp_client = MCPClient(
            server_url=self.config.get('MCP_SERVER_URL', 'ws://localhost:3000')
        )

        # Initialize components with proper parameters
        self.orchestrator = AgentOrchestrator(
            mcp_client=self.mcp_client,
            schema_path=self.config.get('SCHEMA_PATH'),
            db=self.db
        )
        self.schema_validator = SchemaValidator(self.config['SCHEMA_PATH'])
        self.review_queue = ReviewQueue(self.db) if self.db is not None else None
        self.coordinator = EnrichmentCoordinator(self.config)

        # NSQ configuration
        self.nsq_host = self.config['NSQD_HOST']
        self.nsq_port = self.config['NSQD_PORT']
        self.lookupd_http_addresses = self.config['LOOKUPD_HTTP_ADDRESSES']
        self.enrichment_topic = self.config['ENRICHMENT_TOPIC']
        self.enrichment_channel = self.config['ENRICHMENT_CHANNEL']

        # Thread pool for async processing in sync NSQ handler
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="enrichment_worker")

        logger.info(f"EnrichmentWorker initialized - NSQ: {self.nsq_host}:{self.nsq_port}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        # Parse NSQD_ADDRESS if provided (format: "host:port"), otherwise use separate host/port
        nsqd_address = os.getenv('NSQD_ADDRESS', '')
        if ':' in nsqd_address:
            nsqd_host, nsqd_port = nsqd_address.rsplit(':', 1)
            nsqd_port = int(nsqd_port)
        else:
            nsqd_host = os.getenv('NSQD_HOST', 'nsqd')
            nsqd_port = int(os.getenv('NSQD_PORT', '4150'))

        # Build MONGO_URI with proper URL encoding for credentials
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            # If MONGO_URI not provided, build from components
            mongo_user = os.getenv('MONGO_USERNAME', 'gvpocr_admin')
            mongo_pass = os.getenv('MONGO_PASSWORD', '')
            mongo_host = os.getenv('MONGO_HOST', 'mongodb')
            mongo_port = os.getenv('MONGO_PORT', '27017')
            mongo_db = os.getenv('DB_NAME', 'gvpocr')

            if mongo_pass:
                # URL-encode username and password to handle special characters
                mongo_uri = f"mongodb://{quote_plus(mongo_user)}:{quote_plus(mongo_pass)}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
            else:
                mongo_uri = f"mongodb://{mongo_host}:{mongo_port}/{mongo_db}"

        return {
            'MONGO_URI': mongo_uri,
            'DB_NAME': os.getenv('DB_NAME', 'gvpocr'),
            'NSQD_HOST': nsqd_host,
            'NSQD_PORT': nsqd_port,
            'LOOKUPD_HTTP_ADDRESSES': os.getenv('NSQLOOKUPD_ADDRESSES', os.getenv('LOOKUPD_HTTP_ADDRESSES', 'nsqlookupd:4161')).split(','),
            'ENRICHMENT_TOPIC': os.getenv('ENRICHMENT_TOPIC', 'enrichment'),
            'ENRICHMENT_CHANNEL': os.getenv('ENRICHMENT_CHANNEL', 'enrichment_worker'),
            'SCHEMA_PATH': os.getenv('SCHEMA_PATH', '/app/enrichment_service/schema/historical_letters_schema.json'),
            'MCP_SERVER_URL': os.getenv('MCP_SERVER_URL', 'ws://localhost:3000'),
            'COMPLETENESS_THRESHOLD': float(os.getenv('COMPLETENESS_THRESHOLD', '0.95')),
            'BATCH_SIZE': int(os.getenv('BATCH_SIZE', '50')),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
        }

    async def process_task(self, message: Dict[str, Any]) -> bool:
        """
        Process single enrichment task

        Args:
            message: NSQ message containing enrichment task

        Returns:
            True if processed successfully
        """
        task_id = message.get('task_id', 'unknown')
        enrichment_job_id = message.get('enrichment_job_id', '')
        document_id = message.get('document_id', '')
        ocr_data = message.get('ocr_data', {})

        logger.info(f"Processing enrichment task {task_id} for document {document_id}")

        try:
            # Step 1: Validate input
            if not self._validate_input(message):
                logger.error(f"Invalid task {task_id}: missing required fields")
                return False

            # Step 2: Run enrichment pipeline
            enrichment_result = await self.orchestrator.enrich_document(
                document_id=document_id,
                ocr_data=ocr_data,
                collection_metadata=message.get('collection_metadata', {})
            )

            if enrichment_result is None:
                logger.error(f"Enrichment failed for document {document_id}")
                self._record_failure(enrichment_job_id, 'enrichment_failed')
                return False

            # Step 3: Validate schema completeness
            completeness_report = self.schema_validator.calculate_completeness(
                enrichment_result['enriched_data']
            )

            logger.info(
                f"Document {document_id} completeness: {completeness_report['completeness_score']:.1%} "
                f"({completeness_report['present_fields']}/{completeness_report['total_required_fields']} fields)"
            )

            # Step 4: Save enriched document
            saved = self._save_enriched_document(
                document_id=document_id,
                ocr_data=ocr_data,
                enriched_data=enrichment_result['enriched_data'],
                completeness_report=completeness_report,
                enrichment_job_id=enrichment_job_id
            )

            if not saved:
                logger.error(f"Failed to save enriched document {document_id}")
                self._record_failure(enrichment_job_id, 'save_failed')
                return False

            # Step 5: Route to review queue if completeness below threshold
            if not completeness_report['passes_threshold']:
                logger.info(
                    f"Document {document_id} completeness ({completeness_report['completeness_score']:.1%}) "
                    f"below threshold, routing to review"
                )

                if self.review_queue:
                    self.review_queue.create_task(
                        document_id=document_id,
                        enrichment_job_id=enrichment_job_id,
                        reason='completeness_below_threshold',
                        missing_fields=completeness_report['missing_fields'],
                        low_confidence_fields=completeness_report['low_confidence_fields']
                    )
                    self._record_review(enrichment_job_id)
                else:
                    logger.warning(f"Review queue not available, document {document_id} not routed for review")
            else:
                logger.info(f"Document {document_id} passed quality threshold, approved")

            # Step 6: Update job progress
            self.coordinator.update_job_progress(
                enrichment_job_id,
                increment={
                    'processed_count': 1,
                    'success_count': 1
                }
            )

            logger.info(f"✓ Task {task_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            self._record_failure(enrichment_job_id, f'exception: {str(e)}')
            return False

    def _validate_input(self, message: Dict[str, Any]) -> bool:
        """Validate required fields in enrichment task"""
        required_fields = ['document_id', 'enrichment_job_id', 'ocr_data']
        return all(field in message for field in required_fields)

    def _save_enriched_document(
        self,
        document_id: str,
        ocr_data: Dict[str, Any],
        enriched_data: Dict[str, Any],
        completeness_report: Dict[str, Any],
        enrichment_job_id: str
    ) -> bool:
        """
        Save enriched document to MongoDB

        Args:
            document_id: Document ID
            ocr_data: Original OCR data
            enriched_data: Enriched data from agents
            completeness_report: Completeness validation report
            enrichment_job_id: Parent enrichment job ID

        Returns:
            True if saved successfully
        """
        if self.db is None:
            return False

        try:
            enriched_doc = {
                '_id': document_id,
                'enrichment_job_id': enrichment_job_id,
                'ocr_data': ocr_data,
                'enriched_data': enriched_data,
                'quality_metrics': {
                    'completeness_score': completeness_report['completeness_score'],
                    'missing_fields': completeness_report['missing_fields'],
                    'low_confidence_fields': completeness_report['low_confidence_fields'],
                    'total_required_fields': completeness_report['total_required_fields'],
                    'present_fields': completeness_report['present_fields']
                },
                'review_status': 'approved' if completeness_report['passes_threshold'] else 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            result = self.db.enriched_documents.update_one(
                {'_id': document_id},
                {'$set': enriched_doc},
                upsert=True
            )

            logger.debug(f"Saved enriched document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving enriched document {document_id}: {e}")
            return False

    def _record_failure(self, enrichment_job_id: str, reason: str) -> None:
        """Record task failure in job statistics"""
        try:
            self.coordinator.update_job_progress(
                enrichment_job_id,
                increment={
                    'processed_count': 1,
                    'error_count': 1
                }
            )
            logger.debug(f"Recorded failure for job {enrichment_job_id}: {reason}")
        except Exception as e:
            logger.error(f"Error recording failure: {e}")

    def _record_review(self, enrichment_job_id: str) -> None:
        """Record document routed to review"""
        try:
            self.coordinator.update_job_progress(
                enrichment_job_id,
                increment={'review_count': 1}
            )
            logger.debug(f"Recorded review routing for job {enrichment_job_id}")
        except Exception as e:
            logger.error(f"Error recording review: {e}")

    async def start_consuming(self):
        """
        Start consuming messages from NSQ

        Runs the blocking gnsq consumer in a thread pool to avoid blocking the event loop
        """
        logger.info(f"Starting NSQ consumer: topic={self.enrichment_topic}, channel={self.enrichment_channel}")
        logger.info(f"Lookupd addresses: {self.lookupd_http_addresses}")

        try:
            # Create consumer using gnsq
            # Try connecting directly to nsqd first, then fall back to lookupd
            try:
                logger.info(f"Attempting direct connection to nsqd: {self.nsq_host}:{self.nsq_port}")
                consumer = gnsq.Consumer(
                    self.enrichment_topic,
                    self.enrichment_channel,
                    nsqd_tcp_addresses=[f"{self.nsq_host}:{self.nsq_port}"],
                    max_in_flight=100
                )
                logger.info("✅ Connected to nsqd directly")
            except Exception as e:
                logger.warning(f"Direct nsqd connection failed, trying lookupd: {e}")
                consumer = gnsq.Consumer(
                    self.enrichment_topic,
                    self.enrichment_channel,
                    self.lookupd_http_addresses,
                    max_in_flight=100
                )
                logger.info("✅ Connected to nsqlookupd")

            # Set message handler
            consumer.on_message.connect(self._handle_message)

            logger.info("NSQ Consumer created, starting to consume messages...")

            # Run gnsq consumer in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, consumer.start)

        except Exception as e:
            logger.error(f"NSQ consumer error: {e}", exc_info=True)
            raise

    def _handle_message(self, sender=None, message=None) -> bool:
        """
        NSQ message handler - runs async task in thread to avoid blocking NSQ loop
        
        Called by blinker signal which sends (sender, message=msg)

        Args:
            sender: The signal sender (self)
            message: NSQ message object

        Returns:
            True if message was processed successfully
        """
        try:
            if message is None:
                logger.error("No message provided to handler")
                return False
                
            # Decode message
            task_data = json.loads(message.body.decode('utf-8'))

            # Process in thread pool to avoid blocking NSQ event loop
            # Create new event loop for this thread
            result = self._process_task_sync(task_data)

            if result:
                message.finish()  # Acknowledge message
                logger.debug(f"Message acknowledged: task_id={task_data.get('task_id', 'unknown')}")
            else:
                message.requeue()  # Requeue for retry
                logger.warning(f"Message requeued: task_id={task_data.get('task_id', 'unknown')}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NSQ message: {e}")
            message.finish()  # Don't requeue invalid messages
            return False

        except Exception as e:
            logger.error(f"Error handling NSQ message: {e}", exc_info=True)
            message.requeue()  # Requeue on unexpected errors
            return False

    def _process_task_sync(self, task_data: Dict[str, Any]) -> bool:
        """
        Process task synchronously (wrapper for async process_task)

        Runs async process_task in a fresh event loop in a separate thread

        Args:
            task_data: Task data dict

        Returns:
            True if processed successfully
        """
        def run_async_task_in_thread():
            """Helper to run async task in its own event loop in a separate thread"""
            try:
                # Clear any existing event loop for this thread
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # This shouldn't happen in a fresh thread, but handle it
                        logger.warning("Event loop already running in thread")
                        loop = None
                except RuntimeError:
                    loop = None

                # Create a completely fresh event loop
                if loop is None or loop.is_closed():
                    asyncio.set_event_loop(None)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Run the coroutine
                result = loop.run_until_complete(self.process_task(task_data))
                return result
            finally:
                # Always clean up
                try:
                    loop.close()
                except:
                    pass
                asyncio.set_event_loop(None)

        try:
            # Run in thread pool to ensure complete isolation from main event loop
            future = self.executor.submit(run_async_task_in_thread)
            result = future.result(timeout=300)  # 5 minute timeout
            return result
        except Exception as e:
            logger.error(f"Error in sync task processing: {e}", exc_info=True)
            return False

    async def process_batch(self, tasks: list) -> Dict[str, int]:
        """
        Process batch of enrichment tasks concurrently

        Args:
            tasks: List of enrichment task dicts

        Returns:
            Statistics dict with success/failure counts
        """
        logger.info(f"Processing batch of {len(tasks)} documents")

        results = await asyncio.gather(
            *[self.process_task(task) for task in tasks],
            return_exceptions=True
        )

        stats = {
            'total': len(tasks),
            'success': sum(1 for r in results if r is True),
            'failed': sum(1 for r in results if r is False),
            'errors': sum(1 for r in results if isinstance(r, Exception))
        }

        logger.info(f"Batch complete: {stats['success']}/{stats['total']} successful")
        return stats


# Entry point for containerized worker
async def main():
    """Main entry point for enrichment worker"""
    logging.basicConfig(level=logging.INFO)

    worker = EnrichmentWorker()
    await worker.start_consuming()


if __name__ == '__main__':
    asyncio.run(main())
