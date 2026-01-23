"""
Access Level Determiner - Determines document access level (public/restricted/private)
Analyzes content sensitivity to classify access restrictions
"""

import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AccessDeterminer:
    """Determines document access level based on content sensitivity"""

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        """
        Initialize access determiner

        Args:
            ollama_host: Ollama API host URL
            model: Model name for semantic analysis
        """
        self.ollama_host = ollama_host
        self.model = model
        logger.info("AccessDeterminer initialized")

        # Sensitive keywords that indicate restricted/private content
        self.private_keywords = [
            'confidential', 'secret', 'private', 'internal only',
            'not for distribution', 'restricted',
            'personal information', 'ssn', 'social security',
            'medical', 'health', 'diagnosis',
            'financial', 'bank account', 'credit card',
            'password', 'authentication', 'token'
        ]

        self.restricted_keywords = [
            'draft', 'internal', 'preliminary', 'not for public',
            'limited distribution', 'official use',
            'attorney-client', 'privileged', 'work product',
            'proprietary', 'trade secret',
            'personnel file', 'salary', 'performance review'
        ]

        self.public_keywords = [
            'published', 'publicly available', 'open source',
            'press release', 'published in', 'available on', 'website'
        ]

    async def determine(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Determine document access level based on content

        Args:
            text: OCR text from document
            metadata: Optional metadata dictionary

        Returns:
            {
                "access_level": "public|restricted|private",
                "reasoning": str,
                "confidence": float (0-1)
            }
        """
        if metadata is None:
            metadata = {}

        # Check metadata for explicit access level
        if 'access_level' in metadata:
            explicit_level = metadata['access_level'].lower()
            if explicit_level in ['public', 'restricted', 'private']:
                return {
                    'access_level': explicit_level,
                    'reasoning': 'Access level specified in document metadata',
                    'confidence': 0.95
                }

        # Analyze content for sensitivity indicators
        if not text:
            return self._default_access()

        text_lower = text.lower()

        # Check for explicit access markers
        explicit_marker = self._check_explicit_markers(text_lower)
        if explicit_marker:
            return explicit_marker

        # Check for sensitive content keywords
        sensitivity_score = self._calculate_sensitivity_score(text_lower)

        # Determine access level based on sensitivity
        if sensitivity_score >= 0.7:
            return {
                'access_level': 'private',
                'reasoning': 'High sensitivity content: contains personal/confidential information',
                'confidence': 0.85
            }
        elif sensitivity_score >= 0.4:
            return {
                'access_level': 'restricted',
                'reasoning': 'Medium sensitivity content: contains proprietary/internal information',
                'confidence': 0.75
            }
        else:
            return {
                'access_level': 'public',
                'reasoning': 'No significant sensitivity indicators found',
                'confidence': 0.6
            }

    def _check_explicit_markers(self, text_lower: str) -> Dict[str, Any]:
        """Check for explicit access level markers in text"""

        # Check for private markers
        private_markers = [
            r'^\s*\[?\s*private\s*\]?\s*$',
            r'confidential',
            r'for\s+(?:your\s+)?eyes?\s+only',
            r'not?\s+for?\s+(?:public\s+)?distribution',
            r'strictly\s+(?:confidential|private)',
        ]

        for marker in private_markers:
            if re.search(marker, text_lower, re.MULTILINE):
                return {
                    'access_level': 'private',
                    'reasoning': f'Document marked as private/confidential',
                    'confidence': 0.95
                }

        # Check for restricted markers
        restricted_markers = [
            r'restricted',
            r'internal\s+use',
            r'official\s+(?:use|only)',
            r'draft',
            r'work\s+product',
            r'attorney[_-]client',
            r'privileged',
        ]

        for marker in restricted_markers:
            if re.search(marker, text_lower, re.MULTILINE):
                return {
                    'access_level': 'restricted',
                    'reasoning': 'Document marked with restricted access indicators',
                    'confidence': 0.9
                }

        # Check for public markers
        public_markers = [
            r'public\s+domain',
            r'published',
            r'open\s+source',
            r'creative\s+commons',
        ]

        for marker in public_markers:
            if re.search(marker, text_lower, re.MULTILINE):
                return {
                    'access_level': 'public',
                    'reasoning': 'Document marked as public/open access',
                    'confidence': 0.95
                }

        return None

    def _calculate_sensitivity_score(self, text_lower: str) -> float:
        """
        Calculate sensitivity score based on keyword frequency

        Returns: score 0-1 where higher = more sensitive
        """
        words = text_lower.split()

        # Count sensitive keyword matches
        private_count = 0
        restricted_count = 0
        public_count = 0

        for word in words:
            for keyword in self.private_keywords:
                if keyword in word or word in keyword:
                    private_count += 1
            for keyword in self.restricted_keywords:
                if keyword in word or word in keyword:
                    restricted_count += 1
            for keyword in self.public_keywords:
                if keyword in word or word in keyword:
                    public_count += 1

        # Normalize by text length
        text_length = max(len(words), 1)

        # Calculate weighted score
        # Private keywords have weight 1.0, restricted 0.5, public -0.3 (reduces score)
        sensitivity_score = (
            (private_count * 1.0) +
            (restricted_count * 0.5) -
            (public_count * 0.3)
        ) / text_length

        # Clamp to 0-1
        return max(0.0, min(1.0, sensitivity_score))

    def _default_access(self) -> Dict[str, Any]:
        """Return default access level when no text available"""
        return {
            'access_level': 'public',
            'reasoning': 'Default access level (no content available for analysis)',
            'confidence': 0.3
        }
