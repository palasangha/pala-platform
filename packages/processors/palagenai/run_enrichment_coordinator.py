#!/usr/bin/env python3
"""
Enrichment Coordinator - Monitors MongoDB for completed OCR jobs

Polls MongoDB for OCR jobs with status='completed' and enrichment_triggered != True
Creates enrichment jobs and publishes tasks to NSQ 'enrichment' topic
Supports dry-run mode and batch processing
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enrichment_service.coordinator.enrichment_coordinator import EnrichmentCoordinator
from enrichment_service.utils.logging_config import setup_logging, get_logger, inject_context
from enrichment_service.config import config

logger = get_logger(__name__)


class EnrichmentCoordinatorService:
    """Service wrapper for enrichment coordinator"""

    def __init__(self, args: argparse.Namespace):
        """Initialize coordinator service"""
        self.args = args
        self.coordinator: Optional[EnrichmentCoordinator] = None
        self.running = True
        self.stats = {
            'ocr_jobs_processed': 0,
            'enrichment_jobs_created': 0,
            'tasks_published': 0,
            'errors': 0
        }

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    async def initialize(self) -> bool:
        """Initialize coordinator"""
        try:
            # Setup logging
            setup_logging(
                level=self.args.log_level,
                log_file=self.args.log_file,
                service_name='enrichment-coordinator',
                enable_json=True
            )

            logger.info("Initializing enrichment coordinator...")
            logger.info(f"Config: poll_interval={self.args.poll_interval}s, "
                       f"batch_size={self.args.batch_size}, dry_run={self.args.dry_run}")

            # Validate MongoDB connection
            try:
                mongo_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
                mongo_client.admin.command('ping')
                logger.info("✓ MongoDB connection verified")
                mongo_client.close()
            except Exception as e:
                logger.error(f"✗ Failed to connect to MongoDB: {e}")
                return False

            # Initialize coordinator
            self.coordinator = EnrichmentCoordinator()
            logger.info("✓ Enrichment coordinator initialized")

            return True

        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            return False

    async def poll_and_process(self) -> None:
        """
        Main polling loop

        Continuously polls MongoDB for completed OCR jobs and processes them
        """
        logger.info(f"Starting polling loop (interval={self.args.poll_interval}s)")
        logger.info(f"Monitoring for OCR jobs with status=completed and enrichment_triggered!=true")

        while self.running:
            try:
                poll_start = time.time()

                # Find OCR jobs ready for enrichment
                db = MongoClient(config.MONGO_URI)[config.DB_NAME]
                query = {
                    'status': 'completed',
                    '$or': [
                        {'enrichment_triggered': {'$exists': False}},
                        {'enrichment_triggered': False}
                    ]
                }

                ocr_jobs = list(db.ocr_jobs.find(query).limit(self.args.batch_size))

                if ocr_jobs:
                    logger.info(f"Found {len(ocr_jobs)} OCR jobs ready for enrichment")

                    for ocr_job in ocr_jobs:
                        try:
                            ocr_job_id = ocr_job['_id']
                            document_id = ocr_job.get('document_id', str(ocr_job_id))

                            logger.info(f"Processing OCR job {ocr_job_id} (document={document_id})")

                            # Create enrichment job
                            if not self.args.dry_run:
                                enrichment_job = self.coordinator.create_enrichment_job(
                                    ocr_job_id=str(ocr_job_id),
                                    document_id=document_id,
                                    ocr_data=ocr_job.get('ocr_result', {})
                                )

                                if enrichment_job:
                                    logger.info(f"✓ Created enrichment job {enrichment_job['_id']}")
                                    self.stats['enrichment_jobs_created'] += 1

                                    # Publish task to NSQ
                                    task_published = self.coordinator.publish_enrichment_task(
                                        enrichment_job_id=str(enrichment_job['_id']),
                                        ocr_job_id=str(ocr_job_id),
                                        document_id=document_id,
                                        ocr_data=ocr_job.get('ocr_result', {})
                                    )

                                    if task_published:
                                        logger.info(f"✓ Published task to NSQ for job {enrichment_job['_id']}")
                                        self.stats['tasks_published'] += 1
                                    else:
                                        logger.error(f"✗ Failed to publish task for job {enrichment_job['_id']}")
                                        self.stats['errors'] += 1

                                    # Mark OCR job as enrichment triggered
                                    db.ocr_jobs.update_one(
                                        {'_id': ocr_job_id},
                                        {
                                            '$set': {
                                                'enrichment_triggered': True,
                                                'enrichment_job_id': str(enrichment_job['_id']),
                                                'enrichment_triggered_at': datetime.utcnow()
                                            }
                                        }
                                    )
                                    logger.info(f"✓ Marked OCR job {ocr_job_id} as enrichment_triggered=true")
                                else:
                                    logger.error(f"✗ Failed to create enrichment job for {ocr_job_id}")
                                    self.stats['errors'] += 1
                            else:
                                # Dry run - just log
                                logger.info(f"[DRY RUN] Would create enrichment job for {ocr_job_id}")
                                self.stats['enrichment_jobs_created'] += 1

                            self.stats['ocr_jobs_processed'] += 1

                        except Exception as e:
                            logger.error(f"✗ Error processing job: {e}", exc_info=True)
                            self.stats['errors'] += 1

                    poll_duration = time.time() - poll_start
                    logger.info(f"✓ Batch processing completed in {poll_duration:.2f}s")
                else:
                    # No jobs found
                    logger.debug("No OCR jobs ready for enrichment")

                # Sleep before next poll
                await asyncio.sleep(self.args.poll_interval)

            except ConnectionFailure as e:
                logger.error(f"✗ Database connection lost: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)  # Backoff on connection failure
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                self.running = False
            except Exception as e:
                logger.error(f"✗ Unexpected error in polling loop: {e}", exc_info=True)
                self.stats['errors'] += 1
                await asyncio.sleep(5)

    async def run_health_server(self) -> None:
        """Run health check HTTP server"""
        try:
            import aiohttp
            from aiohttp import web

            async def health_check(request):
                """Health check endpoint"""
                return web.json_response({
                    'status': 'healthy' if self.running else 'shutting_down',
                    'timestamp': datetime.utcnow().isoformat(),
                    'stats': self.stats
                })

            app = web.Application()
            app.router.add_get('/health', health_check)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.args.health_port)
            await site.start()

            logger.info(f"✓ Health server started on port {self.args.health_port}")
        except ImportError:
            logger.warning("aiohttp not available, health server disabled")
        except Exception as e:
            logger.error(f"Failed to start health server: {e}")

    async def run(self) -> None:
        """Run coordinator service"""
        try:
            # Initialize
            if not await self.initialize():
                logger.error("✗ Failed to initialize coordinator")
                sys.exit(1)

            # Start health server
            health_task = asyncio.create_task(self.run_health_server())

            # Start polling
            await self.poll_and_process()

        except Exception as e:
            logger.error(f"✗ Service error: {e}", exc_info=True)
            self.running = False
        finally:
            # Cleanup
            logger.info(f"Final statistics: {json.dumps(self.stats, indent=2)}")
            logger.info("Enrichment coordinator shutting down")

    def print_stats(self) -> None:
        """Print current statistics"""
        logger.info(f"=== Coordinator Statistics ===")
        logger.info(f"OCR jobs processed: {self.stats['ocr_jobs_processed']}")
        logger.info(f"Enrichment jobs created: {self.stats['enrichment_jobs_created']}")
        logger.info(f"Tasks published: {self.stats['tasks_published']}")
        logger.info(f"Errors: {self.stats['errors']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Enrichment Coordinator - Monitor OCR jobs and publish enrichment tasks'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=30,
        help='Seconds to wait between polling cycles (default: 30)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Max number of OCR jobs to process per poll (default: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Dry run mode - log what would happen without making changes'
    )
    parser.add_argument(
        '--health-port',
        type=int,
        default=8001,
        help='Port for health check endpoint (default: 8001)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log file path (default: logs/enrichment-coordinator.log)'
    )

    args = parser.parse_args()

    # Run service
    service = EnrichmentCoordinatorService(args)

    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        service.print_stats()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
