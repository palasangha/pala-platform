"""
Document detection and cropping service.
Automatically detects document boundaries and removes background.
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class DocumentDetector:
    """Service for detecting and cropping documents from images"""

    @staticmethod
    def order_points(pts):
        """
        Order points in top-left, top-right, bottom-right, bottom-left order.

        Args:
            pts: Array of 4 points

        Returns:
            Ordered array of points
        """
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left point will have smallest sum
        # Bottom-right point will have largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right point will have smallest difference
        # Bottom-left point will have largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    @staticmethod
    def four_point_transform(image, pts):
        """
        Apply perspective transformation to get top-down view of document.

        Args:
            image: Input image (numpy array)
            pts: Four corner points

        Returns:
            Warped image
        """
        rect = DocumentDetector.order_points(pts)
        (tl, tr, br, bl) = rect

        # Calculate width of new image
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        # Calculate height of new image
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        # Construct destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        # Calculate perspective transform matrix and warp
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        return warped

    @staticmethod
    def detect_document(image: Image.Image, min_area_ratio: float = 0.1) -> Optional[Image.Image]:
        """
        Detect document in image and crop to document boundaries.

        Args:
            image: PIL Image object
            min_area_ratio: Minimum contour area as ratio of image area (default 0.1)

        Returns:
            Cropped PIL Image or None if detection fails
        """
        try:
            # Convert PIL to OpenCV
            img_array = np.array(image)

            # Handle different image modes
            if len(img_array.shape) == 2:  # Grayscale
                gray = img_array
                orig = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:  # RGBA
                orig = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)
            else:  # RGB
                orig = img_array
                gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)

            # Get image dimensions
            height, width = gray.shape
            image_area = height * width

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Apply edge detection
            edged = cv2.Canny(blurred, 50, 150)

            # Dilate edges to close gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edged, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Sort contours by area (largest first)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            document_contour = None

            # Find the largest contour that looks like a document
            for contour in contours[:10]:  # Check top 10 contours
                area = cv2.contourArea(contour)

                # Skip if contour is too small
                if area < image_area * min_area_ratio:
                    continue

                # Approximate contour to polygon
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                # If contour has 4 points, we found a document
                if len(approx) == 4:
                    document_contour = approx
                    logger.info(f"Found document contour with area: {area} ({area/image_area*100:.1f}% of image)")
                    break

            # If no 4-sided contour found, try to find largest rectangular contour
            if document_contour is None:
                for contour in contours[:5]:
                    area = cv2.contourArea(contour)

                    if area < image_area * min_area_ratio:
                        continue

                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = float(w) / h

                    # Check if aspect ratio is reasonable for a document (0.5 to 2.0)
                    if 0.5 <= aspect_ratio <= 2.0:
                        document_contour = np.array([
                            [[x, y]],
                            [[x + w, y]],
                            [[x + w, y + h]],
                            [[x, y + h]]
                        ])
                        logger.info(f"Using bounding rectangle for document (area: {area}, aspect: {aspect_ratio:.2f})")
                        break

            # If document found, apply perspective transform
            if document_contour is not None:
                # Apply four point transform to get top-down view
                warped = DocumentDetector.four_point_transform(orig, document_contour.reshape(4, 2))

                # Convert back to PIL
                cropped_image = Image.fromarray(warped)

                logger.info(f"Successfully cropped document: {image.size} -> {cropped_image.size}")
                return cropped_image
            else:
                logger.warning("No document contour found, returning original image")
                return None

        except Exception as e:
            logger.error(f"Error detecting document: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def auto_crop_document(image: Image.Image, fallback_to_original: bool = True) -> Image.Image:
        """
        Automatically detect and crop document, with fallback to original.

        Args:
            image: PIL Image object
            fallback_to_original: Return original image if detection fails

        Returns:
            Cropped PIL Image (or original if detection fails and fallback enabled)
        """
        cropped = DocumentDetector.detect_document(image)

        if cropped is not None:
            return cropped
        elif fallback_to_original:
            logger.info("Document detection failed, using original image")
            return image
        else:
            raise Exception("Document detection failed and fallback disabled")

    @staticmethod
    def remove_background_simple(image: Image.Image, threshold: int = 240) -> Image.Image:
        """
        Simple background removal by thresholding (works for white backgrounds).

        Args:
            image: PIL Image object
            threshold: Brightness threshold (default 240)

        Returns:
            Image with background removed
        """
        try:
            img_array = np.array(image)

            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Find bounding box of non-white content
            mask = gray < threshold
            coords = np.argwhere(mask)

            if len(coords) == 0:
                logger.warning("No content found, returning original")
                return image

            # Get bounding box
            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0) + 1

            # Add small padding
            padding = 10
            y0 = max(0, y0 - padding)
            x0 = max(0, x0 - padding)
            y1 = min(img_array.shape[0], y1 + padding)
            x1 = min(img_array.shape[1], x1 + padding)

            # Crop
            cropped = img_array[y0:y1, x0:x1]

            return Image.fromarray(cropped)

        except Exception as e:
            logger.error(f"Error in simple background removal: {str(e)}")
            return image
