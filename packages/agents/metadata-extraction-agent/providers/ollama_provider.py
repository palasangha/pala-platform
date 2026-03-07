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
                    "format": "json",  # Force JSON output format
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
        lang_value = language or "en"

        prompt = f"""You are an expert document analyst. Extract comprehensive structured metadata from the following document text{lang_hint}.{context_hint}

Analyze the document carefully and extract ALL available information. Be thorough and precise.

Document text:
{ocr_text}

Extract and return ONLY a valid JSON object (no markdown, no explanation, no extra text) with EVERY field below. Use null for missing values:
{{
  "document_type": "letter|report|memo|contract|notice|email|formal_correspondence|research_document|historical_document|other",
  "document_date": "Extract date in YYYY-MM-DD format if present, otherwise null",
  "summary": "2-3 sentence summary of the document's main purpose and content",
  "key_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "parties": {{
    "people": [
      {{"name": "Full Name", "role": "Sender|Recipient|Author|Director|Department|Organization|Other", "affiliation": "Organization"}}
    ],
    "organizations": [
      {{"name": "Organization Name", "role": "Sender|Recipient|Institution|Department|Other"}}
    ]
  }},
  "places": [
    {{"name": "Location", "context": "Where mentioned in document", "role": "Origin|Destination|Mentioned|Historical|Other"}}
  ],
  "tone": "formal|informal|academic|legal|professional|respectful|urgent|other",
  "language": "{lang_value}",
  "confidence": 0.0-1.0
}}

IMPORTANT INSTRUCTIONS:
- Extract EVERY mention of people with their full names and roles
- Extract EVERY mention of organizations/institutions
- Extract EVERY geographic location mentioned (cities, centers, departments, etc.)
- For document_date, extract any date mentioned (in body or header)
- For summary, provide 2-3 sentences about the main topic
- For key_topics, list 3-5 main themes (e.g., Buddha, Vipassana, meditation, monastery, etc.)
- Confidence: Use 0.8-1.0 if information is explicit, 0.5-0.7 if inferred, 0.0-0.4 if uncertain
- ALL fields required - use null only if truly not mentioned
- Return ONLY valid JSON, no other text"""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Ollama response to extract metadata"""
        try:
            # Clean up the response text - sometimes Ollama includes escape sequences
            response_text = response_text.strip()
            
            # Try to parse as JSON directly first
            try:
                metadata = json.loads(response_text)
                metadata = self._normalize_ollama_response(metadata)
                return metadata
            except json.JSONDecodeError:
                pass
            
            # If direct parsing fails, try to extract JSON from the text
            # Find the first '{' and then find its matching '}'
            start_idx = response_text.find('{')
            if start_idx == -1:
                raise RuntimeError("No JSON object found in Ollama response")
            
            # Find the matching closing brace by counting braces
            brace_count = 0
            end_idx = start_idx
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response_text)):
                char = response_text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
            
            if brace_count != 0:
                raise RuntimeError("Unmatched braces in JSON response")
            
            json_str = response_text[start_idx:end_idx]
            metadata = json.loads(json_str)
            metadata = self._normalize_ollama_response(metadata)
            
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}")
            raise RuntimeError(f"Failed to parse metadata JSON from Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {str(e)}")
            raise

    def _normalize_ollama_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Ollama response to ensure consistent field names and structure.
        
        Ollama may return capitalized field names (e.g., "People" instead of "people")
        that need to be normalized to lowercase for the mapper.
        """
        # Handle parties capitalization (Ollama returns "People"/"Organizations")
        if "parties" in data and isinstance(data["parties"], dict):
            parties = data["parties"]
            
            # Normalize People -> people
            if "People" in parties and "people" not in parties:
                parties["people"] = parties.pop("People")
            
            # Normalize Organizations -> organizations
            if "Organizations" in parties and "organizations" not in parties:
                parties["organizations"] = parties.pop("Organizations")
        
        # Ensure confidence exists - calculate from available data
        if "confidence" not in data:
            data["confidence"] = self._calculate_confidence(data)
        
        logger.info(f"Normalized Ollama response keys: {list(data.keys())}")
        return data

    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate overall confidence score based on extracted data"""
        field_weights = {
            "document_type": 0.15,
            "document_date": 0.15,
            "summary": 0.15,
            "key_topics": 0.15,
            "parties": 0.25,
            "places": 0.10,
            "tone": 0.05,
        }
        
        confidence = 0.0
        total_weight = 0.0
        
        for field, weight in field_weights.items():
            if field in data and data[field]:
                # Field present and non-empty
                if isinstance(data[field], dict):
                    confidence += 0.85 * weight  # 85% confidence for nested objects
                elif isinstance(data[field], (list, str)):
                    if data[field]:  # Non-empty list/string
                        confidence += 0.85 * weight
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            confidence = confidence / total_weight
        
        return round(min(confidence, 1.0), 2)
