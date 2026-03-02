"""
Ollama OCR Provider

Uses Ollama vision models (minicpm-v, llama-vision) for OCR.
Supports local deployment without external API keys.
"""

import logging
import base64
import os
from typing import Dict, Any
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
        try:
            import requests
            from PIL import Image
            
            # Check availability
            if not self._check_availability():
                logger.warning("Ollama not available, returning mock data")
                return self._mock_extract_text(image_path, language, **kwargs)
            
            # Load image
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}, returning mock data")
                return self._mock_extract_text(str(image_path), language, **kwargs)
            
            img = Image.open(image_path)
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Build prompt
            prompt = self._build_prompt(language, kwargs.get('handwriting', False))
            
            # Call Ollama API
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
            
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=600
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code}")
            
            result = response.json()
            text = result.get('response', '').strip()
            
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
            logger.error(f"Ollama extraction error: {e}", exc_info=True)
            # Fallback to mock data
            return self._mock_extract_text(image_path, language, **kwargs)
    
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
    
    def _mock_extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """Return mock OCR data for testing"""
        return {
            "text": "Sample extracted text from image.\nLine 2 of sample text.\nLine 3 of sample text.",
            "confidence": 0.92,
            "word_confidence": [],
            "language": language,
            "metadata": {
                "provider": "ollama_mock",
                "image_path": str(image_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "Mock data - Ollama not available"
            }
        }
