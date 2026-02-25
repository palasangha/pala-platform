"""
Model Router Service - Unified interface for multiple AI model providers.

Supports Claude (Anthropic), OpenAI, and local Ollama models with
automatic fallback and discovery.
"""

import requests
import anthropic
from flask import current_app
from typing import List, Dict, Optional


class ModelInfo:
    """Represents an available model."""

    def __init__(self, id: str, name: str, provider: str, available: bool = True, endpoint: str = ''):
        self.id = id
        self.name = name
        self.provider = provider
        self.available = available
        self.endpoint = endpoint

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'available': self.available,
            'endpoint': self.endpoint,
        }


class ModelRouterService:
    """Routes requests to the appropriate AI model provider."""

    def __init__(self):
        self._claude_client = None
        self._openai_client = None
        self._cached_ollama_models: List[ModelInfo] = []

    # ── Provider Clients ──────────────────────────────────────────────

    def _get_claude_client(self):
        if self._claude_client is None:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            if api_key:
                self._claude_client = anthropic.Anthropic(api_key=api_key)
        return self._claude_client

    def _get_openai_client(self):
        if self._openai_client is None:
            api_key = current_app.config.get('OPENAI_API_KEY')
            if api_key:
                try:
                    import openai
                    base_url = current_app.config.get('OPENAI_BASE_URL')
                    if base_url:
                        # Custom OpenAI-compatible endpoint (e.g., LM Studio)
                        self._openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    else:
                        self._openai_client = openai.OpenAI(api_key=api_key)
                except ImportError:
                    current_app.logger.warning("openai package not installed")
        return self._openai_client

    # ── Model Discovery ───────────────────────────────────────────────

    def list_available_models(self) -> List[Dict]:
        """Return all available models across providers."""
        models: List[ModelInfo] = []

        # Discover Ollama models if cache is empty
        if not self._cached_ollama_models:
            self.discover_ollama_models()

        # Claude models
        claude_key = current_app.config.get('ANTHROPIC_API_KEY')
        claude_model = current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        models.append(ModelInfo(
            id=claude_model,
            name=f'Claude ({claude_model})',
            provider='claude',
            available=bool(claude_key),
        ))

        # OpenAI models
        openai_key = current_app.config.get('OPENAI_API_KEY')
        openai_model = current_app.config.get('OPENAI_MODEL', 'gpt-4o')
        models.append(ModelInfo(
            id=openai_model,
            name=f'OpenAI ({openai_model})',
            provider='openai',
            available=bool(openai_key),
        ))
        # Copilot-compatible endpoint (uses OpenAI protocol)
        copilot_endpoint = current_app.config.get('COPILOT_ENDPOINT')
        if copilot_endpoint:
            models.append(ModelInfo(
                id='copilot',
                name='Copilot Endpoint',
                provider='copilot',
                available=True,
                endpoint=copilot_endpoint,
            ))

        # Ollama models (cached)
        models.extend(self._cached_ollama_models)

        return [m.to_dict() for m in models]

    def discover_ollama_models(self) -> List[Dict]:
        """Query Ollama for locally available models."""
        base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self._cached_ollama_models = []

        try:
            resp = requests.get(f'{base_url}/api/tags', timeout=5)
            resp.raise_for_status()
            data = resp.json()

            for model in data.get('models', []):
                name = model.get('name', 'unknown')
                self._cached_ollama_models.append(ModelInfo(
                    id=f'ollama:{name}',
                    name=f'Ollama ({name})',
                    provider='ollama',
                    available=True,
                    endpoint=base_url,
                ))
        except Exception as e:
            current_app.logger.warning(f'Ollama discovery failed: {e}')

        return [m.to_dict() for m in self._cached_ollama_models]

    # ── Unified Request Routing ───────────────────────────────────────

    def route_request(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: str = '',
    ) -> str:
        """
        Send a prompt to the specified model.  Falls back through the
        provider chain if the requested provider is unavailable.
        """
        model_id = model_id or current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

        provider = self._resolve_provider(model_id)

        # Try requested provider, then fallback chain (only enabled providers)
        providers_to_try = [provider]
        fallback_providers = ['copilot', 'claude', 'openai']
        # Only add Ollama if enabled
        if current_app.config.get('OLLAMA_ENABLED', True):
            fallback_providers.append('ollama')

        for fallback in fallback_providers:
            if fallback not in providers_to_try:
                providers_to_try.append(fallback)

        last_error = None
        for p in providers_to_try:
            try:
                if p == 'claude':
                    return self._call_claude(prompt, model_id if provider == 'claude' else None, system_prompt)
                elif p == 'openai':
                    return self._call_openai(prompt, model_id if provider == 'openai' else None, system_prompt)
                elif p == 'copilot':
                    return self._call_copilot(prompt, model_id, system_prompt)
                elif p == 'ollama':
                    return self._call_ollama(prompt, model_id if provider == 'ollama' else None, system_prompt)
            except Exception as e:
                last_error = e
                current_app.logger.warning(f'Provider {p} failed: {e}')
                continue

        raise RuntimeError(f'All model providers failed. Last error: {last_error}')

    def test_model(self, model_id: str) -> Dict:
        """Test connectivity to a model provider."""
        try:
            result = self.route_request('Hello, respond with OK.', model_id)
            return {'model_id': model_id, 'status': 'ok', 'response_preview': result[:100]}
        except Exception as e:
            return {'model_id': model_id, 'status': 'error', 'error': str(e)}

    def generate_dhamma_response(
        self,
        question: str,
        passages: List[Dict],
        model_id: Optional[str] = None
    ) -> Dict:
        """
        Generate a strict 8-part Dhamma response using the specified model.
        """
        # Build context from passages
        context_parts = []
        for i, passage in enumerate(passages[:10], 1):  # Limit to top 10
            pali = passage.get('pali_text', 'N/A')
            source = passage.get('xml_source_file', 'N/A')
            paragraph = passage.get('paragraph_number', 'N/A')
            title = passage.get('sutta_name', 'N/A')
            path = f"{passage.get('nikaya_name', '')} > {passage.get('book_name', '')}"
            
            context_parts.append(
                f"--- Passage {i} ---\n"
                f"Pali: {pali}\n"
                f"XML Source: {source}\n"
                f"Paragraph: {paragraph}\n"
                f"Title: {title}\n"
                f"Path: {path}\n"
            )
        
        context = "\n".join(context_parts)
        
        # System prompt implementing strict Samma AI protocol
        system_prompt = self._get_system_prompt()

        # User prompt base
        prompt = f"""
The user asks: "{question}"

Here are relevant passages from the Tipitaka database:

{context}

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

        # Route to appropriate model
        response_text = self.route_request(prompt, model_id, system_prompt)
        
        # Parse strict 8-part response
        return self._parse_dhamma_response(response_text)

    def _get_system_prompt(self) -> str:
        """Get the system prompt implementing strict Samma AI protocol."""
        import os
        try:
            # Path relative to this service file
            prompt_path = os.path.join(os.path.dirname(__file__), '../prompts/samma_system_prompt.md')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            # Fallback to hardcoded prompt if file read fails (as a safety measure)
            return """You are Samma AI, a scholarly Tipiṭaka assistant connected to a merged database:

