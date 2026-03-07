#!/usr/bin/env python3
"""
Enrichment Worker - NSQ consumer for enrichment tasks

Consumes enrichment tasks from NSQ 'enrichment' topic
Orchestrates 3-phase MCP agent pipeline for document enrichment
Validates schema completeness and routes documents to review queue if needed
Saves enriched documents to MongoDB
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enrichment_service.workers.enrichment_worker import EnrichmentWorker
from enrichment_service.utils.logging_config import setup_logging, get_logger
from enrichment_service.config import config

logger = get_logger(__name__)


class EnrichmentWorkerService:
    """Service wrapper for enrichment worker"""

    def __init__(self, args: argparse.Namespace):
        """Initialize worker service"""
        self.args = args
        self.worker: Optional[EnrichmentWorker] = None
        self.running = True
        self.stats = {
            'tasks_consumed': 0,
            'documents_enriched': 0,
            'documents_approved': 0,
            'documents_review': 0,
            'errors': 0,
            'start_time': time.time()
        }

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    async def initialize(self) -> bool:
        """Initialize worker"""
        try:
            # Setup logging
            setup_logging(
                level=self.args.log_level,
                log_file=self.args.log_file,
                service_name='enrichment-worker',
                enable_json=True
            )

            logger.info("Initializing enrichment worker...")
            logger.info(f"Config: workers={self.args.workers}, "
                       f"max_concurrent={self.args.max_concurrent}, "
                       f"channel={self.args.channel}")

            # Validate MongoDB connection
            try:
                mongo_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
                mongo_client.admin.command('ping')
                logger.info("✓ MongoDB connection verified")
                mongo_client.close()
            except Exception as e:
                logger.error(f"✗ Failed to connect to MongoDB: {e}")
                return False

            # Validate NSQ connection
            try:
                import nsq
                logger.info(f"✓ NSQ library available (version {nsq.__version__})")
            except ImportError:
                logger.error("✗ NSQ library not available")
                return False
            except Exception as e:
                logger.warning(f"⚠ Warning checking NSQ: {e}")

            # Initialize worker
            self.worker = EnrichmentWorker()
            logger.info("✓ Enrichment worker initialized")

            return True

        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            return False

    async def run_health_server(self) -> None:
        """Run health check HTTP server"""
        try:
            import aiohttp
            from aiohttp import web
            from datetime import datetime

            async def health_check(request):
                """Health check endpoint"""
                uptime_seconds = time.time() - self.stats['start_time']
                return web.json_response({
                    'status': 'healthy' if self.running else 'shutting_down',
                    'timestamp': datetime.utcnow().isoformat(),
                    'uptime_seconds': uptime_seconds,
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
        """Run worker service"""
        try:
            # Initialize
            if not await self.initialize():
                logger.error("✗ Failed to initialize worker")
                sys.exit(1)

            # Start health server
            health_task = asyncio.create_task(self.run_health_server())

            # Start NSQ consumer
            logger.info(f"Starting NSQ consumer (topic=enrichment, channel={self.args.channel})...")
            logger.info(f"Worker will consume and process enrichment tasks from NSQ")

            # Start consuming
            await self.worker.start_consuming()

        except Exception as e:
            logger.error(f"✗ Worker error: {e}", exc_info=True)
            self.running = False
        finally:
            # Cleanup
            if self.worker:
                try:
                    await self.worker.cleanup()
                    logger.info("✓ Worker cleaned up")
                except Exception as e:
                    logger.warning(f"Error during cleanup: {e}")

            uptime_seconds = time.time() - self.stats['start_time']
            logger.info(f"Uptime: {uptime_seconds:.1f}s")
            logger.info(f"Final statistics: {json.dumps(self.stats, indent=2)}")
            logger.info("Enrichment worker shutting down")

    def print_stats(self) -> None:
        """Print current statistics"""
        uptime_seconds = time.time() - self.stats['start_time']
        logger.info(f"=== Worker Statistics ===")
        logger.info(f"Tasks consumed: {self.stats['tasks_consumed']}")
        logger.info(f"Documents enriched: {self.stats['documents_enriched']}")
        logger.info(f"Documents approved (≥95%): {self.stats['documents_approved']}")
        logger.info(f"Documents flagged for review (<95%): {self.stats['documents_review']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Uptime: {uptime_seconds:.1f}s")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Enrichment Worker - Consume and process enrichment tasks from NSQ'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker threads (default: 1)'
    )
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=10,
        help='Max concurrent tasks per worker (default: 10)'
    )
    parser.add_argument(
        '--channel',
        type=str,
        default='enrichment_worker',
        help='NSQ channel name (default: enrichment_worker)'
    )
    parser.add_argument(
        '--health-port',
        type=int,
        default=8002,
        help='Port for health check endpoint (default: 8002)'
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
        help='Log file path (default: logs/enrichment-worker.log)'
    )

    args = parser.parse_args()

    # Run service
    service = EnrichmentWorkerService(args)

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
