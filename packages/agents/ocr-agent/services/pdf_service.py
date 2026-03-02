"""
PDF service for OCR processing.
Handles PDF to image conversion.
"""

import logging
from typing import List
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFService:
    """Service for converting PDFs to images"""
    
    @staticmethod
    def pdf_to_images(
        pdf_path: str,
        dpi: int = 300,
        handwriting: bool = False
    ) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution in dots per inch
            handwriting: If True, use higher DPI for handwriting
        
        Returns:
            List of PIL Image objects, one per page
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.warning("pdf2image not installed, returning empty list")
            return []
        
        try:
            # Adjust DPI for handwriting
            if handwriting:
                dpi = max(dpi, 400)
            
            logger.info(f"Converting PDF to images: {pdf_path} (dpi={dpi})")
            
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted {len(images)} pages from PDF")
            
            return images
            
        except Exception as e:
            logger.error(f"PDF conversion error: {e}", exc_info=True)
            return []
    
    @staticmethod
    def is_pdf(file_path: str) -> bool:
        """Check if file is a PDF"""
        return str(file_path).lower().endswith('.pdf')
