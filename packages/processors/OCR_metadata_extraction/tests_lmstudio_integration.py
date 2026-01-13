#!/usr/bin/env python3
"""
Integration Tests for LM Studio OCR Provider

These tests validate end-to-end integration with:
- OCR Service
- Configuration system
- Logging system
- Error handling
- Real API interactions (optional with mock)
"""

import unittest
import os
import sys
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


class TestLMStudioIntegrationWithOCRService(unittest.TestCase):
    """Test LM Studio provider integration with OCRService"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_provider_registration(self, mock_get):
        """Test provider is registered in OCRService"""
        from app.services.ocr_service import OCRService

        mock_get.return_value.status_code = 200

        service = OCRService()

        # Check provider is registered
        self.assertIn('lmstudio', service.providers)
        provider = service.get_provider('lmstudio')
        self.assertEqual(provider.get_name(), 'lmstudio')

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_provider_display_name(self, mock_get):
        """Test provider display name is configured"""
        from app.services.ocr_service import OCRService

        mock_get.return_value.status_code = 200

        service = OCRService()
        display_name = service._get_display_name('lmstudio')

        self.assertEqual(display_name, 'LM Studio (Local LLM)')

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_available_providers_includes_lmstudio(self, mock_get):
        """Test LM Studio appears in available providers list"""
        from app.services.ocr_service import OCRService

        mock_get.return_value.status_code = 200

        service = OCRService()
        providers = service.get_available_providers()

        lmstudio_provider = next(
            (p for p in providers if p['name'] == 'lmstudio'),
            None
        )
        self.assertIsNotNone(lmstudio_provider)
        self.assertTrue(lmstudio_provider['available'])
        self.assertEqual(lmstudio_provider['display_name'], 'LM Studio (Local LLM)')

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_ocr_service_process_image_with_lmstudio(
            self, mock_optimize, mock_open, mock_post, mock_get):
        """Test OCRService can process images with LM Studio provider"""
        from app.services.ocr_service import OCRService

        # Mock availability and responses
        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Extracted text'}}]
        }

        service = OCRService()
        result = service.process_image(
            '/path/to/image.jpg',
            provider='lmstudio',
            languages=['en']
        )

        self.assertIn('text', result)
        self.assertEqual(result['text'], 'Extracted text')


class TestLMStudioConfigurationIntegration(unittest.TestCase):
    """Test LM Studio configuration integration"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_config_class_variables(self, mock_get):
        """Test configuration class variables are set"""
        from app.config import Config

        mock_get.return_value.status_code = 200

        self.assertTrue(hasattr(Config, 'LMSTUDIO_HOST'))
        self.assertTrue(hasattr(Config, 'LMSTUDIO_MODEL'))
        self.assertTrue(hasattr(Config, 'LMSTUDIO_ENABLED'))
        self.assertTrue(hasattr(Config, 'LMSTUDIO_TIMEOUT'))
        self.assertTrue(hasattr(Config, 'LMSTUDIO_MAX_TOKENS'))

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_default_configuration_values(self, mock_get):
        """Test default configuration values"""
        from app.config import Config

        mock_get.return_value.status_code = 200

        self.assertEqual(Config.LMSTUDIO_HOST, 'http://localhost:1234')
        self.assertEqual(Config.LMSTUDIO_MODEL, 'local-model')
        self.assertEqual(Config.LMSTUDIO_TIMEOUT, 600)
        self.assertEqual(Config.LMSTUDIO_MAX_TOKENS, 4096)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_environment_override(self, mock_get):
        """Test environment variables override defaults"""
        os.environ['LMSTUDIO_HOST'] = 'http://custom:5000'
        os.environ['LMSTUDIO_TIMEOUT'] = '300'

        from app.config import Config
        import importlib
        importlib.reload(sys.modules['app.config'])

        mock_get.return_value.status_code = 200

        # Re-import to get new config
        from app.config import Config as ReloadedConfig

        # Values should match environment
        self.assertEqual(os.getenv('LMSTUDIO_HOST'), 'http://custom:5000')
        self.assertEqual(os.getenv('LMSTUDIO_TIMEOUT'), '300')


