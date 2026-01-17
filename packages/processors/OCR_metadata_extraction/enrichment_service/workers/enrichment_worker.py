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
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import nsq

# Import our enrichment components
from enrichment_service.workers.agent_orchestrator import AgentOrchestrator
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

        # Initialize components
        self.orchestrator = AgentOrchestrator(self.config)
        self.schema_validator = SchemaValidator(self.config['SCHEMA_PATH'])
        self.review_queue = ReviewQueue(self.db) if self.db else None
        self.coordinator = EnrichmentCoordinator(self.config)

        # NSQ configuration
        self.nsq_host = self.config['NSQD_HOST']
        self.nsq_port = self.config['NSQD_PORT']
        self.lookupd_http_addresses = self.config['LOOKUPD_HTTP_ADDRESSES']
        self.enrichment_topic = self.config['ENRICHMENT_TOPIC']
        self.channel = self.config['ENRICHMENT_CHANNEL']

        logger.info(f"EnrichmentWorker initialized - NSQ: {self.nsq_host}:{self.nsq_port}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'MONGO_URI': os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr'),
            'DB_NAME': os.getenv('DB_NAME', 'gvpocr'),
            'NSQD_HOST': os.getenv('NSQD_HOST', 'localhost'),
            'NSQD_PORT': int(os.getenv('NSQD_PORT', '4150')),
            'LOOKUPD_HTTP_ADDRESSES': os.getenv('LOOKUPD_HTTP_ADDRESSES', 'localhost:4161').split(','),
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

                self.review_queue.create_task(
                    document_id=document_id,
                    enrichment_job_id=enrichment_job_id,
                    reason='completeness_below_threshold',
                    missing_fields=completeness_report['missing_fields'],
                    low_confidence_fields=completeness_report['low_confidence_fields']
                )

                self._record_review(enrichment_job_id)
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

        This is a blocking call that runs until the worker is stopped
        """
        logger.info(f"Starting NSQ consumer: topic={self.enrichment_topic}, channel={self.channel}")

        try:
            # Create consumer
            reader = nsq.Reader(
                topic=self.enrichment_topic,
                channel=self.channel,
                lookupd_http_addresses=self.lookupd_http_addresses,
                max_in_flight=100  # Max concurrent messages
            )

            # Set message handler
            reader.set_message_handler(self._handle_message)

            # Start consuming
            nsq.run()

        except Exception as e:
            logger.error(f"NSQ consumer error: {e}", exc_info=True)
            raise

    def _handle_message(self, message) -> bool:
        """
        NSQ message handler

        Args:
            message: NSQ message object

        Returns:
            True if message was processed successfully
        """
        try:
            # Decode message
            task_data = json.loads(message.body.decode('utf-8'))

            # Process asynchronously
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.process_task(task_data))

            if result:
                message.finish()  # Acknowledge message
                logger.debug("Message acknowledged")
            else:
                message.requeue()  # Requeue for retry
                logger.warning("Message requeued")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NSQ message: {e}")
            message.finish()  # Don't requeue invalid messages
            return False

        except Exception as e:
            logger.error(f"Error handling NSQ message: {e}", exc_info=True)
            message.requeue()  # Requeue on unexpected errors
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
