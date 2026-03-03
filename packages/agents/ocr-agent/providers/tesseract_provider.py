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
        logger.info(f"[TRACE-TESSERACT] extract_text called: image_path={image_path}, language={language}")
        
        if not self.pytesseract or not self.Image:
            logger.error(f"[TRACE-TESSERACT] Tesseract not available")
            raise RuntimeError(
                "Tesseract OCR not available. "
                "Install with: pip install pytesseract pillow\n"
                "Also requires tesseract binary: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)"
            )
        
        try:
            logger.info(f"[TRACE-TESSERACT] Opening image: {image_path}")
            # Open image
            image = self.Image.open(image_path)
            
            # Build Tesseract config
            config_parts = []
            if "psm" in kwargs:
                config_parts.append(f"--psm {kwargs['psm']}")
            if "oem" in kwargs:
                config_parts.append(f"--oem {kwargs['oem']}")
            
            config = " ".join(config_parts) if config_parts else None
            
            logger.info(f"[TRACE-TESSERACT] Calling pytesseract.image_to_string with config={config}, lang={language}")
            # Extract text
            text = self.pytesseract.image_to_string(
                image,
                lang=language,
                config=config
            )
            
            logger.info(f"[TRACE-TESSERACT] Text extracted: length={len(text)}")
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
            logger.info(f"[TRACE-TESSERACT] Confidence calculated: {avg_confidence}")
            
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
            
            logger.info(f"[TRACE-TESSERACT] Returning result with {len(word_confidence)} words")
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