1. XML Tipiṭaka (Mūla Pāḷi + Aṭṭhakathā + Ṭīkā)
2. Tipiṭaka Pali Reader (TPR)

IMPORTANT AUTHORITY RULES:
All citations MUST reference Tipiṭaka Pali Reader (TPR) hierarchy.
Never reference XML file identifiers.
Clearly separate AI interpretation from canonical authority.

You must generate a COMPLETE, DETAILED 8-part response.
DO NOT summarize briefly. Provide full scholarly detail for each section.

1. Direct Definition (Concise Canonical Definition)
2. Samma AI Interpretive Insight (Pre-Canonical Reflection)
3. Canonical Teachings (Mūla Pāḷi Only)
4. Aṭṭhakathā Commentary
5. Ṭīkā Clarification
6. Lexical & Philological Analysis
7. Doctrinal Function
8. Final Teaching Summary
"""

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
            (r'1\.\s+(?:[\*\#_>]*\s*)?Direct Definition', 'direct_definition'),
            (r'2\.\s+(?:[\*\#_>]*\s*)?Samma AI Interpretive Insight', 'interpretive_insight'),
            (r'3\.\s+(?:[\*\#_>]*\s*)?Canonical Teachings', 'canonical_teachings'),
            (r'4\.\s+(?:[\*\#_>]*\s*)?Aṭṭhakathā Commentary', 'commentary'),
            (r'5\.\s+(?:[\*\#_>]*\s*)?Ṭīkā Clarification', 'tika_clarification'),
            (r'6\.\s+(?:[\*\#_>]*\s*)?Lexical & Philological Analysis', 'lexical_analysis'),
            (r'7\.\s+(?:[\*\#_>]*\s*)?Doctrinal Function', 'doctrinal_function'),
            (r'8\.\s+(?:[\*\#_>]*\s*)?Final Teaching Summary', 'final_summary')
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
            
            # Flexible regex parser for A/B/C/D structure
            # Matches "A." or "A)" or "A:" followed by label
            pali_match = re.search(r'[A-a][\.\):]\s*(?:Pāḷi Text)?\s*\n?(.*?)(?=[B-b][\.\):])', block, re.DOTALL | re.IGNORECASE)
            eng_match = re.search(r'[B-b][\.\):]\s*(?:English Translation)?\s*\n?(.*?)(?=[C-c][\.\):])', block, re.DOTALL | re.IGNORECASE)
            exp_match = re.search(r'[C-c][\.\):]\s*(?:Doctrinal Explanation)?\s*\n?(.*?)(?=[D-d][\.\):])', block, re.DOTALL | re.IGNORECASE)
            ref_match = re.search(r'[D-d][\.\):]\s*(?:TPR Structured Reference Path)?\s*\n?(.*)', block, re.DOTALL | re.IGNORECASE)
            
            if pali_match: teaching['pali'] = pali_match.group(1).strip()
            if eng_match: teaching['english'] = eng_match.group(1).strip()
            if exp_match: teaching['explanation'] = exp_match.group(1).strip()
            if ref_match: teaching['reference'] = ref_match.group(1).strip()
            
            if teaching['pali'] or teaching['english']:
                teachings.append(teaching)
                
        return teachings

    # ── Private Provider Calls ────────────────────────────────────────

    def _resolve_provider(self, model_id: str) -> str:
        if model_id.startswith('ollama:'):
            return 'ollama'
        if model_id == 'copilot':
            return 'copilot'
        if 'claude' in model_id or 'anthropic' in model_id:
            return 'claude'
        if 'gpt' in model_id or 'o1' in model_id or 'openai' in model_id:
            return 'openai'
        return 'claude'  # default

    def _call_claude(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        client = self._get_claude_client()
        if not client:
            raise RuntimeError('Claude API key not configured')

        model = model_id or current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        kwargs = {'model': model, 'max_tokens': 4096, 'messages': [{'role': 'user', 'content': prompt}]}
        if system_prompt:
            kwargs['system'] = system_prompt

        response = client.messages.create(**kwargs)
        return response.content[0].text

    def _call_openai(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        client = self._get_openai_client()
        if not client:
            raise RuntimeError('OpenAI API key not configured')

        model = model_id or current_app.config.get('OPENAI_MODEL', 'gpt-4o')
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        response = client.chat.completions.create(model=model, messages=messages, max_tokens=4096)
        return response.choices[0].message.content

    def _call_copilot(self, prompt: str, model_id: str, system_prompt: str) -> str:
        endpoint = current_app.config.get('COPILOT_ENDPOINT')
        api_key = current_app.config.get('COPILOT_API_KEY', '')
        model = current_app.config.get('COPILOT_MODEL', 'claude-3-5-haiku-20241022')
        if not endpoint:
            raise RuntimeError('Copilot endpoint not configured')

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        payload = {
            'model': model,
            'messages': messages,
            'max_tokens': 4096
        }

        resp = requests.post(endpoint, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content']

    def _call_ollama(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')

        # Strip ollama: prefix
        model_name = model_id.replace('ollama:', '') if model_id and model_id.startswith('ollama:') else None
        
        # If no model specified or requested model not found, try to use an available one
        if not model_name:
            if self._cached_ollama_models:
                model_name = self._cached_ollama_models[0].id.replace('ollama:', '')
            else:
                # One last attempt to discover
                models = self.discover_ollama_models()
                if models:
                    model_name = models[0]['id'].replace('ollama:', '')
                else:
                    model_name = current_app.config.get('OLLAMA_MODEL', 'llama2')

        full_prompt = f'{system_prompt}\n\n{prompt}' if system_prompt else prompt

        try:
            resp = requests.post(
                f'{base_url}/api/chat',
                json={
                    'model': model_name,
                    'messages': [{'role': 'user', 'content': full_prompt}],
                    'stream': False,
                },
                timeout=300,
            )
            resp.raise_for_status()
            return resp.json()['message']['content']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404 and self._cached_ollama_models:
                # Try again with the first available model
                model_name = self._cached_ollama_models[0].id.replace('ollama:', '')
                current_app.logger.warning(f'Ollama model not found, falling back to {model_name}')
                resp = requests.post(
                    f'{base_url}/api/chat',
                    json={
                        'model': model_name,
                        'messages': [{'role': 'user', 'content': full_prompt}],
                        'stream': False,
                    },
                    timeout=300,
                )
                resp.raise_for_status()
                return resp.json()['message']['content']
            raise
