"""
Relationship Mapper - Maps relationships and connections between entities
"""

import json
import logging
import re
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class RelationshipMapper:
    """Maps relationships between extracted entities"""

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info("RelationshipMapper initialized")

    async def map_relationships(self, text: str, entities: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map relationships between entities in the document

        Identifies connections like:
        - Person A wrote to Person B
        - Person A works for Organization X
        - Person A located in City Y
        - etc.
        """
        if not text or not entities:
            return {"relationships": []}

        relationships = []

        # Extract people and organizations from entities
        people = entities.get('people', [])
        organizations = entities.get('organizations', [])
        locations = entities.get('locations', [])

        # Build relationships from text patterns
        for person in people:
            name = person.get('name', '')
            if not name:
                continue

            # Look for organization associations
            for org in organizations:
                org_name = org.get('name', '')
                # Check if person and org mentioned together
                pattern = rf'{re.escape(name)}.*?{re.escape(org_name)}|{re.escape(org_name)}.*?{re.escape(name)}'
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    relationships.append({
                        'from': name,
                        'to': org_name,
                        'relationship': 'works_for',
                        'confidence': 0.6,
                        'evidence': 'Co-mentioned in text'
                    })

            # Look for location associations
            for loc in locations:
                loc_name = loc.get('name', '')
                pattern = rf'{re.escape(name)}.*?{re.escape(loc_name)}|{re.escape(loc_name)}.*?{re.escape(name)}'
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    relationships.append({
                        'from': name,
                        'to': loc_name,
                        'relationship': 'located_in',
                        'confidence': 0.6,
                        'evidence': 'Co-mentioned in text'
                    })

        # Add role-based relationships
        sender = None
        recipient = None

        for person in people:
            if person.get('role') == 'sender':
                sender = person.get('name')
            elif person.get('role') == 'recipient':
                recipient = person.get('name')

        if sender and recipient:
            relationships.append({
                'from': sender,
                'to': recipient,
                'relationship': 'writes_to',
                'confidence': 0.95,
                'evidence': 'Sender-recipient relationship'
            })

        logger.info(f"Mapped {len(relationships)} relationships")
        return {"relationships": relationships}
