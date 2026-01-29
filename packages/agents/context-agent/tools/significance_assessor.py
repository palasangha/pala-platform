"""
Significance Assessor - Uses Ollama to assess historical significance
"""

import logging
import os
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SignificanceAssessor:
    """Assesses historical significance using Ollama"""

    def __init__(self, api_key: Optional[str] = None):
        # Ollama doesn't need API key, but keep parameter for compatibility
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.enabled = True

        # Don't test connection at startup - will test on first use
        logger.info(f"SignificanceAssessor initialized with Ollama ({self.ollama_model})")

    async def assess(self, text: str, context: str = "") -> Dict[str, Any]:
        """
        Assess the historical significance of a document using Ollama
        """
        if not text:
            return {
                "significance_level": "unknown",
                "assessment": "",
                "confidence": 0.0
            }

        if not self.enabled:
            return self._fallback_assess(text)

        try:
            prompt = self._build_assessment_prompt(text, context)

            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 500
                    }
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            assessment_text = result.get('response', '').strip()

            # Parse assessment
            significance_level = self._extract_significance_level(assessment_text)

            logger.info(f"Assessed significance: {significance_level}")

            return {
                "significance_level": significance_level,
                "assessment": assessment_text,
                "confidence": 0.8,
                "model": f"ollama-{self.ollama_model}"
            }

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return self._fallback_assess(text)

    def _build_assessment_prompt(self, text: str, context: str) -> str:
        """Build prompt for significance assessment"""
        return f"""Assess the historical significance of this letter. Rate it as:
- High: Reveals significant historical events, important figures, or major decisions
- Medium: Documents routine but historically relevant correspondence, provides insights into daily life/practices
- Low: Personal or administrative matter with limited historical importance

Letter excerpt:
{text[:2000]}

{f"Additional context: {context[:500]}" if context else ""}

Provide your assessment in this format:
Significance Level: [HIGH/MEDIUM/LOW]
Reasoning: [2-3 sentences explaining why]
Historical Impact: [Brief description of potential impact]

Assessment:"""

    def _extract_significance_level(self, text: str) -> str:
        """Extract significance level from assessment text"""
        text_upper = text.upper()
        if 'HIGH' in text_upper:
            return 'high'
        elif 'MEDIUM' in text_upper:
            return 'medium'
        elif 'LOW' in text_upper:
            return 'low'
        else:
            return 'unknown'

    def _fallback_assess(self, text: str) -> Dict[str, Any]:
        """Fallback: simple significance assessment"""
        # Very basic heuristic
        text_length = len(text)
        if text_length > 1000:
            level = 'medium'
        elif text_length > 500:
            level = 'low'
        else:
            level = 'low'

        return {
            "significance_level": level,
            "assessment": "Document contains historical correspondence of moderate interest.",
            "confidence": 0.2,
            "model": "fallback"
        }
