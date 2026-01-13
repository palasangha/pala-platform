import os
from .ocr_providers import (
    GoogleVisionProvider,
    GoogleLensProvider,
    SerpAPIGoogleLensProvider,
    ChromeLensProvider,
    OllamaProvider,
    VLLMProvider,
    AzureComputerVisionProvider,
    TesseractProvider,
    EasyOCRProvider,
    LlamaCppProvider,
    ClaudeProvider,
    LMStudioProvider,
    LangChainProvider
)

class OCRService:
    """Service for OCR processing with multiple provider support"""

    def __init__(self):
        """Initialize OCR providers"""
        # Initialize all available providers
        self.providers = {
            'google_vision': GoogleVisionProvider(),
            'google_lens': GoogleLensProvider(),
            'serpapi_google_lens': SerpAPIGoogleLensProvider(),
            'chrome_lens': ChromeLensProvider(),
            'azure': AzureComputerVisionProvider(),
            'ollama': OllamaProvider(),
            'vllm': VLLMProvider(),
            'tesseract': TesseractProvider(),
            'easyocr': EasyOCRProvider(),
            'llamacpp': LlamaCppProvider(),
            'claude': ClaudeProvider(),
            'lmstudio': LMStudioProvider(),
            'langchain': LangChainProvider()
        }

        # Set default provider
        self.default_provider = os.getenv('DEFAULT_OCR_PROVIDER', 'google_vision')

    def get_provider(self, provider_name=None):
        """
        Get a specific OCR provider

        Args:
            provider_name: Name of the provider ('google_vision', 'ollama', 'vllm')

        Returns:
            BaseOCRProvider instance

        Raises:
            ValueError if provider not found or not available
        """
        import logging
        logger = logging.getLogger(__name__)

        # If no provider specified, use default
        use_default = provider_name is None
        provider_name = provider_name or self.default_provider

        if provider_name not in self.providers:
            logger.error(f"Unknown OCR provider: {provider_name}")
            # Only fall back if using default provider
            if use_default:
                logger.warning(f"Unknown default provider, falling back to available provider")
                for name, provider in self.providers.items():
                    if provider.is_available():
                        logger.info(f"Using fallback provider: {name}")
                        return provider
            raise ValueError(f"Unknown OCR provider: {provider_name}")

        provider = self.providers[provider_name]

        if not provider.is_available():
            logger.error(f"OCR provider '{provider_name}' is not available")
            # Only fall back if using default provider
            if use_default:
                logger.warning(f"Default provider not available, falling back to available provider")
                for name, provider in self.providers.items():
                    if provider.is_available():
                        logger.info(f"Using fallback provider: {name}")
                        return provider
                raise ValueError(f"No OCR providers available. Please check configuration.")
            # If user explicitly requested this provider, raise error instead of silently falling back
            raise ValueError(f"OCR provider '{provider_name}' is not available. Please check the provider configuration and logs.")

        return provider

    def get_available_providers(self):
        """
        Get list of available OCR providers

        Returns:
            list: List of dicts with provider info
        """
        available = []
        for name, provider in self.providers.items():
            available.append({
                'name': name,
                'available': provider.is_available(),
                'display_name': self._get_display_name(name)
            })
        return available

    def _get_display_name(self, provider_name):
        """Get human-readable display name for provider"""
        display_names = {
            'google_vision': 'Google Cloud Vision',
            'google_lens': 'Google Lens (Advanced)',
            'serpapi_google_lens': 'Google Lens (SerpAPI - Hindi & English)',
            'chrome_lens': 'Chrome Lens (Local - No API Key)',
            'azure': 'Azure Computer Vision',
            'ollama': 'Ollama (Gemma3)',
            'vllm': 'VLLM',
            'tesseract': 'Tesseract OCR',
            'easyocr': 'EasyOCR',
            'llamacpp': 'llama.cpp (Local LLM)',
            'claude': 'Claude AI (Anthropic)',
            'lmstudio': 'LM Studio (Local LLM)',
            'langchain': 'LangChain (Ollama via LangChain)'
        }
        return display_names.get(provider_name, provider_name)

    def process_image(self, image_path, languages=None, handwriting=False, provider=None, custom_prompt=None, job_id=None):
        """
        Process image and extract text using specified provider

        Args:
            image_path: Path to the image file
            languages: List of language codes (e.g., ['en', 'hi'])
            handwriting: Boolean for handwriting detection
            provider: Provider name ('google_vision', 'ollama', 'vllm')
            custom_prompt: Optional custom prompt for AI-based providers
            job_id: Optional job ID for tracking intermediate images

        Returns:
            dict: OCR results with text and metadata
        """
        ocr_provider = self.get_provider(provider)

        try:
            # Check if provider supports job_id parameter (for intermediate image storage)
            import inspect
            sig = inspect.signature(ocr_provider.process_image)
            supports_job_id = 'job_id' in sig.parameters

            if supports_job_id:
                result = ocr_provider.process_image(
                    image_path=image_path,
                    languages=languages,
                    handwriting=handwriting,
                    custom_prompt=custom_prompt,
                    job_id=job_id
                )
            else:
                result = ocr_provider.process_image(
                    image_path=image_path,
                    languages=languages,
                    handwriting=handwriting,
                    custom_prompt=custom_prompt
                )

            # Add provider info to result
            result['provider'] = ocr_provider.get_name()

            return result

        except Exception as e:
            raise Exception(f"OCR processing failed with {ocr_provider.get_name()}: {str(e)}")

    def process_image_with_handwriting(self, image_path, provider=None):
        """
        Process image with handwriting detection (legacy method for compatibility)

        Args:
            image_path: Path to the image file
            provider: Provider name

        Returns:
            dict: OCR results optimized for handwriting
        """
        return self.process_image(
            image_path=image_path,
            languages=None,
            handwriting=True,
            provider=provider
        )
