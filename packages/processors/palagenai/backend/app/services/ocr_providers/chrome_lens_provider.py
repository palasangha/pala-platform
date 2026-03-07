"""
Chrome Lens Provider for OCR using chrome-lens-py
Supports both typed and handwritten text extraction from images and PDFs
"""
import os
import re
import json
import base64
import asyncio
import io
from datetime import datetime
from pathlib import Path
from PIL import Image
from .base_provider import BaseOCRProvider
from ..pdf_service import PDFService

try:
    from chrome_lens_py import LensAPI
except ImportError:
    LensAPI = None


class ChromeLensProvider(BaseOCRProvider):
    """
    Google Chrome Lens OCR Provider using chrome-lens-py library
    Provides local access to Google Lens without API keys or rate limits
    """

    def __init__(self):
        """Initialize Chrome Lens provider"""
        from app.config import Config

        enabled = os.getenv('CHROME_LENS_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            self.max_image_size_mb = 5
            print("Chrome Lens provider is disabled")
            return

        # Check if LensAPI package is available
        if LensAPI is None:
            self._available = False
            self.max_image_size_mb = 5
            print("⚠ chrome-lens-py package not installed. Install with: pip install chrome-lens-py")
            return

        # Just check availability; will initialize LensAPI per request
        self._available = True
        self.max_image_size_mb = Config.GOOGLE_LENS_MAX_IMAGE_SIZE_MB
        print("✓ Chrome Lens provider initialized successfully")

    def get_name(self):
        """Get provider name"""
        return "chrome_lens"

    def is_available(self):
        """Check if provider is available"""
        return self._available

    def _resize_image_if_needed(self, image_path, max_size_mb=5):
        """
        Resize image if file size or dimensions exceed threshold and save to temporary file

        Args:
            image_path: Path to the image file
            max_size_mb: Maximum file size in MB before resizing (default: 5MB)

        Returns:
            str: Path to the image (original or resized temporary file)
        """
        try:
            # Disable PIL decompression bomb limit to handle large scanned images
            # This must be set BEFORE opening the image
            Image.MAX_IMAGE_PIXELS = None

            # First check pixel dimensions to avoid decompression bomb errors
            img = Image.open(image_path)
            width, height = img.size
            total_pixels = width * height

            # Check file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

            # Resize if either:
            # 1. File size exceeds threshold
            # 2. Image dimensions are very large (>150 million pixels)
            max_pixels = 150_000_000  # ~12,200 x 12,200 pixels
            needs_resize = file_size_mb > max_size_mb or total_pixels > max_pixels

            if not needs_resize:
                img.close()
                return image_path

            # File is too large or has too many pixels, resize it
            if file_size_mb > max_size_mb:
                print(f"Image size ({file_size_mb:.2f}MB) exceeds {max_size_mb}MB threshold, resizing...")
            elif total_pixels > max_pixels:
                print(f"Image dimensions ({width}x{height} = {total_pixels:,} pixels) exceed limit, resizing...")

            # Image is already opened above at line 78
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

            # Create temporary file for resized image
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)

            # Start with high quality and reduce if needed
            quality = 85
            img.save(temp_path, format='JPEG', quality=quality, optimize=True)

            # If still too large, reduce quality further
            while os.path.getsize(temp_path) / (1024 * 1024) > target_size_mb and quality > 50:
                quality -= 10
                img.save(temp_path, format='JPEG', quality=quality, optimize=True)

            final_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            print(f"Image resized from {file_size_mb:.2f}MB to {final_size_mb:.2f}MB (quality: {quality})")

            return temp_path

        except Exception as e:
            print(f"Warning: Failed to resize image, using original: {str(e)}")
            # Fallback to original if resize fails
            return image_path

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """
        Process image or PDF using Chrome Lens
        
        Args:
            image_path: Path to image or PDF file
            languages: List of language codes (e.g., ['en', 'hi'])
            handwriting: Boolean for handwriting detection
            custom_prompt: Optional custom prompt (ignored for Chrome Lens)
        
        Returns:
            dict: OCR results with text and metadata
        """
        # Initialize cleanup variables before try block to ensure they're always defined
        temp_image_paths = []
        resized_image_paths = []
        
        if not self.is_available():
            raise Exception("Chrome Lens provider is not available")
        
        try:
            # Prepare languages list
            if not languages:
                languages = ['en', 'hi']  # Default: English and Hindi
            
            # Check if file exists
            if not os.path.exists(image_path):
                raise Exception(f"Image file not found: {image_path}")
            
            # Check if PDF and convert to images if necessary
            image_paths_to_process = []

            if PDFService.is_pdf(image_path):
                try:
                    temp_image_paths = PDFService.pdf_to_temp_images(image_path, dpi=150)
                    image_paths_to_process = temp_image_paths
                except Exception as pdf_error:
                    raise Exception(f"Failed to convert PDF to images: {str(pdf_error)}")
            else:
                image_paths_to_process = [image_path]

            # Process each page/image
            all_results = {
                'text': '',
                'full_text': '',
                'blocks': [],
                'words': [],
                'confidence': 0.0,
                'detected_language': 'en',
                'handwriting_detected': False,
                'pages_processed': len(image_paths_to_process),
                'raw_response': []
            }

            page_texts = []
            all_blocks = []
            all_words_dict = {}  # Using dict to avoid duplicates

            for page_idx, img_path in enumerate(image_paths_to_process):
                try:
                    # Resize image if needed (configurable threshold, default 5MB)
                    processed_img_path = self._resize_image_if_needed(img_path, max_size_mb=self.max_image_size_mb)

                    # Track resized temp files for cleanup
                    if processed_img_path != img_path:
                        resized_image_paths.append(processed_img_path)

                    # Process image with Chrome Lens (async)
                    result = asyncio.run(self._process_with_chrome_lens_async(processed_img_path, languages, handwriting))
                    
                    # Aggregate results
                    page_text = result.get('text', '')
                    page_texts.append(f"--- Page {page_idx + 1} ---\n{page_text}")
                    
                    all_blocks.extend(result.get('blocks', []))
                    
                    # Add words to dict to track unique words
                    for word in result.get('words', []):
                        word_text = word.get('text', '').lower()
                        if word_text not in all_words_dict:
                            all_words_dict[word_text] = word
                    
                    if result.get('handwriting_detected'):
                        all_results['handwriting_detected'] = True
                    
                    all_results['raw_response'].append(result.get('raw_response'))
                    
                except Exception as e:
                    # Log error but continue processing other pages
                    print(f"Warning: Failed to process page {page_idx + 1}: {str(e)}")
                    page_texts.append(f"--- Page {page_idx + 1} (Error) ---\n[Failed to process: {str(e)}]")
            
            # Combine results from all pages
            all_results['text'] = '\n\n'.join(page_texts)
            all_results['full_text'] = all_results['text']
            all_results['blocks'] = all_blocks
            all_results['words'] = list(all_words_dict.values())[:100]  # Limit to 100 unique words
            
            if page_texts:
                all_results['confidence'] = 0.85
                all_results['detected_language'] = self._detect_language_from_text(all_results['text'], languages)
            
            # Add metadata
            all_results['metadata'] = self._extract_metadata(all_results.get('text', ''), image_path)
            all_results['file_info'] = {
                'filename': os.path.basename(image_path),
                'is_pdf': PDFService.is_pdf(image_path),
                'pages_processed': len(image_paths_to_process),
                'processed_at': datetime.now().isoformat(),
                'handwriting_detected': handwriting or all_results.get('handwriting_detected', False)
            }
            all_results['supported_languages'] = languages
            
            return all_results
            
        except Exception as e:
            raise Exception(f"Chrome Lens processing failed: {str(e)}")
        finally:
            # Cleanup temporary image files from PDF conversion
            if temp_image_paths:
                PDFService.cleanup_temp_images(temp_image_paths)

            # Cleanup resized temporary image files
            if resized_image_paths:
                for resized_path in resized_image_paths:
                    try:
                        if os.path.exists(resized_path):
                            os.remove(resized_path)
                    except Exception as cleanup_error:
                        print(f"Warning: Failed to cleanup resized temp file {resized_path}: {cleanup_error}")

    async def _process_with_chrome_lens_async(self, image_path, languages, handwriting):
        """
        Process image using Chrome Lens library (async)
        
        Args:
            image_path: Path to image file
            languages: List of language codes
            handwriting: Boolean for handwriting detection
        
        Returns:
            dict: Extracted text and metadata
        """
        try:
            if LensAPI is None:
                raise ImportError("chrome-lens-py package not installed")
            
            # Initialize LensAPI and process image
            api = LensAPI()
            result = await api.process_image(image_path)
            
            if not result:
                raise Exception("Chrome Lens returned empty result")
            
            # Extract text from word_data
            extracted_text = self._extract_text_from_lens_result(result)
            
            if not extracted_text or extracted_text.strip() == '':
                raise Exception("Chrome Lens extracted no text - image may not contain readable text")
            
            # Detect language from results
            detected_language = self._detect_language_from_text(extracted_text, languages)
            
            # Detect handwriting
            handwriting_detected = self._detect_handwriting_from_text(extracted_text)
            
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'blocks': self._structure_text_blocks(extracted_text),
                'words': self._extract_words(extracted_text),
                'confidence': 0.9,
                'detected_language': detected_language,
                'handwriting_detected': handwriting_detected or handwriting,
                'raw_response': result
            }
            
        except Exception as e:
            raise Exception(f"Chrome Lens request failed: {str(e)}")

    def _extract_text_from_lens_result(self, result):
        """
        Extract text from Chrome Lens API result
        
        Args:
            result: Result dict from LensAPI.process_image()
        
        Returns:
            str: Extracted text
        """
        if not isinstance(result, dict):
            return ''
        
        # Extract words from word_data array
        word_data = result.get('word_data', [])
        if not word_data:
            return ''
        
        # Group words by lines (using y position)
        lines = {}
        for item in word_data:
            if isinstance(item, dict) and 'word' in item:
                word = item['word']
                geometry = item.get('geometry', {})
                
                # Use center_y to group words into lines
                y_pos = geometry.get('center_y', 0)
                # Round to nearest line (0.01 tolerance)
                line_key = round(y_pos * 100) / 100
                
                if line_key not in lines:
                    lines[line_key] = []
                
                lines[line_key].append(word)
        
        # Sort by y position and join words
        sorted_lines = sorted(lines.items())
        text_lines = [' '.join(words) for _, words in sorted_lines]
        
        return '\n'.join(text_lines) if text_lines else ''

    def _structure_text_blocks(self, text):
        """Structure text into blocks (paragraphs)"""
        blocks = []
        
        # Split by double newlines or significant whitespace
        paragraphs = re.split(r'\n\n+', text)
        
        for para in paragraphs:
            cleaned = para.strip()
            if cleaned:
                blocks.append({
                    'text': cleaned,
                    'confidence': 0.85,
                    'language': self._detect_language_from_text(cleaned, ['en', 'hi'])
                })
        
        return blocks

    def _extract_words(self, text):
        """Extract individual words with confidence scores"""
        words = []
        
        # Split text into words
        word_list = re.findall(r'\b\w+\b', text, re.UNICODE)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in word_list:
            if word.lower() not in seen:
                seen.add(word.lower())
                unique_words.append(word)
        
        for word in unique_words[:100]:  # Limit to first 100 unique words
            words.append({
                'text': word,
                'confidence': 0.85
            })
        
        return words

    def _detect_language_from_text(self, text, supported_languages):
        """
        Detect language from extracted text
        
        Args:
            text: Extracted text
            supported_languages: List of supported language codes
        
        Returns:
            str: Detected language code
        """
        if not text:
            return supported_languages[0] if supported_languages else 'en'
        
        # Hindi character ranges
        hindi_chars = re.compile(
            r'[\u0900-\u097F]+'  # Devanagari script
        )
        
        # Count script occurrences
        hindi_matches = len(hindi_chars.findall(text))
        total_chars = len(text)
        
        if hindi_matches > total_chars * 0.3:  # More than 30% Hindi
            return 'hi'
        elif hindi_matches > 0:
            return 'en-hi'  # Mixed languages
        else:
            return 'en'  # English

    def _detect_handwriting_from_text(self, text):
        """
        Detect if text might be handwritten based on content
        
        Args:
            text: Extracted text
        
        Returns:
            bool: True if text appears to be handwritten
        """
        # Keywords that might indicate handwriting
        handwriting_keywords = [
            'handwritten', 'handwriting', 'written by hand', 'cursive',
            'scrawl', 'script', 'manuscript', 'penned'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in handwriting_keywords)

    def _extract_metadata(self, text, image_path):
        """
        Extract metadata from document text
        
        Args:
            text: Extracted text
            image_path: Path to image file
        
        Returns:
            dict: Extracted metadata
        """
        metadata = {
            'sender': self._extract_sender_info(text),
            'recipient': self._extract_recipient_info(text),
            'date': self._extract_date_info(text),
            'document_type': self._detect_document_type(text),
            'key_fields': self._extract_key_fields(text),
            'language': self._detect_language_from_text(text, ['en', 'hi']),
            'hinglish_content': self._detect_hinglish(text)
        }
        return metadata

    def _extract_sender_info(self, text):
        """Extract sender information"""
        sender_info = {
            'name': None,
            'address': None,
            'email': None,
            'phone': None
        }
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            sender_info['email'] = emails[0]
        
        # Phone patterns (Indian: +91, 10 digits, etc.)
        phone_patterns = [
            r'(?:\+91[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3,4})[-.\s]?(\d{4})',  # Indian
            r'(?:\+\d{1,3}[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',  # General
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                sender_info['phone'] = phones[0]
                break
        
        # Name from first few lines
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) > 3 and not any(x in line.lower() for x in ['@', 'http', 'www']):
                sender_info['name'] = line
                break
        
        return sender_info

    def _extract_recipient_info(self, text):
        """Extract recipient information"""
        recipient_info = {
            'name': None,
            'address': None,
            'email': None,
            'phone': None
        }
        
        lines = text.split('\n')
        
        # Look for "To:", "Recipient:", "Dear" patterns
        for i, line in enumerate(lines):
            lower_line = line.lower()
            if any(x in lower_line for x in ['to:', 'recipient:', 'dear', 'addressed to', 'को']):  # को is Hindi 'to'
                if i + 1 < len(lines):
                    recipient_info['name'] = lines[i + 1].strip()
                    if i + 2 < len(lines):
                        recipient_info['address'] = lines[i + 2].strip()
                break
        
        return recipient_info

    def _extract_date_info(self, text):
        """Extract date information"""
        # Multiple date patterns for English and Indian formats
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

    def _detect_document_type(self, text):
        """Detect document type"""
        text_lower = text.lower()
        
        document_types = {
            'letter': ['dear', 'sincerely', 'regards', 'yours', 'letter', 'खत', 'पत्र'],
            'invoice': ['invoice', 'bill', 'amount due', 'payment', 'total', 'bill no', 'बिल', 'चालान'],
            'receipt': ['receipt', 'thank you', 'received', 'payment received', 'रसीद'],
            'form': ['application', 'form', 'please fill', 'फॉर्म', 'आवेदन'],
            'contract': ['agreement', 'contract', 'terms', 'party', 'करार', 'संविदा'],
            'email': ['from:', 'to:', 'subject:', 'cc:', 'इमेल'],
        }
        
        for doc_type, keywords in document_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return 'document'

    def _extract_key_fields(self, text):
        """Extract key fields from document"""
        key_fields = {}
        
        patterns = {
            'reference': r'(?:ref|reference|ref\s*#|reference\s*#|संदर्भ)[:\s]+([^\n]+)',
            'subject': r'(?:subject|re|विषय)[:\s]+([^\n]+)',
            'invoice_number': r'(?:invoice|invoice\s*#|bill|bill\s*#|बिल)[:\s]+([^\n]+)',
            'amount': r'(?:amount|total|total\s*amount|राशि)[:\s]+([^\n]+)',
            'due_date': r'(?:due|due\s*date|देय)[:\s]+([^\n]+)',
        }
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if match:
                key_fields[field_name] = match.group(1).strip()
        
        return key_fields

    def _detect_hinglish(self, text):
        """Detect if text is Hinglish (Hindi + English mix)"""
        hindi_chars = re.findall(r'[\u0900-\u097F]+', text)
        english_words = re.findall(r'[a-zA-Z]+', text)
        
        has_hindi = len(hindi_chars) > 0
        has_english = len(english_words) > 0
        
        return {
            'is_hinglish': has_hindi and has_english,
            'hindi_content_ratio': len(hindi_chars) / len(text) if text else 0,
            'english_content_ratio': len(english_words) / len(text) if text else 0
        }

