"""
Biography Generator - Uses Claude Opus to generate enhanced biographies
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BiographyGenerator:
    """Generates enhanced biographies using Claude Opus"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.enabled = bool(api_key)

        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info("BiographyGenerator initialized with Claude Opus")
            except Exception as e:
                logger.warning(f"Could not initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.info("BiographyGenerator running in fallback mode")

    async def generate(self, people: List[Dict[str, Any]], context: str = "") -> Dict[str, Dict[str, str]]:
        """
        Generate enhanced biographies for key people

        Returns dictionary of person name -> biography
        """
        if not people:
            return {"biographies": {}}

        if not self.enabled:
            return self._fallback_generate(people)

        biographies = {}

        try:
            for person in people[:5]:  # Limit to 5 people for cost control
                name = person.get('name', '')
                if not name:
                    continue

                prompt = self._build_biography_prompt(name, person, context)

                response = self.client.messages.create(
                    model="claude-opus-4-20250805",
                    max_tokens=400,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                biography = response.content[0].text.strip()
                biographies[name] = biography
                logger.info(f"Generated biography for {name}")

            return {"biographies": biographies}

        except Exception as e:
            logger.error(f"Claude Opus error: {e}")
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
