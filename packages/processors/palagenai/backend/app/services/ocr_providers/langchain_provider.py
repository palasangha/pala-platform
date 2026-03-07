import base64
import os
import requests
import tempfile
from .base_provider import BaseOCRProvider

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

class LangChainProvider(BaseOCRProvider):
    """LangChain Ollama OCR Provider with hybrid PDF handling"""

    def __init__(self):
        """
        Initialize LangChain provider
        Uses the LangChainOllamaService for processing
        Supports both embedded text extraction and OCR for scanned PDFs
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check if LangChain is enabled
        enabled = os.getenv('LANGCHAIN_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            logger.info("LangChain provider is disabled via LANGCHAIN_ENABLED environment variable")
            return

        self._available = self._check_availability()

        if self._available:
            logger.info(f"✓ LangChain provider initialized successfully (hybrid PDF mode enabled)")
        else:
            logger.warning(f"✗ LangChain provider initialization failed")

    def get_name(self):
        return "langchain"

    def is_available(self):
        return self._available

    def _check_availability(self):
        """Check if LangChain service is available"""
        try:
            from app.services.langchain_service import get_langchain_service
            service = get_langchain_service()
            return service.health_check()
        except Exception as e:
            print(f"LangChain service not available: {e}")
            return False

    def _preprocess_image(self, image_path):
        """
        Preprocess image: detect document, crop, and enhance
        Returns path to preprocessed image (temp file)
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("="*80)
        logger.info("STARTING IMAGE PREPROCESSING")
        logger.info("="*80)

        if not CV2_AVAILABLE:
            logger.warning("⚠ OpenCV not available - skipping image preprocessing")
            logger.info("Install opencv-python to enable automatic document detection and cropping")
            return image_path

        try:
            # Load image
            logger.info(f"📁 Loading image: {image_path}")
            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"⚠ Could not load image with OpenCV: {image_path}")
                return image_path

            height, width = img.shape[:2]
            logger.info(f"✓ Original image loaded successfully")
            logger.info(f"  - Dimensions: {width}x{height} pixels")
            logger.info(f"  - Channels: {img.shape[2]}")
            logger.info(f"  - Total pixels: {width * height:,}")

            # Convert to grayscale
            logger.info("🔄 Converting to grayscale for processing...")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            logger.info("🔄 Applying Gaussian blur to reduce noise...")
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge detection
            logger.info("🔄 Performing Canny edge detection...")
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours
            logger.info("🔍 Finding contours in the image...")
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            logger.info(f"  - Found {len(contours)} contours")

            # Find the largest rectangular contour (likely the paper)
            largest_contour = None
            max_area = 0
            candidate_count = 0

            logger.info("🔍 Searching for document rectangle (4-sided polygon)...")
            for idx, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > 10000:  # Minimum area threshold
                    # Approximate the contour to a polygon
                    peri = cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                    # If it has 4 corners, it's likely the paper
                    if len(approx) == 4:
                        candidate_count += 1
                        logger.debug(f"  - Candidate {candidate_count}: area={area:,.0f}, corners={len(approx)}")
                        if area > max_area:
                            max_area = area
                            largest_contour = approx

            if largest_contour is None:
                logger.warning("⚠ Could not detect document rectangle")
                logger.info("🔄 Falling back to brightness-based cropping...")

                # Fallback: find bounding box of all bright areas
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                coords = cv2.findNonZero(thresh)

                if coords is not None:
                    x, y, w, h = cv2.boundingRect(coords)
                    logger.info(f"  - Bright area detected: x={x}, y={y}, w={w}, h={h}")
                else:
                    # If no bright areas, use the whole image
                    logger.warning("⚠ No bright areas detected - using original image without cropping")
                    return image_path

                # Add margin
                margin = 20
                x_orig, y_orig, w_orig, h_orig = x, y, w, h
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(img.shape[1] - x, w + 2*margin)
                h = min(img.shape[0] - y, h + 2*margin)

                logger.info(f"  - Added {margin}px margin")
                logger.info(f"  - Crop region: x={x}, y={y}, w={w}, h={h}")

                cropped = img[y:y+h, x:x+w]
                detection_method = "brightness-based"
            else:
                logger.info(f"✓ Document rectangle detected!")
                logger.info(f"  - Area: {max_area:,.0f} pixels ({max_area/(width*height)*100:.1f}% of image)")
                logger.info(f"  - Evaluated {candidate_count} rectangular candidates")

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(largest_contour)
                logger.info(f"  - Bounding box: x={x}, y={y}, w={w}, h={h}")

                # Add margin
                margin = 20
                x_orig, y_orig, w_orig, h_orig = x, y, w, h
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(img.shape[1] - x, w + 2*margin)
                h = min(img.shape[0] - y, h + 2*margin)

                logger.info(f"  - Added {margin}px margin around document")
                logger.info(f"  - Final crop region: x={x}, y={y}, w={w}, h={h}")

                cropped = img[y:y+h, x:x+w]
                detection_method = "contour-based"

            crop_height, crop_width = cropped.shape[:2]
            size_reduction = (1 - (crop_width * crop_height) / (width * height)) * 100
            logger.info(f"✓ Image cropped successfully")
            logger.info(f"  - New dimensions: {crop_width}x{crop_height} pixels")
            logger.info(f"  - Size reduction: {size_reduction:.1f}%")
            logger.info(f"  - Detection method: {detection_method}")

            # Enhance contrast using CLAHE
            logger.info("🔄 Enhancing contrast with CLAHE (Contrast Limited Adaptive Histogram Equalization)...")
            lab = cv2.cvtColor(cropped, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            logger.info("  - Contrast enhancement applied")

            # Save to temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='ocr_preprocessed_')
            os.close(temp_fd)  # Close the file descriptor

            logger.info(f"💾 Saving preprocessed image...")
            cv2.imwrite(temp_path, enhanced)

            # Get file size
            file_size = os.path.getsize(temp_path)
            logger.info(f"✓ Preprocessed image saved successfully")
            logger.info(f"  - Path: {temp_path}")
            logger.info(f"  - File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

            logger.info("="*80)
            logger.info("IMAGE PREPROCESSING COMPLETED SUCCESSFULLY")
            logger.info("="*80)

            return temp_path

        except Exception as e:
            logger.error("="*80)
            logger.error(f"❌ Image preprocessing failed: {str(e)}")
            logger.error("="*80)
            import traceback
            logger.debug(traceback.format_exc())
            # Return original image path on error
            return image_path

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None, job_id=None):
        """Process image using LangChain with Ollama vision model"""
        if not self.is_available():
            raise Exception("LangChain provider is not available")

        preprocessed_path = None
        intermediate_images = {}

        try:
            from app.services.langchain_service import get_langchain_service
            from app.services.image_optimizer import ImageOptimizer
            from PIL import Image
            import logging
            logger = logging.getLogger(__name__)

            # Check if input is a PDF file
            if image_path.lower().endswith('.pdf'):
                return self._process_pdf(image_path, languages, handwriting, custom_prompt)

            # Preprocess image: detect document, crop, and enhance
            logger.info("Preprocessing image to detect and crop document...")
            preprocessed_path = self._preprocess_image(image_path)

            # Store preprocessed image if it's different from original
            if preprocessed_path and preprocessed_path != image_path:
                try:
                    from app.services.image_storage_service import ImageStorageService
                    from app.models import mongo

                    image_storage = ImageStorageService(mongo)
                    file_id = image_storage.store_image(
                        preprocessed_path,
                        metadata={
                            'job_id': job_id,
                            'original_file': os.path.basename(image_path),
                            'processing_stage': 'preprocessed',
                            'description': 'Document detected, cropped, and contrast enhanced'
                        }
                    )

                    if file_id:
                        intermediate_images['preprocessed'] = {
                            'file_id': file_id,
                            'url': image_storage.get_image_url(file_id, absolute=True),
                            'description': 'Preprocessed image (cropped and enhanced)'
                        }
                        logger.info(f"Stored preprocessed image with ID: {file_id}")
                except Exception as e:
                    logger.warning(f"Failed to store preprocessed image: {e}")

            # Use preprocessed image for OCR
            image_to_process = preprocessed_path if preprocessed_path != image_path else image_path
            logger.info(f"Using image for OCR: {image_to_process}")

            # Load and optimize image
            img = Image.open(image_to_process)

            # Optimize and encode image
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

            # Get LangChain service for configuration
            service = get_langchain_service()

            # Use Ollama's proper multimodal API instead of embedding image in text
            # This prevents the massive token truncation issue
            payload = {
                "model": service.model,
                "prompt": prompt,
                "images": [image_data],  # Proper multimodal input
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for accurate OCR
                    "num_predict": 4096,  # Allow longer responses
                    "num_ctx": 8192  # Increased context window
                }
            }

            response = requests.post(
                f"{service.ollama_host}/api/generate",
                json=payload,
                timeout=600
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

            result = response.json()
            extracted_text = result.get('response', '').strip()

            # Format response to match expected structure
            result_data = {
                'text': extracted_text,
                'full_text': extracted_text,
                'words': [],
                'blocks': [{'text': extracted_text}] if extracted_text else [],
                'confidence': 0.95,
                'intermediate_images': intermediate_images if intermediate_images else None
            }

            return result_data

        except Exception as e:
            raise Exception(f"LangChain OCR processing failed: {str(e)}")
        finally:
            # Clean up temporary preprocessed image
            if preprocessed_path and preprocessed_path != image_path:
                try:
                    if os.path.exists(preprocessed_path):
                        os.remove(preprocessed_path)
                        logger.info(f"Cleaned up temporary file: {preprocessed_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {preprocessed_path}: {e}")

    def _process_pdf(self, pdf_path, languages=None, handwriting=False, custom_prompt=None):
        """
        Process PDF with hybrid approach:
        1. First, try to extract embedded text (if PDF has text)
        2. If PDF is scanned (no extractable text), use OCR with Gemma3
        3. Return combined results with metadata
        """
        from app.services.pdf_service import PDFService
        from app.services.image_optimizer import ImageOptimizer
        from app.services.langchain_service import get_langchain_service
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Step 1: Check if PDF has embedded text
            logger.info(f"Processing PDF with hybrid mode: {pdf_path}")
            embedded_text = self._extract_embedded_text(pdf_path)
            has_embedded_text = bool(embedded_text and any(embedded_text.values()))

            logger.info(f"PDF has embedded text: {has_embedded_text}")

            if has_embedded_text:
                # PDF has text - return extracted text with metadata
                logger.info("Using embedded text extraction")
                return self._process_pdf_with_embedded_text(pdf_path, embedded_text)
            else:
                # PDF is scanned - use OCR with LangChain
                logger.info("PDF is scanned - using Gemma3 OCR")
                return self._process_pdf_with_ocr(pdf_path, languages, handwriting, custom_prompt)

        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            if "PDF2Image library not available" in str(e):
                raise Exception(f"Cannot process PDF: {str(e)}")
            raise

    def _extract_embedded_text(self, pdf_path):
        """
        Extract embedded text from PDF using PyPDF2
        Returns dict with page_num as key and extracted text as value
        """
        import logging
        logger = logging.getLogger(__name__)

        if not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available - cannot extract embedded text")
            return {}

        try:
            reader = PdfReader(pdf_path)
            extracted = {}

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    extracted[page_num] = text.strip()

            logger.info(f"Extracted embedded text from {len(extracted)}/{len(reader.pages)} pages")
            return extracted

        except Exception as e:
            logger.warning(f"Failed to extract embedded text: {str(e)}")
            return {}

    def _process_pdf_with_embedded_text(self, pdf_path, embedded_text):
        """Process PDF that has embedded text (no OCR needed)"""
        from app.services.pdf_service import PDFService

        try:
            # Get metadata
            metadata = PDFService.extract_pdf_metadata(pdf_path)

            # Combine text from all pages
            all_text = []
            all_blocks = []

            for page_num in sorted(embedded_text.keys()):
                page_text = embedded_text[page_num]
                all_text.append(f"--- Page {page_num} ---\n{page_text}")
                all_blocks.append({
                    'text': page_text,
                    'page': page_num,
                    'source': 'embedded'
                })

            combined_text = '\n\n'.join(all_text)

            return {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.99,
                'pages_processed': len(embedded_text),
                'processing_method': 'embedded_text_extraction',
                'metadata': metadata
            }
        except Exception as e:
            raise Exception(f"Failed to process PDF with embedded text: {str(e)}")

    def _process_pdf_with_ocr(self, pdf_path, languages=None, handwriting=False, custom_prompt=None):
        """Process scanned PDF using OCR with LangChain/Gemma3"""
        from app.services.pdf_service import PDFService
        from app.services.image_optimizer import ImageOptimizer
        from app.services.langchain_service import get_langchain_service
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Get metadata
            metadata = PDFService.extract_pdf_metadata(pdf_path)

            # Convert PDF pages to PIL Image objects
            page_images = PDFService.pdf_to_images(
                pdf_path,
                handwriting=handwriting
            )

            if not page_images:
                raise Exception("No pages found in PDF")

            # Process each page with OCR
            all_text = []
            all_blocks = []
            service = get_langchain_service()

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
                    prompt = f"[Page {page_num}/{len(page_images)}] {prompt}"

                # Use Ollama's proper multimodal API instead of embedding image in text
                payload = {
                    "model": service.model,
                    "prompt": prompt,
                    "images": [image_data],  # Proper multimodal input
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Lower temperature for accurate OCR
                        "num_predict": 4096,  # Allow longer responses
                        "num_ctx": 8192  # Increased context window
                    }
                }

                response = requests.post(
                    f"{service.ollama_host}/api/generate",
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
                        'page': page_num,
                        'source': 'ocr'
                    })

            # Combine all pages
            combined_text = '\n\n'.join(all_text)

            return {
                'text': combined_text,
                'full_text': combined_text,
                'words': [],
                'blocks': all_blocks,
                'confidence': 0.95,
                'pages_processed': len(page_images),
                'processing_method': 'ocr_gemma3',
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise Exception(f"Failed to process PDF with OCR: {str(e)}")

    def _build_prompt(self, languages, handwriting):
        """Build appropriate prompt for OCR task"""
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

            # Special handling for Indian languages
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
