"""
Biography Generator - Uses Ollama to generate enhanced biographies
"""

import logging
import os
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BiographyGenerator:
    """Generates enhanced biographies using Ollama"""

    def __init__(self, api_key: Optional[str] = None):
        # Ollama doesn't need API key, but keep parameter for compatibility
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.enabled = True

        # Don't test connection at startup - will test on first use
        logger.info(f"BiographyGenerator initialized with Ollama ({self.ollama_model})")

    async def generate(self, people: List[Dict[str, Any]], context: str = "") -> Dict[str, Dict[str, str]]:
        """
        Generate enhanced biographies for key people using Ollama
        """
        if not people:
            return {"biographies": {}}

        if not self.enabled:
            return self._fallback_generate(people)

        biographies = {}

        try:
            for person in people[:5]:  # Limit to 5 people
                name = person.get('name', '')
                if not name:
                    continue

                prompt = self._build_biography_prompt(name, person, context)

                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.6,
                            "num_predict": 300
                        }
                    },
                    timeout=90
                )
                response.raise_for_status()

                result = response.json()
                biography = result.get('response', '').strip()
                biographies[name] = biography
                logger.info(f"Generated biography for {name}")

            return {"biographies": biographies}

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return self._fallback_generate(people)

    def _build_biography_prompt(self, name: str, person_data: Dict[str, Any], context: str) -> str:
        """Build prompt for biography generation"""
        role = person_data.get('role', 'mentioned')
        title = person_data.get('title', '')
        person_context = person_data.get('context', '')

        role_desc = {
            'sender': 'the author/sender',
            'recipient': 'the recipient',
            'mentioned': 'mentioned in the correspondence'
        }.get(role, 'mentioned in the correspondence')

        return f"""Generate a concise biographical sketch (3-4 sentences) for {name}, who is {role_desc} in this letter.

Person details:
- Role: {role}
- Title/Position: {title or 'Not specified'}
- Context: {person_context or 'Not specified'}

Letter context (first 1000 chars):
{context[:1000] if context else 'No additional context'}

Create a biographical paragraph that:
1. Briefly identifies who this person is or was
2. Mentions their role or position
3. If historically recognizable, notes their significance
4. Otherwise, infers their importance from context in the letter

Biographical sketch for {name}:"""

    def _fallback_generate(self, people: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """Fallback: simple biography generation"""
        biographies = {}

        for person in people[:3]:
            name = person.get('name', '')
            if not name:
                continue

            title = person.get('title', '')
            role = person.get('role', 'mentioned')

            if role == 'sender':
                bio = f"{name} is the author and sender of this historical correspondence."
            elif role == 'recipient':
                bio = f"{name} is the recipient of this letter."
            else:
                bio = f"{name} is a person mentioned in this historical correspondence."

            if title:
                bio += f" {title}."

            biographies[name] = bio

        return {"biographies": biographies}
