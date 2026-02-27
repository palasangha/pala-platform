"""
Base OCR Provider Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseOCRProvider(ABC):
    """Abstract base class for OCR providers"""
    
    @abstractmethod
    async def extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from an image
        
        Args:
            image_path: Path to image file
            language: Language code
            **kwargs: Provider-specific options
        
        Returns:
            Dictionary containing:
                - text: Extracted text
                - confidence: Overall confidence score (0-1)
                - word_confidence: Per-word confidence scores
                - language: Detected/specified language
                - metadata: Additional metadata
        """
        pass
