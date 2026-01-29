#!/usr/bin/env python3
"""
ZIP Regeneration Worker - Listens for enrichment completion and regenerates ZIP files
"""

import asyncio
import json
import logging
import os
import sys
import requests
import gnsq
from pymongo import MongoClient

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from app.workers.result_aggregator import ResultAggregator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ZipRegenerationWorker:
    """Worker that regenerates ZIP files when enrichment completes"""
    
    def __init__(self):
        self.nsq_host = os.getenv('NSQD_HOST', 'nsqd')
        self.nsq_port = int(os.getenv('NSQD_PORT', '4150'))
        self.topic = 'zip_regeneration'
        self.channel = 'zip_worker'
        
        # MongoDB connection for ResultAggregator
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/gvpocr')
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client['gvpocr']
        
        # Initialize ResultAggregator
        self.aggregator = ResultAggregator()
        
        logger.info(f"ZipRegenerationWorker initialized - NSQ: {self.nsq_host}:{self.nsq_port}")
    
    def handle_message(self, sender=None, message=None):
        """Handle ZIP regeneration message"""
        if message is None:
            logger.error("No message provided to handler")
            return
        
        try:
            data = json.loads(message.body.decode('utf-8'))
            logger.info(f"Received ZIP regeneration task: {data}")
            
            ocr_job_id = data.get('ocr_job_id')
            enrichment_job_id = data.get('enrichment_job_id')
            
            if not ocr_job_id:
                logger.error("No OCR job ID in message")
                message.finish()
                return
            
            logger.info(f"Regenerating ZIP for OCR job: {ocr_job_id}")
            
            # Regenerate ZIP with enrichment data
            success = self.aggregator.regenerate_zip_with_enrichment(ocr_job_id)
            
            if success:
                logger.info(f"✓ ZIP regenerated successfully for job {ocr_job_id}")
                message.finish()
            else:
                logger.error(f"✗ Failed to regenerate ZIP for job {ocr_job_id}")
                message.requeue()
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            message.requeue()
    
    def start(self):
        """Start consuming from NSQ"""
        logger.info(f"Starting ZIP regeneration worker - Topic: {self.topic}, Channel: {self.channel}")
        
        consumer = gnsq.Consumer(
            self.topic,
            self.channel,
            nsqd_tcp_addresses=[f"{self.nsq_host}:{self.nsq_port}"],
            max_in_flight=1  # Process one at a time
        )
        
        # Set message handler
        consumer.on_message.connect(self.handle_message)
        
        logger.info("Starting consumer...")
        consumer.start()


if __name__ == '__main__':
    worker = ZipRegenerationWorker()
    worker.start()
