import os
from .base_provider import BaseOCRProvider

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

class EasyOCRProvider(BaseOCRProvider):
    """EasyOCR Provider"""

    def __init__(self):
        """Initialize EasyOCR provider"""
        # Check if EasyOCR is enabled
        enabled = os.getenv('EASYOCR_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.reader = None
            print("EasyOCR provider is disabled via EASYOCR_ENABLED environment variable")
            return

        if not EASYOCR_AVAILABLE:
            self._available = False
            self.reader = None
            print("EasyOCR not available: easyocr package not installed")
            return

        try:
            # Initialize with default languages (English)
            # Will be reinitialized with specific languages when processing
            self.reader = None
            self._available = True
            self._current_languages = []
            self.use_gpu = os.getenv('EASYOCR_GPU', 'True').lower() == 'true'
            print("EasyOCR initialized successfully")
        except Exception as e:
            print(f"EasyOCR initialization failed: {e}")
            self._available = False
            self.reader = None

    def get_name(self):
        return "easyocr"

    def is_available(self):
        return self._available and EASYOCR_AVAILABLE

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using EasyOCR"""
        if not self.is_available():
            raise Exception("EasyOCR provider is not available")

        # Note: custom_prompt is not used by EasyOCR
        try:
            # Map language codes to EasyOCR format
            easyocr_langs = self._map_languages(languages)

            # Initialize or reinitialize reader if languages changed
            if self.reader is None or set(easyocr_langs) != set(self._current_languages):
                print(f"Initializing EasyOCR with languages: {easyocr_langs}")
                self.reader = easyocr.Reader(
                    easyocr_langs,
                    gpu=self.use_gpu,
                    verbose=False
                )
                self._current_languages = easyocr_langs

            # Process image
            # paragraph=True combines text into paragraphs
            results = self.reader.readtext(
                image_path,
                detail=1,  # Return coordinates and confidence
                paragraph=True if not handwriting else False
            )

            # Extract text and blocks
            full_text = []
            blocks = []

            for result in results:
                # result format: (bbox, text, confidence)
                bbox, text, confidence = result
                full_text.append(text)
                blocks.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox
                })

            extracted_text = '\n'.join(full_text)

            # Calculate average confidence
            avg_confidence = sum(b['confidence'] for b in blocks) / len(blocks) if blocks else 0

            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': blocks,
                'confidence': avg_confidence
            }

        except Exception as e:
            raise Exception(f"EasyOCR processing failed: {str(e)}")

    def _map_languages(self, languages):
        """Map language codes to EasyOCR format"""
        if not languages:
            return ['en']

        # EasyOCR language code mapping
        # Full list: https://www.jaided.ai/easyocr/
        lang_map = {
            'en': 'en',
            'hi': 'hi',
            'es': 'es',
            'fr': 'fr',
            'de': 'de',
            'zh': 'ch_sim',  # Simplified Chinese
            'ja': 'ja',
            'ar': 'ar',
            'ru': 'ru',
            'pt': 'pt',
            'it': 'it',
            'ko': 'ko',
            'th': 'th',
            'vi': 'vi',
            'bn': 'bn',  # Bengali
            'ta': 'ta',  # Tamil
            'te': 'te',  # Telugu
            'kn': 'kn',  # Kannada
            'ml': 'ml',  # Malayalam
            'mr': 'mr',  # Marathi
        }

        # Convert language codes
        easyocr_langs = []
        for lang in languages:
            mapped_lang = lang_map.get(lang, lang)
            if mapped_lang not in easyocr_langs:
                easyocr_langs.append(mapped_lang)

        return easyocr_langs
