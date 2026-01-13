import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import time
from .base_provider import BaseOCRProvider

class AzureComputerVisionProvider(BaseOCRProvider):
    """Azure Computer Vision OCR Provider"""

    def __init__(self, endpoint=None, key=None):
        """
        Initialize Azure Computer Vision provider

        Args:
            endpoint: Azure Computer Vision endpoint
            key: Azure Computer Vision subscription key
        """
        # Check if Azure is enabled
        enabled = os.getenv('AZURE_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.client = None
            self.endpoint = None
            self.key = None
            print("Azure Computer Vision provider is disabled via AZURE_ENABLED environment variable")
            return

        self.endpoint = endpoint or os.getenv('AZURE_VISION_ENDPOINT')
        self.key = key or os.getenv('AZURE_VISION_KEY')

        try:
            if self.endpoint and self.key:
                credentials = CognitiveServicesCredentials(self.key)
                self.client = ComputerVisionClient(self.endpoint, credentials)
                self._available = True
            else:
                self.client = None
                self._available = False
        except Exception as e:
            print(f"Azure Computer Vision initialization failed: {e}")
            self.client = None
            self._available = False

    def get_name(self):
        return "azure"

    def is_available(self):
        return self._available and self.client is not None

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using Azure Computer Vision API"""
        if not self.is_available():
            raise Exception("Azure Computer Vision provider is not available")

        # Note: custom_prompt is not used by Azure Computer Vision API
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()

            # Map language codes to Azure supported languages
            language = self._map_language(languages)

            # Call Read API (supports both print and handwriting)
            read_response = self.client.read_in_stream(
                image_data,
                language=language,
                raw=True
            )

            # Get the operation ID from the response
            operation_location = read_response.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]

            # Poll for the result
            max_attempts = 30
            attempt = 0
            while attempt < max_attempts:
                read_result = self.client.get_read_result(operation_id)

                if read_result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                    break

                time.sleep(1)
                attempt += 1

            if read_result.status == OperationStatusCodes.failed:
                raise Exception("Azure OCR processing failed")

            # Extract text from results
            full_text = []
            blocks = []

            if read_result.analyze_result:
                for page in read_result.analyze_result.read_results:
                    for line in page.lines:
                        full_text.append(line.text)
                        blocks.append({
                            'text': line.text,
                            'confidence': getattr(line, 'confidence', 0.95)
                        })

            extracted_text = '\n'.join(full_text)

            # Calculate average confidence
            avg_confidence = sum(b.get('confidence', 0.95) for b in blocks) / len(blocks) if blocks else 0

            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': blocks,
                'confidence': avg_confidence
            }

        except Exception as e:
            raise Exception(f"Azure Computer Vision OCR processing failed: {str(e)}")

    def _map_language(self, languages):
        """Map language codes to Azure supported format"""
        if not languages:
            return 'en'

        # Azure uses two-letter language codes
        # Take the first language if multiple are provided
        lang = languages[0] if languages else 'en'

        # Azure supports: en, es, fr, de, it, nl, pt, zh-Hans, zh-Hant, ja, ko, ar, etc.
        return lang
