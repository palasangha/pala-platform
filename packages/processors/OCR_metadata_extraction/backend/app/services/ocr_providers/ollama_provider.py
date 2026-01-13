import requests
import base64
import os
from .base_provider import BaseOCRProvider

class OllamaProvider(BaseOCRProvider):
    """Ollama (Gemma3) OCR Provider"""

    def __init__(self, host=None, model="minicpm-v"):
        """
        Initialize Ollama provider

        Args:
            host: Ollama server host (e.g., "http://172.12.0.83:11434")
            model: Model name to use (default: llama3.2-vision for multilingual support)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if Ollama is enabled
        enabled = os.getenv('OLLAMA_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.host = None
            self.model = None
            logger.info("Ollama provider is disabled via OLLAMA_ENABLED environment variable")
            return

        self.host = host or os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'llama3.2-vision')
        self._available = self._check_availability()
        
        if self._available:
            logger.info(f"✓ Ollama provider initialized successfully (model: {self.model}, host: {self.host})")
        else:
            logger.warning(f"✗ Ollama provider initialization failed (model: {self.model}, host: {self.host})")

    def get_name(self):
        return "ollama"

    def is_available(self):
        return self._available

    def _check_availability(self):
        """Check if Ollama server is available"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Ollama server not available: {e}")
            return False

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using Ollama vision model"""
        if not self.is_available():
            raise Exception("Ollama provider is not available")

        try:
            # Check if input is a PDF file
            if image_path.lower().endswith('.pdf'):
                return self._process_pdf(image_path, languages, handwriting, custom_prompt)

            # Load and optimize image
            from PIL import Image
            from app.services.image_optimizer import ImageOptimizer

            # Open image
            img = Image.open(image_path)

            # Optimize and encode image (resize only if > 5MB)
            image_data = base64.b64encode(
                ImageOptimizer.optimize_and_encode(
                    img,
                    target_size_mb=5.0,
                    auto_optimize=True,
                    auto_crop=False,
                    format='JPEG'
                )
            ).decode('utf-8')

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._build_prompt(languages, handwriting)

            # Call Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more accurate OCR
                    "num_predict": 4096  # Allow longer responses
                }
            }

            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=600
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

            result = response.json()
            print(result)
            extracted_text = result.get('response', '').strip()

            # Format response to match expected structure
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95  # Ollama doesn't provide confidence scores
            }

        except requests.exceptions.Timeout:
            raise Exception("Ollama request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to Ollama server at {self.host}")
        except Exception as e:
            raise Exception(f"Ollama OCR processing failed: {str(e)}")

    def _process_pdf(self, pdf_path, languages=None, handwriting=False, custom_prompt=None):
        """Process PDF by converting pages to images and processing each page"""
        from app.services.pdf_service import PDFService
        from app.services.image_optimizer import ImageOptimizer

        try:
            # Convert PDF pages to PIL Image objects with optimal DPI
            # DPI is automatically selected based on handwriting flag
            page_images = PDFService.pdf_to_images(
                pdf_path,
                handwriting=handwriting
            )

            if not page_images:
                raise Exception("No pages found in PDF")

            # Process each page
            all_text = []
            all_blocks = []

            for page_num, page_img in enumerate(page_images, 1):
                # Optimize and encode page image (resize only if > 5MB)
                image_data = base64.b64encode(
                    ImageOptimizer.optimize_and_encode(
                        page_img,
                        target_size_mb=5.0,
                        auto_optimize=True,
                        auto_crop=False,
                        format='JPEG'
                    )
                ).decode('utf-8')

                # Use custom prompt if provided, otherwise build default
                if custom_prompt:
                    prompt = custom_prompt
                else:
                    prompt = self._build_prompt(languages, handwriting)

                # Add page number context for multi-page PDFs
                if len(page_images) > 1:
                    prompt = f"[Page {page_num}/{len(page_images)}] {prompt}"

                # Call Ollama API for this page
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096
                    }
                }

                response = requests.post(
                    f"{self.host}/api/generate",
                    json=payload,
                    timeout=600
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error on page {page_num}: {response.status_code} - {response.text}")

                result = response.json()
                page_text = result.get('response', '').strip()

                if page_text:
                    # Add page separator for multi-page PDFs
                    if len(page_images) > 1:
                        all_text.append(f"\n--- Page {page_num} ---\n{page_text}")
                    else:
                        all_text.append(page_text)

                    all_blocks.append({
                        'text': page_text,
                        'page': page_num
                    })

            # Combine all pages
            combined_text = '\n\n'.join(all_text)

            return {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.95,
                'pages_processed': len(page_images)
            }

        except Exception as e:
            # Re-raise with more context
            if "PDF2Image library not available" in str(e):
                raise Exception(f"Cannot process PDF: {str(e)}")
            raise

    def _build_prompt(self, languages, handwriting):
        """Build appropriate prompt for OCR task with enhanced multilingual support"""
        prompt = "You are an expert OCR system. Extract ALL text from this image with 100% accuracy. "

        if handwriting:
            prompt += "This image contains HANDWRITTEN text - pay special attention to letter formation and strokes. "

        if languages:
            lang_names = {
                'en': 'English',
                'hi': 'Hindi (Devanagari script)',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ar': 'Arabic',
                'bn': 'Bengali',
                'te': 'Telugu',
                'ta': 'Tamil',
                'mr': 'Marathi',
                'ur': 'Urdu'
            }
            lang_list = [lang_names.get(lang, lang) for lang in languages]

            # Special handling for Indian languages with Devanagari/Indic scripts
            indic_langs = {'hi', 'bn', 'te', 'ta', 'mr', 'ur'}
            if any(lang in indic_langs for lang in languages):
                prompt += f"IMPORTANT: This image contains text in {', '.join(lang_list)}. "
                prompt += "Pay special attention to Devanagari and Indic script characters. "
                prompt += "Recognize all vowel marks (matras), consonant conjuncts, and diacritical marks accurately. "
            else:
                prompt += f"The text is in {', '.join(lang_list)}. "

        prompt += "\n\nRULES:\n"
        prompt += "1. Extract EVERY character, word, and line exactly as shown\n"
        prompt += "2. Preserve the original formatting, spacing, and line breaks\n"
        prompt += "3. Do NOT translate, interpret, or explain the text\n"
        prompt += "4. Do NOT add any commentary or notes\n"
        prompt += "5. Output ONLY the extracted text, nothing else\n"

        return prompt
