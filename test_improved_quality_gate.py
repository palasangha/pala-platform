#!/usr/bin/env python3
"""
Test script to regenerate questions with improved quality gate (0.75 threshold + duplicate detection)
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
    logger.info("=" * 100)
    logger.info("TEST: Regenerate Questions with Improved Quality Gate (0.75 threshold + duplicate detection)")
    logger.info("=" * 100)
    
    # Import required modules
    try:
        from provider_factory import get_provider
        from question_generator import QuestionGenerator
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
        
        # Ollama provider (using SimpleOllamaProvider from main.py logic)
        import os
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'mistral')
        
        # Create a simple ollama provider that has the necessary methods
        class SimpleOllamaProvider:
            def __init__(self, base_url, model):
                self.base_url = base_url
                self.model = model
            
            def is_available(self):
                try:
                    import requests
                    resp = requests.get(f'{self.base_url}/api/tags', timeout=2)
                    return resp.status_code == 200
                except:
                    return False
            
            async def generate_text(self, prompt, **kwargs):
                import requests
                resp = requests.post(
                    f'{self.base_url}/api/generate',
                    json={'model': self.model, 'prompt': prompt, 'stream': False},
                    timeout=60
                )
                return resp.json().get('response', '')
        
        ollama_provider = SimpleOllamaProvider(base_url=base_url, model=model)
        if not ollama_provider.is_available():
            logger.error("❌ Ollama provider not available - cannot regenerate")
            return False
        logger.info("✓ Ollama provider available")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        return False
    
    # Fetch and regenerate for first document
    try:
        logger.info("\nFetching documents...")
        all_docs = await storage_provider.list_documents()
        
        if isinstance(all_docs, dict):
            documents = all_docs.get('documents', [])
        else:
            documents = all_docs
        
        if not documents:
            logger.warning("No documents to process")
            return True
        
        first_doc = documents[0]
        doc_id = first_doc.get('id') if isinstance(first_doc, dict) else getattr(first_doc, 'id', None)
        
        logger.info(f"\n{'='*100}")
        logger.info(f"Regenerating questions for: {doc_id}")
        logger.info(f"{'='*100}")
        
        # Retrieve full document
        doc = await storage_provider.retrieve_document(doc_id)
        if not doc:
            logger.error(f"Failed to retrieve document {doc_id}")
            return False
        
        logger.info(f"✓ Document retrieved: {doc.original_file}")
        logger.info(f"  Type: {doc.type}")
        logger.info(f"  File format: {doc.file_format}")
        
        # Generate questions with improved quality gate
        try:
            logger.info("\n" + "="*100)
            logger.info("GENERATING QUESTIONS WITH IMPROVED QUALITY GATE (0.75 threshold + duplicate detection)")
            logger.info("="*100)
            
            gen = QuestionGenerator(ollama_provider)
            questions = await gen.generate_questions_for_document(
                doc_id=doc.id,
                doc_type=doc.type,
                metadata=doc.metadata,
                processed_data=doc.processed_data,
                original_file=doc.original_file,
                embedding_model=embedding_model,
                verify_with_llm=True
            )
            
            if questions:
                logger.info(f"\n{'='*100}")
                logger.info(f"✓ Generated {len(questions)} high-quality questions (filtered from many candidates)")
                logger.info(f"{'='*100}")
                
                # Display generated questions
                for i, q in enumerate(questions, 1):
                    ev = q.get('evidence', [])
                    conf = float(ev[0].get('confidence', 0.0)) if ev else 0.0
                    snippet = ev[0].get('snippet', '').split('\n')[0] if ev else ''
                    
                    logger.info(f"\nQ{i}. {q.get('text', 'N/A')[:80]}")
                    logger.info(f"    Confidence: {conf:.2f}")
                    logger.info(f"    Snippet preview: {snippet[:100]}")
                
                # Persist to document
                logger.info(f"\n{'='*100}")
                logger.info("PERSISTING QUESTIONS TO DOCUMENT METADATA")
                logger.info(f"{'='*100}")
                
                # Build questions payload
                questions_payload = {
                    'questions': questions,
                    'questions_generation_status': 'generated',
                    'question_count': len(questions),
                    'generation_timestamp': str(__import__('datetime').datetime.now(timezone.utc).isoformat()),
                    'generation_model': 'ollama',
                    'confidence_floor': 0.75,
                    'quality_method': 'threshold-0.75 + duplicate-detection'
                }
                
                # Update document metadata
                app_patch = {'questions_payload': questions_payload}
                await storage_provider.update_document_metadata(
                    doc_id=doc_id,
                    app_data_patch=app_patch
                )
                logger.info(f"✓ Questions persisted to document metadata")
                
                # Verify persistence
                updated_doc = await storage_provider.retrieve_document(doc_id)
                updated_payload = getattr(updated_doc, 'app_data', {}).get('questions_payload', {})
                stored_count = len(updated_payload.get('questions', []))
                logger.info(f"✓ Verification: {stored_count} questions stored in metadata")
                
                return True
            else:
                logger.warning("No questions generated")
                return False
        
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            return False
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    from datetime import timezone
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
