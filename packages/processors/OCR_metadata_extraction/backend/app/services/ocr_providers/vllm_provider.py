import requests
import base64
import os
from .base_provider import BaseOCRProvider

class VLLMProvider(BaseOCRProvider):
    """VLLM OCR Provider"""

    def __init__(self, host=None, model=None, api_key=None):
        """
        Initialize VLLM provider

        Args:
            host: VLLM server host (e.g., "http://vllm:8000")
            model: Model name to use
            api_key: API key for authentication
        """
        from app.config import Config

        # Check if VLLM is enabled
        enabled = os.getenv('VLLM_ENABLED', 'false').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.host = None
            self.model = None
            self.api_key = None
            print("VLLM provider is disabled via VLLM_ENABLED environment variable")
            return

        self.host = host or Config.VLLM_HOST
        self.model = model or Config.VLLM_MODEL
        self.api_key = api_key or Config.VLLM_API_KEY
        self.timeout = Config.VLLM_TIMEOUT
        self.max_tokens = Config.VLLM_MAX_TOKENS
        self._available = self._check_availability()

    def get_name(self):
        return "vllm"

    def is_available(self):
        return self._available

    def _check_availability(self):
        """Check if VLLM server is available"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.host}/v1/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"VLLM server not available: {e}")
            return False

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using VLLM vision model"""
        if not self.is_available():
            raise Exception("VLLM provider is not available")

        try:
            # Check if input is a PDF file
            if image_path.lower().endswith('.pdf'):
                return self._process_pdf(image_path, languages, handwriting, custom_prompt)

            # Load and optimize image
            from PIL import Image
            from app.services.image_optimizer import ImageOptimizer

            # Open and optimize image (resize only if > 5MB)
            img = Image.open(image_path)
            image_data = base64.b64encode(
                ImageOptimizer.optimize_and_encode(
                    img,
                    target_size_mb=5.0,
                    auto_optimize=True,
                    auto_crop=False,
                    format='JPEG'
                )
            ).decode('utf-8')

            mime_type = 'image/jpeg'

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._build_prompt(languages, handwriting)

            # Call VLLM API using OpenAI-compatible format
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.1
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(
                f"{self.host}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise Exception(f"VLLM API error: {response.status_code} - {response.text}")

            result = response.json()

            # Extract text from response
            if 'choices' in result and len(result['choices']) > 0:
                extracted_text = result['choices'][0]['message']['content'].strip()
            else:
                extracted_text = ''

            # Format response to match expected structure
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95  # VLLM doesn't provide confidence scores
            }

        except requests.exceptions.Timeout:
            raise Exception("VLLM request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to VLLM server at {self.host}")
        except Exception as e:
            raise Exception(f"VLLM OCR processing failed: {str(e)}")

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

                # Call VLLM API for this page
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.1
                }

                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                response = requests.post(
                    f"{self.host}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code != 200:
                    raise Exception(f"VLLM API error on page {page_num}: {response.status_code} - {response.text}")

                result = response.json()

                # Extract text from response
                if 'choices' in result and len(result['choices']) > 0:
                    page_text = result['choices'][0]['message']['content'].strip()
                else:
                    page_text = ''

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
        """Build appropriate prompt for OCR task"""
        prompt = "Extract all text from this image accurately. "

        if handwriting:
            prompt += "The image contains handwritten text. Pay close attention to handwriting recognition. "

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

        prompt += "Return only the extracted text without any explanations, commentary, or markdown formatting. Maintain the original line breaks and formatting."

        return prompt
