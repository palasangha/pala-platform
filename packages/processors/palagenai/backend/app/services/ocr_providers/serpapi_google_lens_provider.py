"""
SerpAPI Google Lens Provider for OCR with Hindi and English support
Supports both typed and handwritten text extraction from letters/documents
"""
import os
import re
import json
import base64
import io
from datetime import datetime
from pathlib import Path
from .base_provider import BaseOCRProvider

try:
    from google_search_results import GoogleSearch
except ImportError:
    GoogleSearch = None


class SerpAPIGoogleLensProvider(BaseOCRProvider):
    """
    Google Lens OCR Provider using SerpAPI with enhanced support for:
    - Hindi and English text extraction
    - Handwritten and typed text recognition
    - Metadata extraction from letters and documents
    """

    def __init__(self):
        """Initialize SerpAPI Google Lens provider"""
        self.api_key = os.getenv('SERPAPI_API_KEY')
        self.use_local_processing = os.getenv('USE_LOCAL_LENS_PROCESSING', 'false').lower() in ('true', '1', 'yes')
        
        enabled = os.getenv('SERPAPI_GOOGLE_LENS_ENABLED', 'true').lower() in ('true', '1', 'yes')
        
        if not enabled:
            self._available = False
            print("SerpAPI Google Lens provider is disabled")
            return
        
        # Check if GoogleSearch package is available
        if GoogleSearch is None:
            self._available = False
            print("⚠ google-search-results package not installed. Install with: pip install google-search-results")
            return
        
        # If API key is available, use SerpAPI
        if self.api_key:
            self._available = True
            self.api_endpoint = "https://serpapi.com"
            print("✓ SerpAPI Google Lens provider initialized with API key")
        else:
            self._available = False
            print("⚠ No SERPAPI_API_KEY found. Please set SERPAPI_API_KEY environment variable")

    def get_name(self):
        """Get provider name"""
        return "serpapi_google_lens"

    def is_available(self):
        """Check if provider is available"""
        return self._available

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """
        Process image using Google Lens via SerpAPI
        
        Args:
            image_path: Path to image file
            languages: List of language codes (e.g., ['en', 'hi', 'en-hi'])
            handwriting: Boolean for handwriting detection
            custom_prompt: Optional custom prompt for text extraction
        
        Returns:
            dict: OCR results with text, metadata, and language info
        """
        if not self.is_available():
            raise Exception("SerpAPI Google Lens provider is not available")
        
        try:
            # Prepare languages list
            if not languages:
                languages = ['en', 'hi']  # Default: English and Hindi
            
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine image type
            file_ext = Path(image_path).suffix.lower()
            image_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            image_type = image_type_map.get(file_ext, 'image/jpeg')
            
            # Process with SerpAPI
            result = self._process_with_serpapi(image_data, image_type, languages, handwriting, image_path)
            
            # Extract and structure results
            result['metadata'] = self._extract_metadata(result.get('extracted_text', ''), image_path)
            result['file_info'] = {
                'filename': os.path.basename(image_path),
                'processed_at': datetime.now().isoformat(),
                'handwriting_detected': handwriting or result.get('handwriting_detected', False)
            }
            result['supported_languages'] = languages
            
            return result
            
        except Exception as e:
            raise Exception(f"SerpAPI Google Lens processing failed: {str(e)}")

    def _process_with_serpapi(self, image_data, image_type, languages, handwriting, image_path=None):
        """
        Process image using SerpAPI Google Lens API with serpapi package
        
        Args:
            image_data: Base64 encoded image data
            image_type: Image MIME type
            languages: List of language codes
            handwriting: Boolean for handwriting detection
            image_path: Path to image file (unused, kept for compatibility)
        
        Returns:
            dict: Extracted text and metadata
        """
        try:
            if GoogleSearch is None:
                raise ImportError("google-search-results package not installed. Install with: pip install google-search-results")
            
            # Prepare the request using serpapi package
            params = {
                'api_key': self.api_key,
                'engine': 'google_lens',
                'image': f"data:{image_type};base64,{image_data}",
                'hl': 'en',  # Output language
            }
            
            # Add handwriting hint if needed
            if handwriting:
                params['handwriting'] = 'true'
            
            # Make API request using serpapi GoogleSearch class
            try:
                search = GoogleSearch(params)
                api_response = search.get_dict()
            except (ValueError, json.JSONDecodeError) as e:
                raise Exception(f"SerpAPI response parsing failed: {str(e)}")
            
            if not api_response:
                raise Exception("SerpAPI returned empty response")
            
            if api_response.get('error'):
                raise Exception(f"SerpAPI error: {api_response.get('error')}")
            
            # Extract results from SerpAPI response
            results = api_response.get('results', {})
            
            # If no results, it's likely an API issue
            if not results:
                raise Exception("SerpAPI returned no results - please check your API key and rate limits")
            
            # Parse text from lens results
            extracted_text = self._parse_serpapi_results(results)
            
            # If no text extracted
            if not extracted_text or extracted_text.strip() == '':
                raise Exception("No text extracted from SerpAPI results - image may not contain readable text")
            
            # Detect language from results
            detected_language = self._detect_language_from_text(extracted_text, languages)
            
            return {
                'text': extracted_text,
                'full_text': extracted_text,
                'blocks': self._structure_text_blocks(extracted_text),
                'words': self._extract_words(extracted_text),
                'confidence': results.get('confidence', 0.8),
                'detected_language': detected_language,
                'handwriting_detected': self._detect_handwriting(results),
                'raw_response': results
            }
            
        except Exception as e:
            raise Exception(f"SerpAPI request failed: {str(e)}")

    def _parse_serpapi_results(self, results):
        """Parse text from SerpAPI results"""
        extracted_text = ""
        
        # Extract from different possible result formats
        if isinstance(results, dict):
            # Check for knowledge_graph text
            if 'knowledge_graph' in results:
                extracted_text += results['knowledge_graph'].get('title', '') + '\n'
            
            # Check for snippet or description
            if 'snippet' in results:
                extracted_text += results['snippet'] + '\n'
            
            if 'description' in results:
                extracted_text += results['description'] + '\n'
            
            # Check for lens results array
            if 'lens_results' in results:
                for item in results['lens_results']:
                    if isinstance(item, dict):
                        extracted_text += item.get('title', '') + '\n'
                        extracted_text += item.get('description', '') + '\n'
        
        elif isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    extracted_text += item.get('title', '') + ' '
                    extracted_text += item.get('description', '') + '\n'
        
        return extracted_text.strip() if extracted_text.strip() else str(results)

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
        
        for word in word_list:
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

    def _detect_handwriting(self, results):
        """Detect if text contains handwriting"""
        if isinstance(results, dict):
            result_str = json.dumps(results).lower()
            return any(word in result_str for word in ['handwritten', 'handwriting', 'cursive', 'manuscript'])
        return False

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
