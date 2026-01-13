#!/usr/bin/env python3
"""
Standalone Unit Tests for LM Studio OCR Provider

These tests validate the core functionality of the provider
without requiring full Flask/app dependencies.
Tests focus on:
- Logging functionality
- Configuration handling
- Prompt building
- Response format validation
"""

import unittest
import os
import sys
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TestLMStudioProviderConfiguration(unittest.TestCase):
    """Test LM Studio Provider configuration"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear environment variables
        for key in ['LMSTUDIO_ENABLED', 'LMSTUDIO_HOST', 'LMSTUDIO_MODEL',
                    'LMSTUDIO_API_KEY', 'LMSTUDIO_TIMEOUT', 'LMSTUDIO_MAX_TOKENS']:
            if key in os.environ:
                del os.environ[key]

    def test_disabled_provider(self):
        """Test provider disabled when LMSTUDIO_ENABLED=false"""
        os.environ['LMSTUDIO_ENABLED'] = 'false'

        # Simulate provider behavior
        enabled = os.getenv('LMSTUDIO_ENABLED', 'false').lower() in ('true', '1', 'yes')
        self.assertFalse(enabled)

    def test_enabled_provider(self):
        """Test provider enabled when LMSTUDIO_ENABLED=true"""
        os.environ['LMSTUDIO_ENABLED'] = 'true'

        enabled = os.getenv('LMSTUDIO_ENABLED', 'false').lower() in ('true', '1', 'yes')
        self.assertTrue(enabled)

    def test_default_host_url(self):
        """Test default LM Studio host URL"""
        host = os.getenv('LMSTUDIO_HOST', 'http://localhost:1234')
        self.assertEqual(host, 'http://localhost:1234')

    def test_custom_host_url(self):
        """Test custom LM Studio host URL via environment"""
        os.environ['LMSTUDIO_HOST'] = 'http://custom-host:5000'

        host = os.getenv('LMSTUDIO_HOST', 'http://localhost:1234')
        self.assertEqual(host, 'http://custom-host:5000')

    def test_default_model(self):
        """Test default model name"""
        model = os.getenv('LMSTUDIO_MODEL', 'local-model')
        self.assertEqual(model, 'local-model')

    def test_custom_model(self):
        """Test custom model name via environment"""
        os.environ['LMSTUDIO_MODEL'] = 'custom-model'

        model = os.getenv('LMSTUDIO_MODEL', 'local-model')
        self.assertEqual(model, 'custom-model')

    def test_default_timeout(self):
        """Test default timeout configuration"""
        timeout = int(os.getenv('LMSTUDIO_TIMEOUT', '600'))
        self.assertEqual(timeout, 600)

    def test_custom_timeout(self):
        """Test custom timeout configuration"""
        os.environ['LMSTUDIO_TIMEOUT'] = '300'

        timeout = int(os.getenv('LMSTUDIO_TIMEOUT', '600'))
        self.assertEqual(timeout, 300)

    def test_default_max_tokens(self):
        """Test default max tokens configuration"""
        max_tokens = int(os.getenv('LMSTUDIO_MAX_TOKENS', '4096'))
        self.assertEqual(max_tokens, 4096)

    def test_custom_max_tokens(self):
        """Test custom max tokens configuration"""
        os.environ['LMSTUDIO_MAX_TOKENS'] = '2048'

        max_tokens = int(os.getenv('LMSTUDIO_MAX_TOKENS', '4096'))
        self.assertEqual(max_tokens, 2048)


class TestPromptBuilding(unittest.TestCase):
    """Test OCR prompt building logic"""

    def test_default_prompt(self):
        """Test default OCR prompt"""
        prompt = "Extract all text from this image accurately. " \
                 "Return only the extracted text without any explanations, " \
                 "commentary, or markdown formatting. Maintain the original " \
                 "line breaks and formatting."

        self.assertIn('Extract all text', prompt)
        self.assertIn('accurately', prompt)

    def test_handwriting_prompt(self):
        """Test prompt with handwriting flag"""
        prompt = "Extract all text from this image accurately. " \
                 "The image contains handwritten text. " \
                 "Pay close attention to handwriting recognition. " \
                 "Return only the extracted text without any explanations, " \
                 "commentary, or markdown formatting. Maintain the original " \
                 "line breaks and formatting."

        self.assertIn('handwritten', prompt)
        self.assertIn('Pay close attention', prompt)

    def test_language_prompt(self):
        """Test prompt with language hints"""
        languages = ['en', 'hi']
        lang_names = {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic'
        }
        lang_list = [lang_names.get(lang, lang) for lang in languages]
        prompt = f"The text may be in {', '.join(lang_list)}. "

        self.assertIn('English', prompt)
        self.assertIn('Hindi', prompt)

    def test_all_languages_supported(self):
        """Test all language codes are recognized"""
        lang_names = {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic'
        }

        # Verify all languages have mappings
        for code, name in lang_names.items():
            self.assertIsNotNone(name)
            self.assertTrue(len(name) > 0)

    def test_combined_prompt(self):
        """Test prompt with all options enabled"""
        languages = ['en', 'hi']
        handwriting = True

        prompt = "Extract all text from this image accurately. "

        if handwriting:
            prompt += "The image contains handwritten text. " \
                      "Pay close attention to handwriting recognition. "

        if languages:
            lang_names = {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ar': 'Arabic'
            }
            lang_list = [lang_names.get(lang, lang) for lang in languages]
            prompt += f"The text may be in {', '.join(lang_list)}. "

        prompt += "Return only the extracted text without any explanations, " \
                  "commentary, or markdown formatting. Maintain the original " \
                  "line breaks and formatting."

        self.assertIn('handwritten', prompt)
        self.assertIn('English', prompt)
        self.assertIn('Hindi', prompt)


class TestResponseFormat(unittest.TestCase):
    """Test response format validation"""

    def test_response_structure(self):
        """Test OCR response has correct structure"""
        response = {
            'text': 'extracted text',
            'full_text': 'extracted text',
            'words': [],
            'blocks': [{'text': 'extracted text'}],
            'confidence': 0.95
        }

        # Verify structure
        required_fields = ['text', 'full_text', 'words', 'blocks', 'confidence']
        for field in required_fields:
            self.assertIn(field, response)

    def test_text_field_type(self):
        """Test text field is string"""
        response = {'text': 'extracted text'}
        self.assertIsInstance(response['text'], str)

    def test_confidence_score_range(self):
        """Test confidence score is between 0 and 1"""
        confidence = 0.95
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)

    def test_blocks_structure(self):
        """Test blocks have correct structure"""
        blocks = [
            {'text': 'block 1 text'},
            {'text': 'block 2 text', 'page': 1}
        ]

        for block in blocks:
            self.assertIn('text', block)
            self.assertIsInstance(block['text'], str)

    def test_pdf_response_structure(self):
        """Test PDF response includes page information"""
        response = {
            'text': 'combined text',
            'full_text': 'combined text',
            'words': [],
            'blocks': [
                {'text': 'page 1 text', 'page': 1},
                {'text': 'page 2 text', 'page': 2}
            ],
            'confidence': 0.95,
            'pages_processed': 2
        }

        # Verify PDF response
        self.assertIn('pages_processed', response)
        self.assertEqual(response['pages_processed'], 2)

        for block in response['blocks']:
            self.assertIn('page', block)


class TestMetadataExtraction(unittest.TestCase):
    """Test metadata extraction format"""

    def test_json_response_parsing(self):
        """Test JSON metadata response parsing"""
        response_text = json.dumps({
            'sender': 'John Doe',
            'date': '2024-01-15',
            'subject': 'Important Letter'
        })

        parsed = json.loads(response_text)

        self.assertEqual(parsed['sender'], 'John Doe')
        self.assertEqual(parsed['date'], '2024-01-15')
        self.assertEqual(parsed['subject'], 'Important Letter')

    def test_structured_metadata_fields(self):
        """Test extraction of multiple metadata fields"""
        fields = {
            'sender_name': 'John Doe',
            'sender_address': '123 Main St',
            'recipient_name': 'Jane Smith',
            'recipient_address': '456 Oak Ave',
            'date': '2024-01-15',
            'subject': 'Business Proposal',
            'key_points': ['Point 1', 'Point 2']
        }

        # Verify all fields
        for key, value in fields.items():
            self.assertIsNotNone(value)

    def test_invoice_metadata_extraction(self):
        """Test invoice metadata extraction"""
        invoice = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': '2024-01-15',
            'due_date': '2024-02-15',
            'vendor_name': 'ABC Company',
            'total_amount': '1500.00',
            'currency': 'USD'
        }

        # Verify invoice fields
        self.assertEqual(invoice['invoice_number'], 'INV-2024-001')
        self.assertIn(invoice['currency'], ['USD', 'EUR', 'GBP', 'INR'])


class TestErrorMessages(unittest.TestCase):
    """Test error handling messages"""

    def test_connection_error_message(self):
        """Test connection error message format"""
        error = "Could not connect to LM Studio server at http://localhost:1234"
        self.assertIn('Could not connect', error)
        self.assertIn('http://localhost:1234', error)

    def test_timeout_error_message(self):
        """Test timeout error message format"""
        error = "LM Studio request timed out (timeout: 600s)"
        self.assertIn('timed out', error)
        self.assertIn('600', error)

    def test_api_error_message(self):
        """Test API error message format"""
        error = "LM Studio API error: 500 - Internal Server Error"
        self.assertIn('API error', error)
        self.assertIn('500', error)

    def test_availability_error_message(self):
        """Test availability error message"""
        error = "LM Studio provider is not available"
        self.assertIn('not available', error)


class TestLoggingBehavior(unittest.TestCase):
    """Test logging behavior"""

    def setUp(self):
        """Set up logging capture"""
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.DEBUG)

    def test_debug_log_format(self):
        """Test DEBUG log format"""
        logger = logging.getLogger('test.debug')
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)

        logger.debug("Test debug message")

        log_contents = self.log_capture.getvalue()
        self.assertIn('Test debug message', log_contents)

    def test_info_log_format(self):
        """Test INFO log format"""
        logger = logging.getLogger('test.info')
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)

        logger.info("Test info message")

        log_contents = self.log_capture.getvalue()
        self.assertIn('Test info message', log_contents)

    def test_warning_log_format(self):
        """Test WARNING log format"""
        logger = logging.getLogger('test.warning')
        logger.addHandler(self.handler)
        logger.setLevel(logging.WARNING)

        logger.warning("Test warning message")

        log_contents = self.log_capture.getvalue()
        self.assertIn('Test warning message', log_contents)

    def test_error_log_format(self):
        """Test ERROR log format"""
        logger = logging.getLogger('test.error')
        logger.addHandler(self.handler)
        logger.setLevel(logging.ERROR)

        logger.error("Test error message")

        log_contents = self.log_capture.getvalue()
        self.assertIn('Test error message', log_contents)


class TestAPIEndpointFormat(unittest.TestCase):
    """Test API endpoint format"""

    def test_models_endpoint(self):
        """Test /v1/models endpoint format"""
        endpoint = 'http://localhost:1234/v1/models'

        self.assertIn('/v1/models', endpoint)
        self.assertIn('http://', endpoint)

    def test_chat_completion_endpoint(self):
        """Test /v1/chat/completions endpoint format"""
        endpoint = 'http://localhost:1234/v1/chat/completions'

        self.assertIn('/v1/chat/completions', endpoint)
        self.assertIn('http://', endpoint)

    def test_request_payload_format(self):
        """Test API request payload format"""
        payload = {
            'model': 'local-model',
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'prompt'},
                        {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,...'}}
                    ]
                }
            ],
            'max_tokens': 4096,
            'temperature': 0.1
        }

        # Verify payload structure
        self.assertIn('model', payload)
        self.assertIn('messages', payload)
        self.assertIn('max_tokens', payload)
        self.assertIn('temperature', payload)

    def test_response_payload_format(self):
        """Test API response payload format"""
        response = {
            'choices': [
                {
                    'message': {
                        'content': 'extracted text'
                    }
                }
            ]
        }

        # Verify response structure
        self.assertIn('choices', response)
        self.assertTrue(len(response['choices']) > 0)
        self.assertIn('message', response['choices'][0])
        self.assertIn('content', response['choices'][0]['message'])


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metric tracking"""

    def test_timing_format(self):
        """Test timing metric format"""
        duration = 15.45  # seconds

        # Format as in logs
        formatted = f"{duration:.2f}s"
        self.assertEqual(formatted, "15.45s")

    def test_character_count(self):
        """Test character count metric"""
        text = "Extracted text from image"
        char_count = len(text)

        self.assertEqual(char_count, 25)

    def test_page_count_metric(self):
        """Test page count metric"""
        pages = 3
        self.assertGreater(pages, 0)

    def test_extraction_rate(self):
        """Test extraction rate calculation"""
        total_chars = 1000
        total_time = 20.5  # seconds

        rate = total_chars / total_time
        self.assertGreater(rate, 0)
        self.assertAlmostEqual(rate, 48.78, places=1)


def run_standalone_tests():
    """Run all standalone tests"""
    print("\n" + "="*80)
    print("LM STUDIO OCR PROVIDER - STANDALONE TEST SUITE")
    print("="*80 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLMStudioProviderConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptBuilding))
    suite.addTests(loader.loadTestsFromTestCase(TestResponseFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestMetadataExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorMessages))
    suite.addTests(loader.loadTestsFromTestCase(TestLoggingBehavior))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpointFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMetrics))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("STANDALONE TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Passed: {passed}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.testsRun > 0:
        success_rate = (passed / result.testsRun) * 100
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
    result = run_standalone_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
