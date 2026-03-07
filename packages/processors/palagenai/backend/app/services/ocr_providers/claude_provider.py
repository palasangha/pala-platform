import base64
import os
from .base_provider import BaseOCRProvider

class ClaudeProvider(BaseOCRProvider):
    """Claude AI (Anthropic) OCR Provider"""

    def __init__(self, api_key=None, model="claude-3-5-sonnet-20241022"):
        """
        Initialize Claude provider

        Args:
            api_key: Anthropic API key
            model: Model name to use (default: claude-3-5-sonnet-20241022 for vision support)
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check if Claude is enabled
        enabled = os.getenv('CLAUDE_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.client = None
            self.model = None
            logger.info("Claude provider is disabled via CLAUDE_ENABLED environment variable")
            return

        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model or os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')

        if not self.api_key:
            self._available = False
            self.client = None
            logger.warning("✗ Claude provider initialization failed: ANTHROPIC_API_KEY not set")
            return

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self._available = True
            logger.info(f"✓ Claude provider initialized successfully (model: {self.model})")
        except ImportError:
            self._available = False
            self.client = None
            logger.error("✗ Claude provider initialization failed: anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            self._available = False
            self.client = None
            logger.error(f"✗ Claude provider initialization failed: {str(e)}")

    def get_name(self):
        return "claude"

    def is_available(self):
        return self._available and self.client is not None

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image using Claude vision model"""
        if not self.is_available():
            raise Exception("Claude provider is not available. Please set ANTHROPIC_API_KEY environment variable and ensure 'anthropic' package is installed.")

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
            # Claude supports up to 5MB images
            optimized_bytes = ImageOptimizer.optimize_and_encode(
                img,
                target_size_mb=5.0,
                auto_optimize=True,
                auto_crop=False,
                format='JPEG'
            )

            image_data = base64.b64encode(optimized_bytes).decode('utf-8')

            # Determine media type
            image_format = img.format.lower() if img.format else 'jpeg'
            media_type_map = {
                'jpeg': 'image/jpeg',
                'jpg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            media_type = media_type_map.get(image_format, 'image/jpeg')

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._build_prompt(languages, handwriting)

            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.1,  # Lower temperature for more accurate OCR
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Extract text from response
            extracted_text = ""
            for block in message.content:
                if block.type == "text":
                    extracted_text += block.text

            extracted_text = extracted_text.strip()

            # Format response to match expected structure
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95  # Claude doesn't provide confidence scores
            }

        except Exception as e:
            if "anthropic" in str(e).lower():
                raise Exception(f"Claude API error: {str(e)}")
            raise Exception(f"Claude OCR processing failed: {str(e)}")

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
                optimized_bytes = ImageOptimizer.optimize_and_encode(
                    page_img,
                    target_size_mb=5.0,
                    auto_optimize=True,
                    auto_crop=False,
                    format='JPEG'
                )

                image_data = base64.b64encode(optimized_bytes).decode('utf-8')

                # Use custom prompt if provided, otherwise build default
                if custom_prompt:
                    prompt = custom_prompt
                else:
                    prompt = self._build_prompt(languages, handwriting)

                # Add page number context for multi-page PDFs
                if len(page_images) > 1:
                    prompt = f"[Page {page_num}/{len(page_images)}] {prompt}"

                # Call Claude API for this page
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ],
                        }
                    ],
                )

                # Extract text from response
                page_text = ""
                for block in message.content:
                    if block.type == "text":
                        page_text += block.text

                page_text = page_text.strip()

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
