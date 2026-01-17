"""
Summarizer - Uses Claude Sonnet to generate high-quality summaries
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Summarizer:
    """Generates summaries using Claude Sonnet"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = bool(api_key)

        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info("Summarizer initialized with Claude API")
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.info("Summarizer running in fallback mode (no API key)")

    async def summarize(self, text: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate summary of letter content using Claude Sonnet

        Returns fallback if Claude is unavailable
        """
        if not text:
            return {"summary": "", "confidence": 0.0}

        if not self.enabled:
            return self._fallback_summarize(text)

        try:
            # Build prompt with context
            prompt = self._build_summary_prompt(text, entities)

            # Call Claude Sonnet (better quality than Haiku for summaries)
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            summary = response.content[0].text.strip()
            logger.info(f"Generated summary: {len(summary)} chars")

            return {
                "summary": summary,
                "confidence": 0.9,
                "model": "claude-sonnet"
            }

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_summarize(text)

    def _build_summary_prompt(self, text: str, entities: Dict[str, Any] = None) -> str:
        """Build prompt for summary generation"""
        entity_context = ""
        if entities:
            people = entities.get('people', [])
            organizations = entities.get('organizations', [])
            if people or organizations:
                entity_context = "\n\nKey entities mentioned:\n"
                for p in people[:3]:
                    entity_context += f"- {p.get('name', '')}\n"
                for o in organizations[:2]:
                    entity_context += f"- {o.get('name', '')}\n"

        return f"""Write a concise 2-3 sentence summary of this historical letter. Focus on:
1. The main purpose or topic
2. Key people involved
3. Main conclusions or requests

Letter text:
{text[:2000]}
{entity_context}

Summary (2-3 sentences, concise and direct):"""

    def _fallback_summarize(self, text: str) -> Dict[str, Any]:
        """Fallback: simple summarization using text extraction"""
        # Very basic fallback: extract first and last paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if len(paragraphs) >= 2:
            summary = f"{paragraphs[0]} {paragraphs[-1]}"
        elif paragraphs:
            summary = paragraphs[0][:200]
        else:
            summary = text[:200]

        return {
            "summary": summary,
            "confidence": 0.3,
            "model": "fallback"
        }
