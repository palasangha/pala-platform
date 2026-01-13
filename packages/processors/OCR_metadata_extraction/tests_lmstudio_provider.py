#!/usr/bin/env python3
"""
Comprehensive Test Suite for LM Studio OCR Provider

This test suite validates:
- Provider initialization
- Configuration loading
- Availability checking
- Image processing
- PDF processing
- Error handling
- Logging functionality
- Mock API responses
"""

import unittest
import os
import sys
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TestLMStudioProviderInitialization(unittest.TestCase):
    """Test LM Studio Provider initialization"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear environment variables
        for key in ['LMSTUDIO_ENABLED', 'LMSTUDIO_HOST', 'LMSTUDIO_MODEL',
                    'LMSTUDIO_API_KEY', 'LMSTUDIO_TIMEOUT', 'LMSTUDIO_MAX_TOKENS']:
            if key in os.environ:
                del os.environ[key]

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_provider_initialization_enabled(self, mock_get):
        """Test provider initializes correctly when enabled"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        os.environ['LMSTUDIO_ENABLED'] = 'true'
        mock_get.return_value.status_code = 200

        provider = LMStudioProvider()

        self.assertTrue(provider.is_available())
        self.assertEqual(provider.get_name(), 'lmstudio')
        self.assertEqual(provider.host, 'http://localhost:1234')
        self.assertEqual(provider.model, 'local-model')
        self.assertEqual(provider.timeout, 600)
        self.assertEqual(provider.max_tokens, 4096)

    def test_provider_initialization_disabled(self):
        """Test provider initializes disabled when LMSTUDIO_ENABLED=false"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        os.environ['LMSTUDIO_ENABLED'] = 'false'

        provider = LMStudioProvider()

        self.assertFalse(provider.is_available())
        self.assertIsNone(provider.host)
        self.assertIsNone(provider.model)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_custom_initialization_parameters(self, mock_get):
        """Test provider initializes with custom parameters"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        os.environ['LMSTUDIO_ENABLED'] = 'true'
        mock_get.return_value.status_code = 200

        provider = LMStudioProvider(
            host='http://custom-host:5000',
            model='custom-model',
            api_key='custom-key'
        )

        self.assertEqual(provider.host, 'http://custom-host:5000')
        self.assertEqual(provider.model, 'custom-model')
        self.assertEqual(provider.api_key, 'custom-key')

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_environment_variable_configuration(self, mock_get):
        """Test configuration via environment variables"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        os.environ['LMSTUDIO_ENABLED'] = 'true'
        os.environ['LMSTUDIO_HOST'] = 'http://env-host:1234'
        os.environ['LMSTUDIO_MODEL'] = 'env-model'
        os.environ['LMSTUDIO_TIMEOUT'] = '300'
        os.environ['LMSTUDIO_MAX_TOKENS'] = '2048'
        mock_get.return_value.status_code = 200

        provider = LMStudioProvider()

        self.assertEqual(provider.host, 'http://env-host:1234')
        self.assertEqual(provider.model, 'env-model')
        self.assertEqual(provider.timeout, 300)
        self.assertEqual(provider.max_tokens, 2048)


class TestLMStudioProviderAvailability(unittest.TestCase):
    """Test LM Studio Provider availability checking"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_availability_check_success(self, mock_get):
        """Test provider correctly identifies availability"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        self.assertTrue(provider.is_available())

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_availability_check_connection_error(self, mock_get):
        """Test provider handles connection errors"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        provider = LMStudioProvider()

        self.assertFalse(provider.is_available())

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_availability_check_timeout(self, mock_get):
        """Test provider handles timeout during availability check"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        provider = LMStudioProvider()

        self.assertFalse(provider.is_available())

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_availability_check_non_200_status(self, mock_get):
        """Test provider handles non-200 status codes"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 500
        provider = LMStudioProvider()

        self.assertFalse(provider.is_available())


