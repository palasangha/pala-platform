from abc import ABC, abstractmethod

class BaseOCRProvider(ABC):
    """Base class for OCR providers"""

    @abstractmethod
    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """
        Process image and extract text

        Args:
            image_path: Path to the image file
            languages: List of language codes (e.g., ['en', 'hi'])
            handwriting: Boolean indicating if handwriting detection is needed
            custom_prompt: Optional custom prompt for AI-based providers

        Returns:
            dict: OCR results with structure:
            {
                'text': str,
                'full_text': str,
                'words': list,
                'blocks': list,
                'confidence': float
            }
        """
        pass

    @abstractmethod
    def is_available(self):
        """
        Check if the provider is available and properly configured

        Returns:
            bool: True if provider is available
        """
        pass

    @abstractmethod
    def get_name(self):
        """
        Get the provider name

        Returns:
            str: Provider name
        """
        pass
