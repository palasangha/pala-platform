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
        self.max_tokens = int(os.getenv('LMSTUDIO_MAX_TOKENS', '8192'))  # Increased for JSON responses
        self.skip_availability_check = os.getenv('LMSTUDIO_SKIP_AVAILABILITY_CHECK', 'false').lower() in ('true', '1', 'yes')

        # Structured output configuration
        self.enable_structured_output = os.getenv(
            'LMSTUDIO_ENABLE_STRUCTURED_OUTPUT', 'true'
        ).lower() in ('true', '1', 'yes')

        logger.info(
            f"LM Studio provider configured: "
            f"host={self.host}, model={self.model}, timeout={self.timeout}s, max_tokens={self.max_tokens}, "
            f"structured_output={self.enable_structured_output}, skip_check={self.skip_availability_check}"
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

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None, enable_structured_output=None):
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
                return self._process_pdf(image_path, languages, handwriting, custom_prompt, enable_structured_output)

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

            # Determine if structured output should be used
            if enable_structured_output is None:
                enable_structured_output = self.enable_structured_output

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                logger.debug("Using custom prompt for OCR")
                prompt = custom_prompt
                enable_structured_output = False  # Custom prompts bypass structured extraction
            else:
                if enable_structured_output:
                    logger.debug("Building structured JSON extraction prompt")
                    prompt = self._build_structured_prompt(languages, handwriting)
                else:
                    logger.debug("Building text-only OCR prompt")
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
                llm_response = result['choices'][0]['message']['content'].strip()
                logger.debug(f"LLM response received, length: {len(llm_response)} chars")
            else:
                logger.warning("No choices in API response")
                llm_response = ''

            # Try to parse structured JSON if enabled
            structured_data = None
            ocr_text = llm_response

            if enable_structured_output and llm_response:
                success, parsed_json, error = self._parse_json_response(llm_response)

                if success and parsed_json:
                    # Validate JSON structure
                    if 'ocr_text' in parsed_json:
                        ocr_text = parsed_json['ocr_text']
                        structured_data = parsed_json.get('structured_data', {})

                        # Validate completeness of structured data
                        if structured_data:
                            is_valid, missing_fields, completeness = self._validate_structured_data(structured_data)
                            logger.info(
                                f"Structured data extracted - Completeness: {completeness:.1f}% "
                                f"({len(structured_data)} sections)"
                            )
                            if missing_fields:
                                logger.warning(f"Missing fields ({len(missing_fields)}): {', '.join(missing_fields[:5])}")

                            # Add validation metadata
                            structured_data['_validation'] = {
                                'is_complete': is_valid,
                                'completeness_score': completeness,
                                'missing_fields': missing_fields
                            }
                        else:
                            logger.info("Successfully extracted structured data with {len(structured_data)} sections")
                    else:
                        logger.warning("JSON parsed but missing 'ocr_text' field, falling back to text-only")
                        structured_data = None
                else:
                    logger.warning(f"JSON parsing failed: {error}. Falling back to text-only mode")
                    structured_data = None

            # Format response with backward compatibility
            response_data = {
                'text': ocr_text,
                'full_text': ocr_text,
                'words': [],
                'blocks': [{'text': ocr_text}] if ocr_text else [],
                'confidence': 0.95,  # LM Studio doesn't provide confidence scores
                'raw_llm_response': llm_response  # Store raw LLM output for auditing/debugging
            }

            # Add structured data if available
            if structured_data:
                response_data['structured_data'] = structured_data
                response_data['extraction_mode'] = 'structured'
            else:
                response_data['extraction_mode'] = 'text_only'

            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Image processing completed successfully in {total_duration:.2f}s. "
                f"Mode: {response_data.get('extraction_mode', 'unknown')}, "
                f"Extracted {len(ocr_text)} characters"
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

    def _process_pdf(self, pdf_path, languages=None, handwriting=False, custom_prompt=None, enable_structured_output=None):
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

            # Determine if structured output should be used
            if enable_structured_output is None:
                enable_structured_output = self.enable_structured_output

            # Process each page
            all_text = []
            all_blocks = []
            all_structured_pages = []
            all_raw_responses = []
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
                    page_enable_structured = False
                else:
                    if enable_structured_output:
                        prompt = self._build_structured_prompt(languages, handwriting)
                        page_enable_structured = True
                    else:
                        prompt = self._build_prompt(languages, handwriting)
                        page_enable_structured = False

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
                    llm_response = result['choices'][0]['message']['content'].strip()
                    logger.debug(f"Page {page_num} response received: {len(llm_response)} chars")
                    all_raw_responses.append({'page': page_num, 'response': llm_response})
                else:
                    llm_response = ''
                    logger.warning(f"No content extracted from page {page_num}")

                # Try to parse structured JSON if enabled
                page_structured = None
                page_text = llm_response

                if page_enable_structured and llm_response:
                    logger.info(f"Page {page_num}: Attempting to parse structured JSON from response")
                    success, parsed_json, error = self._parse_json_response(llm_response)

                    if success and parsed_json and 'ocr_text' in parsed_json:
                        page_text = parsed_json['ocr_text']
                        page_structured = parsed_json.get('structured_data', {})
                        logger.info(f"Page {page_num}: Successfully parsed structured JSON")

                        # Validate completeness of structured data for this page
                        if page_structured:
                            is_valid, missing_fields, completeness = self._validate_structured_data(page_structured)
                            logger.info(
                                f"Page {page_num} structured data - Completeness: {completeness:.1f}%"
                            )
                            if missing_fields and len(missing_fields) > 0:
                                logger.debug(f"Page {page_num} missing: {', '.join(missing_fields[:3])}")

                            # Add validation metadata
                            page_structured['_validation'] = {
                                'is_complete': is_valid,
                                'completeness_score': completeness,
                                'missing_fields': missing_fields
                            }

                        all_structured_pages.append(page_structured)
                    else:
                        logger.warning(f"Page {page_num} JSON parsing failed: {error}. Using text-only mode")
                        page_structured = None
                else:
                    if not page_enable_structured:
                        logger.debug(f"Page {page_num}: Structured output disabled, using text-only")

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

            # Build response with optional structured data
            response = {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.95,
                'pages_processed': page_count,
                'raw_llm_response': all_raw_responses
            }

            # Add structured data if any pages provided it
            if all_structured_pages:
                # Merge structured data from all pages (use first page for sender/recipient)
                merged_structured = {}
                if all_structured_pages:
                    merged_structured = all_structured_pages[0].copy()
                    # Combine body paragraphs from all pages
                    if 'content' in merged_structured and 'body' in merged_structured['content']:
                        all_bodies = merged_structured['content']['body'] if isinstance(merged_structured['content']['body'], list) else [merged_structured['content']['body']]
                        for page_struct in all_structured_pages[1:]:
                            if 'content' in page_struct and 'body' in page_struct['content']:
                                page_body = page_struct['content']['body']
                                if isinstance(page_body, list):
                                    all_bodies.extend(page_body)
                                else:
                                    all_bodies.append(page_body)
                        merged_structured['content']['body'] = all_bodies

                response['structured_data'] = merged_structured
                response['extraction_mode'] = 'structured'
            else:
                response['extraction_mode'] = 'text_only'

            return response

        except Exception as e:
            logger.error(f"LM Studio PDF processing failed: {str(e)}", exc_info=True)
            # Re-raise with more context
            if "PDF2Image library not available" in str(e):
                raise Exception(f"Cannot process PDF: {str(e)}")
            raise

    def _validate_structured_data(self, structured_data):
        """
        Validate that structured_data contains all required sections and fields

        Returns:
            Tuple of (is_valid: bool, missing_fields: list, completeness_score: float)
        """
        required_structure = {
            'document': {
                'date': ['creation_date', 'sent_date'],
                'languages': [],
                'physical_attributes': ['letterhead', 'pages'],
                'correspondence': {
                    'sender': ['name', 'location', 'contact_info'],
                    'recipient': ['name', 'location']
                }
            },
            'content': ['full_text', 'salutation', 'body', 'closing', 'signature']
        }

        missing_fields = []
        total_fields = 0
        present_fields = 0

        # Check document section
        if 'document' not in structured_data:
            missing_fields.append('document')
        else:
            doc = structured_data['document']

            # Check date
            if 'date' not in doc:
                missing_fields.append('document.date')
            else:
                total_fields += 2
                if 'creation_date' in doc['date']:
                    present_fields += 1
                else:
                    missing_fields.append('document.date.creation_date')
                if 'sent_date' in doc['date']:
                    present_fields += 1
                else:
                    missing_fields.append('document.date.sent_date')

            # Check languages
            total_fields += 1
            if 'languages' in doc:
                present_fields += 1
            else:
                missing_fields.append('document.languages')

            # Check physical_attributes
            if 'physical_attributes' not in doc:
                missing_fields.append('document.physical_attributes')
            else:
                total_fields += 2
                if 'letterhead' in doc['physical_attributes']:
                    present_fields += 1
                else:
                    missing_fields.append('document.physical_attributes.letterhead')
                if 'pages' in doc['physical_attributes']:
                    present_fields += 1
                else:
                    missing_fields.append('document.physical_attributes.pages')

            # Check correspondence
            if 'correspondence' not in doc:
                missing_fields.append('document.correspondence')
            else:
                corr = doc['correspondence']
                total_fields += 5

                if 'sender' in corr:
                    sender = corr['sender']
                    if 'name' in sender:
                        present_fields += 1
                    else:
                        missing_fields.append('document.correspondence.sender.name')
                    if 'location' in sender:
                        present_fields += 1
                    else:
                        missing_fields.append('document.correspondence.sender.location')
                    if 'contact_info' in sender:
                        present_fields += 1
                    else:
                        missing_fields.append('document.correspondence.sender.contact_info')
                else:
                    missing_fields.append('document.correspondence.sender')

                if 'recipient' in corr:
                    recipient = corr['recipient']
                    if 'name' in recipient:
                        present_fields += 1
                    else:
                        missing_fields.append('document.correspondence.recipient.name')
                    if 'location' in recipient:
                        present_fields += 1
                    else:
                        missing_fields.append('document.correspondence.recipient.location')
                else:
                    missing_fields.append('document.correspondence.recipient')

        # Check content section
        if 'content' not in structured_data:
            missing_fields.append('content')
        else:
            content = structured_data['content']
            content_fields = ['full_text', 'salutation', 'body', 'closing', 'signature']
            total_fields += len(content_fields)

            for field in content_fields:
                if field in content:
                    present_fields += 1
                else:
                    missing_fields.append(f'content.{field}')

        completeness_score = (present_fields / total_fields * 100) if total_fields > 0 else 0
        is_valid = len(missing_fields) == 0

        return is_valid, missing_fields, completeness_score

    def _parse_json_response(self, llm_response: str):
        """
        Parse JSON from LLM response, handling markdown code blocks

        Returns:
            Tuple of (success: bool, parsed_json: Dict or None, error_message: str)
        """
        import re
        import json

        # Strategy 1: Try parsing entire response as JSON
        try:
            data = json.loads(llm_response.strip())
            logger.debug("Parsed response as direct JSON")
            return True, data, ""
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown code blocks (```json ... ```)
        code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, llm_response, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match.strip())
                logger.debug("Extracted JSON from markdown code block")
                return True, data, ""
            except json.JSONDecodeError:
                continue

        # Strategy 3: Find JSON object using brace matching ({ ... })
        start_idx = llm_response.find('{')
        if start_idx != -1:
            brace_count = 0
            for i in range(start_idx, len(llm_response)):
                if llm_response[i] == '{':
                    brace_count += 1
                elif llm_response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = llm_response[start_idx:i+1]
                            data = json.loads(json_str)
                            logger.debug("Extracted JSON using brace matching")
                            return True, data, ""
                        except json.JSONDecodeError:
                            break

        # All strategies failed
        error_msg = "Failed to extract valid JSON from LLM response"
        logger.warning(f"{error_msg}. Response preview: {llm_response[:200]}...")
        return False, None, error_msg

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

    def _build_structured_prompt(self, languages, handwriting):
        """Build prompt for structured JSON extraction with document metadata"""

        # Skip structured output for handwriting - fall back to text-only
        if handwriting:
            return self._build_prompt(languages, handwriting)

        prompt = """You are an expert OCR system with document analysis capabilities.

TASK: Extract ALL text from this document AND identify structured metadata visible in the image.

STEP 1 - COMPLETE OCR TRANSCRIPTION:
- Extract EVERY word, number, and character exactly as shown
- Preserve line breaks, indentation, and spacing
- Mark unclear text as [unclear]
- Do NOT skip any text

STEP 2 - EXTRACT VISIBLE METADATA:
Identify the following information ONLY if clearly visible in the image:
- Document date (creation/sent date in YYYY-MM-DD format)
- Languages used
- Letterhead description
- Sender information (name, location, address from letterhead)
- Recipient information (name from salutation like "Dear...")
- Letter structure (salutation, body paragraphs, closing, signature)

CRITICAL RULES:
1. Only extract information DIRECTLY VISIBLE in the image
2. Do NOT infer or assume information not shown
3. Leave fields empty ("" or []) if information is not visible
4. Ensure all JSON is valid and properly formatted
5. Return ONLY JSON, no explanations or markdown

OUTPUT FORMAT:
{
  "ocr_text": "Complete transcription here...",
  "structured_data": {
    "document": {
      "date": {
        "creation_date": "YYYY-MM-DD or empty string",
        "sent_date": "YYYY-MM-DD or empty string"
      },
      "languages": ["en"],
      "physical_attributes": {
        "letterhead": "Description of letterhead if visible",
        "pages": 1
      },
      "correspondence": {
        "sender": {
          "name": "",
          "location": "",
          "contact_info": {"address": ""}
        },
        "recipient": {
          "name": "",
          "location": ""
        }
      }
    },
    "content": {
      "full_text": "Same as ocr_text",
      "salutation": "Opening greeting",
      "body": ["Paragraph 1", "Paragraph 2"],
      "closing": "Closing statement",
      "signature": "Signature description"
    }
  }
}

Begin extraction:"""

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
            lang_note = f"\nExpected language(s): {', '.join(lang_list)}\n"
            prompt = prompt.replace("Begin extraction:", f"{lang_note}Begin extraction:")

        return prompt
