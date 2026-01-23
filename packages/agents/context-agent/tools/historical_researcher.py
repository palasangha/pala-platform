"""
Historical Researcher - Uses Claude Opus to research historical context
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HistoricalResearcher:
    """Researches historical context using Claude Opus"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = bool(api_key)

        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info("HistoricalResearcher initialized with Claude Opus")
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.info("HistoricalResearcher running in fallback mode")

    async def research(
        self,
        text: str,
        people: List[Dict[str, Any]] = None,
        locations: List[Dict[str, Any]] = None,
        events: List[Dict[str, Any]] = None,
        date: str = ""
    ) -> Dict[str, Any]:
        """
        Research historical context for document

        Uses Claude Opus for highest quality contextual analysis
        """
        if not text:
            return {"historical_context": "", "confidence": 0.0}

        if not self.enabled:
            return self._fallback_research(text, date)

        try:
            prompt = self._build_research_prompt(text, people, locations, events, date)

            # Use Claude Opus for highest quality
            response = self.client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            historical_context = response.content[0].text.strip()
            logger.info(f"Generated historical context: {len(historical_context)} chars")

            return {
                "historical_context": historical_context,
                "confidence": 0.95,
                "model": "claude-opus"
            }

        except Exception as e:
            logger.error(f"Claude Opus error: {e}")
            return self._fallback_research(text, date)

    def _build_research_prompt(
        self,
        text: str,
        people: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        date: str
    ) -> str:
        """Build prompt for historical research"""
        context_items = []

        if date:
            context_items.append(f"Date: {date}")

        if people:
            people_names = [p.get('name', '') for p in people[:3] if p.get('name')]
            if people_names:
                context_items.append(f"Key people: {', '.join(people_names)}")

        if locations:
            location_names = [l.get('name', '') for l in locations[:3] if l.get('name')]
            if location_names:
                context_items.append(f"Locations: {', '.join(location_names)}")

        if events:
            event_names = [e.get('name', '') for e in events[:2] if e.get('name')]
            if event_names:
                context_items.append(f"Mentioned events: {', '.join(event_names)}")

        context_section = '\n'.join(context_items) if context_items else "No specific context provided"

        return f"""You are a historian analyzing a historical letter. Provide rich historical context that explains:

1. The historical period and events of the time
2. Relevant cultural, political, or social context
3. How the people, organizations, and locations mentioned fit into broader history
4. Why this correspondence might be significant

Letter excerpt:
{text[:2000]}

Additional context:
{context_section}

Provide 3-4 paragraphs of historical context that illuminate this letter's place in history.
Focus on factual, verifiable historical information. Be specific with dates and events when possible.

Historical context:"""

    def _fallback_research(self, text: str, date: str) -> Dict[str, Any]:
        """Fallback: simple context generation"""
        context = f"This correspondence"
        if date:
            context += f" from {date}"
        context += " represents a historical letter that documents communication in its era."

        return {
            "historical_context": context,
            "confidence": 0.2,
            "model": "fallback"
        }
