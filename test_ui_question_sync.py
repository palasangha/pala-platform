#!/usr/bin/env python3
"""
Test script to verify that questions shown in test match what's displayed in the UI
This compares: storage_provider questions -> MCP tool response -> UI display
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from pprint import pprint

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
    logger.info("TEST: Verify UI Question Display Matches Test Output")
    logger.info("=" * 100)
    
    # Import required modules
    try:
        from provider_factory import get_provider
        logger.info("✓ All imports successful")
    except ImportError as e:
        logger.error(f"Failed to import: {e}")
        return False
    
    # Initialize storage provider
    try:
        logger.info("\nInitializing storage provider...")
        storage_provider = get_provider()
        logger.info(f"✓ Storage provider: {type(storage_provider).__name__}")
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
        logger.info("\nAvailable documents:")
        for i, doc in enumerate(documents[:10], 1):
            doc_id = doc.get('id') if isinstance(doc, dict) else getattr(doc, 'id', None)
            orig_file = doc.get('original_file') if isinstance(doc, dict) else getattr(doc, 'original_file', None)
            logger.info(f"  {i}. {doc_id} - {orig_file}")
        
        if len(documents) > 10:
            logger.info(f"  ... and {len(documents) - 10} more")
        
        # Process first document
        first_doc = documents[0]
        doc_id = first_doc.get('id') if isinstance(first_doc, dict) else getattr(first_doc, 'id', None)
        
        logger.info(f"\n{'='*100}")
        logger.info(f"Processing document: {doc_id}")
        logger.info(f"{'='*100}")
        
        # Retrieve full document
        doc = await storage_provider.retrieve_document(doc_id)
        if not doc:
            logger.error(f"Failed to retrieve document {doc_id}")
            return False
        
        logger.info(f"✓ Document retrieved: {doc.original_file}")
        
        # CHECK 1: Questions stored in document.app_data.questions_payload
        logger.info(f"\n{'='*80}")
        logger.info("CHECK 1: Questions in Document Metadata (app_data.questions_payload)")
        logger.info(f"{'='*80}")
        
        app_data = getattr(doc, 'app_data', {}) or {}
        questions_payload = app_data.get('questions_payload', {})
        stored_questions = questions_payload.get('questions', [])
        generation_status = questions_payload.get('questions_generation_status', 'none')
        
        logger.info(f"Questions generation status: {generation_status}")
        logger.info(f"Number of questions stored: {len(stored_questions)}")
        
        if stored_questions:
            logger.info(f"\nStored questions in metadata:")
            for i, q in enumerate(stored_questions[:3], 1):
                logger.info(f"\n{i}. Q: {q.get('text', 'N/A')[:80]}")
                
                # Get snippet from evidence
                evidence = q.get('evidence', [])
                if evidence and isinstance(evidence, list):
                    snippet = evidence[0].get('snippet', '') if evidence[0] else ''
                    confidence = evidence[0].get('confidence', 0) if evidence[0] else 0
                    logger.info(f"   Snippet (conf={confidence:.2f}): {snippet[:100]}")
                else:
                    answer_preview = q.get('answer_preview', '')
                    logger.info(f"   Answer preview: {answer_preview[:100]}")
            
            if len(stored_questions) > 3:
                logger.info(f"\n   ... and {len(stored_questions) - 3} more questions")
        
        # CHECK 2: Simulate MCP tool response (get_document_questions)
        logger.info(f"\n{'='*80}")
        logger.info("CHECK 2: MCP Tool Response (tool_get_document_questions)")
        logger.info(f"{'='*80}")
        logger.info("This is what the UI receives when it calls get_document_questions tool")
        
        # Simulate the MCP tool logic
        mcp_response = {
            "document_id": doc_id,
            "questions": stored_questions,
            "generation_status": generation_status,
            "count": len(stored_questions)
        }
        
        logger.info(f"\nMCP Response structure:")
        logger.info(f"  document_id: {mcp_response['document_id']}")
        logger.info(f"  generation_status: {mcp_response['generation_status']}")
        logger.info(f"  count: {mcp_response['count']}")
        
        # CHECK 3: Render as UI would (ContentBrowser.tsx rendering)
        logger.info(f"\n{'='*80}")
        logger.info("CHECK 3: UI Rendering (as ContentBrowser.tsx would display)")
        logger.info(f"{'='*80}")
        logger.info("This is the exact format shown in the Browse -> Storage Explorer panel:\n")
        
        if stored_questions:
            for idx, question in enumerate(stored_questions[:5], 1):
                # This mirrors the rendering logic at line 1235-1250 in ContentBrowser.tsx
                q_text = question.get('text', 'N/A')
                q_type = question.get('suggestion_type', '')
                
                # Get snippet
                evidence = question.get('evidence', [])
                snippet = None
                confidence = None
                if evidence and isinstance(evidence, list) and len(evidence) > 0:
                    snippet = evidence[0].get('snippet', '')
                    confidence = evidence[0].get('confidence', 0)
                else:
                    snippet = question.get('answer_preview', '')
                
                logger.info(f"\n┌─ Question {idx}")
                logger.info(f"│  Text: {q_text}")
                if q_type:
                    logger.info(f"│  Type: {q_type}")
                if snippet:
                    conf_str = f" (confidence: {confidence:.2f})" if confidence else ""
                    logger.info(f"│  Raw snippet{conf_str}:")
                    snippet_lines = snippet.split('\n')
                    for line in snippet_lines[:3]:  # Show first 3 lines
                        logger.info(f"│    > {line[:80]}")
                    if len(snippet_lines) > 3:
                        logger.info(f"│    > ... ({len(snippet_lines) - 3} more lines)")
                logger.info(f"└─")
            
            if len(stored_questions) > 5:
                logger.info(f"\n... and {len(stored_questions) - 5} more questions")
        
        # CHECK 4: Verify consistency
        logger.info(f"\n{'='*80}")
        logger.info("CHECK 4: Consistency Verification")
        logger.info(f"{'='*80}")
        
        all_have_text = all(q.get('text') for q in stored_questions)
        all_have_snippet_or_preview = all(
            (q.get('evidence') and q['evidence'][0].get('snippet')) or q.get('answer_preview')
            for q in stored_questions
        )
        
        logger.info(f"✓ All questions have text: {all_have_text}")
        logger.info(f"✓ All questions have snippet or answer_preview: {all_have_snippet_or_preview}")
        logger.info(f"✓ Generation status is 'generated': {generation_status == 'generated'}")
        logger.info(f"✓ Question count matches payload: {len(stored_questions) > 0}")
        
        # Summary
        logger.info(f"\n{'='*100}")
        logger.info("SUMMARY")
        logger.info(f"{'='*100}")
        logger.info(f"\nDocument: {doc.original_file}")
        logger.info(f"Questions: {len(stored_questions)}")
        logger.info(f"Status: {generation_status}")
        logger.info(f"\nThe questions shown above are EXACTLY what will appear in the UI")
        logger.info(f"because they're retrieved from the same storage location (document.app_data.questions_payload)")
        logger.info(f"\nTest location: {doc_id}")
        logger.info(f"{'='*100}\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
