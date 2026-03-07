import requests
import base64
import os
from .base_provider import BaseOCRProvider

class LlamaCppProvider(BaseOCRProvider):
    """llama.cpp OCR Provider for running local LLMs"""

    def __init__(self, host=None, model=None):
        """
        Initialize llama.cpp provider

        Args:
            host: llama.cpp server host (e.g., "http://localhost:8000")
            model: Model name (optional, llama.cpp uses what's loaded)
        """
        # Check if llama.cpp is enabled
        enabled = os.getenv('LLAMACPP_ENABLED', 'false').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.host = None
            self.model = None
            print("llama.cpp provider is disabled via LLAMACPP_ENABLED environment variable")
            return

        self.host = host or os.getenv('LLAMACPP_HOST', 'http://localhost:8000')
        self.model = model or os.getenv('LLAMACPP_MODEL', 'gemma-3-12b')
        self._available = self._check_availability()

    def get_name(self):
        return "llamacpp"

    def is_available(self):
        return self._available

    def _check_availability(self):
        """Check if llama.cpp server is available"""
        try:
            # llama.cpp provides /health endpoint
            response = requests.get(f"{self.host}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"llama.cpp server not available at {self.host}: {e}")
            return False

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using llama.cpp vision model"""
        if not self.is_available():
            raise Exception("llama.cpp provider is not available")

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

            # Call llama.cpp API with vision/multimodal support
            # llama.cpp supports image input in base64 format
            payload = {
                "prompt": prompt,
                "image_data": image_data,
                "temperature": 0.1,  # Lower temperature for more accurate OCR
                "top_p": 0.95,
                "max_tokens": 4096,  # Allow longer responses
                "stream": False
            }

            response = requests.post(
                f"{self.host}/completion",
                json=payload,
                timeout=600
            )

            if response.status_code != 200:
                raise Exception(f"llama.cpp API error: {response.status_code} - {response.text}")

            result = response.json()
            extracted_text = result.get('content', '').strip()

            # Format response to match expected structure
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95  # llama.cpp doesn't provide confidence scores
            }

        except requests.exceptions.Timeout:
            raise Exception("llama.cpp request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to llama.cpp server at {self.host}")
        except Exception as e:
            raise Exception(f"llama.cpp OCR processing failed: {str(e)}")

    def _process_pdf(self, pdf_path, languages=None, handwriting=False, custom_prompt=None):
        """Process PDF by converting pages to images and processing each page"""
        from app.services.pdf_service import PDFService
        from app.services.image_optimizer import ImageOptimizer

        try:
            # Convert PDF pages to PIL Image objects with optimal DPI
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
                # Optimize and encode page image
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
                    prompt = f"{prompt}\n\n(This is page {page_num} of {len(page_images)})"

                # Call llama.cpp API
                payload = {
                    "prompt": prompt,
                    "image_data": image_data,
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_tokens": 4096,
                    "stream": False
                }

                response = requests.post(
                    f"{self.host}/completion",
                    json=payload,
                    timeout=600
                )

                if response.status_code != 200:
                    raise Exception(f"llama.cpp API error on page {page_num}: {response.status_code}")

                result = response.json()
                page_text = result.get('content', '').strip()
                all_text.append(page_text)
                all_blocks.append({
                    'page': page_num,
                    'text': page_text
                })

            # Combine results from all pages
            combined_text = '\n\n'.join(all_text)

            return {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.95
            }

        except Exception as e:
            raise Exception(f"llama.cpp PDF processing failed: {str(e)}")

    def _build_prompt(self, languages=None, handwriting=False):
        """Build OCR prompt for llama.cpp"""
        prompt = "Extract all text from this image accurately and completely. "
        
        if languages:
            langs = ", ".join(languages)
            prompt += f"The text may be in {langs}. "
        
        if handwriting:
            prompt += "The text may include handwritten content. "
        
        prompt += "Preserve formatting and structure as much as possible. Return only the extracted text."
        
        return prompt