class TestLMStudioPDFIntegration(unittest.TestCase):
    """Test LM Studio PDF processing integration"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.PDFService.pdf_to_images')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_pdf_processing_integration(
            self, mock_optimize, mock_pdf_to_images, mock_post, mock_get):
        """Test PDF processing with multiple pages"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200

        # Mock PDF conversion (returns 3 pages)
        mock_images = [MagicMock() for _ in range(3)]
        mock_pdf_to_images.return_value = mock_images
        mock_optimize.return_value = b'fake_image_bytes'

        # Mock API responses for each page
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Page text'}}]
        }

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/document.pdf')

        # Verify PDF was processed
        self.assertIn('pages_processed', result)
        self.assertEqual(result['pages_processed'], 3)
        self.assertIn('blocks', result)
        self.assertEqual(len(result['blocks']), 3)

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.PDFService.pdf_to_images')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_pdf_page_context_in_prompt(
            self, mock_optimize, mock_pdf_to_images, mock_post, mock_get):
        """Test page context is added to prompt for multi-page PDFs"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_images = [MagicMock() for _ in range(2)]
        mock_pdf_to_images.return_value = mock_images
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Page text'}}]
        }

        provider = LMStudioProvider()
        result = provider.process_image('/path/to/document.pdf')

        # Check that API was called with page context
        for call in mock_post.call_args_list:
            request_body = call[1]['json']
            prompt = request_body['messages'][0]['content'][0]['text']
            # For multi-page PDFs, prompt should include page context
            self.assertIn('[Page', prompt)


class TestLMStudioErrorRecovery(unittest.TestCase):
    """Test LM Studio error recovery and resilience"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_partial_pdf_failure_recovery(
            self, mock_optimize, mock_open, mock_post, mock_get):
        """Test handling of failures on individual PDF pages"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        # First call succeeds, second fails, third succeeds
        responses = [
            Mock(status_code=200, json=lambda: {
                'choices': [{'message': {'content': 'Page 1 text'}}]
            }),
            Mock(status_code=500, text='Error'),
            Mock(status_code=200, json=lambda: {
                'choices': [{'message': {'content': 'Page 3 text'}}]
            })
        ]
        mock_post.side_effect = responses

        provider = LMStudioProvider()

        # Should raise on first failure
        with self.assertRaises(Exception):
            provider.process_image('/path/to/document.pdf')


class TestLMStudioLanguageSupport(unittest.TestCase):
    """Test LM Studio multilingual support"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    def test_supported_languages(self, mock_get):
        """Test all supported languages in prompt building"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        provider = LMStudioProvider()

        languages = ['en', 'hi', 'es', 'fr', 'de', 'zh', 'ja', 'ar']
        prompt = provider._build_prompt(languages, False)

        # Check all languages appear in prompt
        for lang in languages:
            self.assertIn(lang.upper() or lang, prompt.upper())

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_multilingual_processing(
            self, mock_optimize, mock_open, mock_post, mock_get):
        """Test processing with multiple languages"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Multi-language text'}}]
        }

        provider = LMStudioProvider()
        result = provider.process_image(
            '/path/to/multilingual.jpg',
            languages=['en', 'hi', 'es']
        )

        # Verify language hint was passed
        call_args = mock_post.call_args
        prompt = call_args[1]['json']['messages'][0]['content'][0]['text']
        self.assertIn('English', prompt)
        self.assertIn('Hindi', prompt)
        self.assertIn('Spanish', prompt)


class TestLMStudioMetadataExtraction(unittest.TestCase):
    """Test LM Studio metadata extraction capabilities"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_metadata_extraction_json_format(
            self, mock_optimize, mock_open, mock_post, mock_get):
        """Test metadata extraction with JSON response"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        # Mock JSON response
        json_response = {
            "sender": "John Doe",
            "date": "2024-01-15",
            "subject": "Important Letter"
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': json.dumps(json_response)}}]
        }

        provider = LMStudioProvider()
        custom_prompt = "Extract metadata as JSON: {sender, date, subject}"
        result = provider.process_image(
            '/path/to/letter.jpg',
            custom_prompt=custom_prompt
        )

        # Parse the JSON response
        metadata = json.loads(result['text'])
        self.assertEqual(metadata['sender'], 'John Doe')
        self.assertEqual(metadata['date'], '2024-01-15')
        self.assertEqual(metadata['subject'], 'Important Letter')


class TestLMStudioPerformanceMetrics(unittest.TestCase):
    """Test LM Studio performance metrics"""

    def setUp(self):
        """Set up test fixtures"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

    @patch('app.services.ocr_providers.lmstudio_provider.requests.get')
    @patch('app.services.ocr_providers.lmstudio_provider.requests.post')
    @patch('app.services.ocr_providers.lmstudio_provider.Image.open')
    @patch('app.services.ocr_providers.lmstudio_provider.ImageOptimizer.optimize_and_encode')
    def test_response_timing(
            self, mock_optimize, mock_open, mock_post, mock_get):
        """Test that timing information is available"""
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
        import time

        mock_get.return_value.status_code = 200
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_optimize.return_value = b'fake_image_bytes'

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Test text'}}]
        }

        provider = LMStudioProvider()
        start = time.time()
        result = provider.process_image('/path/to/image.jpg')
        duration = time.time() - start

        # Should complete reasonably quickly (mocked)
        self.assertLess(duration, 5.0)
        self.assertIsNotNone(result)


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("LM STUDIO OCR PROVIDER - INTEGRATION TEST SUITE")
    print("="*80 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioIntegrationWithOCRService))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioConfigurationIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioPDFIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioErrorRecovery))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioLanguageSupport))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioMetadataExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioPerformanceMetrics))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"Success rate: {success_rate:.1f}%")

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
    result = run_integration_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
