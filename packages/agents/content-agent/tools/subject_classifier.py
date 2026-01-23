"""
Subject Classifier - Classifies letter by subject taxonomy
"""

import json
import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SubjectClassifier:
    """Classifies documents by subject using Ollama"""

    # Subject taxonomy for historical letters
    SUBJECT_TAXONOMY = [
        'correspondence',
        'administrative',
        'business_transaction',
        'personal_matters',
        'organizational_management',
        'spiritual_practice',
        'educational_content',
        'event_invitation',
        'travel_logistics',
        'historical_documentation'
    ]

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info("SubjectClassifier initialized")

    async def classify(self, text: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """Classify letter by subject"""
        if not text:
            return {"subjects": []}

        prompt = self._build_prompt(text[:2000])

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
                subjects_data = json.loads(result['response'])
                subjects = subjects_data.get('subjects', [])

                # Normalize and validate subjects
                normalized = []
                for subject in subjects:
                    if isinstance(subject, dict):
                        normalized.append({
                            'subject': subject.get('subject', ''),
                            'confidence': subject.get('confidence', 0.7)
                        })
                    else:
                        normalized.append({'subject': str(subject), 'confidence': 0.6})

                logger.info(f"Classified {len(normalized)} subjects")
                return {"subjects": normalized}
            else:
                return self._fallback_classify(text)

        except Exception as e:
            logger.error(f"Error classifying subjects: {e}")
            return self._fallback_classify(text)

    def _build_prompt(self, text: str) -> str:
        """Build prompt for subject classification"""
        taxonomy = ', '.join(self.SUBJECT_TAXONOMY)

        return f"""Classify this historical letter by subject. Choose 1-3 categories from:
{taxonomy}

Letter text:
{text}

Return ONLY valid JSON:
{{
  "subjects": [
    {{
      "subject": "subject_category",
      "confidence": 0.0-1.0,
      "reasoning": "Why this category applies"
    }}
  ]
}}
"""

    def _fallback_classify(self, text: str) -> Dict[str, Any]:
        """Fallback: classify based on keyword matching"""
        text_lower = text.lower()

        subjects = []

        # Check for keyword patterns
        patterns = {
            'correspondence': ['dear', 'sincerely', 'yours', 'recipient', 'sender'],
            'business_transaction': ['payment', 'invoice', 'account', 'transaction', 'business'],
            'personal_matters': ['personal', 'family', 'private', 'personal concerns'],
            'organizational_management': ['meeting', 'committee', 'organization', 'policy', 'management'],
            'spiritual_practice': ['meditation', 'practice', 'dharma', 'vipassana', 'spiritual'],
            'educational_content': ['course', 'training', 'teaching', 'education', 'learn'],
            'event_invitation': ['invited', 'invitation', 'event', 'gathering', 'please join'],
            'travel_logistics': ['travel', 'visit', 'journey', 'route', 'transport'],
        }

        for subject, keywords in patterns.items():
            match_count = sum(1 for keyword in keywords if keyword in text_lower)
            if match_count >= 2:
                subjects.append({
                    'subject': subject,
                    'confidence': min(1.0, match_count / len(keywords)),
                    'reasoning': 'Keyword matching'
                })

        # If no subjects matched, default to correspondence
        if not subjects:
            subjects.append({
                'subject': 'correspondence',
                'confidence': 0.5,
                'reasoning': 'Default classification'
            })

        logger.info(f"Classified {len(subjects)} subjects using fallback")
        return {"subjects": subjects}
