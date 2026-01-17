"""
Entity Disambiguator - Uses Claude to disambiguate and enrich extracted entities
Handles name disambiguation, role clarification, biographical enhancement
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class EntityDisambiguator:
    """Uses Claude API to disambiguate entities (when API key available)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = bool(api_key)

        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info("EntityDisambiguator initialized with Claude API")
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.info("EntityDisambiguator running in fallback mode (no API key)")

    async def disambiguate_people(self, people: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
        """
        Disambiguate and enrich person entities using Claude

        If Claude is unavailable, returns original people list
        """
        if not self.enabled or not people:
            return people

        try:
            # Build prompt for disambiguation
            prompt = self._build_disambiguation_prompt(people, context)

            # Call Claude Haiku (fast, cheap)
            response = self.client.messages.create(
                model="claude-haiku-4-5-20241001",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            try:
                import json
                result_text = response.content[0].text
                # Extract JSON from response
                json_start = result_text.find('[')
                json_end = result_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    enriched_people = json.loads(json_str)
                    logger.info(f"Disambiguated {len(enriched_people)} people using Claude")
                    return enriched_people
            except Exception as e:
                logger.warning(f"Failed to parse Claude response: {e}")
                return people

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Return original people on error
            return people

    def _build_disambiguation_prompt(self, people: List[Dict[str, Any]], context: str) -> str:
        """Build prompt for Claude to disambiguate people"""
        people_json = '\n'.join([
            f"- {p.get('name', '')}: {p.get('role', '')} ({p.get('title', '')})"
            for p in people
        ])

        return f"""Analyze these people extracted from a historical letter and provide disambiguation:

Context (first 500 chars of letter):
{context[:500]}

Extracted people:
{people_json}

For each person, provide:
1. Confirmed name (handle spelling variations, transliterations)
2. Role clarification
3. Best guess at full identity/biography if recognizable
4. Confidence in the identification

Return ONLY valid JSON array:
[
  {{
    "name": "Full Name",
    "original_name": "As written in document",
    "role": "sender|recipient|mentioned",
    "title": "Position/Title",
    "biography": "Brief biographical info if known",
    "confidence": 0.0-1.0
  }}
]

Do not include any markdown or explanation, just the JSON array.
"""

    async def enrich_with_biography(self, people: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich people with biographical information

        This would typically be called by context-agent (Claude Opus)
        """
        if not self.enabled or not people:
            return people

        # This is a placeholder - actual implementation would call Claude Opus
        # for detailed biographical generation
        return people
