"""
Claude Service - Integration with Anthropic's Claude API

This service handles communication with Claude API and implements
the 4-part Dhamma response protocol defined in SOUL.md.
"""

import anthropic
from flask import current_app
from typing import List, Dict
import requests


class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            if not api_key:
                # Don't raise error here, handle it in generate_dhamma_response
                return None
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def generate_dhamma_response(
        self,
        question: str,
        passages: List[Dict]
    ) -> Dict:
        """
        Generate a strict 8-part Dhamma response using Claude, with Ollama fallback.
        """
        model = current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        response_text = None

        # Build context from passages
        passage_context = self._format_passages_for_context(passages)

        # System prompt implementing strict Samma AI protocol
        system_prompt = self._get_system_prompt()

        # User prompt base
        user_prompt_base = f"""
The user asks: "{question}"

Here are relevant passages from the Tipitaka database:

{passage_context}

Please provide a complete 8-part Dhamma response following the strict protocol defined in your system prompt.
Your output must exactly follow the headers:
1. Direct Definition
2. Samma AI Interpretive Insight
3. Canonical Teachings (Mūla Pāḷi Only)
4. Aṭṭhakathā Commentary
5. Ṭīkā Clarification
6. Lexical & Philological Analysis
7. Doctrinal Function
8. Final Teaching Summary

Important:
- ALL citation citations MUST reference Tipiṭaka Pali Reader (TPR) hierarchy.
- Never reference XML file identifiers.
- If TPR reference data is unavailable, explicitly state: "Exact TPR page/paragraph not available in current database."
"""

        # Try Claude first
        if api_key and self.client:
            try:
                current_app.logger.info(f"Attempting to call Claude API with model {model}")
                response = self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt_base}
                    ]
                )
                response_text = response.content[0].text
            except (anthropic.APIStatusError, ValueError) as e:
                current_app.logger.warning(f"Claude API call failed: {e}. Attempting Ollama fallback.")
        else:
            current_app.logger.warning("ANTHROPIC_API_KEY not configured or client not initialized. Attempting Ollama fallback.")

        # Fallback to Ollama if Claude failed or API key not set
        if response_text is None and current_app.config.get('OLLAMA_ENABLED'):
            try:
                # Prepend system prompt for Ollama as it might not have a dedicated system parameter
                ollama_full_prompt = f"{system_prompt}\n\n{user_prompt_base}"
                response_text = self._generate_ollama_response(ollama_full_prompt)
            except Exception as e:
                current_app.logger.error(f"Ollama fallback failed: {e}")
                raise RuntimeError("Failed to generate response from both Claude and Ollama.")
        elif response_text is None:
            raise RuntimeError("Anthropic API key is not configured and Ollama is not enabled or failed.")

        # Parse response into 8 parts
        return self._parse_dhamma_response(response_text)

    def _generate_ollama_response(self, prompt: str) -> str:
        """Generate response using Ollama API."""
        if not hasattr(self, '_ollama_base_url') or self._ollama_base_url is None: # Lazy load config
            self._ollama_enabled = current_app.config.get('OLLAMA_ENABLED', False)
            self._ollama_base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            self._ollama_model = current_app.config.get('OLLAMA_MODEL', 'llama2')

        if not self._ollama_enabled:
            raise RuntimeError("Ollama is not enabled in configuration.")

        try:
            ollama_url = f"{self._ollama_base_url}/api/chat"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self._ollama_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            current_app.logger.info(f"Attempting to call Ollama API at {ollama_url} with model {self._ollama_model}")
            response = requests.post(ollama_url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            return data['message']['content']
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Ollama API request failed: {e}")
            raise
        except (KeyError, TypeError) as e:
            current_app.logger.error(f"Ollama API response parsing error: {e}")
            raise
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt implementing strict Samma AI protocol."""
        return """You are Samma AI, a scholarly Tipiṭaka assistant connected to a merged database:

1. XML Tipiṭaka (Mūla Pāḷi + Aṭṭhakathā + Ṭīkā)
2. Tipiṭaka Pali Reader (TPR)
   - English translation available only for Mūla Pāḷi
   - No English translation for Aṭṭhakathā or Ṭīkā
   - Includes additional dictionaries and lexical tools

IMPORTANT AUTHORITY RULES:
All citations MUST reference Tipiṭaka Pali Reader (TPR) hierarchy.
Never reference XML file identifiers.
Clearly separate AI interpretation from canonical authority.
Never fabricate page or paragraph numbers.
If TPR reference data is unavailable, explicitly state:
  "Exact TPR page/paragraph not available in current database."

------------------------------------------------------------
1. Direct Definition (Concise Canonical Definition)
------------------------------------------------------------
3–6 lines.
Technical and doctrinally precise.
No storytelling.
No personal interpretation.

------------------------------------------------------------
2. Samma AI Interpretive Insight (Pre-Canonical Reflection)
------------------------------------------------------------
This section contains Samma AI’s synthesized understanding.
It integrates doctrinal principles across Nikāyas.
May use illustrative explanation or conceptual narrative.
Clearly label:
  "Interpretive Insight (Samma AI Synthesis)"
This is NOT canonical text.
No invented quotes.
No fabricated attribution.

------------------------------------------------------------
3. Canonical Teachings (Mūla Pāḷi Only)
------------------------------------------------------------
For each teaching:

Teaching 1
----------
A. Pāḷi Text (short excerpt only)
B. English Translation (from TPR only)
C. Doctrinal Explanation (2–5 lines)
D. TPR Structured Reference Path:

Format strictly as:

Mūla Pāḷi  
→ Sutta Piṭaka  
   → [Nikāya Name]  
      → [Vagga / Paṇṇāsa / Division]  
         → [Subsection if any]  
            → [Sutta Name]  
TPR Page: [Page Number]  
TPR Paragraph: [Paragraph Number]

Repeat for Teaching 2, Teaching 3 if relevant.

Rules:
Prioritize primary Nikāya sources.
Do NOT mix commentary here.
Do NOT include full sutta text.
Only short, relevant excerpts.

------------------------------------------------------------
4. Aṭṭhakathā Commentary
------------------------------------------------------------
For each relevant commentary:

A. Pāḷi excerpt
B. Concise English conceptual summary (NOT translation)
C. TPR Structured Reference Path (Commentary hierarchy)

Clearly label:
"Aṭṭhakathā (Commentarial Authority)"

------------------------------------------------------------
5. Ṭīkā Clarification (If Doctrinally Relevant)
------------------------------------------------------------
Same format as commentary:
Short Pāḷi excerpt
Conceptual clarification
TPR structured reference

Include only if it adds doctrinal nuance.

------------------------------------------------------------
6. Lexical & Philological Analysis
------------------------------------------------------------
Root (Dhātu)
Morphology
Literal meaning
Technical doctrinal meaning
Contextual shifts across Nikāyas (if applicable)
Mention dictionary source (TPR lexical tables if used)

------------------------------------------------------------
7. Doctrinal Function
------------------------------------------------------------
Explain analytically how the concept functions within:
Four Noble Truths
Dependent Origination
Three Characteristics
Path factors (if relevant)

Keep analytical and structured.

------------------------------------------------------------
8. Final Teaching Summary (Samma AI Guided Reflection)
------------------------------------------------------------
This section is Samma AI’s concluding synthesis.

Integrative explanation.
Practical orientation.
Kalyāṇamitta tone (guiding but not devotional).
Show how understanding this concept leads toward liberation.
End with orientation toward Nibbāna as ultimate goal.
No fabricated quotes.
No mystical speculation.

Label clearly:
"Final Guided Reflection (Samma AI)"
"""

    def _format_passages_for_context(self, passages: List[Dict]) -> str:
        """Format database passages for Claude context."""
        if not passages:
            return "No relevant passages found in the database."

        formatted = []
        for i, p in enumerate(passages, 1):
            passage_text = f"""
--- Passage {i} ---
Pali: {p.get('pali_text', 'N/A')}
XML Source: {p.get('xml_source_file', 'N/A')}
Paragraph: {p.get('paragraph_number', 'N/A')}
Title: {p.get('sutta_name', 'N/A')}
Path: {p.get('nikaya_name', '')} > {p.get('book_name', '')}
"""
            formatted.append(passage_text)

        return "\n".join(formatted)

    def _parse_dhamma_response(self, response_text: str) -> Dict:
        """Parse strict 8-part response."""
        parts = {
            'direct_definition': '',
            'interpretive_insight': '',
            'canonical_teachings': [],
            'commentary': '',
            'tika_clarification': '',
            'lexical_analysis': '',
            'doctrinal_function': '',
            'final_summary': '',
            'raw_response': response_text
        }

        # Normalize line endings
        text = response_text.replace('\r\n', '\n')

        # Split using numbered headers (fuzzy matching to be safe)
        import re
        
        # Define the regex pattern for headers
        patterns = [
            (r'1\.\s+Direct Definition', 'direct_definition'),
            (r'2\.\s+Samma AI Interpretive Insight', 'interpretive_insight'),
            (r'3\.\s+Canonical Teachings', 'canonical_teachings'),
            (r'4\.\s+Aṭṭhakathā Commentary', 'commentary'),
            (r'5\.\s+Ṭīkā Clarification', 'tika_clarification'),
            (r'6\.\s+Lexical & Philological Analysis', 'lexical_analysis'),
            (r'7\.\s+Doctrinal Function', 'doctrinal_function'),
            (r'8\.\s+Final Teaching Summary', 'final_summary')
        ]
        
        # Helper to find start index of a section
        def get_start_index(key_idx, content):
            pattern = patterns[key_idx][0]
            match = re.search(pattern, content, re.IGNORECASE)
            return match.start() if match else -1

        # Extract content between headers
        for i in range(len(patterns)):
            key = patterns[i][1]
            start_idx = get_start_index(i, text)
            
            if start_idx == -1:
                continue
                
            # Find end index (start of next section)
            end_idx = len(text)
            for j in range(i + 1, len(patterns)):
                next_start = get_start_index(j, text)
                if next_start != -1:
                    end_idx = next_start
                    break
            
            # Extract content (removing the header itself)
            header_match = re.search(patterns[i][0], text[start_idx:], re.IGNORECASE)
            header_end = start_idx + header_match.end() if header_match else start_idx
            
            content = text[header_end:end_idx].strip()
            # Remove divider lines if present
            content = re.sub(r'^-+$', '', content, flags=re.MULTILINE).strip()
            
            if key == 'canonical_teachings':
                parts['canonical_teachings'] = self._parse_canonical_teachings(content)
            else:
                parts[key] = content

        return parts

    def _parse_canonical_teachings(self, content: str) -> List[Dict]:
        """Parse the Canonical Teachings section."""
        teachings = []
        
        # Split by "Teaching X"
        import re
        teaching_blocks = re.split(r'Teaching\s+\d+', content)
        
        for block in teaching_blocks:
            if not block.strip() or '----------' in block:
                # Skip empty blocks or pure divider blocks if any
                 if not block.strip().replace('-', ''): 
                     continue

            # Basic extraction of A, B, C, D
            teaching = {
                'pali': '',
                'english': '',
                'explanation': '',
                'reference': ''
            }
            
            # Simple regex parser for A/B/C/D structure
            pali_match = re.search(r'A\.\s+Pāḷi Text.*?\n(.*?)(?=B\.)', block, re.DOTALL | re.IGNORECASE)
            eng_match = re.search(r'B\.\s+English Translation.*?\n(.*?)(?=C\.)', block, re.DOTALL | re.IGNORECASE)
            exp_match = re.search(r'C\.\s+Doctrinal Explanation.*?\n(.*?)(?=D\.)', block, re.DOTALL | re.IGNORECASE)
            ref_match = re.search(r'D\.\s+TPR Structured Reference Path.*?\n(.*)', block, re.DOTALL | re.IGNORECASE)
            
            if pali_match: teaching['pali'] = pali_match.group(1).strip()
            if eng_match: teaching['english'] = eng_match.group(1).strip()
            if exp_match: teaching['explanation'] = exp_match.group(1).strip()
            if ref_match: teaching['reference'] = ref_match.group(1).strip()
            
            if teaching['pali'] or teaching['english']:
                teachings.append(teaching)
                
        return teachings

