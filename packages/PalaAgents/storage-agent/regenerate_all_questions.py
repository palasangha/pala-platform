#!/usr/bin/env python3
"""
Regenerate questions for all documents using Ollama
"""
import asyncio
import sqlite3
import json
import logging
import os
import sys
from pathlib import Path

# Add metadata-extraction-agent to path for Ollama provider
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(agent_dir, '../metadata-extraction-agent'))

from question_generator import QuestionGenerator
from providers.ollama_provider import OllamaMetadataProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def regenerate_all_questions():
    """Generate questions for all documents"""
    
    # Initialize Ollama provider
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    model = os.getenv('OLLAMA_MODEL', 'mistral')
    
    logger.info(f"🔌 Connecting to Ollama at {base_url} (model: {model})...")
    ollama_provider = OllamaMetadataProvider(base_url=base_url, model=model)
    
    if not ollama_provider.is_available():
        logger.error("❌ Ollama not available!")
        return
    
    logger.info("✅ Ollama connected")
    
    # Initialize generator
    gen = QuestionGenerator(ollama_provider)
    
    # Connect to storage DB
    storage_conn = sqlite3.connect('storage_metadata.db')
    storage_conn.row_factory = sqlite3.Row
    storage_c = storage_conn.cursor()
    
    # Get all documents
    storage_c.execute("SELECT id, original_file, processed_data FROM documents")
    documents = storage_c.fetchall()
    
    logger.info(f"🔄 Processing {len(documents)} documents...")
    
    success_count = 0
    error_count = 0
    
    for i, doc in enumerate(documents, 1):
        doc_id = doc['id']
        filename = doc['original_file']
        
        try:
            logger.info(f"\n[{i}/{len(documents)}] Generating questions for: {filename}")
            
            # Parse processed_data
            processed_data = json.loads(doc['processed_data'])
            
            # Extract content (handle nested structure)
            if isinstance(processed_data, dict) and 'result' in processed_data:
                # Nested structure from OCR processor
                content_data = processed_data['result']
                if isinstance(content_data, dict):
                    content = content_data.get('content', '')
                else:
                    content = str(content_data)
            elif isinstance(processed_data, dict) and 'content' in processed_data:
                content = processed_data['content']
            else:
                content = str(processed_data)
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"⚠️  Insufficient content for {filename} (length: {len(content)})")
                continue
            
            # Generate questions
            logger.info(f"✍️  Generating questions from {len(content)} chars of content...")
            questions = await gen.generate_questions(doc_id, content)
            
            if not questions:
                logger.warning(f"⚠️  No questions generated for {filename}")
                continue
            
            # Store questions
            stored_count = await gen.store_questions(doc_id, questions)
            logger.info(f"✅ Stored {stored_count} questions for {filename}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing {filename}: {e}", exc_info=True)
            error_count += 1
    
    storage_conn.close()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Complete: {success_count} successful, {error_count} errors")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(regenerate_all_questions())
