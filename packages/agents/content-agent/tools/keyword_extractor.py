"""
Keyword Extractor - Extracts keywords using Ollama
"""

import json
import logging
import re
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extracts keywords from text using Ollama"""

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info(f"KeywordExtractor initialized with model {model}")

    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract keywords from text"""
        if not text:
            return {"keywords": []}

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
                keywords_data = json.loads(result['response'])
                keywords = keywords_data.get('keywords', [])

                # Normalize keywords
                normalized = [
                    {
                        'keyword': k.get('keyword', k) if isinstance(k, dict) else k,
                        'relevance': k.get('relevance', 0.7) if isinstance(k, dict) else 0.7,
                        'frequency': k.get('frequency', 1) if isinstance(k, dict) else 1
                    }
                    for k in keywords
                ]

                logger.info(f"Extracted {len(normalized)} keywords")
                return {"keywords": normalized}
            else:
                return self._fallback_extract(text)

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return self._fallback_extract(text)

    def _build_prompt(self, text: str) -> str:
        """Build prompt for keyword extraction"""
        return f"""Extract 5-10 important keywords and key concepts from this historical letter.

Letter text:
{text}

Return ONLY valid JSON:
{{
  "keywords": [
    {{
      "keyword": "Key Term",
      "relevance": 0.0-1.0,
      "frequency": number of times mentioned
    }}
  ]
}}

Focus on:
1. Important concepts or themes
2. Specific terms unique to this letter
3. Technical or specialized vocabulary
4. Names of projects, initiatives, or events
"""

    def _fallback_extract(self, text: str) -> Dict[str, Any]:
        """Fallback: extract keywords using word frequency"""
        # Simple word frequency analysis
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter common words
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'it', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we',
            'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }

        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        keywords = [
            {
                'keyword': word,
                'relevance': min(1.0, freq / 10),
                'frequency': freq
            }
            for word, freq in top_keywords
        ]

        logger.info(f"Extracted {len(keywords)} keywords using fallback")
        return {"keywords": keywords}
