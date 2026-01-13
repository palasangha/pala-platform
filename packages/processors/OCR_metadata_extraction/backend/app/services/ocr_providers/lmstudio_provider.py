import requests
import base64
import os
import logging
from datetime import datetime
from .base_provider import BaseOCRProvider

# Set up logger for LM Studio provider
logger = logging.getLogger(__name__)


class LMStudioProvider(BaseOCRProvider):
    """LM Studio OCR Provider for running local LLMs with OpenAI-compatible API"""

    def __init__(self, host=None, model=None, api_key=None):
        """
        Initialize LM Studio provider

        Args:
            host: LM Studio API host (e.g., "http://localhost:1234")
            model: Model name to use (optional, uses default loaded model)
            api_key: API key for authentication (optional)
        """
        from app.config import Config

        logger.debug("Initializing LM Studio provider")

        # Check if LM Studio is enabled
        enabled = os.getenv('LMSTUDIO_ENABLED', 'false').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self._availability_checked = True
            self.host = None
            self.model = None
            self.api_key = None
            logger.info("LM Studio provider is disabled via LMSTUDIO_ENABLED environment variable")
            return

        self.host = host or os.getenv('LMSTUDIO_HOST', 'http://lmstudio:1234')
        self.model = model or os.getenv('LMSTUDIO_MODEL', 'gemma-3-12b')
        self.api_key = api_key or os.getenv('LMSTUDIO_API_KEY', 'lm-studio')
        self.timeout = int(os.getenv('LMSTUDIO_TIMEOUT', '600'))
        self.max_tokens = int(os.getenv('LMSTUDIO_MAX_TOKENS', '4096'))
        self.skip_availability_check = os.getenv('LMSTUDIO_SKIP_AVAILABILITY_CHECK', 'false').lower() in ('true', '1', 'yes')

        logger.info(
            f"LM Studio provider configured: "
            f"host={self.host}, model={self.model}, timeout={self.timeout}s, max_tokens={self.max_tokens}, skip_check={self.skip_availability_check}"
        )

        # Lazy availability check - don't block initialization
        if self.skip_availability_check:
            # If skip check is enabled, assume provider is available
            self._available = True
            self._availability_checked = True
            logger.info(f"LM Studio availability check is SKIPPED - assuming provider is available")
        else:
            # Otherwise, perform lazy check on first use
            self._available = None
            self._availability_checked = False
            logger.info(f"LM Studio provider will check availability on first use")

    def get_name(self):
        return "lmstudio"

    def is_available(self):
        # Lazy availability check - check on first call, then cache result
        if not self._availability_checked:
            self._available = self._check_availability()
            self._availability_checked = True
            if self._available:
                logger.info("LM Studio provider is available and ready")
            else:
                logger.warning(f"LM Studio provider is NOT available at {self.host}")
        return self._available

    def _check_availability(self):
        """Check if LM Studio API server is available"""
        # If skip check is enabled, assume available (for host-based deployments)
        if self.skip_availability_check:
            logger.info(f"LM Studio availability check is SKIPPED - assuming available")
            return True

        try:
            logger.debug(f"Checking LM Studio availability at {self.host}")

            # LM Studio uses OpenAI-compatible API, check /v1/models endpoint
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.host}/v1/models",
                headers=headers,
                timeout=5,  # Quick 5-second timeout for availability check
                verify=False  # Disable SSL verification for local development
            )

            if response.status_code == 200:
                logger.debug(f"LM Studio availability check successful (status: {response.status_code})")
                return True
            else:
                logger.warning(f"LM Studio returned status {response.status_code} on availability check")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while checking LM Studio availability at {self.host} - server may be slow or unresponsive")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while checking LM Studio at {self.host}: {e}")
            logger.error(f"Hint: If running in Docker, make sure LMSTUDIO_HOST uses 'localhost' or '172.17.0.1', not 'host.docker.internal'")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking LM Studio availability: {e}", exc_info=True)
            return False

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using LM Studio vision model"""
        start_time = datetime.now()
        logger.info(f"Starting image processing: {image_path}")

        if not self.is_available():
            error_msg = "LM Studio provider is not available"
            logger.error(error_msg)
            raise Exception(error_msg)

        try:
            logger.debug(f"Image path: {image_path}, languages: {languages}, handwriting: {handwriting}")

            # Check if input is a PDF file
            if image_path.lower().endswith('.pdf'):
                logger.info("PDF detected, using PDF processing pipeline")
                return self._process_pdf(image_path, languages, handwriting, custom_prompt)

            # Load and optimize image
            from PIL import Image, ImageEnhance
            from app.services.image_optimizer import ImageOptimizer

            logger.debug(f"Opening image file: {image_path}")
            img = Image.open(image_path)
            logger.debug(f"Image loaded: size={img.size}, format={img.format}")

            # Enhance image for better OCR accuracy (for typed documents)
            if not handwriting:
                logger.debug("Applying image enhancement for document OCR")
                # Increase contrast for better text clarity
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)  # Increase contrast by 30%
                
                # Slightly increase sharpness
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.2)  # Increase sharpness by 20%
                
                logger.debug("Image enhancement applied")

            # Optimize and encode image - use PNG (lossless) for better OCR accuracy
            logger.debug("Encoding image to PNG format (lossless) for maximum OCR accuracy")
            image_bytes = ImageOptimizer.optimize_and_encode(
                img,
                target_size_mb=5.0,
                auto_optimize=False,  # Disable size optimization for OCR
                auto_crop=False,
                format='PNG'  # Use PNG for lossless encoding
            )
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            logger.debug(f"Image encoded to PNG, size: {len(image_data)} bytes")

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                logger.debug("Using custom prompt for OCR")
                prompt = custom_prompt
            else:
                logger.debug("Building default OCR prompt")
                prompt = self._build_prompt(languages, handwriting)

            logger.debug(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

            mime_type = 'image/png'  # PNG is lossless, better for OCR

            # Call LM Studio API using OpenAI-compatible format
            logger.debug(f"Preparing API request to {self.host}/v1/chat/completions")
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
                "temperature": 0.0,  # Use 0 for deterministic/accurate responses
                "top_p": 0.95,  # Reduce randomness
                "frequency_penalty": 0.0,  # Reduce repetition penalties for accuracy
                "presence_penalty": 0.0
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            logger.debug(f"Sending request with model={self.model}, max_tokens={self.max_tokens}, timeout={self.timeout}s")
            api_start = datetime.now()

            response = requests.post(
                f"{self.host}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            api_duration = (datetime.now() - api_start).total_seconds()
            logger.debug(f"API response received in {api_duration:.2f}s (status: {response.status_code})")

            if response.status_code != 200:
                error_msg = f"LM Studio API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            result = response.json()

            # Extract text from response
            if 'choices' in result and len(result['choices']) > 0:
                extracted_text = result['choices'][0]['message']['content'].strip()
                logger.debug(f"Text extracted successfully, length: {len(extracted_text)} chars")
            else:
                logger.warning("No choices in API response")
                extracted_text = ''

            # Format response to match expected structure
            response_data = {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95  # LM Studio doesn't provide confidence scores
            }

            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Image processing completed successfully in {total_duration:.2f}s. "
                f"Extracted {len(extracted_text)} characters"
            )

            return response_data

        except requests.exceptions.Timeout:
            error_msg = "LM Studio request timed out"
            logger.error(f"{error_msg} (timeout: {self.timeout}s)", exc_info=True)
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Could not connect to LM Studio server at {self.host}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"LM Studio OCR processing failed: {str(e)}", exc_info=True)
            raise Exception(f"LM Studio OCR processing failed: {str(e)}")

    def _process_pdf(self, pdf_path, languages=None, handwriting=False, custom_prompt=None):
        """Process PDF by converting pages to images and processing each page"""
        from app.services.pdf_service import PDFService
        from app.services.image_optimizer import ImageOptimizer

        start_time = datetime.now()
        logger.info(f"Starting PDF processing: {pdf_path}")

        try:
            # Convert PDF pages to PIL Image objects with optimal DPI
            logger.debug("Converting PDF to images")
            page_images = PDFService.pdf_to_images(
                pdf_path,
                handwriting=handwriting
            )

            logger.info(f"PDF converted to {len(page_images)} page(s)")

            if not page_images:
                raise Exception("No pages found in PDF")

            # Process each page
            all_text = []
            all_blocks = []
            page_count = len(page_images)

            for page_num, page_img in enumerate(page_images, 1):
                logger.debug(f"Processing page {page_num}/{page_count}")

                # Optimize and encode page image - use PNG for lossless quality
                image_data = base64.b64encode(
                    ImageOptimizer.optimize_and_encode(
                        page_img,
                        target_size_mb=5.0,
                        auto_optimize=False,  # Disable size optimization
                        auto_crop=False,
                        format='PNG'  # Lossless format
                    )
                ).decode('utf-8')

                # Use custom prompt if provided, otherwise build default
                if custom_prompt:
                    prompt = custom_prompt
                else:
                    prompt = self._build_prompt(languages, handwriting)

                # Add page number context for multi-page PDFs
                if page_count > 1:
                    prompt = f"[Page {page_num}/{page_count}] {prompt}"
                    logger.debug(f"Added page context to prompt")

                # Call LM Studio API for this page
                logger.debug(f"Calling LM Studio API for page {page_num}")
                page_start = datetime.now()

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
                                        "url": f"data:image/png;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.0,  # Deterministic for accuracy
                    "top_p": 0.95,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
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

                page_duration = (datetime.now() - page_start).total_seconds()
                logger.debug(f"Page {page_num} API call completed in {page_duration:.2f}s (status: {response.status_code})")

                if response.status_code != 200:
                    error_msg = f"LM Studio API error on page {page_num}: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                result = response.json()

                # Extract text from response
                if 'choices' in result and len(result['choices']) > 0:
                    page_text = result['choices'][0]['message']['content'].strip()
                    logger.debug(f"Page {page_num} text extracted: {len(page_text)} chars")
                else:
                    page_text = ''
                    logger.warning(f"No content extracted from page {page_num}")

                if page_text:
                    # Add page separator for multi-page PDFs
                    if page_count > 1:
                        all_text.append(f"\n--- Page {page_num} ---\n{page_text}")
                    else:
                        all_text.append(page_text)

                    all_blocks.append({
                        'text': page_text,
                        'page': page_num
                    })

            # Combine all pages
            combined_text = '\n\n'.join(all_text)
            total_duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"PDF processing completed successfully in {total_duration:.2f}s. "
                f"Processed {page_count} page(s), extracted {len(combined_text)} total characters"
            )

            return {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.95,
                'pages_processed': page_count
            }

        except Exception as e:
            logger.error(f"LM Studio PDF processing failed: {str(e)}", exc_info=True)
            # Re-raise with more context
            if "PDF2Image library not available" in str(e):
                raise Exception(f"Cannot process PDF: {str(e)}")
            raise

    def _build_prompt(self, languages, handwriting):
        """Build appropriate prompt for OCR task"""
        
        # Check if this is a document-focused OCR (not handwriting)
        is_document = not handwriting
        
        if is_document:
            # For typed documents, emphasize accuracy and structure
            prompt = (
                "You are an expert OCR system. Your task is to extract ALL text from this document image with maximum accuracy.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Extract EVERY word, character, and number exactly as shown\n"
                "2. Preserve all formatting: line breaks, indentation, spacing\n"
                "3. Do NOT skip any text\n"
                "4. Do NOT make assumptions about illegible text\n"
                "5. If you cannot read a word clearly, mark it as [unclear]\n"
                "6. Maintain paragraph structure\n"
                "7. Return ONLY the extracted text - no explanations or markdown\n\n"
                "Begin extraction:"
            )
        else:
            # For handwritten text, be more flexible
            prompt = (
                "Extract all text from this handwritten image with maximum accuracy.\n\n"
                "INSTRUCTIONS:\n"
                "1. Pay close attention to handwriting details\n"
                "2. Extract every readable word\n"
                "3. Preserve line breaks and general layout\n"
                "4. For unclear text, make your best interpretation\n"
                "5. Return only the extracted text without explanations\n\n"
                "Begin extraction:"
            )

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
            lang_note = f"Document language: {', '.join(lang_list)}\n"
            # Insert language note after the critical instructions
            if is_document:
                prompt = prompt.replace("\nBegin extraction:", f"\n{lang_note}Begin extraction:")
            else:
                prompt = prompt.replace("\nBegin extraction:", f"\n{lang_note}Begin extraction:")

        return prompt
