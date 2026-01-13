"""Entry point for result aggregator service"""
import logging
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workers.result_aggregator import ResultAggregator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Starting Result Aggregator Service")
    logger.info("=" * 80)

    aggregator = ResultAggregator(check_interval=10)

    try:
        aggregator.run()
    except KeyboardInterrupt:
        logger.info("Result Aggregator shutting down gracefully...")
    except Exception as e:
        logger.error(f"Result Aggregator failed with error: {e}", exc_info=True)
        sys.exit(1)
