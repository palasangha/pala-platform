"""
Ollama Metadata Extraction Provider

Extracts structured metadata from OCR text using local Ollama models.
Provides cost-free, locally-running metadata extraction.
"""

import json
import logging
import os
import re
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from .base_provider import BaseMetadataProvider

logger = logging.getLogger(__name__)


class OllamaMetadataProvider(BaseMetadataProvider):
    """Ollama-based provider for metadata extraction from OCR text"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Initialize Ollama metadata provider.

        Args:
            base_url: Ollama server URL (defaults to OLLAMA_BASE_URL env var or http://localhost:11434)
            model: Ollama model to use (defaults to OLLAMA_MODEL env var or mistral)
            timeout: Request timeout in seconds (default: 120)
        """
        # Check if Ollama is enabled
        enabled = os.getenv("OLLAMA_ENABLED", "true").lower() in ("true", "1", "yes")

        if not enabled:
            self._available = False
            logger.info("Ollama metadata provider is disabled via OLLAMA_ENABLED")
            return

        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.timeout = timeout
        self.max_input_chars = int(os.getenv("OLLAMA_MAX_INPUT_CHARS", "10000"))

        # Check if Ollama is available
        self._available = self._check_availability()

        if self._available:
            logger.info(
                f"✓ Ollama metadata provider initialized (model: {self.model}, url: {self.base_url})"
            )
        else:
            logger.warning(
                f"✗ Ollama provider not available at {self.base_url}. Check if Ollama is running."
            )

    def is_available(self) -> bool:
        """Check if Ollama provider is available"""
        return self._available

    def _check_availability(self) -> bool:
        """Check if Ollama service is running and model is available"""
        try:
            import requests

            # Check if Ollama is running
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            if response.status_code != 200:
                return False

            # Check if the model is available
            tags_data = response.json()
            models = tags_data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            if not any(self.model in name for name in model_names):
                logger.warning(
                    f"✗ Model '{self.model}' not found in Ollama. Available models: {model_names}"
                )
                return False

            return True
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    async def extract_metadata(
        self,
        ocr_text: str,
        language: Optional[str] = None,
        document_context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured metadata from OCR text using Ollama.

        Args:
            ocr_text: OCR-extracted text from document
            language: ISO language code (e.g., "en", "hi")
            document_context: Context hint (e.g., "historical_letter", "monastery_record")
            custom_prompt: Override default extraction prompt

        Returns:
            Structured metadata with confidence scores for all fields

        Raises:
            ValueError: If provider not available or text is empty
            json.JSONDecodeError: If Ollama response cannot be parsed as JSON
        """
        if not self.is_available():
            raise ValueError(
                f"Ollama provider is not available at {self.base_url}. Is Ollama running?"
            )

        if not ocr_text or not ocr_text.strip():
            raise ValueError("OCR text cannot be empty")

        try:
            prepared_text = self._prepare_input_text(ocr_text)

            # Build extraction prompt
            prompt = custom_prompt or self._build_extraction_prompt(
                language, document_context
            )
            response_schema = self._get_response_schema()

            logger.info(
                f"Extracting metadata from {len(prepared_text)} chars of text using Ollama"
            )

            # Call Ollama API via aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{prompt}\n\nDocument text:\n\n{prepared_text}",
                        "stream": False,
                        "format": response_schema,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"Ollama API returned status {response.status}"
                        )

                    result = await response.json()
                    response_text = result.get("response", "")

            logger.info(f"Raw Ollama response (first 500 chars): {response_text[:500]}")

            # Parse JSON response
            extracted_data = self._parse_ollama_response(response_text)
            self._validate_ollama_response(extracted_data)

            logger.info(
                f"Metadata extraction complete: {len(extracted_data)} fields extracted. Keys: {list(extracted_data.keys())}"
            )
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            raise ValueError(f"Failed to parse metadata extraction response: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama metadata extraction failed: {e}")
            raise

    def _build_extraction_prompt(
        self, language: Optional[str] = None, document_context: Optional[str] = None
    ) -> str:
        """
        Build Ollama prompt for metadata extraction.
        
        Uses a simplified schema to maximize JSON compliance with LLMs like Mistral.
        More complex fields are filled in post-processing by the mapper.
        """

        prompt = """You are an expert historical document analyst. Analyze the provided OCR text and extract structured metadata in JSON format.

CRITICAL: Return ONLY valid JSON, no markdown or extra text.

Extract these fields (use null for unknown):
{
  "document_type": {
    "value": "letter|memo|report|email|contract|form|invitation|telegram|fax|other|unknown",
    "confidence": 0.0
  },
  "document_date": {
    "value": "YYYY-MM-DD format or null",
    "confidence": 0.0
  },
  "people": [
    {"name": "full_name", "role": "sender|recipient|author|mentioned|signed", "confidence": 0.0}
  ],
  "organizations": [
    {"name": "org_name", "role": "sender|recipient|mentioned", "confidence": 0.0}
  ],
  "locations": [
    {"name": "place_name", "role": "origin|destination|mentioned", "confidence": 0.0}
  ],
  "summary": {
    "text": "concise 1-2 sentence summary of document content and purpose",
    "confidence": 0.0
  },
  "topics": ["key_topic_1", "key_topic_2"],
  "tone": "formal|informal|urgent|neutral|other",
  "sentiment": "positive|neutral|negative",
  "language": "en",
  "access_level": "public|restricted|private",
  "confidence_notes": "brief explanation of confidence levels"
}

INSTRUCTIONS:
1. Extract ALL people, organizations, and locations mentioned
2. Identify sender and recipient if applicable
3. Assign reasonable confidence scores (0.0-1.0) based on clarity
4. Use ISO date format (YYYY-MM-DD) when possible
5. Be thorough but accurate - mark uncertain items with lower confidence
6. Return ONLY JSON, no explanatory text
"""

        if language:
            prompt += f"\nLanguage hint: {language}\n"

        if document_context:
            prompt += f"Document type hint: {document_context}\n"

        return prompt

    def _prepare_input_text(self, ocr_text: str) -> str:
        """Trim OCR text to a safe size for Ollama."""
        normalized_text = ocr_text.strip()

        if len(normalized_text) <= self.max_input_chars:
            return normalized_text

        logger.warning(
            f"Ollama input too long ({len(normalized_text)} chars). Truncating to {self.max_input_chars} chars."
        )
        return normalized_text[: self.max_input_chars]

    @staticmethod
    def _get_response_schema() -> Dict[str, Any]:
        """Return the JSON schema Ollama should follow for metadata extraction."""
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "document_type",
                "document_date",
                "people",
                "organizations",
                "locations",
                "summary",
                "topics",
                "tone",
                "sentiment",
                "language",
            ],
            "properties": {
                "document_type": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["value", "confidence"],
                    "properties": {
                        "value": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                },
                "document_date": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["value", "confidence"],
                    "properties": {
                        "value": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                },
                "people": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "role", "confidence"],
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
                "organizations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "role", "confidence"],
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
                "locations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "role", "confidence"],
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
                "summary": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["text", "confidence"],
                    "properties": {
                        "text": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                },
                "topics": {"type": "array", "items": {"type": "string"}},
                "tone": {"type": "string"},
                "sentiment": {"type": "string"},
                "language": {"type": "string"},
                "access_level": {"type": ["string", "null"]},
                "confidence_notes": {"type": ["string", "null"]},
            },
        }

    @staticmethod
    def _validate_ollama_response(data: Dict[str, Any]) -> None:
        """Validate that Ollama returned the schema expected by the mapper."""
        required_keys = [
            "document_type",
            "document_date",
            "people",
            "organizations",
            "locations",
            "summary",
            "topics",
            "tone",
            "sentiment",
            "language",
        ]

        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise ValueError(
                f"Ollama response missing required metadata keys: {missing_keys}. Response keys: {list(data.keys())}"
            )

        if not isinstance(data.get("document_type"), dict) or "value" not in data["document_type"]:
            raise ValueError("Ollama response has invalid 'document_type' structure")

        if not isinstance(data.get("document_date"), dict) or "value" not in data["document_date"]:
            raise ValueError("Ollama response has invalid 'document_date' structure")

        for key in ["people", "organizations", "locations", "topics"]:
            if not isinstance(data.get(key), list):
                raise ValueError(f"Ollama response has invalid '{key}' structure")

        if not isinstance(data.get("summary"), dict) or "text" not in data["summary"]:
            raise ValueError("Ollama response has invalid 'summary' structure")

    def _parse_ollama_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Ollama's JSON response.

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

            raise ValueError(f"Could not parse Ollama response as JSON: {response_text[:200]}")
