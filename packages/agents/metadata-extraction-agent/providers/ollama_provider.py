"""
Ollama Metadata Extraction Provider

Extracts structured metadata from OCR text using local Ollama models.
Supports any model available in local Ollama instance.
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime

from .base_provider import BaseMetadataProvider

logger = logging.getLogger(__name__)


class OllamaMetadataProvider(BaseMetadataProvider):
    """Ollama-based provider for metadata extraction from OCR text"""

    def __init__(self, base_url: Optional[str] = None, model: str = "minicpm-v"):
        """
        Initialize Ollama metadata provider.

        Args:
            base_url: Ollama server URL (defaults to OLLAMA_BASE_URL env var or http://localhost:11434)
            model: Ollama model to use (default: minicpm-v)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "minicpm-v")

        # Check if Ollama is enabled
        enabled = os.getenv("OLLAMA_ENABLED", "true").lower() in ("true", "1", "yes")

        if not enabled:
            self._available = False
            logger.info("Ollama metadata provider is disabled via OLLAMA_ENABLED")
            return

        try:
            import requests
            import ollama

            self.requests = requests
            self.ollama = ollama
            self._available = self._check_ollama_available()
            
            if self._available:
                logger.info(f"✓ Ollama metadata provider initialized (URL: {self.base_url}, model: {self.model})")
            else:
                logger.warning(f"✗ Ollama provider: Unable to connect to {self.base_url}")
        except ImportError:
            self._available = False
            logger.error(
                "✗ Ollama provider: required packages not installed. Run: pip install requests ollama"
            )
        except Exception as e:
            self._available = False
            logger.error(f"✗ Ollama provider initialization failed: {str(e)}")

    def _check_ollama_available(self) -> bool:
        """Check if Ollama server is available and model can be accessed"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                
                # Check if our model is available
                model_base = self.model.split(":")[0]
                if model_base in model_names or len(model_names) > 0:
                    logger.info(f"Available Ollama models: {', '.join(model_names)}")
                    return True
                else:
                    logger.warning(f"Model {self.model} not found. Available: {model_names}")
                    return False
            return False
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    def is_available(self) -> bool:
        """Check if Ollama provider is available"""
        return self._available

    def _get_available_models(self) -> list:
        """Get list of available models from Ollama"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name", "").split(":")[0] for m in models]
        except Exception as e:
            logger.debug(f"Failed to get available models: {e}")
        return []

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
            Dictionary with extracted metadata fields
        """
        if not self.is_available():
            raise RuntimeError("Ollama provider is not available")

        try:
            # Build the extraction prompt
            prompt = custom_prompt or self._build_prompt(ocr_text, language, document_context)

            # Call Ollama API
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,  # Lower temperature for more structured output
                },
                timeout=120,
            )

            if response.status_code != 200:
                available_models = self._get_available_models()
                model_list = ", ".join(available_models) if available_models else "none"
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                logger.error(f"Requested model: {self.model}, Available models: {model_list}")
                raise RuntimeError(f"Ollama API returned status {response.status_code}. Model '{self.model}' not available. Available: {model_list}")

            result = response.json()
            generated_text = result.get("response", "")

            # Parse the generated text to extract JSON
            metadata = self._parse_response(generated_text)
            
            logger.info(f"Metadata extracted via Ollama ({self.model})")
            return metadata

        except Exception as e:
            logger.error(f"Error in Ollama metadata extraction: {str(e)}", exc_info=True)
            raise

    def _build_prompt(self, ocr_text: str, language: Optional[str], document_context: Optional[str]) -> str:
        """Build the extraction prompt for Ollama"""
        lang_hint = f" in {language}" if language else ""
        context_hint = f" The document appears to be a {document_context}." if document_context else ""

        prompt = f"""Extract structured metadata from the following OCR text{lang_hint}. {context_hint}

OCR Text:
{ocr_text}

Extract and return a JSON object with the following fields (use null for missing values):
{{
  "document_type": "type of document (letter, report, invoice, etc)",
  "document_date": "date if present (YYYY-MM-DD format or null)",
  "summary": "brief summary of the document",
  "key_topics": ["list", "of", "topics"],
  "parties": {{
    "people": [
      {{"name": "Person Name", "role": "their role if identifiable"}}
    ],
    "organizations": [
      {{"name": "Organization Name"}}
    ]
  }},
  "places": [
    {{"name": "Location", "context": "how it appears in document"}}
  ],
  "tone": "formal/informal/academic/etc",
  "language": "{language or 'detected'}",
  "confidence": 0.7
}}

Return ONLY the JSON object, no other text."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Ollama response to extract metadata"""
        try:
            # Try to extract JSON from the response
            # Look for JSON object pattern
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                metadata = json.loads(json_str)
            else:
                # If no JSON found, create basic structure
                logger.warning("Could not parse JSON from Ollama response")
                metadata = {
                    "summary": response_text[:500],
                    "confidence": 0.3,
                    "note": "Partial extraction - Ollama response parsing incomplete"
                }

            # Ensure confidence score exists
            if "confidence" not in metadata:
                metadata["confidence"] = 0.6

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise RuntimeError(f"Failed to parse metadata JSON from Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {str(e)}")
            raise
