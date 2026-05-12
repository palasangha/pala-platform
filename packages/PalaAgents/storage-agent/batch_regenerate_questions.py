#!/usr/bin/env python3
"""
Batch Question Regeneration Script

Generates questions for all existing documents in the library.
Supports resume capability and rate limiting.

Usage:
    python3 batch_regenerate_questions.py [--limit 100] [--resume] [--skip-existing]
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import argparse
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add parent directories to path
agent_dir = Path(__file__).parent
sys.path.insert(0, str(agent_dir.parent / "metadata-extraction-agent"))


async def main():
    parser = argparse.ArgumentParser(description="Batch regenerate questions for existing documents")
    parser.add_argument("--limit", type=int, default=None, help="Maximum documents to process")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--skip-existing", action="store_true", help="Skip documents that already have questions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between documents (seconds)")
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("BATCH QUESTION REGENERATION")
    logger.info("=" * 80)
    logger.info(f"Options: limit={args.limit}, resume={args.resume}, skip_existing={args.skip_existing}, delay={args.delay}s")
    
    # Initialize components
    try:
        from provider_factory import get_provider
        from questions_db import QuestionsDB
        from question_generator import QuestionGenerator
        from providers.ollama_provider import OllamaMetadataProvider
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    
    try:
        logger.info("Initializing components...")
        
        # Storage provider
        storage_provider = get_provider()
        logger.info(f"✓ Storage provider initialized: {type(storage_provider).__name__}")
        
        # Embedding model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✓ Embedding model loaded")
        
        # Ollama provider
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'mistral')
        ollama_provider = OllamaMetadataProvider(base_url=base_url, model=model)
        if not ollama_provider.is_available():
            logger.error("Ollama provider not available")
            return False
        logger.info(f"✓ Ollama provider initialized (url={base_url}, model={model})")
        
        # Questions database
        db_path = agent_dir / 'data' / 'questions_metadata.db'
        questions_db = QuestionsDB(str(db_path))
        logger.info(f"✓ Questions database initialized: {db_path}")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        return False
    
    # Create checkpoint file
    checkpoint_file = agent_dir / 'data' / 'batch_regeneration_checkpoint.json'
    checkpoint = {}
    
    if args.resume and checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            logger.info(f"✓ Resuming from checkpoint: processed={checkpoint.get('processed_count', 0)}")
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            checkpoint = {}
    
    # Get all documents
    try:
        logger.info("Fetching all documents...")
        all_docs = await storage_provider.list_documents()
        
        if isinstance(all_docs, dict):
            documents = all_docs.get('documents', [])
        else:
            documents = all_docs
        
        logger.info(f"✓ Found {len(documents)} total documents")
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        return False
    
    # Filter documents
    processed_ids = set(checkpoint.get('processed_ids', []))
    docs_to_process = []
    
    for doc in documents:
        doc_id = doc.get('id') if isinstance(doc, dict) else getattr(doc, 'id', None)
        
        if not doc_id:
            continue
        
        # Skip if already processed
        if args.resume and doc_id in processed_ids:
            continue
        
        # Skip if exists and skip-existing is set
        if args.skip_existing:
            existing = questions_db.get_questions_for_document(doc_id)
            if existing:
                continue
        
        docs_to_process.append(doc)
    
    logger.info(f"Will process {len(docs_to_process)} documents")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] Documents to process:")
        for i, doc in enumerate(docs_to_process[:10], 1):
            doc_id = doc.get('id') if isinstance(doc, dict) else getattr(doc, 'id', None)
            logger.info(f"  {i}. {doc_id}")
        if len(docs_to_process) > 10:
            logger.info(f"  ... and {len(docs_to_process) - 10} more")
        return True
    
    # Process documents
    if args.limit:
        docs_to_process = docs_to_process[:args.limit]
    
    logger.info(f"\nStarting batch processing ({len(docs_to_process)} documents)...")
    
    stats = {
        'total': len(docs_to_process),
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'errors': [],
    }
    
    gen = QuestionGenerator(ollama_provider)
    
    for i, doc in enumerate(docs_to_process, 1):
        doc_id = doc.get('id') if isinstance(doc, dict) else getattr(doc, 'id', None)
        
        try:
            # Get full document details
            if isinstance(doc, dict):
                # Already have the data
                doc_type = doc.get('type', 'document')
                metadata = doc.get('metadata', {})
                processed_data = doc.get('processed_data', {})
                original_file = doc.get('original_file', '')
            else:
                # Fetch from storage
                full_doc = await storage_provider.retrieve_document(doc_id)
                if not full_doc:
                    logger.warning(f"[{i}/{len(docs_to_process)}] ⚠ Document {doc_id} not found during retrieval")
                    stats['skipped'] += 1
                    continue
                
                doc_type = full_doc.type
                metadata = full_doc.metadata
                processed_data = full_doc.processed_data
                original_file = full_doc.original_file
            
            logger.info(f"[{i}/{len(docs_to_process)}] Processing: {doc_id}")
            
            # Check if already has questions
            existing = questions_db.get_questions_for_document(doc_id)
            if existing:
                logger.info(f"  ⊘ Already has {len(existing)} questions, skipping")
                stats['skipped'] += 1
            else:
                # Generate questions
                questions_db.mark_generation_status(doc_id, 'generating')
                
                questions = await gen.generate_questions_for_document(
                    doc_id=doc_id,
                    doc_type=doc_type,
                    metadata=metadata,
                    processed_data=processed_data,
                    original_file=original_file,
                    embedding_model=embedding_model
                )
                
                if questions:
                    questions_db.store_questions_batch(questions)
                    questions_db.mark_generation_status(
                        doc_id, 'generated',
                        question_count=len(questions)
                    )
                    logger.info(f"  ✓ Generated {len(questions)} questions")
                    stats['success'] += 1
                else:
                    questions_db.mark_generation_status(doc_id, 'generated', question_count=0)
                    logger.warning(f"  ⚠ No questions generated")
                    stats['skipped'] += 1
            
            stats['processed'] += 1
            
            # Save checkpoint
            checkpoint['processed_count'] = stats['processed']
            checkpoint['processed_ids'] = list(processed_ids | {doc_id})
            checkpoint['last_processed_id'] = doc_id
            checkpoint['last_processed_at'] = datetime.now().isoformat()
            checkpoint['stats'] = stats
            
            if i % 10 == 0:  # Save checkpoint every 10 docs
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint, f, indent=2)
            
            # Rate limiting
            if i < len(docs_to_process):
                await asyncio.sleep(args.delay)
        
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            stats['failed'] += 1
            stats['errors'].append({'doc_id': doc_id, 'error': str(e)})
            
            try:
                questions_db.mark_generation_status(doc_id, 'failed', error_message=str(e))
            except:
                pass
    
    # Final checkpoint save
    checkpoint['processed_count'] = stats['processed']
    checkpoint['final_stats'] = stats
    checkpoint['completed_at'] = datetime.now().isoformat()
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("BATCH REGENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Success: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    
    if stats['errors']:
        logger.info("\nErrors:")
        for error in stats['errors'][:10]:
            logger.info(f"  - {error['doc_id']}: {error['error']}")
    
    logger.info(f"\nCheckpoint saved to: {checkpoint_file}")
    
    return stats['failed'] == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
