"""
Base Provider Interface for Metadata Extraction

All metadata extraction providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseMetadataProvider(ABC):
    """Abstract base class for metadata extraction providers"""

    @abstractmethod
    async def extract_metadata(
        self,
        ocr_text: str,
        language: Optional[str] = None,
        document_context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured metadata from OCR text.

        Args:
            ocr_text: OCR-extracted text from document
            language: ISO language code (e.g., "en", "hi")
            document_context: Context hint (e.g., "historical_letter", "monastery_record")
            custom_prompt: Override default extraction prompt

        Returns:
            Dictionary with extracted metadata fields and confidence scores.
            All fields should include "confidence" (0.0-1.0).

            Example structure:
            {
                "document_type": {"value": "letter", "confidence": 0.95},
                "document_date": {"value": "1892-03-15", "confidence": 0.88},
                "parties": {
                    "people": [
                        {"name": "John Smith", "role": "sender", "confidence": 0.92}
                    ],
                    "organizations": [],
                    "confidence": 0.90
                },
                "places": {
                    "locations": [
                        {"name": "London", "role": "origin", "confidence": 0.95}
                    ],
                    "confidence": 0.95
                },
                "storage_location": {
                    "archive": "Pala Sangha",
                    "collection": "Letters",
                    "box": "15",
                    "folder": "3",
                    "confidence": 0.75
                },
                "access_level": {
                    "value": "public",
                    "reasoning": "Historical document, no sensitive info",
                    "confidence": 0.85
                },
                "summary": {
                    "value": "Brief description of document content",
                    "confidence": 0.88
                },
                "key_topics": {
                    "topics": ["Buddhism", "Monastery", "Administration"],
                    "confidence": 0.82
                },
                "tone_sentiment": {
                    "tone": "formal",
                    "sentiment": "neutral",
                    "confidence": 0.80
                },
                "language": "en",
                "notes": "Optional observations"
            }
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available (API keys configured, dependencies installed).

        Returns:
            True if provider can be used, False otherwise
        """
        pass
