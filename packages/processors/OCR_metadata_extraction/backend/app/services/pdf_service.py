"""
PDF handling service for converting PDFs to images for OCR processing.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFService:
    """Service for handling PDF operations, including conversion to images."""

    @staticmethod
    def is_pdf(file_path: str) -> bool:
        """
        Check if a file is a PDF based on extension.

        Args:
            file_path: Path to the file

        Returns:
            True if file is a PDF, False otherwise
        """
        return file_path.lower().endswith('.pdf')

    @staticmethod
    def get_optimal_dpi(document_type: Optional[str] = None, handwriting: bool = False) -> int:
        """
        Get optimal DPI based on document type.

        Args:
            document_type: Type of document ('high_quality', 'low_quality', 'default')
            handwriting: Whether document contains handwriting

        Returns:
            Optimal DPI value
        """
        from app.config import Config

        if handwriting:
            return Config.OCR_PDF_DPI_HANDWRITING

        if document_type == 'high_quality':
            return Config.OCR_PDF_DPI_HIGH_QUALITY
        elif document_type == 'low_quality':
            return Config.OCR_PDF_DPI_LOW_QUALITY
        else:
            return Config.OCR_PDF_DPI_DEFAULT

    @staticmethod
    def pdf_to_images(pdf_path: str, dpi: Optional[int] = None, document_type: Optional[str] = None, handwriting: bool = False) -> list:
        """
        Convert PDF to list of PIL Image objects.

        Args:
            pdf_path: Path to PDF file
            dpi: DPI for conversion (uses optimal DPI if not specified)
            document_type: Type of document ('high_quality', 'low_quality', 'default')
            handwriting: Whether document contains handwriting

        Returns:
            List of PIL Image objects (one per page)

        Raises:
            Exception: If pdf2image is not installed or conversion fails
        """
        if not PDF2IMAGE_AVAILABLE:
            raise Exception(
                "PDF2Image library not available. Install with: pip install pdf2image\n"
                "Note: You may also need to install poppler: "
                "apt-get install poppler-utils (Ubuntu/Debian) or brew install poppler (macOS)"
            )

        if not os.path.exists(pdf_path):
            raise Exception(f"PDF file not found: {pdf_path}")

        # Use provided DPI or get optimal DPI based on document type
        if dpi is None:
            dpi = PDFService.get_optimal_dpi(document_type, handwriting)

        try:
            logger.info(f"Converting PDF to images: {pdf_path} (DPI: {dpi}, type: {document_type or 'default'})")
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Successfully converted PDF to {len(images)} page(s)")
            return images
        except Exception as e:
            raise Exception(f"Failed to convert PDF to images: {str(e)}")
    
    @staticmethod
    def pdf_to_temp_images(pdf_path: str, dpi: int = 200) -> list:
        """
        Convert PDF pages to temporary image files.
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for conversion
            
        Returns:
            List of temporary image file paths (one per page)
            
        Raises:
            Exception: If conversion fails
        """
        images = PDFService.pdf_to_images(pdf_path, dpi=dpi)
        
        temp_paths = []
        temp_dir = tempfile.gettempdir()
        
        try:
            for idx, image in enumerate(images):
                # Create temporary image file for each page
                temp_path = os.path.join(temp_dir, f"pdf_page_{idx}_{Path(pdf_path).stem}_{os.getpid()}.png")
                image.save(temp_path, 'PNG')
                temp_paths.append(temp_path)
                logger.info(f"Saved page {idx} to: {temp_path}")
        except Exception as e:
            # Clean up on failure
            for temp_path in temp_paths:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
            raise Exception(f"Failed to save temporary images: {str(e)}")
        
        return temp_paths
    
    @staticmethod
    def cleanup_temp_images(image_paths: list) -> None:
        """
        Clean up temporary image files.

        Args:
            image_paths: List of temporary file paths to delete
        """
        for image_path in image_paths:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Cleaned up temporary image: {image_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary image {image_path}: {str(e)}")

    @staticmethod
    def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary containing PDF metadata

        Raises:
            Exception: If PyPDF2 is not installed or extraction fails
        """
        if not PYPDF2_AVAILABLE:
            raise Exception(
                "PyPDF2 library not available. Install with: pip install PyPDF2"
            )

        if not os.path.exists(pdf_path):
            raise Exception(f"PDF file not found: {pdf_path}")

        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata

            # Extract basic info
            result = {
                'page_count': len(reader.pages),
                'file_size_bytes': os.path.getsize(pdf_path),
                'file_size_mb': round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
                'encrypted': reader.is_encrypted
            }

            # Extract metadata if available
            if metadata:
                # Common metadata fields
                result['title'] = metadata.get('/Title', '')
                result['author'] = metadata.get('/Author', '')
                result['subject'] = metadata.get('/Subject', '')
                result['creator'] = metadata.get('/Creator', '')
                result['producer'] = metadata.get('/Producer', '')
                result['keywords'] = metadata.get('/Keywords', '')

                # Date fields - handle various formats
                creation_date = metadata.get('/CreationDate', '')
                mod_date = metadata.get('/ModDate', '')

                result['creation_date'] = PDFService._parse_pdf_date(creation_date) if creation_date else None
                result['modification_date'] = PDFService._parse_pdf_date(mod_date) if mod_date else None

                # Add any custom metadata fields
                result['custom_metadata'] = {
                    k: v for k, v in metadata.items()
                    if k not in ['/Title', '/Author', '/Subject', '/Creator',
                                '/Producer', '/Keywords', '/CreationDate', '/ModDate']
                }
            else:
                # No metadata available
                result.update({
                    'title': '',
                    'author': '',
                    'subject': '',
                    'creator': '',
                    'producer': '',
                    'keywords': '',
                    'creation_date': None,
                    'modification_date': None,
                    'custom_metadata': {}
                })

            logger.info(f"Successfully extracted metadata from PDF: {pdf_path}")
            return result

        except Exception as e:
            raise Exception(f"Failed to extract PDF metadata: {str(e)}")

    @staticmethod
    def _parse_pdf_date(date_str: str) -> Optional[str]:
        """
        Parse PDF date format to ISO format.
        PDF dates are typically in format: D:YYYYMMDDHHmmSSOHH'mm'

        Args:
            date_str: PDF date string

        Returns:
            ISO formatted date string or None if parsing fails
        """
        if not date_str:
            return None

        try:
            # Remove 'D:' prefix if present
            if date_str.startswith('D:'):
                date_str = date_str[2:]

            # Extract date components
            year = date_str[0:4]
            month = date_str[4:6] if len(date_str) >= 6 else '01'
            day = date_str[6:8] if len(date_str) >= 8 else '01'
            hour = date_str[8:10] if len(date_str) >= 10 else '00'
            minute = date_str[10:12] if len(date_str) >= 12 else '00'
            second = date_str[12:14] if len(date_str) >= 14 else '00'

            # Create datetime and format as ISO
            dt = datetime(
                int(year), int(month), int(day),
                int(hour), int(minute), int(second)
            )
            return dt.isoformat()

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse PDF date '{date_str}': {e}")
            return date_str  # Return original string if parsing fails
