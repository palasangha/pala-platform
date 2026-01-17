"""
NER Extractor - Extracts named entities using Ollama
Handles: people, organizations, locations, events
"""

import json
import logging
import re
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class NERExtractor:
    """Performs Named Entity Recognition using Ollama"""

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info(f"NERExtractor initialized with model {model}")

    async def extract_people(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract person names from text"""
        if not text:
            return {"people": []}

        prompt = self._build_people_prompt(text[:2000])

        try:
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'format': 'json',
                    'stream': False,
                    'temperature': 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                people_data = json.loads(result['response'])
                people = people_data.get('people', [])

                # Validate and normalize
                normalized = [self._normalize_person(p) for p in people]
                return {"people": normalized}
            else:
                return self._fallback_extract_people(text)

        except Exception as e:
            logger.error(f"Error extracting people: {e}")
            return self._fallback_extract_people(text)

    async def extract_organizations(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract organization names from text"""
        if not text:
            return {"organizations": []}

        prompt = self._build_organizations_prompt(text[:2000])

        try:
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'format': 'json',
                    'stream': False,
                    'temperature': 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                orgs_data = json.loads(result['response'])
                organizations = orgs_data.get('organizations', [])

                normalized = [self._normalize_organization(o) for o in organizations]
                return {"organizations": normalized}
            else:
                return self._fallback_extract_organizations(text)

        except Exception as e:
            logger.error(f"Error extracting organizations: {e}")
            return self._fallback_extract_organizations(text)

    async def extract_locations(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract location names from text"""
        if not text:
            return {"locations": []}

        prompt = self._build_locations_prompt(text[:2000])

        try:
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'format': 'json',
                    'stream': False,
                    'temperature': 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                locs_data = json.loads(result['response'])
                locations = locs_data.get('locations', [])

                normalized = [self._normalize_location(l) for l in locations]
                return {"locations": normalized}
            else:
                return self._fallback_extract_locations(text)

        except Exception as e:
            logger.error(f"Error extracting locations: {e}")
            return self._fallback_extract_locations(text)

    async def extract_events(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract historical events from text"""
        if not text:
            return {"events": []}

        prompt = self._build_events_prompt(text[:2000])

        try:
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'format': 'json',
                    'stream': False,
                    'temperature': 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                events_data = json.loads(result['response'])
                events = events_data.get('events', [])

                normalized = [self._normalize_event(e) for e in events]
                return {"events": normalized}
            else:
                return self._fallback_extract_events(text)

        except Exception as e:
            logger.error(f"Error extracting events: {e}")
            return self._fallback_extract_events(text)

    def _build_people_prompt(self, text: str) -> str:
        """Build prompt for person extraction"""
        return f"""Extract all person names from this historical document. For each person, identify:
1. Full name as written in the document
2. Role or context (sender, recipient, mentioned person)
3. Any titles or positions mentioned

Document text:
{text}

Return ONLY valid JSON (no markdown):
{{
  "people": [
    {{
      "name": "Full Name",
      "role": "sender|recipient|mentioned",
      "title": "Position/Title or empty",
      "context": "Brief context about this person"
    }}
  ]
}}

If no people are mentioned, return {{"people": []}}.
"""

    def _build_organizations_prompt(self, text: str) -> str:
        """Build prompt for organization extraction"""
        return f"""Extract all organizations, institutions, and groups from this historical document.

Document text:
{text}

Return ONLY valid JSON:
{{
  "organizations": [
    {{
      "name": "Organization Name",
      "type": "institution|company|government|religious|other",
      "location": "City, Country or empty"
    }}
  ]
}}
"""

    def _build_locations_prompt(self, text: str) -> str:
        """Build prompt for location extraction"""
        return f"""Extract all geographic locations, cities, countries, and places from this historical document.

Document text:
{text}

Return ONLY valid JSON:
{{
  "locations": [
    {{
      "name": "Place Name",
      "type": "city|country|region|other",
      "context": "How it's mentioned in the text"
    }}
  ]
}}
"""

    def _build_events_prompt(self, text: str) -> str:
        """Build prompt for event extraction"""
        return f"""Extract all historical events mentioned in this document.

Document text:
{text}

Return ONLY valid JSON:
{{
  "events": [
    {{
      "name": "Event Name",
      "date": "Year or date if mentioned, otherwise empty",
      "description": "Brief description from context"
    }}
  ]
}}
"""

    def _normalize_person(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize person object"""
        return {
            'name': person.get('name', ''),
            'role': person.get('role', 'mentioned'),
            'title': person.get('title', ''),
            'context': person.get('context', ''),
            'confidence': 0.7
        }

    def _normalize_organization(self, org: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize organization object"""
        return {
            'name': org.get('name', ''),
            'type': org.get('type', 'other'),
            'location': org.get('location', ''),
            'confidence': 0.7
        }

    def _normalize_location(self, loc: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize location object"""
        return {
            'name': loc.get('name', ''),
            'type': loc.get('type', 'other'),
            'context': loc.get('context', ''),
            'confidence': 0.7
        }

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event object"""
        return {
            'name': event.get('name', ''),
            'date': event.get('date', ''),
            'description': event.get('description', ''),
            'confidence': 0.6
        }

    def _fallback_extract_people(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback: extract people using regex patterns"""
        people = []

        # Look for common salutation patterns
        salutation_match = re.search(r'Dear\s+(?:Mr\.|Mrs\.|Ms\.|Dr\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
        if salutation_match:
            people.append({
                'name': salutation_match.group(1),
                'role': 'recipient',
                'title': '',
                'context': 'Recipient of letter',
                'confidence': 0.6
            })

        # Look for capitalized names
        name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})'
        for match in re.finditer(name_pattern, text[:500]):  # Check first 500 chars
            name = match.group(1)
            if len(name) > 3 and name not in [p['name'] for p in people]:
                people.append({
                    'name': name,
                    'role': 'mentioned',
                    'title': '',
                    'context': 'Mentioned in document',
                    'confidence': 0.5
                })

        return {"people": people[:5]}  # Limit to 5

    def _fallback_extract_organizations(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback: extract organizations using regex"""
        organizations = []

        org_patterns = [
            r'(Vipassana Research Institute|VRI)',
            r'(Institute|Academy|University|College|Organization|Society)\s+(?:for|of)\s+([A-Za-z\s]+)',
            r'(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Institute|Academy|University|Organization)',
        ]

        for pattern in org_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                org_name = match.group(1) if len(match.groups()) == 0 else match.group(1)
                if org_name not in [o['name'] for o in organizations]:
                    organizations.append({
                        'name': org_name,
                        'type': 'institution',
                        'location': '',
                        'confidence': 0.6
                    })

        return {"organizations": organizations[:5]}

    def _fallback_extract_locations(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback: extract locations using regex"""
        locations = []

        # Known locations from context
        known_locations = [
            'India', 'Igatpuri', 'Maharashtra', 'Bombay', 'Delhi',
            'Dhammagiri', 'Bihar', 'Patna'
        ]

        for loc in known_locations:
            if loc in text:
                locations.append({
                    'name': loc,
                    'type': 'location',
                    'context': 'Mentioned in text',
                    'confidence': 0.7
                })

        return {"locations": locations}

    def _fallback_extract_events(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback: extract events using regex"""
        events = []

        # Look for year patterns
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years = re.findall(year_pattern, text)

        if years:
            events.append({
                'name': 'Historical correspondence',
                'date': years[0],
                'description': 'Letter from historical period',
                'confidence': 0.5
            })

        return {"events": events}
