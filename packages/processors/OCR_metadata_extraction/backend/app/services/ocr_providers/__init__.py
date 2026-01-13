"""OCR Provider modules"""
from .base_provider import BaseOCRProvider
from .google_vision_provider import GoogleVisionProvider
from .google_lens_provider import GoogleLensProvider
from .serpapi_google_lens_provider import SerpAPIGoogleLensProvider
from .chrome_lens_provider import ChromeLensProvider
from .ollama_provider import OllamaProvider
from .vllm_provider import VLLMProvider
from .azure_provider import AzureComputerVisionProvider
from .tesseract_provider import TesseractProvider
from .easyocr_provider import EasyOCRProvider
from .llamacpp_provider import LlamaCppProvider
from .claude_provider import ClaudeProvider
from .lmstudio_provider import LMStudioProvider
from .langchain_provider import LangChainProvider

__all__ = [
    'BaseOCRProvider',
    'GoogleVisionProvider',
    'GoogleLensProvider',
    'SerpAPIGoogleLensProvider',
    'ChromeLensProvider',
    'OllamaProvider',
    'VLLMProvider',
    'AzureComputerVisionProvider',
    'TesseractProvider',
    'EasyOCRProvider',
    'LlamaCppProvider',
    'ClaudeProvider',
    'LMStudioProvider',
    'LangChainProvider'
]

