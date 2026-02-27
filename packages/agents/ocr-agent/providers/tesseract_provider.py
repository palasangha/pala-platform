"""
Tesseract OCR Provider

Uses pytesseract to extract text from images.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from .base_provider import BaseOCRProvider

logger = logging.getLogger(__name__)


class TesseractOCRProvider(BaseOCRProvider):
    """OCR provider using Tesseract"""
    
    def __init__(self):
        """Initialize Tesseract provider"""
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
            logger.info("Tesseract OCR provider initialized")
        except ImportError:
            logger.warning(
                "pytesseract or PIL not installed. "
                "Install with: pip install pytesseract pillow"
            )
            self.pytesseract = None
            self.Image = None
    
    async def extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from image using Tesseract
        
        Args:
            image_path: Path to image file
            language: Language code (e.g., 'eng', 'fra', 'deu')
            **kwargs: Tesseract options (e.g., psm, oem)
        
        Returns:
            Dictionary containing extracted text and metadata
        """
        if not self.pytesseract or not self.Image:
            # Fallback to mock data
            logger.warning("Tesseract not available, using mock data")
            return self._mock_extract_text(image_path, language, **kwargs)
        
        try:
            # Open image
            image = self.Image.open(image_path)
            
            # Build Tesseract config
            config_parts = []
            if "psm" in kwargs:
                config_parts.append(f"--psm {kwargs['psm']}")
            if "oem" in kwargs:
                config_parts.append(f"--oem {kwargs['oem']}")
            
            config = " ".join(config_parts) if config_parts else None
            
            # Extract text
            text = self.pytesseract.image_to_string(
                image,
                lang=language,
                config=config
            )
            
            # Get detailed data with confidence scores
            data = self.pytesseract.image_to_data(
                image,
                lang=language,
                config=config,
                output_type=self.pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [
                int(conf) for conf in data.get('conf', []) 
                if conf != '-1' and str(conf).isdigit()
            ]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            
            # Build word-level confidence data
            word_confidence = []
            for i, word in enumerate(data.get('text', [])):
                if word.strip() and data['conf'][i] != '-1':
                    word_confidence.append({
                        'word': word,
                        'confidence': int(data['conf'][i]) / 100.0,
                        'bbox': {
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
            
            return {
                "text": text.strip(),
                "confidence": round(avg_confidence, 3),
                "word_confidence": word_confidence,
                "language": language,
                "metadata": {
                    "provider": "tesseract",
                    "image_path": str(image_path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "image_size": {
                        "width": image.width,
                        "height": image.height
                    },
                    "psm": kwargs.get("psm", 3),
                    "oem": kwargs.get("oem", 3)
                }
            }
            
        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}", exc_info=True)
            raise
    
    def _mock_extract_text(
        self,
        image_path: str,
        language: str = "eng",
        **kwargs
    ) -> Dict[str, Any]:
        """Return mock OCR data for testing"""
        return {
            "text": "Letter dated 15th March 1892\n\nDear Venerable Sir,\n\nI write to inform you of the monastery's administrative matters. The construction of the new meditation hall has progressed well under the supervision of Brother Thomas. We anticipate completion by June.\n\nRespectfully yours,\nJohn Smith\nSecretary, Monastery Board",
            "confidence": 0.95,
            "word_confidence": [
                {"word": "Letter", "confidence": 0.98, "bbox": {"left": 10, "top": 10, "width": 50, "height": 20}},
                {"word": "dated", "confidence": 0.96, "bbox": {"left": 65, "top": 10, "width": 45, "height": 20}},
            ],
            "language": language,
            "metadata": {
                "provider": "mock",
                "image_path": str(image_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "psm": kwargs.get("psm", 3),
                "note": "Mock data - pytesseract not installed"
            }
        }
