from google.cloud import vision
import io
import os
from PIL import Image
from pdf2image import convert_from_path
from .base_provider import BaseOCRProvider

class GoogleVisionProvider(BaseOCRProvider):
    """Google Cloud Vision OCR Provider"""

    def __init__(self):
        """Initialize Google Cloud Vision client"""
        # Check if Google Vision is enabled
        enabled = os.getenv('GOOGLE_VISION_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.client = None
            print("Google Vision provider is disabled via GOOGLE_VISION_ENABLED environment variable")
            return

        try:
            self.client = vision.ImageAnnotatorClient()
            self._available = True
        except Exception as e:
            print(f"Google Vision initialization failed: {e}")
            self.client = None
            self._available = False

    def get_name(self):
        return "google_vision"

    def is_available(self):
        return self._available and self.client is not None

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using Google Cloud Vision API"""
        if not self.is_available():
            raise Exception("Google Vision provider is not available")

        # Note: custom_prompt is not used by Google Vision API
        if handwriting:
            return self._process_with_handwriting(image_path)
        else:
            return self._process_standard(image_path, languages)

    def _process_standard(self, image_path, languages=None):
        """Standard text detection"""
        try:
            content = None
            if image_path.lower().endswith('.pdf'):
                # For PDFs, convert the first page to an image
                images = convert_from_path(image_path, first_page=1, last_page=1)
                if images:
                    img = images[0]
                    img = img.convert('RGB')
                    byte_arr = io.BytesIO()
                    img.save(byte_arr, format='PNG')
                    content = byte_arr.getvalue()
            else:
                # Normalize other image types
                with Image.open(image_path) as img:
                    img = img.convert('RGB')
                    byte_arr = io.BytesIO()
                    img.save(byte_arr, format='PNG')
                    content = byte_arr.getvalue()

            if not content:
                raise Exception("Could not extract image content from file")

            image = vision.Image(content=content)

            # Configure image context with language hints if provided
            image_context = None
            if languages:
                image_context = vision.ImageContext(language_hints=languages)

            # Perform text detection
            if image_context:
                response = self.client.text_detection(
                    image=image,
                    image_context=image_context
                )
            else:
                response = self.client.text_detection(image=image)

            # Check for errors
            if response.error.message:
                raise Exception(f"Google Vision API error: {response.error.message}")

            texts = response.text_annotations

            if not texts:
                return {
                    'text': '',
                    'full_text': '',
                    'words': [],
                    'blocks': [],
                    'confidence': 0
                }

            # First annotation contains the entire detected text
            full_text = texts[0].description if texts else ''

            # Extract individual words
            words = []
            for text in texts[1:]:
                words.append({
                    'text': text.description,
                    'bounds': self._get_bounds(text)
                })

            # Get document text with structure
            document = self._get_document_text(response)

            return {
                'text': full_text,
                'full_text': full_text,
                'words': words,
                'blocks': document.get('blocks', []),
                'confidence': document.get('confidence', 0)
            }

        except Exception as e:
            raise Exception(f"Google Vision OCR processing failed: {str(e)}")

    def _process_with_handwriting(self, image_path):
        """Process image with handwriting detection"""
        try:
            content = None
            if image_path.lower().endswith('.pdf'):
                # For PDFs, convert the first page to an image
                images = convert_from_path(image_path, first_page=1, last_page=1)
                if images:
                    img = images[0]
                    img = img.convert('RGB')
                    byte_arr = io.BytesIO()
                    img.save(byte_arr, format='PNG')
                    content = byte_arr.getvalue()
            else:
                # Normalize other image types
                with Image.open(image_path) as img:
                    img = img.convert('RGB')
                    byte_arr = io.BytesIO()
                    img.save(byte_arr, format='PNG')
                    content = byte_arr.getvalue()

            if not content:
                raise Exception("Could not extract image content from file")

            image = vision.Image(content=content)

            # Use document text detection for better handwriting recognition
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                raise Exception(f"Google Vision API error: {response.error.message}")

            if not response.full_text_annotation:
                return {
                    'text': '',
                    'full_text': '',
                    'blocks': [],
                    'confidence': 0,
                    'words': []
                }

            full_text = response.full_text_annotation.text

            # Extract blocks with confidence
            blocks = []
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ''
                    block_confidence = 0
                    word_count = 0

                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            block_text += word_text + ' '
                            block_confidence += word.confidence
                            word_count += 1

                    if word_count > 0:
                        blocks.append({
                            'text': block_text.strip(),
                            'confidence': block_confidence / word_count
                        })

            avg_confidence = sum(b['confidence'] for b in blocks) / len(blocks) if blocks else 0

            return {
                'text': full_text,
                'full_text': full_text,
                'blocks': blocks,
                'confidence': avg_confidence,
                'words': []
            }

        except Exception as e:
            raise Exception(f"Google Vision handwriting OCR failed: {str(e)}")

    def _get_bounds(self, annotation):
        """Get bounding box coordinates"""
        vertices = annotation.bounding_poly.vertices
        return {
            'x1': vertices[0].x,
            'y1': vertices[0].y,
            'x2': vertices[2].x,
            'y2': vertices[2].y
        }

    def _get_document_text(self, response):
        """Extract structured document text"""
        if not response.full_text_annotation:
            return {'blocks': [], 'confidence': 0}

        blocks = []
        total_confidence = 0
        word_count = 0

        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                block_text = ''
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        block_text += word_text + ' '
                        total_confidence += word.confidence
                        word_count += 1

                if block_text.strip():
                    blocks.append({'text': block_text.strip()})

        avg_confidence = total_confidence / word_count if word_count > 0 else 0

        return {
            'blocks': blocks,
            'confidence': avg_confidence
        }
