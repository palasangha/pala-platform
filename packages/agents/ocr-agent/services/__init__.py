"""
Image optimization service for OCR processing.
Handles image resizing and format conversion.
"""

import logging
import io
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """Service for optimizing images for OCR processing"""
    
    @staticmethod
    def optimize_image(
        image: Image.Image,
        quality: int = 85,
        target_size_mb: float = 5.0,
        auto_optimize: bool = True
    ) -> Image.Image:
        """
        Optimize image for OCR processing
        
        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            target_size_mb: Target file size in MB
            auto_optimize: Whether to apply automatic optimizations
        
        Returns:
            Optimized PIL Image object
        """
        if not auto_optimize:
            return image
        
        # Convert to RGB if needed
        if image.mode not in ('RGB', 'L', 'RGBA'):
            image = image.convert('RGB')
        
        # Check file size
        target_bytes = int(target_size_mb * 1024 * 1024)
        buffer = io.BytesIO()
        img_format = 'JPEG' if image.mode != 'RGBA' else 'PNG'
        image.save(buffer, format=img_format, quality=quality)
        current_size = buffer.tell()
        
        # If already below target, return as-is
        if current_size <= target_bytes:
            logger.debug(f"Image size {current_size/(1024*1024):.2f}MB is within target")
            return image
        
        # Calculate optimal resize
        size_ratio = target_bytes / current_size
        scale = size_ratio ** 0.5
        
        new_width = max(512, int(image.width * scale))
        new_height = max(512, int(image.height * scale))
        
        logger.info(f"Resizing image from {image.width}x{image.height} to {new_width}x{new_height}")
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    @staticmethod
    def optimize_and_encode(
        image: Image.Image,
        quality: int = 85,
        target_size_mb: float = 5.0,
        auto_optimize: bool = True,
        format: str = 'JPEG'
    ) -> bytes:
        """
        Optimize image and encode to bytes
        
        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            target_size_mb: Target file size in MB
            auto_optimize: Whether to apply automatic optimizations
            format: Output format (JPEG, PNG)
        
        Returns:
            Image bytes
        """
        optimized = ImageOptimizer.optimize_image(image, quality, target_size_mb, auto_optimize)
        
        buffer = io.BytesIO()
        # Convert to RGB for JPEG
        if format.upper() == 'JPEG' and optimized.mode != 'RGB':
            optimized = optimized.convert('RGB')
        
        optimized.save(buffer, format=format.upper(), quality=quality)
        return buffer.getvalue()
