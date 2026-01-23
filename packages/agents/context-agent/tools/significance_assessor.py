"""
Significance Assessor - Uses Claude Opus to assess historical significance
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SignificanceAssessor:
    """Assesses historical significance using Claude Opus"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = bool(api_key)

        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info("SignificanceAssessor initialized with Claude Opus")
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.info("SignificanceAssessor running in fallback mode")

    async def assess(self, text: str, context: str = "") -> Dict[str, Any]:
        """
        Assess the historical significance of a document

        Returns significance level and detailed assessment
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

            response = self.client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            assessment_text = response.content[0].text.strip()

            # Parse assessment
            significance_level = self._extract_significance_level(assessment_text)

            logger.info(f"Assessed significance: {significance_level}")

            return {
                "significance_level": significance_level,
                "assessment": assessment_text,
                "confidence": 0.9,
                "model": "claude-opus"
            }

        except Exception as e:
            logger.error(f"Claude Opus error: {e}")
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
