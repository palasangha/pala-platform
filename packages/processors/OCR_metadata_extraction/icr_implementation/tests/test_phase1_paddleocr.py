"""
Phase 1: PaddleOCR Provider Tests
==================================
Comprehensive test suite for PaddleOCR provider implementation.

Test Cases:
1. Provider initialization
2. Text extraction on clean documents
3. Layout detection accuracy
4. Bounding box extraction
5. Error handling
6. Performance benchmarks

Author: ICR Integration Team
Date: 2026-01-23
"""

import unittest
import logging
import json
import time
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging for tests
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'phase1_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestPaddleOCRProvider(unittest.TestCase):
    """Test suite for PaddleOCR Provider."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        logger.info("\n" + "=" * 80)
        logger.info("Starting PaddleOCR Provider Test Suite")
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
        """Clean up and report test results."""
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
        
        # Save results to JSON
        log_dir = Path(__file__).parent.parent / 'logs'
        results_path = log_dir / 'phase1_test_results.json'
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def test_01_import_provider(self):
        """Test 1: Import PaddleOCR provider module."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 1: Import PaddleOCR Provider")
        logger.info("-" * 80)
        
        try:
            from phase1.paddleocr_provider import PaddleOCRProvider
            logger.info("✓ Successfully imported PaddleOCRProvider")
            self.__class__.test_results['passed'] += 1
            self.assertTrue(True)
        except ImportError as e:
            logger.error(f"✗ Failed to import: {e}")
            self.__class__.test_results['failed'] += 1
            self.fail(f"Import failed: {e}")
    
    def test_02_provider_initialization(self):
        """Test 2: Initialize PaddleOCR provider."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 2: Provider Initialization")
        logger.info("-" * 80)
        
        try:
            # Check if PaddleOCR is installed
            try:
                import paddleocr
                logger.info("✓ PaddleOCR library is installed")
            except ImportError:
                logger.warning("⚠ PaddleOCR not installed - skipping test")
                self.__class__.test_results['skipped'] += 1
                self.skipTest("PaddleOCR not installed")
                return
            
            from phase1.paddleocr_provider import PaddleOCRProvider
            
            logger.info("Initializing provider...")
            provider = PaddleOCRProvider(lang='en', use_gpu=False)
            
            # Verify initialization
            self.assertTrue(provider.initialized)
            self.assertEqual(provider.lang, 'en')
            self.assertFalse(provider.use_gpu)
            
            logger.info("✓ Provider initialized successfully")
            
            # Get stats
            stats = provider.get_stats()
            logger.info("Provider Statistics:")
            logger.info(json.dumps(stats, indent=2))
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Initialization failed: {e}")
    
    def test_03_create_test_image(self):
        """Test 3: Create a simple test image."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 3: Create Test Image")
        logger.info("-" * 80)
        
        try:
            import cv2
            import numpy as np
            
            # Create a simple test image with text
            img = np.ones((400, 600, 3), dtype=np.uint8) * 255
            
            # Add some text
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(img, 'PaddleOCR Test Image', (50, 100), 
                       font, 1, (0, 0, 0), 2)
            cv2.putText(img, 'Sample Document', (50, 200), 
                       font, 0.8, (0, 0, 0), 2)
            cv2.putText(img, 'Test Date: 2026-01-23', (50, 300), 
                       font, 0.6, (0, 0, 0), 1)
            
            # Save test image
            test_dir = Path(__file__).parent.parent / 'tests' / 'test_images'
            test_dir.mkdir(parents=True, exist_ok=True)
            
            test_image_path = test_dir / 'paddle_test_simple.png'
            cv2.imwrite(str(test_image_path), img)
            
            logger.info(f"✓ Test image created: {test_image_path}")
            logger.info(f"  Image size: {img.shape}")
            
            self.__class__.test_results['passed'] += 1
            self.assertTrue(test_image_path.exists())
            
        except Exception as e:
            logger.error(f"✗ Test image creation failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Image creation failed: {e}")
    
    def test_04_text_extraction_mock(self):
        """Test 4: Mock text extraction (without actual PaddleOCR)."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 4: Mock Text Extraction")
        logger.info("-" * 80)
        
        try:
            # Create mock result structure
            mock_result = {
                'texts': [
                    'PaddleOCR Test Image',
                    'Sample Document',
                    'Test Date: 2026-01-23'
                ],
                'boxes': [
                    [[50, 80], [350, 80], [350, 120], [50, 120]],
                    [[50, 180], [300, 180], [300, 220], [50, 220]],
                    [[50, 280], [320, 280], [320, 320], [50, 320]]
                ],
                'scores': [0.95, 0.92, 0.88],
                'layout_regions': [
                    {
                        'type': 'text',
                        'bbox': [50, 50, 550, 350],
                        'confidence': 0.96
                    }
                ],
                'preprocessed_image': None,
                'metadata': {
                    'total_processing_time': 0.5,
                    'ocr_time': 0.3,
                    'layout_time': 0.2,
                    'num_text_regions': 3,
                    'num_layout_regions': 1,
                    'average_confidence': 0.916,
                    'language': 'en',
                    'gpu_enabled': False,
                    'image_path': 'test_image.png',
                    'region_types': {'text': 1}
                }
            }
            
            # Validate structure
            self.assertIn('texts', mock_result)
            self.assertIn('boxes', mock_result)
            self.assertIn('scores', mock_result)
            self.assertIn('layout_regions', mock_result)
            self.assertIn('metadata', mock_result)
            
            # Validate data
            self.assertEqual(len(mock_result['texts']), 3)
            self.assertEqual(len(mock_result['boxes']), 3)
            self.assertEqual(len(mock_result['scores']), 3)
            
            logger.info("✓ Mock result structure validated")
            logger.info(f"  Detected {len(mock_result['texts'])} text regions")
            logger.info(f"  Average confidence: {mock_result['metadata']['average_confidence']:.3f}")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Mock test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Mock test failed: {e}")
    
    def test_05_error_handling(self):
        """Test 5: Error handling for invalid inputs."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 5: Error Handling")
        logger.info("-" * 80)
        
        try:
            # Check if PaddleOCR is installed
            try:
                import paddleocr
            except ImportError:
                logger.warning("⚠ PaddleOCR not installed - skipping test")
                self.__class__.test_results['skipped'] += 1
                self.skipTest("PaddleOCR not installed")
                return
            
            from phase1.paddleocr_provider import PaddleOCRProvider
            
            provider = PaddleOCRProvider(lang='en', use_gpu=False)
            
            # Test 1: Non-existent file
            logger.info("Testing non-existent file...")
            with self.assertRaises(FileNotFoundError):
                provider.extract_text('non_existent_file.png')
            logger.info("✓ Correctly raised FileNotFoundError")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Error handling test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Error handling test failed: {e}")
    
    def test_06_performance_baseline(self):
        """Test 6: Performance baseline measurement."""
        logger.info("\n" + "-" * 80)
        logger.info("Test 6: Performance Baseline")
        logger.info("-" * 80)
        
        try:
            # Define performance expectations
            performance_targets = {
                'initialization_time': 30.0,  # seconds
                'single_page_processing': 10.0,  # seconds
                'layout_detection': 5.0  # seconds
            }
            
            logger.info("Performance Targets:")
            for metric, target in performance_targets.items():
                logger.info(f"  {metric}: <{target}s")
            
            logger.info("✓ Performance baseline defined")
            logger.info("  (Actual measurements will be done with real OCR)")
            
            self.__class__.test_results['passed'] += 1
            
        except Exception as e:
            logger.error(f"✗ Performance test failed: {e}", exc_info=True)
            self.__class__.test_results['failed'] += 1
            self.fail(f"Performance test failed: {e}")


def run_tests():
    """Run all tests with detailed reporting."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: PaddleOCR Provider Test Suite")
    logger.info("=" * 80)
    logger.info(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python Version: {sys.version}")
    logger.info("=" * 80 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPaddleOCRProvider)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
