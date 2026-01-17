"""
Document Type Classifier - Classifies historical documents into categories
Uses Ollama LLM for efficient, local classification
"""

import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Classifies document type based on OCR text using Ollama"""

    VALID_TYPES = ['letter', 'memo', 'telegram', 'fax', 'email', 'invitation']

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        """
        Initialize classifier

        Args:
            ollama_host: Ollama API host URL
            model: Model name (e.g., 'llama3.2', 'mistral')
        """
        self.ollama_host = ollama_host
        self.model = model
        logger.info(f"DocumentClassifier initialized with model {model}")

    async def classify(self, text: str, ocr_confidence: float = 1.0) -> Dict[str, Any]:
        """
        Classify document type based on OCR text

        Args:
            text: OCR extracted text (first 2000 characters used)
            ocr_confidence: OCR confidence score (0-1)

        Returns:
            {
                "document_type": "letter|memo|telegram|fax|email|invitation",
                "confidence": float (0-1),
                "reasoning": str
            }
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for classification")
            return self._default_classification()

        # Truncate text for efficiency
        text_excerpt = text[:2000]

        # Build classification prompt
        prompt = self._build_prompt(text_excerpt)

        try:
            # Call Ollama API
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'format': 'json',
                    'stream': False,
                    'temperature': 0.3  # Lower temperature for consistency
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                classification = json.loads(result['response'])

                # Validate and normalize response
                return self._normalize_classification(classification, ocr_confidence)
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._fallback_classify(text_excerpt, ocr_confidence)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            return self._fallback_classify(text_excerpt, ocr_confidence)
        except requests.RequestException as e:
            logger.error(f"Ollama connection error: {e}")
            return self._fallback_classify(text_excerpt, ocr_confidence)
        except Exception as e:
            logger.error(f"Unexpected error in classification: {e}")
            return self._default_classification()

    def _build_prompt(self, text: str) -> str:
        """Build the classification prompt"""
        return f"""You are analyzing a historical document to determine its type. Classify it into ONE of these categories:

- letter: Personal or official correspondence (formal letter format with salutation and closing)
- memo: Internal organizational note or memorandum (typically brief, informal)
- telegram: Telegraphic message (brief, formal, often with STOP markers)
- fax: Fax transmission (typically includes header information like date/sender/recipient)
- email: Electronic mail message
- invitation: Formal or informal invitation to an event or gathering

Analyze the document structure, language style, and formatting to determine the most likely type.

Document text (first 2000 characters):
{text}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "type": "letter|memo|telegram|fax|email|invitation",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this classification was chosen"
}}
"""

    def _normalize_classification(self, classification: Dict[str, Any], ocr_confidence: float) -> Dict[str, Any]:
        """
        Normalize and validate classification response

        Args:
            classification: Raw classification from LLM
            ocr_confidence: OCR confidence to factor into final confidence

        Returns:
            Normalized classification
        """
        doc_type = classification.get('type', 'letter').lower()

        # Validate type
        if doc_type not in self.VALID_TYPES:
            logger.warning(f"Invalid type '{doc_type}', defaulting to 'letter'")
            doc_type = 'letter'

        # Get confidence and combine with OCR confidence
        model_confidence = float(classification.get('confidence', 0.5))
        # Weight the combined confidence: 70% model, 30% OCR confidence
        final_confidence = min(1.0, (model_confidence * 0.7) + (ocr_confidence * 0.3))

        return {
            'document_type': doc_type,
            'confidence': round(final_confidence, 3),
            'reasoning': str(classification.get('reasoning', 'Classification based on document structure and language patterns'))
        }

    def _fallback_classify(self, text: str, ocr_confidence: float) -> Dict[str, Any]:
        """
        Rule-based fallback classification when Ollama is unavailable

        Uses heuristic patterns to classify documents
        """
        text_lower = text.lower()
        text_first_500 = text[:500].lower()

        logger.info("Using fallback classification")

        # Check for letter patterns
        letter_indicators = ['dear ', 'sincerely', 'yours truly', 'regards', 'respectfully', 'salutation']
        if any(indicator in text_first_500 for indicator in letter_indicators):
            return {
                'document_type': 'letter',
                'confidence': 0.7,
                'reasoning': 'Contains letter salutation and closing patterns'
            }

        # Check for telegram patterns
        if 'stop' in text_lower and len(text.split()) < 100:
            return {
                'document_type': 'telegram',
                'confidence': 0.8,
                'reasoning': 'Short text with STOP markers characteristic of telegrams'
            }

        # Check for memo patterns
        if any(word in text_first_500 for word in ['memo:', 'memorandum:', 'subject:', 'from:', 'to:']):
            return {
                'document_type': 'memo',
                'confidence': 0.75,
                'reasoning': 'Contains memo header format (subject, from, to)'
            }

        # Check for invitation patterns
        if any(word in text_lower for word in ['cordially invited', 'invitation', 'you are invited', 'please join', 'honor of']):
            return {
                'document_type': 'invitation',
                'confidence': 0.75,
                'reasoning': 'Contains invitation language patterns'
            }

        # Check for fax patterns
        if any(word in text_first_500 for word in ['fax', 'facsimile', 'phone:', 'pages:', 'urgent']):
            return {
                'document_type': 'fax',
                'confidence': 0.7,
                'reasoning': 'Contains fax transmission markers'
            }

        # Default to letter
        return {
            'document_type': 'letter',
            'confidence': 0.5,
            'reasoning': 'Default classification (insufficient distinctive patterns)'
        }

    def _default_classification(self) -> Dict[str, Any]:
        """Return default classification when no text is available"""
        return {
            'document_type': 'letter',
            'confidence': 0.3,
            'reasoning': 'No text available for classification'
        }