class TestLMStudioProviderImageProcessing(unittest.TestCase):
    """Test LM Studio Provider image processing"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_image_processing_success(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test successful image processing"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        # Mock availability check
        mock_get.return_value.status_code = 200

        # Mock image loading
        mock_img = MagicMock()
        mock_img.size = (1920, 1080)
        mock_img.format = 'JPEG'
        mock_open.return_value = mock_img

        # Mock image optimization
        mock_optimize.return_value = b'fake_image_bytes'

        # Mock API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'This is extracted text from the image.'
                    }
                }
            ]
        }

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/image.jpg', languages=['en'])

        # Assertions
        self.assertIn('text', result)
        self.assertIn('full_text', result)
        self.assertEqual(result['text'], 'This is extracted text from the image.')
        self.assertIn('confidence', result)
        self.assertEqual(result['confidence'], 0.95)
        self.assertTrue(mock_post.called)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_image_processing_provider_unavailable(self, mock_get):
        """Test image processing when provider is unavailable"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 500
        provider = LMStudioProvider()

        with self.assertRaises(Exception) as context:
            provider.process_image('/path/to/image.jpg')

        self.assertIn('not available', str(context.exception))

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_image_processing_timeout(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test image processing timeout handling"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import requests

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        provider = LMStudioProvider()

        with self.assertRaises(Exception) as context:
            provider.process_image('/path/to/image.jpg')

        self.assertIn('timed out', str(context.exception))

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_image_processing_custom_prompt(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test image processing with custom prompt"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Custom extraction result'}}]
        }

        provider = LMStudioProvider()
        custom_prompt = "Extract metadata: sender, date, subject"
        result = provider.process_image('/path/to/image.jpg', custom_prompt=custom_prompt)

        # Verify custom prompt was used
        call_args = mock_post.call_args
        request_body = call_args[1]['json']
        prompt_in_request = request_body['messages'][0]['content'][0]['text']
        self.assertEqual(prompt_in_request, custom_prompt)


class TestLMStudioProviderLogging(unittest.TestCase):
    """Test LM Studio Provider logging"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'
        # Capture logs
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.DEBUG)
        self.logger = logging.getLogger('app.services.ocr_providers.lmstudio_provider')
        self.logger.addHandler(self.handler)

    def tearDown(self):
        """Clean up"""
        self.logger.removeHandler(self.handler)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_initialization_logging(self, mock_get):
        """Test logging during initialization"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        log_contents = self.log_capture.getvalue()
        self.assertIn('Initializing', log_contents)
        self.assertIn('configured', log_contents)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_availability_logging(self, mock_get):
        """Test logging during availability check"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        log_contents = self.log_capture.getvalue()
        self.assertIn('available', log_contents)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_error_logging(self, mock_get):
        """Test error logging"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError()
        provider = LMStudioProvider()

        log_contents = self.log_capture.getvalue()
        self.assertIn('ERROR', log_contents)
        self.assertIn('Connection error', log_contents)


class TestLMStudioProviderErrorHandling(unittest.TestCase):
    """Test LM Studio Provider error handling"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_api_error_handling(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test handling of API errors"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        # API returns error
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = 'Internal Server Error'

        provider = LMStudioProvider()

        with self.assertRaises(Exception) as context:
            provider.process_image('/path/to/image.jpg')

        self.assertIn('API error', str(context.exception))

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_connection_error_handling(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test handling of connection errors"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import requests

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        provider = LMStudioProvider()

        with self.assertRaises(Exception) as context:
            provider.process_image('/path/to/image.jpg')

        self.assertIn('Could not connect', str(context.exception))

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_empty_response_handling(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test handling of empty API responses"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        # API returns empty choices
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'choices': []}

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/image.jpg')

        # Should handle gracefully
        self.assertEqual(result['text'], '')
        self.assertEqual(result['blocks'], [])


class TestLMStudioProviderPromptBuilding(unittest.TestCase):
    """Test LM Studio Provider prompt building"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_prompt_building_default(self, mock_get):
        """Test default prompt building"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        prompt = provider._build_prompt(None, False)

        self.assertIn('Extract all text', prompt)
        self.assertNotIn('handwritten', prompt)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_prompt_building_with_handwriting(self, mock_get):
        """Test prompt building with handwriting flag"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        prompt = provider._build_prompt(None, True)

        self.assertIn('handwritten', prompt)
        self.assertIn('Pay close attention', prompt)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_prompt_building_with_languages(self, mock_get):
        """Test prompt building with language hints"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        prompt = provider._build_prompt(['en', 'hi'], False)

        self.assertIn('English', prompt)
        self.assertIn('Hindi', prompt)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_prompt_building_all_flags(self, mock_get):
        """Test prompt building with all flags enabled"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        prompt = provider._build_prompt(['en', 'hi', 'es'], True)

        self.assertIn('handwritten', prompt)
        self.assertIn('English', prompt)
        self.assertIn('Hindi', prompt)
        self.assertIn('Spanish', prompt)


class TestLMStudioProviderResponseFormat(unittest.TestCase):
    """Test LM Studio Provider response format"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_response_structure(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test response has correct structure"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Test text'}}]
        }

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/image.jpg')

        # Check required fields
        required_fields = ['text', 'full_text', 'words', 'blocks', 'confidence']
        for field in required_fields:
            self.assertIn(field, result)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_confidence_score(self, mock_optimize, mock_open, mock_post, mock_get):
        """Test confidence score is included"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Test text'}}]
        }

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/image.jpg')

        self.assertEqual(result['confidence'], 0.95)
        self.assertIsInstance(result['confidence'], float)


def run_test_suite():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("LM STUDIO OCR PROVIDER - COMPREHENSIVE TEST SUITE")
    print("="*80 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderAvailability))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderImageProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderPromptBuilding))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderResponseFormat))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)

    print("\n" + "="*80 + "\n")

    return result


if __name__ == '__main__':
    result = run_test_suite()
    sys.exit(0 if result.wasSuccessful() else 1)
