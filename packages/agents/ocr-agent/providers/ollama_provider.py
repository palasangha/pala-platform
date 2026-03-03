"""
Ollama OCR Provider

Uses Ollama vision models (minicpm-v, llama-vision) for OCR.
Supports local deployment without external API keys.
"""

import logging
import base64
import os
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from .base_provider import BaseOCRProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseOCRProvider):
    """OCR provider using Ollama vision models"""
    
    def __init__(self, host: str = None, model: str = None):
        """
        Initialize Ollama provider
        
        Args:
            host: Ollama server URL (e.g., "http://localhost:11434")
            model: Model name (e.g., "minicpm-v", "llama2-vision")
        """
        self.host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'minicpm-v')
        self._available = None
        logger.info(f"Ollama provider initialized: host={self.host}, model={self.model}")
    
    def _check_availability(self) -> bool:
        """Check if Ollama server is available"""
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False

    def _list_models(self) -> List[str]:
        """Return available model names from Ollama server."""
        import requests

        response = requests.get(f"{self.host}/api/tags", timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama /api/tags failed with status {response.status_code}")

        data = response.json() or {}
        models = data.get("models", [])
        return [m.get("name", "") for m in models if isinstance(m, dict) and m.get("name")]

    def _extract_response_text(self, payload: Dict[str, Any]) -> str:
        """Extract text from Ollama response payload."""
        text = (payload.get("response") or "").strip()
        if text:
            return text

        message = payload.get("message")
        if isinstance(message, dict):
            content = (message.get("content") or "").strip()
            if content:
                return content

        return ""
    
    async def extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from image using Ollama vision model
        
        Args:
            image_path: Path to image file
            language: Language code (optional)
            **kwargs: Additional options
        
        Returns:
            Dictionary containing extracted text and metadata
        """
        logger.info(f"[TRACE-OLLAMA] extract_text called: image_path={image_path}, language={language}")
        try:
            import requests
            from PIL import Image
            
            logger.info(f"[TRACE-OLLAMA] Checking Ollama availability at {self.host}")
            # Check availability
            if not self._check_availability():
                raise RuntimeError(
                    f"Ollama server is not reachable at {self.host}. "
                    "Start it with `ollama serve`."
                )

            logger.info(f"[TRACE-OLLAMA] Ollama server available, listing models")
            available_models = self._list_models()
            logger.info(f"[TRACE-OLLAMA] Available models: {available_models}")
            
            if not any(name == self.model or name.startswith(f"{self.model}:") for name in available_models):
                raise RuntimeError(
                    f"Ollama model '{self.model}' not found. Available: {available_models[:10]}. "
                    f"Install with `ollama pull {self.model}`."
                )
            
            logger.info(f"[TRACE-OLLAMA] Model {self.model} found, loading image from {image_path}")
            # Load image
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            img = Image.open(image_path)
            logger.info(f"[TRACE-OLLAMA] Image loaded: size={img.size}")
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            logger.info(f"[TRACE-OLLAMA] Image encoded to base64, size={len(image_data)} chars")
            
            # Build prompt
            prompt = self._build_prompt(language, kwargs.get('handwriting', False))
            
            # Build request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 4096
                }
            }
            
            logger.info(f"[TRACE-OLLAMA] Calling Ollama API at {self.host}/api/generate - this may take several minutes for model loading and inference...")
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=1800
            )
            
            logger.info(f"[TRACE-OLLAMA] API response received: status={response.status_code}")
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text[:500]}")
            
            result = response.json()
            logger.info(f"[TRACE-OLLAMA] Response parsed successfully")
            text = self._extract_response_text(result)
            logger.info(f"[TRACE-OLLAMA] Text extracted: length={len(text)}")

            if not text:
                raise RuntimeError(
                    "Ollama returned an empty OCR response. "
                    "Try a stronger vision model or verify image quality."
                )
            
            logger.info(f"[TRACE-OLLAMA] Extraction successful, returning result")
            return {
                "text": text,
                "confidence": 0.92,
                "word_confidence": [],
                "language": language,
                "metadata": {
                    "provider": "ollama",
                    "model": self.model,
                    "image_path": str(image_path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "image_size": {
                        "width": img.width,
                        "height": img.height
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[TRACE-OLLAMA] Extraction error: {e}", exc_info=True)
            raise
    
    def _build_prompt(self, language: str, handwriting: bool = False) -> str:
        """Build OCR prompt"""
        prompt = "Extract ALL text from this image exactly as shown. "
        
        if handwriting:
            prompt += "This is HANDWRITTEN text - pay attention to letter formation. "
        
        prompt += "\nRULES:\n"
        prompt += "1. Extract EVERY character and word exactly\n"
        prompt += "2. Preserve formatting and line breaks\n"
        prompt += "3. Do NOT translate or interpret\n"
        prompt += "4. Output ONLY the extracted text\n"
        
        return prompt
    
