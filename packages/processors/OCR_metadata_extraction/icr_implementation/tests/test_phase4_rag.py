"""
Phase 4: RAG Pipeline Tests
============================
Comprehensive test suite for Phase 4 implementation.

Test Coverage:
1. Vector store service
2. Document indexing
3. Semantic search
4. RAG QA service
5. Question answering
6. Citations

Author: ICR Integration Team
Date: 2026-01-23
"""

import unittest
import logging
import json
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'phase4_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestPhase4Implementation(unittest.TestCase):
    """Test suite for Phase 4: RAG Pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("\n" + "=" * 80)
        logger.info("Starting Phase 4 Test Suite")
        logger.info("=" * 80)
        
        cls.test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
    
    @classmethod
    def tearDownClass(cls):
        """Clean up and report results."""
        duration = time.time() - cls.test_results['start_time']
        
        logger.info("\n" + "=" * 80)
        logger.info("Test Suite Summary")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {cls.test_results['total_tests']}")
        logger.info(f"Passed: {cls.test_results['passed']}")
        logger.info(f"Failed: {cls.test_results['failed']}")
        logger.info(f"Skipped: {cls.test_results['skipped']}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)
        
        # Save results
        log_dir = Path(__file__).parent.parent / 'logs'
        results_path = log_dir / 'phase4_test_results.json'
        
        with open(results_path, 'w') as f:
            json.dump(cls.test_results, f, indent=2)
        
        logger.info(f"Results saved to: {results_path}")
    
    def setUp(self):
        """Set up each test."""
        self.__class__.test_results['total_tests'] += 1
        self.test_start = time.time()
    
    def tearDown(self):
        """Clean up after each test."""
        duration = time.time() - self.test_start
        logger.info(f"Test duration: {duration:.3f}s\n")
    
    def test_01_import_vector_store(self):
        """Test 1: Import vector store service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 1: Import Vector Store Service")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            logger.info("✓ Successfully imported VectorStoreService")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_02_import_rag_qa(self):
        """Test 2: Import RAG QA service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 2: Import RAG QA Service")
        logger.info("-" * 80)
        
        try:
            from phase4.rag_qa_service import RAGQAService
            logger.info("✓ Successfully imported RAGQAService")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_03_vector_store_initialization(self):
        """Test 3: Initialize vector store."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 3: Vector Store Initialization")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            
            logger.info("Initializing vector store...")
            vs = VectorStoreService(collection_name="test_collection")
            
            # Verify initialization
            self.assertTrue(vs.initialized)
            
            # Get stats
            stats = vs.get_stats()
            logger.info("Vector Store Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ Vector store initialized successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_04_mock_document_indexing(self):
        """Test 4: Mock document indexing."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 4: Mock Document Indexing")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            
            vs = VectorStoreService()
            
            # Index a document
            doc_markdown = """# Test Document

This is a test document for indexing.

## Section 1
Content for section 1.

## Section 2
Content for section 2."""
            
            logger.info("Indexing document...")
            result = vs.index_document(
                document_id="test_doc_1",
                markdown=doc_markdown
            )
            
            # Validate result
            self.assertIn('num_chunks', result)
            self.assertGreater(result['num_chunks'], 0)
            
            logger.info("✓ Document indexed successfully")
            logger.info(f"  Chunks: {result['num_chunks']}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Indexing test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_05_mock_semantic_search(self):
        """Test 5: Mock semantic search."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 5: Mock Semantic Search")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            
            vs = VectorStoreService()
            
            # Search
            query = "What is this document about?"
            logger.info(f"Searching for: {query}")
            
            results = vs.search(query=query, n_results=3)
            
            # Validate results
            self.assertIn('chunks', results)
            self.assertIn('scores', results)
            
            logger.info("✓ Search successful")
            logger.info(f"  Results: {len(results['chunks'])}")
            if results['scores']:
                logger.info(f"  Top score: {results['scores'][0]:.4f}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Search test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_06_rag_qa_initialization(self):
        """Test 6: Initialize RAG QA service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 6: RAG QA Service Initialization")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            from phase4.rag_qa_service import RAGQAService
            
            vs = VectorStoreService()
            logger.info("Initializing RAG QA service...")
            
            qa = RAGQAService(vs, llm_provider='openai')
            
            # Verify initialization
            self.assertTrue(qa.initialized)
            
            # Get stats
            stats = qa.get_stats()
            logger.info("RAG QA Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ RAG QA initialized successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_07_mock_question_answering(self):
        """Test 7: Mock question answering."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 7: Mock Question Answering")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            from phase4.rag_qa_service import RAGQAService
            
            vs = VectorStoreService()
            qa = RAGQAService(vs)
            
            # Ask a question
            question = "What is the main topic of the document?"
            logger.info(f"Question: {question}")
            
            result = qa.answer_question(question, n_context_chunks=3)
            
            # Validate result
            self.assertIn('answer', result)
            self.assertIn('confidence', result)
            self.assertIn('sources', result)
            
            logger.info("✓ Question answered successfully")
            logger.info(f"  Answer length: {len(result['answer'])} chars")
            logger.info(f"  Confidence: {result['confidence']:.2f}")
            logger.info(f"  Sources: {len(result['sources'])}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ QA test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_08_citation_generation(self):
        """Test 8: Citation generation."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 8: Citation Generation")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            from phase4.rag_qa_service import RAGQAService
            
            vs = VectorStoreService()
            qa = RAGQAService(vs)
            
            # Ask question with citations
            result = qa.answer_question(
                "Test question",
                include_citations=True
            )
            
            # Validate citations
            self.assertIn('citations', result)
            
            logger.info("✓ Citations generated")
            logger.info(f"  Citations: {len(result['citations'])}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Citation test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_09_error_handling(self):
        """Test 9: Error handling."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 9: Error Handling")
        logger.info("-" * 80)
        
        try:
            from phase4.vector_store_service import VectorStoreService
            
            vs = VectorStoreService()
            
            # Test document retrieval for non-existent doc
            logger.info("Testing with non-existent document...")
            result = vs.get_document("nonexistent_doc_12345")
            
            # Should return None or empty, not crash
            logger.info("✓ Handled non-existent document gracefully")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Error handling test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_10_performance_baseline(self):
        """Test 10: Performance baseline."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 10: Performance Baseline")
        logger.info("-" * 80)
        
        try:
            # Define performance targets
            performance_targets = {
                'embedding_time': 0.1,  # seconds per document
                'search_time': 0.1,  # seconds
                'qa_time': 5.0,  # seconds (with LLM)
                'indexing_throughput': 50  # docs/second
            }
            
            logger.info("Performance Targets:")
            for metric, target in performance_targets.items():
                if 'throughput' in metric:
                    logger.info(f"  {metric}: >{target} docs/s")
                else:
                    logger.info(f"  {metric}: <{target}s")
            
            logger.info("✓ Performance baseline defined")
            logger.info("  (Actual measurements require full integration)")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Performance test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")


def run_tests():
    """Run all tests with detailed reporting."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4: RAG Pipeline Test Suite")
    logger.info("=" * 80)
    logger.info(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python Version: {sys.version}")
    logger.info("=" * 80 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase4Implementation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
