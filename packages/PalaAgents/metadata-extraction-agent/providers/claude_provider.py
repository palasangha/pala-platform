"""
Claude Metadata Extraction Provider

Extracts structured metadata from OCR text using Anthropic's Claude API.
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime

from .base_provider import BaseMetadataProvider

logger = logging.getLogger(__name__)


class ClaudeMetadataProvider(BaseMetadataProvider):
    """Claude-based provider for metadata extraction from OCR text"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude metadata provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        # Check if Claude is enabled
        enabled = os.getenv("CLAUDE_ENABLED", "true").lower() in ("true", "1", "yes")

        if not enabled:
            self._available = False
            self.client = None
            self.model = None
            logger.info("Claude metadata provider is disabled via CLAUDE_ENABLED")
            return

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

        if not self.api_key:
            self._available = False
            self.client = None
            logger.warning("✗ Claude provider: ANTHROPIC_API_KEY not set")
            return

        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
            self._available = True
            logger.info(f"✓ Claude metadata provider initialized (model: {self.model})")
        except ImportError:
            self._available = False
            self.client = None
            logger.error(
                "✗ Claude provider: anthropic package not installed. Run: pip install anthropic"
            )
        except Exception as e:
            self._available = False
            self.client = None
            logger.error(f"✗ Claude provider initialization failed: {str(e)}")

    def is_available(self) -> bool:
        """Check if Claude provider is available"""
        return self._available and self.client is not None

    async def extract_metadata(
        self,
        ocr_text: str,
        language: Optional[str] = None,
        document_context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured metadata from OCR text using Claude.

        Args:
            ocr_text: OCR-extracted text from document
            language: ISO language code (e.g., "en", "hi")
            document_context: Context hint (e.g., "historical_letter", "monastery_record")
            custom_prompt: Override default extraction prompt

        Returns:
            Structured metadata with confidence scores for all fields

        Raises:
            ValueError: If provider not available or text is empty
            json.JSONDecodeError: If Claude response cannot be parsed as JSON
        """
        if not self.is_available():
            raise ValueError(
                "Claude provider is not available. Set ANTHROPIC_API_KEY environment variable."
            )

        if not ocr_text or not ocr_text.strip():
            raise ValueError("OCR text cannot be empty")

        try:
            # Build extraction prompt
            prompt = custom_prompt or self._build_extraction_prompt(language, document_context)

            logger.info(f"Extracting metadata from {len(ocr_text)} chars of text")

            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,  # Lower temperature for consistency
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nDocument text:\n\n{ocr_text}",
                    }
                ],
            )

            # Extract response text
            response_text = message.content[0].text

            logger.debug(f"Raw Claude response: {response_text[:200]}...")

            # Parse JSON response
            extracted_data = self._parse_claude_response(response_text)

            logger.info(f"Metadata extraction complete: {len(extracted_data)} fields extracted")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            raise ValueError(f"Failed to parse metadata extraction response: {str(e)}")
        except Exception as e:
            logger.error(f"Claude metadata extraction failed: {e}")
            raise

    def _build_extraction_prompt(
        self, language: Optional[str] = None, document_context: Optional[str] = None
    ) -> str:
        """Build Claude prompt for metadata extraction"""

        prompt = """You are an expert historical document analyst. Extract structured metadata from the provided OCR text.

Return a JSON object with these fields (use null for unknown values, include all fields even if empty):
{
  "document_type": {
    "value": "letter|memo|telegram|fax|email|invitation|form|contract|report|other",
    "confidence": 0.0-1.0
  },
  "document_date": {
    "value": "YYYY-MM-DD or date string or null",
    "confidence": 0.0-1.0
  },
  "parties": {
    "people": [
      {"name": "person_name", "role": "sender|recipient|mentioned|signed", "confidence": 0.0-1.0}
    ],
    "organizations": [
      {"name": "org_name", "role": "sender|recipient|mentioned", "confidence": 0.0-1.0}
    ],
    "confidence": 0.0-1.0
  },
  "places": {
    "locations": [
      {"name": "place_name", "role": "mentioned|origin|destination", "confidence": 0.0-1.0}
    ],
    "confidence": 0.0-1.0
  },
  "storage_location": {
    "archive": "archive_name or null",
    "collection": "collection_name or null",
    "box": "box_number or null",
    "folder": "folder_number or null",
    "confidence": 0.0-1.0
  },
  "access_level": {
    "value": "public|restricted|private",
    "reasoning": "brief explanation",
    "confidence": 0.0-1.0
  },
  "summary": {
    "value": "brief summary of document",
    "confidence": 0.0-1.0
  },
  "key_topics": {
    "topics": ["topic1", "topic2", ...],
    "confidence": 0.0-1.0
  },
  "tone_sentiment": {
    "tone": "formal|informal|urgent|matter-of-fact|other",
    "sentiment": "positive|negative|neutral",
    "confidence": 0.0-1.0
  },
  "language": "ISO-639-1 code (en, hi, etc)",
  "notes": "any important observations or null"
}

CRITICAL REQUIREMENTS:
1. ALL confidence scores must be 0.0-1.0 (higher = more confident)
2. Return ONLY valid JSON, no markdown or extra text
3. Include all fields even if empty/null
4. For dates, use ISO format (YYYY-MM-DD) or describe as extracted
5. Be conservative with confidence - if uncertain, lower the score
6. Extract EVERY detail from the text accurately
7. Analyze relationships between parties carefully
8. Identify all locations and their roles in the document
"""

        if language:
            prompt += f"\nDocument language hint: {language}\n"

        if document_context:
            prompt += f"Document context/type hint: {document_context}\n"

        return prompt

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response.

        Attempts to extract and parse JSON from response text.
        """
        try:
            # Try direct JSON parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response (in case there's extra text)
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            raise ValueError(f"Could not parse Claude response as JSON: {response_text[:200]}")
