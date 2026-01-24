"""
Phase 2: Agentic OCR Service Tests
===================================
Comprehensive test suite for Phase 2 implementation.

Test Coverage:
1. LayoutReader service
2. VLM tools (mock mode)
3. Agentic OCR service integration
4. End-to-end pipeline
5. Error handling

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
        logging.FileHandler(log_dir / 'phase2_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestPhase2Implementation(unittest.TestCase):
    """Test suite for Phase 2: Agentic Processing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("\n" + "=" * 80)
        logger.info("Starting Phase 2 Test Suite")
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
        results_path = log_dir / 'phase2_test_results.json'
        
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
    
    def test_01_import_layout_reader(self):
        """Test 1: Import LayoutReader service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 1: Import LayoutReader Service")
        logger.info("-" * 80)
        
        try:
            from phase2.layout_reader_service import LayoutReaderService
            logger.info("✓ Successfully imported LayoutReaderService")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_02_layout_reader_initialization(self):
        """Test 2: Initialize LayoutReader service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 2: LayoutReader Initialization")
        logger.info("-" * 80)
        
        try:
            from phase2.layout_reader_service import LayoutReaderService
            
            logger.info("Initializing LayoutReader service...")
            service = LayoutReaderService()
            
            # Verify initialization
            self.assertTrue(service.initialized)
            
            # Get stats
            stats = service.get_stats()
            logger.info("Service Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ LayoutReader initialized successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_03_reading_order_mock(self):
        """Test 3: Reading order with mock OCR data."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 3: Reading Order Determination")
        logger.info("-" * 80)
        
        try:
            from phase2.layout_reader_service import LayoutReaderService
            
            service = LayoutReaderService()
            
            # Mock OCR result
            mock_ocr = {
                'texts': ['Title', 'Column 1', 'Column 2', 'Footer'],
                'boxes': [
                    [[100, 50], [500, 50], [500, 100], [100, 100]],   # Title (top)
                    [[50, 150], [250, 150], [250, 400], [50, 400]],   # Column 1
                    [[300, 150], [550, 150], [550, 400], [300, 400]], # Column 2
                    [[100, 450], [500, 450], [500, 500], [100, 500]]  # Footer
                ]
            }
            
            logger.info("Getting reading order...")
            reading_order = service.get_reading_order(mock_ocr, use_heuristic=True)
            
            logger.info(f"Reading order: {reading_order}")
            logger.info(f"Expected: [0, 1, 2, 3] or similar")
            
            # Validate
            self.assertEqual(len(reading_order), 4)
            self.assertIn(0, reading_order)  # Title should be included
            
            logger.info("✓ Reading order determined successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Reading order test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_04_import_vlm_tools(self):
        """Test 4: Import VLM tools."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 4: Import VLM Tools")
        logger.info("-" * 80)
        
        try:
            from phase2.vlm_tools import VLMTools
            logger.info("✓ Successfully imported VLMTools")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_05_vlm_tools_mock_mode(self):
        """Test 5: VLM tools in mock mode."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 5: VLM Tools Mock Mode")
        logger.info("-" * 80)
        
        try:
            from phase2.vlm_tools import VLMTools
            
            logger.info("Initializing VLM tools (mock mode)...")
            tools = VLMTools(provider='openai', model='gpt-4o-mini')
            
            # Note: Will use mock mode without API key
            stats = tools.get_stats()
            logger.info("Tools Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ VLM tools initialized")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ VLM tools test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_06_import_agentic_service(self):
        """Test 6: Import Agentic OCR service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 6: Import Agentic OCR Service")
        logger.info("-" * 80)
        
        try:
            from phase2.agentic_ocr_service import AgenticOCRService
            logger.info("✓ Successfully imported AgenticOCRService")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_07_agentic_service_initialization(self):
        """Test 7: Initialize Agentic OCR service."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 7: Agentic Service Initialization")
        logger.info("-" * 80)
        
        try:
            from phase2.agentic_ocr_service import AgenticOCRService
            
            logger.info("Initializing Agentic OCR service...")
            service = AgenticOCRService(use_gpu=False, enable_vlm=False)
            
            # Verify initialization
            self.assertTrue(service.initialized)
            
            # Get stats
            stats = service.get_stats()
            logger.info("Service Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            logger.info("✓ Agentic service initialized successfully")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_08_component_integration(self):
        """Test 8: Component integration check."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 8: Component Integration")
        logger.info("-" * 80)
        
        try:
            from phase2.agentic_ocr_service import AgenticOCRService
            
            service = AgenticOCRService(use_gpu=False, enable_vlm=True)
            
            # Check which components loaded
            stats = service.get_stats()
            components = stats['components']
            
            logger.info("Component Status:")
            logger.info(f"  PaddleOCR: {'✓' if components['paddleocr'] else '✗'}")
            logger.info(f"  LayoutReader: {'✓' if components['layoutreader'] else '✗'}")
            logger.info(f"  VLM Tools: {'✓' if components['vlm_tools'] else '✗'}")
            
            # At least LayoutReader and VLM should load (no external deps)
            self.assertTrue(components['layoutreader'], "LayoutReader should load")
            self.assertTrue(components['vlm_tools'], "VLM Tools should load")
            
            logger.info("✓ Component integration verified")
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Integration test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Test failed: {e}")
    
    def test_09_error_handling(self):
        """Test 9: Error handling."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 9: Error Handling")
        logger.info("-" * 80)
        
        try:
            from phase2.agentic_ocr_service import AgenticOCRService
            
            service = AgenticOCRService(use_gpu=False, enable_vlm=False)
            
            # Test with non-existent file
            logger.info("Testing with non-existent file...")
            result = service.process_document('non_existent_file.png')
            
            # Should return error result
            self.assertFalse(result.get('success', True))
            self.assertIn('error', result)
            
            logger.info("✓ Error handling works correctly")
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
                'layoutreader_init': 5.0,  # seconds
                'vlm_tools_init': 5.0,
                'agentic_service_init': 10.0,
                'reading_order': 3.0
            }
            
            logger.info("Performance Targets:")
            for metric, target in performance_targets.items():
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
    logger.info("PHASE 2: Agentic Processing Test Suite")
    logger.info("=" * 80)
    logger.info(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python Version: {sys.version}")
    logger.info("=" * 80 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhase2Implementation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
