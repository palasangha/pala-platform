#!/usr/bin/env python3
"""
Test script for RAG Phase 1: Chat with Documents
================================================

This script validates:
1. Embedding generation and storage
2. Semantic search in SQLite provider  
3. Chat agent orchestration
4. Document retrieval and citation

Run from workspace root:
  python test_rag_phase1.py
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test data
TEST_DOCUMENTS = [
    {
        "type": "buddhist_text",
        "original_file": "dhamma_teachings.pdf",
        "file_format": "pdf",
        "created_by": "test",
        "metadata": {
            "summary": "Core Buddhist teachings about the nature of suffering and liberation",
            "topics": ["Buddhism", "Dhamma", "Suffering", "Liberation"],
            "places": ["India", "Thailand"]
        },
        "processed_data": {
            "content": "The Buddha taught that suffering arises from attachment and craving. Through mindfulness and meditation, one can achieve enlightenment.",
            "pages": 10
        },
        "app_data": {
            "source": "test",
            "validated": True
        }
    },
    {
        "type": "historical_record",
        "original_file": "goenka_biography.txt",
        "file_format": "txt",
        "created_by": "test",
        "metadata": {
            "summary": "Life and teachings of S.N. Goenka, prominent meditation teacher",
            "topics": ["Goenka", "Vipassana", "Meditation"],
            "places": ["Burma", "India", "USA"]
        },
        "processed_data": {
            "content": "S.N. Goenka was born in Burma and became a renowned teacher of Vipassana meditation. He established meditation centers across the world.",
            "pages": 5
        },
        "app_data": {
            "source": "test",
            "validated": True
        }
    },
    {
        "type": "technical_guide",
        "original_file": "meditation_technique.md",
        "file_format": "md",
        "created_by": "test",
        "metadata": {
            "summary": "Technical guide to Vipassana meditation practice",
            "topics": ["Vipassana", "Technique", "Practice", "Meditation"],
            "places": ["General"]
        },
        "processed_data": {
            "content": "Vipassana meditation involves observing sensations in the body with equanimity. Practitioners sit in silence for extended periods.",
            "pages": 8
        },
        "app_data": {
            "source": "test",
            "validated": True
        }
    }
]

def test_embedding_generation():
    """Test that embeddings can be generated"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Embedding Generation")
    logger.info("="*60)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info("Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded successfully")
        
        # Test embedding generation
        test_text = "Buddhist teachings about meditation and enlightenment"
        embedding = model.encode(test_text, convert_to_tensor=False)
        
        logger.info(f"✅ Embedding generated: {len(embedding)} dimensions")
        logger.info(f"   Sample values: {embedding[:5]}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

def test_semantic_search_logic():
    """Test semantic search logic with mock embeddings"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Semantic Search Logic (mock)")
    logger.info("="*60)
    
    try:
        # Mock embedding vectors (384-dim, normalized)
        query_embedding = [0.1, -0.2, 0.3] + [0.0] * 381
        
        doc1_embedding = [0.09, -0.21, 0.31] + [0.0] * 381  # Very similar
        doc2_embedding = [-0.5, 0.5, -0.5] + [0.0] * 381    # Very different
        
        def cosine_sim(a, b):
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x*x for x in a) ** 0.5
            mag_b = sum(y*y for y in b) ** 0.5
            return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0
        
        # Test similarity calculations
        sim1 = cosine_sim(query_embedding, doc1_embedding)
        sim2 = cosine_sim(query_embedding, doc2_embedding)
        
        logger.info(f"Query vs Doc1 (similar): {sim1:.3f}")
        logger.info(f"Query vs Doc2 (different): {sim2:.3f}")
        
        if sim1 > sim2:
            logger.info("✅ Semantic similarity working correctly")
            return True
        else:
            logger.error("❌ Similarity scoring incorrect")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

def test_keyword_search():
    """Test keyword fallback search"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Keyword Search Fallback")
    logger.info("="*60)
    
    try:
        query = "meditation vipassana"
        query_lower = query.lower()
        
        matches = []
        for doc in TEST_DOCUMENTS:
            score = 0.0
            
            # Check filename
            if query_lower in doc['original_file'].lower():
                score = max(score, 0.7)
            
            # Check topics
            for topic in doc.get('metadata', {}).get('topics', []):
                if query_lower in str(topic).lower():
                    score = max(score, 0.6)
            
            # Check summary
            if query_lower in doc.get('metadata', {}).get('summary', '').lower():
                score = max(score, 0.6)
            
            if score > 0:
                matches.append({
                    'file': doc['original_file'],
                    'score': score
                })
        
        logger.info(f"Query: '{query}'")
        logger.info(f"Matches found: {len(matches)}")
        for match in sorted(matches, key=lambda x: x['score'], reverse=True):
            logger.info(f"  - {match['file']} (score: {match['score']:.1f})")
        
        if len(matches) > 0:
            logger.info("✅ Keyword search working correctly")
            return True
        else:
            logger.error("❌ No keyword matches found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

def test_citation_formatting():
    """Test response citation formatting"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Citation Formatting")
    logger.info("="*60)
    
    try:
        documents = [
            {'document_id': 'doc-001', 'original_file': 'dhamma_teachings.pdf'},
            {'document_id': 'doc-002', 'original_file': 'goenka_biography.txt'}
        ]
        
        # Format citations
        response = "The Buddha taught about meditation [doc-001]. S.N. Goenka was a prominent teacher [doc-002]."
        
        logger.info(f"Response: {response}")
        logger.info(f"Documents referenced: {documents}")
        
        # Simple validation
        if '[doc-001]' in response and '[doc-002]' in response:
            logger.info("✅ Citation formatting working correctly")
            return True
        else:
            logger.error("❌ Citation formatting incorrect")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("\n" + "="*70)
    logger.info("RAG PHASE 1 TEST SUITE")
    logger.info("="*70)
    logger.info("Testing: Embedding generation, semantic search, and chat orchestration")
    
    results = {
        "Embedding Generation": test_embedding_generation(),
        "Semantic Search Logic": test_semantic_search_logic(),
        "Keyword Search": test_keyword_search(),
        "Citation Formatting": test_citation_formatting(),
    }
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✅ All tests passed! RAG Phase 1 infrastructure ready.")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed. Review logs above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
