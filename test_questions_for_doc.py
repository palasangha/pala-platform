#!/usr/bin/env python3
"""
Test script to generate and display questions for existing documents
"""

import asyncio
import sys
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths
agent_dir = Path(__file__).parent / 'packages' / 'PalaAgents' / 'storage-agent'
sys.path.insert(0, str(agent_dir))


async def main():
    logger.info("=" * 80)
    logger.info("TEST: Generate Questions for Existing Documents")
    logger.info("=" * 80)
    
    # Import required modules
    try:
        from provider_factory import get_provider
        from questions_db import QuestionsDB
        from question_generator import QuestionGenerator
        from providers.ollama_provider import OllamaMetadataProvider
        from sentence_transformers import SentenceTransformer
        logger.info("✓ All imports successful")
    except ImportError as e:
        logger.error(f"Failed to import: {e}")
        return False
    
    # Initialize components
    try:
        logger.info("\nInitializing components...")
        
        # Storage provider
        storage_provider = get_provider()
        logger.info(f"✓ Storage provider: {type(storage_provider).__name__}")
        
        # Embedding model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✓ Embedding model loaded: all-MiniLM-L6-v2")
        
        # Ollama provider
        ollama_provider = OllamaMetadataProvider()
        if not ollama_provider.is_available():
            logger.warning("⚠ Ollama provider not available - skipping generation")
            logger.info("   To generate questions, ensure Ollama is running: docker-compose up ollama")
            return True  # Don't fail, just skip
        logger.info("✓ Ollama provider available")
        
        # Questions database
        db_path = agent_dir / 'data' / 'questions_metadata.db'
        questions_db = QuestionsDB(str(db_path))
        logger.info(f"✓ Questions DB: {db_path}")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        return False
    
    # List documents
    try:
        logger.info("\nFetching documents...")
        all_docs = await storage_provider.list_documents()
        
        if isinstance(all_docs, dict):
            documents = all_docs.get('documents', [])
        else:
            documents = all_docs
        
        logger.info(f"✓ Found {len(documents)} documents")
        
        if not documents:
            logger.warning("No documents to process")
            return True
        
        # Show document list
        logger.info("\nDocuments in database:")
        for i, doc in enumerate(documents[:5], 1):
            doc_id = doc.get('id') if isinstance(doc, dict) else getattr(doc, 'id', None)
            doc_type = doc.get('type') if isinstance(doc, dict) else getattr(doc, 'type', None)
            orig_file = doc.get('original_file') if isinstance(doc, dict) else getattr(doc, 'original_file', None)
            logger.info(f"  {i}. {doc_id}")
            logger.info(f"     Type: {doc_type}, File: {orig_file}")
        
        if len(documents) > 5:
            logger.info(f"  ... and {len(documents) - 5} more")
        
        # Process first document with questions
        first_doc = documents[0]
        doc_id = first_doc.get('id') if isinstance(first_doc, dict) else getattr(first_doc, 'id', None)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Generating questions for: {doc_id}")
        logger.info(f"{'='*80}")
        
        # Retrieve full document
        doc = await storage_provider.retrieve_document(doc_id)
        if not doc:
            logger.error(f"Failed to retrieve document {doc_id}")
            return False
        
        logger.info(f"✓ Document retrieved")
        logger.info(f"  Type: {doc.type}")
        logger.info(f"  Original file: {doc.original_file}")
        logger.info(f"  File format: {doc.file_format}")
        
        # Generate questions
        try:
            logger.info("\nGenerating questions...")
            questions_db.mark_generation_status(doc_id, 'generating')
            
            gen = QuestionGenerator(ollama_provider)
            questions = await gen.generate_questions_for_document(
                doc_id=doc.id,
                doc_type=doc.type,
                metadata=doc.metadata,
                processed_data=doc.processed_data,
                original_file=doc.original_file,
                embedding_model=embedding_model
            )
            
            if questions:
                logger.info(f"✓ Generated {len(questions)} questions")
                
                # Store questions
                questions_db.store_questions_batch(questions)
                questions_db.mark_generation_status(
                    doc_id, 'generated',
                    question_count=len(questions)
                )
                logger.info(f"✓ Stored questions in database")
                
                # Display questions
                logger.info(f"\n{'='*80}")
                logger.info(f"Generated Questions for: {doc.original_file}")
                logger.info(f"{'='*80}")
                
                for i, q in enumerate(questions, 1):
                    logger.info(f"\n{i}. {q.get('text', 'N/A')[:100]}")
                    logger.info(f"   Type: {q.get('suggestion_type', 'N/A')}")
                    logger.info(f"   Embedding dims: {len(q.get('embedding', []))}")
                
                # Now search for a test query
                logger.info(f"\n{'='*80}")
                logger.info(f"Test: Search for similar questions")
                logger.info(f"{'='*80}")
                
                test_query = "What is the main teaching?"
                logger.info(f"\nQuery: '{test_query}'")
                
                query_embedding = embedding_model.encode(test_query).tolist()
                results = questions_db.search_questions_by_embedding(query_embedding, top_k=3, similarity_threshold=0.3)
                
                logger.info(f"✓ Found {len(results)} similar questions:")
                for i, result in enumerate(results, 1):
                    logger.info(f"\n{i}. {result['text'][:80]}")
                    logger.info(f"   Similarity: {result['similarity']:.3f}")
                    logger.info(f"   Document: {result['provenance']}")
                
            else:
                logger.warning("No questions generated")
        
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            questions_db.mark_generation_status(doc_id, 'failed', error_message=str(e))
            return False
        
        logger.info(f"\n{'='*80}")
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info(f"{'='*80}")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
