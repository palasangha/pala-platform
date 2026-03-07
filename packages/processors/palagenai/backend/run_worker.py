"""Entry point for starting an OCR worker process"""
import argparse
import logging
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workers.ocr_worker import OCRWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OCR Worker for NSQ')
    parser.add_argument('--worker-id', required=True, help='Unique worker identifier')
    parser.add_argument('--nsqlookupd', required=True, nargs='+', help='NSQ lookupd HTTP addresses (e.g., nsqlookupd:4161)')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info(f"Starting OCR Worker: {args.worker_id}")
    logger.info(f"NSQ lookupd addresses: {args.nsqlookupd}")
    logger.info("=" * 80)

    worker = OCRWorker(args.worker_id, args.nsqlookupd)

    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info(f"Worker {args.worker_id} shutting down gracefully...")
    except Exception as e:
        logger.error(f"Worker {args.worker_id} failed with error: {e}", exc_info=True)
        sys.exit(1)
