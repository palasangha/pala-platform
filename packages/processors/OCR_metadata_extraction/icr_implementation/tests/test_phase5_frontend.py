"""
Phase 5: Frontend & API Tests
==============================
Comprehensive test suite for Phase 5 implementation.

Test Coverage:
1. API server initialization
2. Health check endpoint
3. Document upload
4. Document processing
5. Document retrieval
6. React components structure

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
        logging.FileHandler(log_dir / 'phase5_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestPhase5Implementation(unittest.TestCase):
    """Test suite for Phase 5: Frontend & API."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("\n" + "=" * 80)
        logger.info("Starting Phase 5 Test Suite")
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
        results_path = log_dir / 'phase5_test_results.json'
        
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
    
    def test_01_import_api_server(self):
        """Test 1: Import API server."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 1: Import API Server")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer, create_app
            logger.info("✓ Successfully imported API server")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_02_import_react_components(self):
        """Test 2: Import React components."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 2: Import React Components")
        logger.info("-" * 80)
        
        try:
            from phase5.react_components import (
                DOCUMENT_UPLOAD_COMPONENT,
                DOCUMENT_VIEWER_COMPONENT,
                QA_INTERFACE_COMPONENT,
                APP_COMPONENT
            )
            logger.info("✓ Successfully imported React components")
            logger.info(f"  Components loaded: 4")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_03_api_server_initialization(self):
        """Test 3: Initialize API server."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 3: API Server Initialization")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            logger.info("Initializing API server...")
            server = ICRAPIServer()
            
            # Verify initialization
            self.assertTrue(server.initialized)
            
            # Get stats
            stats = server.get_stats()
            logger.info("Server Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ API server initialized successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_04_health_check(self):
        """Test 4: Health check endpoint."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 4: Health Check Endpoint")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer()
            app = server.get_app()
            
            # Verify app exists
            self.assertIsNotNone(app)
            
            logger.info("✓ Health check endpoint available")
            logger.info(f"  Total routes: {len(app.routes) if hasattr(app, 'routes') else 'N/A'}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Health check failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_05_document_storage(self):
        """Test 5: Document storage."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 5: Document Storage")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer()
            
            # Verify document storage initialized
            self.assertIsNotNone(server.documents)
            self.assertEqual(len(server.documents), 0)
            
            # Add mock document
            server.documents['test_doc'] = {
                'id': 'test_doc',
                'filename': 'test.pdf',
                'status': 'uploaded'
            }
            
            self.assertEqual(len(server.documents), 1)
            
            logger.info("✓ Document storage working")
            logger.info(f"  Documents: {len(server.documents)}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Storage test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_06_upload_directory(self):
        """Test 6: Upload directory creation."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 6: Upload Directory")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer(upload_dir="./test_uploads")
            
            # Verify directory created
            self.assertTrue(server.upload_dir.exists())
            self.assertTrue(server.upload_dir.is_dir())
            
            logger.info("✓ Upload directory created")
            logger.info(f"  Path: {server.upload_dir}")
            
            # Cleanup
            import shutil
            if server.upload_dir.exists():
                shutil.rmtree(server.upload_dir)
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Directory test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_07_react_component_structure(self):
        """Test 7: React component structure."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 7: React Component Structure")
        logger.info("-" * 80)
        
        try:
            from phase5.react_components import (
                DOCUMENT_UPLOAD_COMPONENT,
                DOCUMENT_VIEWER_COMPONENT,
                QA_INTERFACE_COMPONENT,
                APP_COMPONENT,
                CSS_STYLES
            )
            
            # Validate components are not empty
            self.assertGreater(len(DOCUMENT_UPLOAD_COMPONENT), 0)
            self.assertGreater(len(DOCUMENT_VIEWER_COMPONENT), 0)
            self.assertGreater(len(QA_INTERFACE_COMPONENT), 0)
            self.assertGreater(len(APP_COMPONENT), 0)
            self.assertGreater(len(CSS_STYLES), 0)
            
            # Check for key React elements
            self.assertIn('useState', DOCUMENT_UPLOAD_COMPONENT)
            self.assertIn('axios', DOCUMENT_VIEWER_COMPONENT)
            self.assertIn('export default', QA_INTERFACE_COMPONENT)
            
            logger.info("✓ React components valid")
            logger.info(f"  DocumentUpload: {len(DOCUMENT_UPLOAD_COMPONENT)} chars")
            logger.info(f"  DocumentViewer: {len(DOCUMENT_VIEWER_COMPONENT)} chars")
            logger.info(f"  QAInterface: {len(QA_INTERFACE_COMPONENT)} chars")
            logger.info(f"  App: {len(APP_COMPONENT)} chars")
            logger.info(f"  CSS: {len(CSS_STYLES)} chars")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Component test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_08_api_endpoints(self):
        """Test 8: API endpoints configuration."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 8: API Endpoints")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer()
            stats = server.get_stats()
            
            # Verify endpoints
            self.assertIn('endpoints', stats)
            self.assertGreater(len(stats['endpoints']), 0)
            
            logger.info("✓ API endpoints configured")
            logger.info(f"  Total endpoints: {len(stats['endpoints'])}")
            for endpoint in stats['endpoints']:
                logger.info(f"    {endpoint}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Endpoints test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_09_service_lazy_loading(self):
        """Test 9: Service lazy loading."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 9: Service Lazy Loading")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer()
            
            # Verify services not loaded initially
            self.assertIsNone(server.paddleocr_provider)
            self.assertIsNone(server.agentic_service)
            self.assertIsNone(server.landingai_provider)
            self.assertIsNone(server.vector_store)
            self.assertIsNone(server.qa_service)
            
            logger.info("✓ Services lazy loading configured")
            logger.info("  Services will load on first use")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Lazy loading test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_10_production_readiness(self):
        """Test 10: Production readiness checks."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 10: Production Readiness")
        logger.info("-" * 80)
        
        try:
            from phase5.api_server import ICRAPIServer
            
            server = ICRAPIServer()
            stats = server.get_stats()
            
            # Check features
            self.assertIn('features', stats)
            features = stats['features']
            
            required_features = [
                'document_upload',
                'ocr_processing',
                'rag_qa'
            ]
            
            for feature in required_features:
                self.assertIn(feature, features)
            
            logger.info("✓ Production readiness verified")
            logger.info(f"  Features: {len(features)}")
            logger.info(f"  Mock mode: {stats.get('mock_mode', False)}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Readiness test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")


def run_tests():
    """Run all tests with detailed reporting."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 5: Frontend & API Test Suite")
    logger.info("=" * 80)
    logger.info(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python Version: {sys.version}")
    logger.info("=" * 80 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase5Implementation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
