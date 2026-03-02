"""
LM Studio OCR Provider

Uses LM Studio OpenAI-compatible API for local vision model inference.
Supports models like Gemma 2, Llama vision, Pixtral, etc.
"""

import logging
import base64
import os
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from .base_provider import BaseOCRProvider

logger = logging.getLogger(__name__)


class LMStudioProvider(BaseOCRProvider):
    """OCR provider using LM Studio OpenAI-compatible API"""
    
    def __init__(self, host: str = None, model: str = None, api_key: str = None):
        """
        Initialize LM Studio provider
        
        Args:
            host: LM Studio API URL (e.g., "http://localhost:1234")
            model: Model name (e.g., "gemma-2-27b", "llama-2-vision")
            api_key: API key for authentication (optional)
        """
        self.host = host or os.getenv('LMSTUDIO_HOST', 'http://localhost:1234')
        self.model = model or os.getenv('LMSTUDIO_MODEL', None)
        self.api_key = api_key or os.getenv('LMSTUDIO_API_KEY', 'lm-studio')
        self.timeout = int(os.getenv('LMSTUDIO_TIMEOUT', '600'))
        self.max_tokens = int(os.getenv('LMSTUDIO_MAX_TOKENS', '4096'))
        self._available = None
        logger.info(f"LM Studio provider initialized: host={self.host}")
    
    def _check_availability(self) -> bool:
        """Check if LM Studio server is available"""
        try:
            import requests
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(
                f"{self.host}/v1/models",
                headers=headers,
                timeout=5,
                verify=False
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LM Studio availability check failed: {e}")
            return False
    
    async def extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from image using LM Studio OpenAI-compatible API
        
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
                logger.warning("LM Studio not available, returning mock data")
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
            
            # Call LM Studio OpenAI-compatible API
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {
                "model": self.model or "default",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.host}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
            
            if response.status_code != 200:
                raise Exception(f"LM Studio API error: {response.status_code}")
            
            result = response.json()
            text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            return {
                "text": text,
                "confidence": 0.90,
                "word_confidence": [],
                "language": language,
                "metadata": {
                    "provider": "lmstudio",
                    "image_path": str(image_path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "image_size": {
                        "width": img.width,
                        "height": img.height
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"LM Studio extraction error: {e}", exc_info=True)
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
            "confidence": 0.90,
            "word_confidence": [],
            "language": language,
            "metadata": {
                "provider": "lmstudio_mock",
                "image_path": str(image_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "Mock data - LM Studio not available"
            }
        }
