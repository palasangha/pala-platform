"""Google Lens Provider for OCR and metadata extraction from documents/letters"""
from google.cloud import vision
import io
import os
import re
from datetime import datetime
from PIL import Image
from .base_provider import BaseOCRProvider


class GoogleLensProvider(BaseOCRProvider):
    """Google Lens OCR Provider with metadata extraction from letters and documents"""

    def __init__(self):
        """Initialize Google Cloud Vision client for Lens capabilities"""
        from app.config import Config

        enabled = os.getenv('GOOGLE_LENS_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.client = None
            self.max_image_size_mb = 5
            print("Google Lens provider is disabled via GOOGLE_LENS_ENABLED environment variable")
            return

        try:
            self.client = vision.ImageAnnotatorClient()
            self.max_image_size_mb = Config.GOOGLE_LENS_MAX_IMAGE_SIZE_MB
            self._available = True
        except Exception as e:
            print(f"Google Lens initialization failed: {e}")
            self.client = None
            self.max_image_size_mb = 5
            self._available = False

    def get_name(self):
        return "google_lens"

    def is_available(self):
        return self._available and self.client is not None

    def _resize_image_if_needed(self, image_path, max_size_mb=5):
        """
        Resize image if file size exceeds threshold

        Args:
            image_path: Path to the image file
            max_size_mb: Maximum file size in MB before resizing (default: 5MB)

        Returns:
            bytes: Image content (resized if needed)
        """
        # Check file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

        # If file size is under threshold, just read and return
        if file_size_mb <= max_size_mb:
            with io.open(image_path, 'rb') as image_file:
                return image_file.read()

        # File is too large, resize it
        print(f"Image size ({file_size_mb:.2f}MB) exceeds {max_size_mb}MB threshold, resizing...")

        try:
            # Increase PIL decompression bomb limit for large images
            Image.MAX_IMAGE_PIXELS = None  # Disable limit temporarily

            # Open image with PIL
            img = Image.open(image_path)

            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                img = background
            elif img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Calculate resize ratio based on file size
            # Target size is 80% of max_size_mb to ensure we stay under threshold
            target_size_mb = max_size_mb * 0.8
            size_ratio = target_size_mb / file_size_mb
            scale_factor = size_ratio ** 0.5  # Square root because area scales quadratically

            # Resize image
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to bytes buffer as JPEG
            buffer = io.BytesIO()

            # Start with high quality and reduce if needed
            quality = 85
            img.save(buffer, format='JPEG', quality=quality, optimize=True)

            # If still too large, reduce quality further
            while buffer.tell() / (1024 * 1024) > target_size_mb and quality > 50:
                buffer.seek(0)
                buffer.truncate()
                quality -= 10
                img.save(buffer, format='JPEG', quality=quality, optimize=True)

            final_size_mb = buffer.tell() / (1024 * 1024)
            print(f"Image resized from {file_size_mb:.2f}MB to {final_size_mb:.2f}MB (quality: {quality})")

            return buffer.getvalue()

        except Exception as e:
            print(f"Warning: Failed to resize image, using original: {str(e)}")
            # Fallback to original if resize fails
            with io.open(image_path, 'rb') as image_file:
                return image_file.read()

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """
        Process image using Google Lens-like capabilities (Vision API)
        Extracts text and metadata from letters/documents
        """
        if not self.is_available():
            raise Exception("Google Lens provider is not available")

        try:
            # Resize image if needed (configurable threshold, default 5MB)
            content = self._resize_image_if_needed(image_path, max_size_mb=self.max_image_size_mb)

            image = vision.Image(content=content)

            # Use batch_annotate_images for proper API response
            request = vision.BatchAnnotateImagesRequest(
                requests=[
                    {
                        'image': image,
                        'features': [
                            {
                                'type_': vision.Feature.Type.DOCUMENT_TEXT_DETECTION,
                                'max_results': 100
                            },
                            {
                                'type_': vision.Feature.Type.OBJECT_LOCALIZATION,
                                'max_results': 50
                            }
                        ]
                    }
                ]
            )

            response = self.client.batch_annotate_images(request=request)
            print(response)
            
            # Get the first response from the batch
            if not response.responses:
                raise Exception("No response from Vision API")
            
            image_response = response.responses[0]

            # Extract text and blocks
            text_result = self._extract_text_with_structure(image_response)

            # Extract metadata
            metadata = self._extract_metadata(image_response, image_path)

            # Combine results
            return {
                'text': text_result['full_text'],
                'full_text': text_result['full_text'],
                'words': text_result['words'],
                'blocks': text_result['blocks'],
                'confidence': text_result['confidence'],
                'metadata': metadata
            }

        except Exception as e:
            raise Exception(f"Google Lens OCR processing failed: {str(e)}")

    def _extract_text_with_structure(self, response):
        """Extract text with structural information (blocks, paragraphs, words)"""
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")

        # Use document text detection for better structure
        full_text = ''
        blocks = []
        words = []
        total_confidence = 0
        word_count = 0

        if response.full_text_annotation:
            full_text = response.full_text_annotation.text

            # Extract blocks with confidence scores
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ''
                    block_confidence = 0
                    block_word_count = 0
                    block_bounds = None

                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            block_text += word_text + ' '
                            block_confidence += word.confidence
                            block_word_count += 1
                            word_count += 1
                            total_confidence += word.confidence

                            # Track word bounds
                            if word.bounding_box and word.bounding_box.vertices:
                                words.append({
                                    'text': word_text,
                                    'confidence': word.confidence,
                                    'bounds': self._get_bounds_from_vertices(word.bounding_box.vertices)
                                })

                            # Get first block bounds
                            if block_bounds is None and word.bounding_box and word.bounding_box.vertices:
                                block_bounds = self._get_bounds_from_vertices(word.bounding_box.vertices)

                    if block_text.strip():
                        avg_block_confidence = block_confidence / block_word_count if block_word_count > 0 else 0
                        blocks.append({
                            'text': block_text.strip(),
                            'confidence': avg_block_confidence,
                            'bounds': block_bounds
                        })

        avg_confidence = total_confidence / word_count if word_count > 0 else 0

        return {
            'full_text': full_text,
            'blocks': blocks,
            'words': words,
            'confidence': avg_confidence
        }

    def _extract_metadata(self, response, image_path):
        """
        Extract metadata from the document/letter:
        - Sender information
        - Recipient information
        - Date
        - Document type
        - Key fields
        """
        metadata = {
            'sender': self._extract_sender_info(response),
            'recipient': self._extract_recipient_info(response),
            'date': self._extract_date_info(response),
            'document_type': self._detect_document_type(response),
            'key_fields': self._extract_key_fields(response),
            'language': self._detect_language(response),
            'file_info': {
                'filename': os.path.basename(image_path),
                'processed_at': datetime.now().isoformat()
            }
        }
        return metadata

    def _extract_sender_info(self, response):
        """Extract sender information from the document"""
        sender_info = {
            'name': None,
            'address': None,
            'email': None,
            'phone': None
        }

        if not response.full_text_annotation:
            return sender_info

        text = response.full_text_annotation.text.lower()
        lines = response.full_text_annotation.text.split('\n')

        # Look for email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.full_text_annotation.text)
        if emails:
            sender_info['email'] = emails[0]

        # Look for phone numbers
        phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})'
        phones = re.findall(phone_pattern, response.full_text_annotation.text)
        if phones:
            sender_info['phone'] = phones[0]

        # First few lines likely contain sender name/address
        if len(lines) > 0:
            # First non-empty line could be sender name
            for line in lines[:5]:
                if line.strip() and len(line.strip()) > 3:
                    if sender_info['name'] is None:
                        sender_info['name'] = line.strip()
                        break

        return sender_info

    def _extract_recipient_info(self, response):
        """Extract recipient information from the document"""
        recipient_info = {
            'name': None,
            'address': None,
            'email': None,
            'phone': None
        }

        if not response.full_text_annotation:
            return recipient_info

        text = response.full_text_annotation.text
        lines = text.split('\n')

        # Look for "To:" or "Recipient:" patterns
        for i, line in enumerate(lines):
            lower_line = line.lower()
            if 'to:' in lower_line or 'recipient:' in lower_line or 'dear' in lower_line:
                # Next line likely contains recipient info
                if i + 1 < len(lines):
                    recipient_info['name'] = lines[i + 1].strip()
                    # Try to get address from next line
                    if i + 2 < len(lines):
                        recipient_info['address'] = lines[i + 2].strip()
                break

        return recipient_info

    def _extract_date_info(self, response):
        """Extract date information from the document"""
        if not response.full_text_annotation:
            return None

        text = response.full_text_annotation.text

        # Common date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]

        return None

    def _detect_document_type(self, response):
        """Detect the type of document (letter, invoice, form, etc.)"""
        if not response.full_text_annotation:
            return 'unknown'

        text = response.full_text_annotation.text.lower()

        # Keywords for different document types
        document_type_keywords = {
            'letter': ['dear', 'sincerely', 'regards', 'truly yours', 'yours faithfully'],
            'invoice': ['invoice', 'bill', 'amount due', 'payment', 'total', 'invoice #'],
            'receipt': ['receipt', 'payment received', 'thank you', 'receipt #'],
            'form': ['please fill', 'form', 'application', 'questionnaire'],
            'contract': ['agreement', 'contract', 'terms and conditions', 'party', 'hereinafter'],
            'email': ['from:', 'to:', 'subject:', 'cc:', 'bcc:'],
        }

        for doc_type, keywords in document_type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return doc_type

        return 'document'

    def _extract_key_fields(self, response):
        """Extract common key fields from documents"""
        key_fields = {}

        if not response.full_text_annotation:
            return key_fields

        text = response.full_text_annotation.text
        lines = text.split('\n')

        # Look for common field patterns
        field_patterns = {
            'reference': r'(?:ref|reference|ref\s*#|reference\s*#)[:\s]+([^\n]+)',
            'subject': r'(?:subject|re)[:\s]+([^\n]+)',
            'invoice_number': r'(?:invoice|invoice\s*#)[:\s]+([^\n]+)',
            'amount': r'(?:amount|total|total\s*amount)[:\s]+([^\n]+)',
            'due_date': r'(?:due|due\s*date)[:\s]+([^\n]+)',
        }

        for field_name, pattern in field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                key_fields[field_name] = match.group(1).strip()

        return key_fields

    def _detect_language(self, response):
        """Detect the language of the document"""
        if response.text_annotations:
            # Get the detected language from the first text annotation
            for annotation in response.text_annotations:
                if hasattr(annotation, 'locale') and annotation.locale:
                    return annotation.locale
        return 'en'  # Default to English

    def _get_bounds_from_vertices(self, vertices):
        """Convert vertices to bounds dictionary"""
        if not vertices or len(vertices) < 4:
            return {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}

        x_coords = [v.x for v in vertices]
        y_coords = [v.y for v in vertices]

        return {
            'x1': min(x_coords),
            'y1': min(y_coords),
            'x2': max(x_coords),
            'y2': max(y_coords)
        }
