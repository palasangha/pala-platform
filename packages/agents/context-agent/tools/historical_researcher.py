"""
Historical Researcher - Uses Ollama for historical context research
"""

import logging
import os
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HistoricalResearcher:
    """Researches historical context using Ollama"""

    def __init__(self, api_key: Optional[str] = None):
        # Ollama doesn't need API key, but keep parameter for compatibility
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.enabled = True

        # Don't test connection at startup - will test on first use
        logger.info(f"HistoricalResearcher initialized with Ollama ({self.ollama_model})")

    async def research(
        self,
        text: str,
        people: List[Dict[str, Any]] = None,
        locations: List[Dict[str, Any]] = None,
        events: List[Dict[str, Any]] = None,
        date: str = ""
    ) -> Dict[str, Any]:
        """
        Research historical context for document using Ollama
        """
        if not text:
            return {"historical_context": "", "confidence": 0.0}

        if not self.enabled:
            return self._fallback_research(text, date)

        try:
            prompt = self._build_research_prompt(text, people, locations, events, date)

            # Use Ollama for context generation
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000
                    }
                },
                timeout=180
            )
            response.raise_for_status()

            result = response.json()
            historical_context = result.get('response', '').strip()
            logger.info(f"Generated historical context: {len(historical_context)} chars")

            return {
                "historical_context": historical_context,
                "confidence": 0.85,
                "model": f"ollama-{self.ollama_model}"
            }

        except Exception as e:
            logger.error(f"Ollama error: {e}")
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
