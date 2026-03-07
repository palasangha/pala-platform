"""
Image optimization service for OCR processing.
Handles image resizing, quality optimization, and format conversion.
"""

import logging
from typing import Tuple, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """Service for optimizing images for OCR processing"""

    @staticmethod
    def get_image_file_size(image: Image.Image, quality: int = 95) -> int:
        """
        Calculate the file size of an image in bytes.

        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)

        Returns:
            File size in bytes
        """
        buffer = io.BytesIO()
        # Ensure RGB for JPEG
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        image.save(buffer, format='JPEG', quality=quality)
        return buffer.tell()

    @staticmethod
    def calculate_optimal_size_for_filesize(
        width: int,
        height: int,
        current_size_bytes: int,
        target_size_bytes: int = 5 * 1024 * 1024  # 5MB default
    ) -> Tuple[int, int]:
        """
        Calculate optimal image dimensions to achieve target file size.

        Args:
            width: Original width
            height: Original height
            current_size_bytes: Current file size in bytes
            target_size_bytes: Target file size in bytes (default 5MB)

        Returns:
            Tuple of (new_width, new_height)
        """
        # If image is already smaller than target, don't resize
        if current_size_bytes <= target_size_bytes:
            logger.info(f"Image size ({current_size_bytes / (1024*1024):.2f}MB) is within limit, no resize needed")
            return width, height

        # Calculate scale factor based on file size ratio
        # File size roughly scales with pixel count (width * height)
        size_ratio = target_size_bytes / current_size_bytes
        scale = size_ratio ** 0.5  # Square root because area scales quadratically

        new_width = int(width * scale)
        new_height = int(height * scale)

        # Ensure minimum reasonable size
        if new_width < 512 or new_height < 512:
            logger.warning(f"Calculated size too small, using minimum 512px on shortest side")
            if width < height:
                new_width = 512
                new_height = int(height * (512 / width))
            else:
                new_height = 512
                new_width = int(width * (512 / height))

        logger.info(f"Resizing image from {width}x{height} ({current_size_bytes/(1024*1024):.2f}MB) to {new_width}x{new_height} (target: {target_size_bytes/(1024*1024):.2f}MB)")
        return new_width, new_height

    @staticmethod
    def optimize_image(
        image: Image.Image,
        quality: Optional[int] = None,
        target_size_mb: float = 5.0,
        auto_optimize: bool = True
    ) -> Image.Image:
        """
        Optimize image for OCR processing based on file size.

        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            target_size_mb: Target file size in MB (default 5MB)
            auto_optimize: Whether to apply automatic optimizations

        Returns:
            Optimized PIL Image object
        """
        from app.config import Config

        # Use config defaults if not specified
        if quality is None:
            quality = Config.OCR_IMAGE_QUALITY

        width, height = image.size

        # Convert to RGB if needed (for consistency)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
            logger.debug(f"Converted image mode to RGB")

        # Resize if needed and auto-optimization is enabled
        # COMMENTED OUT: Image resizing disabled while keeping document cropping
        # if auto_optimize and Config.OCR_AUTO_OPTIMIZE_IMAGES:
        #     # Calculate current file size
        #     current_size = ImageOptimizer.get_image_file_size(image, quality)
        #     target_size_bytes = int(target_size_mb * 1024 * 1024)
        #
        #     new_width, new_height = ImageOptimizer.calculate_optimal_size_for_filesize(
        #         width, height, current_size, target_size_bytes
        #     )
        #
        #     if (new_width, new_height) != (width, height):
        #         # Use LANCZOS for high-quality downsampling
        #         image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        #         logger.info(f"Resized image to {new_width}x{new_height}")

        return image

    @staticmethod
    def optimize_and_encode(
        image: Image.Image,
        quality: Optional[int] = None,
        target_size_mb: float = 5.0,
        auto_optimize: bool = True,
        auto_crop: bool = True,
        format: str = 'JPEG'
    ) -> bytes:
        """
        Optimize image and encode to bytes.

        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            target_size_mb: Target file size in MB (default 5MB)
            auto_optimize: Whether to apply automatic optimizations
            auto_crop: Whether to auto-detect and crop document
            format: Output format (JPEG, PNG)

        Returns:
            Image bytes
        """
        from app.config import Config

        if quality is None:
            quality = Config.OCR_IMAGE_QUALITY

        # Step 1: Auto-crop document if enabled
        if auto_crop and Config.OCR_AUTO_CROP_DOCUMENT:
            from app.services.document_detector import DocumentDetector
            logger.info("Attempting document detection and cropping...")
            cropped = DocumentDetector.auto_crop_document(image, fallback_to_original=True)
            if cropped is not None:
                image = cropped

        # Step 2: Optimize image size
        optimized_image = ImageOptimizer.optimize_image(
            image, quality, target_size_mb, auto_optimize
        )

        # Step 3: Encode to bytes
        buffer = io.BytesIO()

        if format.upper() == 'JPEG':
            # Ensure RGB for JPEG
            if optimized_image.mode not in ('RGB', 'L'):
                optimized_image = optimized_image.convert('RGB')
            optimized_image.save(buffer, format='JPEG', quality=quality, optimize=True)
        elif format.upper() == 'PNG':
            optimized_image.save(buffer, format='PNG', optimize=True)
        else:
            optimized_image.save(buffer, format=format, quality=quality)

        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def analyze_image_quality(image: Image.Image) -> dict:
        """
        Analyze image to suggest optimal DPI/quality settings.

        Args:
            image: PIL Image object

        Returns:
            Dictionary with quality analysis and recommendations
        """
        width, height = image.size

        # Simple heuristics for document type detection
        analysis = {
            'width': width,
            'height': height,
            'total_pixels': width * height,
            'aspect_ratio': width / height if height > 0 else 0,
        }

        # Suggest document type based on size
        if width < 1000 or height < 1000:
            analysis['suggested_document_type'] = 'low_quality'
            analysis['reason'] = 'Small image size detected'
        elif width > 3000 or height > 3000:
            analysis['suggested_document_type'] = 'high_quality'
            analysis['reason'] = 'High resolution image detected'
        else:
            analysis['suggested_document_type'] = 'default'
            analysis['reason'] = 'Standard resolution image'

        # Check if resize needed
        max_dim = max(width, height)
        from app.config import Config
        if max_dim > Config.OCR_MAX_IMAGE_DIMENSION:
            analysis['resize_recommended'] = True
            analysis['resize_reason'] = f'Image exceeds max dimension ({Config.OCR_MAX_IMAGE_DIMENSION}px)'
        else:
            analysis['resize_recommended'] = False

        return analysis

    @staticmethod
    def get_recommended_dpi(image: Image.Image, handwriting: bool = False) -> int:
        """
        Get recommended DPI based on image analysis.

        Args:
            image: PIL Image object
            handwriting: Whether document contains handwriting

        Returns:
            Recommended DPI value
        """
        from app.services.pdf_service import PDFService

        analysis = ImageOptimizer.analyze_image_quality(image)
        document_type = analysis['suggested_document_type']

        return PDFService.get_optimal_dpi(document_type, handwriting)
