"""
Metadata Extraction Providers

Pluggable providers for different AI models to extract metadata from OCR text.
Each provider implements the BaseMetadataProvider interface.

Available providers:
- ClaudeMetadataProvider: Uses Anthropic Claude API
- OllamaMetadataProvider: Uses local Ollama models
- (Future) GeminiMetadataProvider: Uses Google Gemini API
- (Future) OpenAIMetadataProvider: Uses OpenAI GPT models
"""

from .base_provider import BaseMetadataProvider
from .claude_provider import ClaudeMetadataProvider
from .ollama_provider import OllamaMetadataProvider

__all__ = ["BaseMetadataProvider", "ClaudeMetadataProvider", "OllamaMetadataProvider"]
