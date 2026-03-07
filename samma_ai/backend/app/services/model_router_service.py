"""
Model Router Service - Unified interface for multiple AI model providers.

Supports Claude (Anthropic), OpenAI, and local Ollama models with
automatic fallback and discovery.
"""

import traceback
import logging
import requests
import anthropic
from flask import current_app
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


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
            if not api_key:
                logger.warning(
                    "[ModelRouterService._get_claude_client] ANTHROPIC_API_KEY is not set — "
                    "Claude provider will be unavailable."
                )
                return None
            self._claude_client = anthropic.Anthropic(api_key=api_key)
            logger.debug("[ModelRouterService._get_claude_client] Claude client initialised.")
        return self._claude_client

    def _get_openai_client(self):
        if self._openai_client is None:
            api_key = current_app.config.get('OPENAI_API_KEY')
            if not api_key:
                logger.warning(
                    "[ModelRouterService._get_openai_client] OPENAI_API_KEY is not set — "
                    "OpenAI provider will be unavailable."
                )
                return None
            try:
                import openai
                base_url = current_app.config.get('OPENAI_BASE_URL')
                if base_url:
                    self._openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    logger.debug(
                        "[ModelRouterService._get_openai_client] OpenAI client initialised "
                        "with custom base_url=%s", base_url,
                    )
                else:
                    self._openai_client = openai.OpenAI(api_key=api_key)
                    logger.debug("[ModelRouterService._get_openai_client] OpenAI client initialised.")
            except ImportError:
                logger.error(
                    "[ModelRouterService._get_openai_client] 'openai' package is NOT installed. "
                    "Run: pip install openai"
                )
        return self._openai_client

    # ── Model Discovery ───────────────────────────────────────────────

    def list_available_models(self) -> List[Dict]:
        """Return all available models across providers."""
        models: List[ModelInfo] = []

        if not self._cached_ollama_models:
            self.discover_ollama_models()

        claude_key   = current_app.config.get('ANTHROPIC_API_KEY')
        claude_model = current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        models.append(ModelInfo(
            id=claude_model, name=f'Claude ({claude_model})',
            provider='claude', available=bool(claude_key),
        ))

        openai_key   = current_app.config.get('OPENAI_API_KEY')
        openai_model = current_app.config.get('OPENAI_MODEL', 'gpt-4o')
        models.append(ModelInfo(
            id=openai_model, name=f'OpenAI ({openai_model})',
            provider='openai', available=bool(openai_key),
        ))

        copilot_endpoint = current_app.config.get('COPILOT_ENDPOINT')
        if copilot_endpoint:
            models.append(ModelInfo(
                id='copilot', name='Copilot Endpoint',
                provider='copilot', available=True, endpoint=copilot_endpoint,
            ))

        models.extend(self._cached_ollama_models)
        return [m.to_dict() for m in models]

    def discover_ollama_models(self) -> List[Dict]:
        """Query Ollama for locally available models."""
        base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self._cached_ollama_models = []
        logger.debug("[ModelRouterService.discover_ollama_models] Querying %s/api/tags ...", base_url)
        try:
            resp = requests.get(f'{base_url}/api/tags', timeout=5)
            resp.raise_for_status()
            data = resp.json()
            for model in data.get('models', []):
                name = model.get('name', 'unknown')
                self._cached_ollama_models.append(ModelInfo(
                    id=f'ollama:{name}', name=f'Ollama ({name})',
                    provider='ollama', available=True, endpoint=base_url,
                ))
            logger.info(
                "[ModelRouterService.discover_ollama_models] Found %d Ollama models: %s",
                len(self._cached_ollama_models),
                [m.id for m in self._cached_ollama_models],
            )
        except Exception as exc:
            logger.warning(
                "[ModelRouterService.discover_ollama_models] Ollama discovery failed — "
                "base_url=%s  error=%s", base_url, exc,
            )
        return [m.to_dict() for m in self._cached_ollama_models]

    # ── Unified Request Routing ───────────────────────────────────────

    def route_request(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: str = '',
    ) -> str:
        """
        Send a prompt to the specified model. Falls back through the
        provider chain if the requested provider is unavailable.
        """
        model_id = model_id or current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        provider = self._resolve_provider(model_id)

        providers_to_try = [provider]
        if provider != 'ollama':
            fallback_providers = ['copilot', 'claude', 'openai']
            if current_app.config.get('OLLAMA_ENABLED', True):
                fallback_providers.append('ollama')
            for fallback in fallback_providers:
                if fallback not in providers_to_try:
                    providers_to_try.append(fallback)

        logger.info(
            "[ModelRouterService.route_request] model_id=%s  resolved_provider=%s  "
            "fallback_chain=%s  prompt_len=%d  system_prompt_len=%d",
            model_id, provider, providers_to_try, len(prompt), len(system_prompt),
        )

        last_error = None
        for attempt, p in enumerate(providers_to_try, 1):
            logger.info(
                "[ModelRouterService.route_request] Attempt %d/%d — trying provider=%s",
                attempt, len(providers_to_try), p,
            )
            try:
                if p == 'claude':
                    result = self._call_claude(prompt, model_id if provider == 'claude' else None, system_prompt)
                elif p == 'openai':
                    result = self._call_openai(prompt, model_id if provider == 'openai' else None, system_prompt)
                elif p == 'copilot':
                    result = self._call_copilot(prompt, model_id, system_prompt)
                elif p == 'ollama':
                    result = self._call_ollama(prompt, model_id if provider == 'ollama' else None, system_prompt)
                else:
                    logger.warning(
                        "[ModelRouterService.route_request] Unknown provider=%s — skipping.", p,
                    )
                    continue
                logger.info(
                    "[ModelRouterService.route_request] Provider=%s succeeded — "
                    "response_len=%d", p, len(result),
                )
                return result
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[ModelRouterService.route_request] Provider=%s FAILED (attempt %d/%d) — "
                    "error=%s\n%s",
                    p, attempt, len(providers_to_try), exc, traceback.format_exc(),
                )

        logger.error(
            "[ModelRouterService.route_request] ALL providers failed. "
            "chain=%s  last_error=%s", providers_to_try, last_error,
        )
        raise RuntimeError(f'All model providers failed. Last error: {last_error}')

    def test_model(self, model_id: str) -> Dict:
        """Test connectivity to a model provider."""
        logger.info("[ModelRouterService.test_model] Testing model_id=%s", model_id)
        try:
            result = self.route_request('Hello, respond with OK.', model_id)
            logger.info("[ModelRouterService.test_model] model_id=%s  status=ok", model_id)
            return {'model_id': model_id, 'status': 'ok', 'response_preview': result[:100]}
        except Exception as exc:
            logger.error(
                "[ModelRouterService.test_model] model_id=%s FAILED — error=%s\n%s",
                model_id, exc, traceback.format_exc(),
            )
            return {'model_id': model_id, 'status': 'error', 'error': str(exc)}

    def generate_dhamma_response(
        self,
        question: str,
        passages: List[Dict],
        model_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate a strict 8-part Dhamma response using the specified model.
        """
        logger.info(
            "[ModelRouterService.generate_dhamma_response] question=%.80r  "
            "passages=%d  model_id=%s",
            question, len(passages), model_id,
        )

        # ── Build context from passages ───────────────────────────────────────
        # Limit to 5 passages and truncate Pali/English to avoid 413 Payload Too Large
        PASSAGE_LIMIT   = 5
        PALI_MAX_CHARS  = 500
        EN_MAX_CHARS    = 300

        context_parts = []
        for i, passage in enumerate(passages[:PASSAGE_LIMIT], 1):
            pali    = passage.get('pali_text', 'N/A')
            english = passage.get('english_translation', '')
            para    = passage.get('paragraph_number', 'N/A')
            title   = passage.get('sutta_name', 'N/A')
            path    = f"{passage.get('nikaya_name', '')} > {passage.get('book_name', '')}"

            # Truncate long texts to keep payload within API limits
            if len(pali) > PALI_MAX_CHARS:
                pali = pali[:PALI_MAX_CHARS] + '…'
            if english and len(english) > EN_MAX_CHARS:
                english = english[:EN_MAX_CHARS] + '…'

            context_part = (
                f"--- Passage {i} ---\n"
                f"Pali: {pali}\n"
            )
            if english:
                context_part += f"English: {english}\n"
            context_part += (
                f"Paragraph: {para}\n"
                f"Title: {title}\n"
                f"Path: {path}\n"
            )
            context_parts.append(context_part)

        logger.debug(
            "[ModelRouterService.generate_dhamma_response] Context built — "
            "passages_used=%d/%d  context_chars=%d",
            len(context_parts), len(passages),
            sum(len(c) for c in context_parts),
        )

        context = "\n".join(context_parts)

        if not passages:
            logger.warning(
                "[ModelRouterService.generate_dhamma_response] No passages supplied — "
                "LLM will have no Tipitaka context. question=%.80r", question,
            )
        # ── System prompt ─────────────────────────────────────────────────────
        system_prompt = self._get_system_prompt()
        logger.debug(
            "[ModelRouterService.generate_dhamma_response] system_prompt_len=%d",
            len(system_prompt),
        )

        # ── User prompt ───────────────────────────────────────────────────────
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

CRITICAL for section 3 - use EXACTLY this format:
Teaching 1

A. Pāḷi Text
"<pali quote here>"

B. English Translation (TPR)
"<english translation here>"

C. Doctrinal Explanation
<explanation here>

D. TPR Structured Reference Path
<Pitaka → Nikāya → Book → Sutta>

Important:
- ALL citation citations MUST reference Tipiṭaka Pali Reader (TPR) hierarchy.
- Never reference XML file identifiers.
- If TPR reference data is unavailable, explicitly state: "Exact TPR page/paragraph not available in current database."
"""
        logger.debug(
            "[ModelRouterService.generate_dhamma_response] full_prompt_len=%d", len(prompt),
        )

        # ── Route to model ────────────────────────────────────────────────────
        try:
            response_text = self.route_request(prompt, model_id, system_prompt)
            logger.info(
                "[ModelRouterService.generate_dhamma_response] LLM response received — "
                "len=%d  first_100=%.100r",
                len(response_text), response_text,
            )
        except Exception as exc:
            logger.error(
                "[ModelRouterService.generate_dhamma_response] route_request FAILED — "
                "model_id=%s  error=%s\n%s",
                model_id, exc, traceback.format_exc(),
            )
            raise

        # ── Parse 8-part response ─────────────────────────────────────────────
        try:
            parsed = self._parse_dhamma_response(response_text)
            logger.info(
                "[ModelRouterService.generate_dhamma_response] Parsed response — "
                "canonical_teachings=%d  empty_sections=%s",
                len(parsed.get('canonical_teachings', [])),
                [k for k, v in parsed.items() if k != 'raw_response' and not v],
            )
            return parsed
        except Exception as exc:
            logger.error(
                "[ModelRouterService.generate_dhamma_response] _parse_dhamma_response FAILED — "
                "error=%s\n%s", exc, traceback.format_exc(),
            )
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt implementing strict Samma AI protocol."""
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), '../prompts/samma_system_prompt.md')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(
                "[ModelRouterService._get_system_prompt] Loaded from file — len=%d  path=%s",
                len(content), prompt_path,
            )
            return content
        except Exception as exc:
            logger.error(
                "[ModelRouterService._get_system_prompt] FAILED to read prompt file '%s' — "
                "using hardcoded fallback.  error=%s\n%s",
                prompt_path, exc, traceback.format_exc(),
            )
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
        import re

        logger.debug(
            "[ModelRouterService._parse_dhamma_response] Parsing response_len=%d",
            len(response_text),
        )

        parts = {
            'direct_definition': '',
            'interpretive_insight': '',
            'canonical_teachings': [],
            'commentary': '',
            'tika_clarification': '',
            'lexical_analysis': '',
            'doctrinal_function': '',
            'final_summary': '',
            'raw_response': response_text,
        }

        text = response_text.replace('\r\n', '\n')

        patterns = [
            (r'1\.\s+(?:[\*\#_>]*\s*)?Direct Definition',                  'direct_definition'),
            (r'2\.\s+(?:[\*\#_>]*\s*)?Samma AI Interpretive Insight',      'interpretive_insight'),
            (r'3\.\s+(?:[\*\#_>]*\s*)?Canonical Teachings',                'canonical_teachings'),
            (r'4\.\s+(?:[\*\#_>]*\s*)?Aṭṭhakathā Commentary',             'commentary'),
            (r'5\.\s+(?:[\*\#_>]*\s*)?Ṭīkā Clarification',                'tika_clarification'),
            (r'6\.\s+(?:[\*\#_>]*\s*)?Lexical & Philological Analysis',    'lexical_analysis'),
            (r'7\.\s+(?:[\*\#_>]*\s*)?Doctrinal Function',                 'doctrinal_function'),
            (r'8\.\s+(?:[\*\#_>]*\s*)?(?:Final Teaching Summary|Final Guided Reflection)', 'final_summary'),
        ]

        def get_start_index(key_idx, content):
            pattern = patterns[key_idx][0]
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.start()
            logger.debug(
                "[ModelRouterService._parse_dhamma_response] Header NOT FOUND: pattern=%r",
                pattern,
            )
            return -1

        found_sections = []
        for i in range(len(patterns)):
            key = patterns[i][1]
            start_idx = get_start_index(i, text)

            if start_idx == -1:
                logger.warning(
                    "[ModelRouterService._parse_dhamma_response] Section %d (%s) MISSING — "
                    "header pattern not found in LLM response. "
                    "This means the model did not follow the required format.",
                    i + 1, key,
                )
                continue

            end_idx = len(text)
            for j in range(i + 1, len(patterns)):
                next_start = get_start_index(j, text)
                if next_start != -1:
                    end_idx = next_start
                    break

            header_match = re.search(patterns[i][0], text[start_idx:], re.IGNORECASE)
            header_end   = start_idx + header_match.end() if header_match else start_idx

            content = text[header_end:end_idx].strip()
            content = re.sub(r'^-+$', '', content, flags=re.MULTILINE).strip()

            if key == 'canonical_teachings':
                teachings = self._parse_canonical_teachings(content)
                parts['canonical_teachings'] = teachings
                found_sections.append(f"{key}({len(teachings)} teachings)")
                if not teachings:
                    logger.warning(
                        "[ModelRouterService._parse_dhamma_response] Section 3 (canonical_teachings) "
                        "found but parsed 0 teachings. content_len=%d  content_preview=%.200r",
                        len(content), content,
                    )
            else:
                parts[key] = content
                found_sections.append(key if content else f"{key}(EMPTY)")
                if not content:
                    logger.warning(
                        "[ModelRouterService._parse_dhamma_response] Section '%s' found but "
                        "content is EMPTY after stripping. Check LLM output format.", key,
                    )

        logger.info(
            "[ModelRouterService._parse_dhamma_response] Parse complete — "
            "found_sections=%s", found_sections,
        )
        return parts

    def _parse_canonical_teachings(self, content: str) -> List[Dict]:
        """Parse the Canonical Teachings section."""
        import re
        teachings = []
        logger.debug(
            "[ModelRouterService._parse_canonical_teachings] content_len=%d", len(content),
        )

        teaching_blocks = re.split(r'Teaching\s+\d+', content)
        real_blocks = [b for b in teaching_blocks
                       if b.strip() and b.strip().replace('-', '').replace('_', '').strip()]

        if not real_blocks:
            logger.warning(
                "[ModelRouterService._parse_canonical_teachings] No 'Teaching N' markers found "
                "in canonical_teachings section. Treating whole section as one block. "
                "content_preview=%.200r", content,
            )
            real_blocks = [content] if content.strip() else []

        logger.debug(
            "[ModelRouterService._parse_canonical_teachings] %d teaching blocks to parse.",
            len(real_blocks),
        )

        for block_idx, block in enumerate(real_blocks):
            teaching = {'pali': '', 'english': '', 'explanation': '', 'reference': ''}

            pali_match = re.search(
                r'[A-a][\.\):]\s*(?:Pāḷi\s+Text)?[:\.\s]*\n?(.+?)(?=\n\s*[B-b][\.\):])',
                block, re.DOTALL | re.IGNORECASE,
            )
            eng_match = re.search(
                r'[B-b][\.\):]\s*(?:English\s+Translation)?[:\.\s\(\w\)]*\n?(.+?)(?=\n\s*[C-c][\.\):])',
                block, re.DOTALL | re.IGNORECASE,
            )
            exp_match = re.search(
                r'[C-c][\.\):]\s*(?:Doctrinal\s+Explanation)?[:\.\s]*\n?(.+?)(?=\n\s*[D-d][\.\):])',
                block, re.DOTALL | re.IGNORECASE,
            )
            ref_match = re.search(
                r'[D-d][\.\):]\s*(?:TPR\s+Structured\s+Reference)?[:\.\s]*\n?(.+)$',
                block, re.DOTALL | re.IGNORECASE,
            )

            if pali_match:
                teaching['pali'] = re.sub(r'^["\'""]', '', pali_match.group(1).strip())
            if eng_match:
                teaching['english'] = re.sub(r'^["\'""]', '', eng_match.group(1).strip())
            if exp_match:
                teaching['explanation'] = exp_match.group(1).strip()
            if ref_match:
                teaching['reference'] = ref_match.group(1).strip()

            # Fallback: quoted text extraction
            if not teaching['pali'] and not teaching['english']:
                quoted = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]{10,})["\u201c\u201d]', block)
                if quoted:
                    teaching['pali'] = quoted[0].strip()
                    if len(quoted) > 1:
                        teaching['english'] = quoted[1].strip()
                prose = re.sub(r'["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d]', '', block).strip()
                prose = re.sub(r'\*+', '', prose).strip()
                if prose and not teaching['explanation']:
                    teaching['explanation'] = prose[:500]
                logger.debug(
                    "[ModelRouterService._parse_canonical_teachings] Block %d: "
                    "A/B/C/D not found — used quoted-text fallback.  "
                    "pali_found=%s  english_found=%s",
                    block_idx, bool(teaching['pali']), bool(teaching['english']),
                )

            if not teaching['reference']:
                ref_line = re.search(
                    r'((?:Sutta|Vinaya|Abhidhamma)\s*[Pṭ]iṭaka[^\n]*)',
                    block, re.IGNORECASE,
                )
                if ref_line:
                    teaching['reference'] = ref_line.group(1).strip()

            if teaching['pali'] or teaching['english'] or teaching['explanation']:
                teachings.append(teaching)
                logger.debug(
                    "[ModelRouterService._parse_canonical_teachings] Block %d — "
                    "pali=%d chars  english=%d chars  explanation=%d chars  reference=%d chars",
                    block_idx,
                    len(teaching['pali']), len(teaching['english']),
                    len(teaching['explanation']), len(teaching['reference']),
                )
            else:
                logger.warning(
                    "[ModelRouterService._parse_canonical_teachings] Block %d — "
                    "all fields empty, skipping. block_preview=%.100r",
                    block_idx, block,
                )

        logger.info(
            "[ModelRouterService._parse_canonical_teachings] Parsed %d teachings from %d blocks.",
            len(teachings), len(real_blocks),
        )
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
        logger.debug(
            "[ModelRouterService._resolve_provider] model_id=%s did not match any provider — "
            "defaulting to 'claude'", model_id,
        )
        return 'claude'

    def _call_claude(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        client = self._get_claude_client()
        if not client:
            raise RuntimeError(
                '[ModelRouterService._call_claude] Claude API key not configured (ANTHROPIC_API_KEY missing)'
            )
        model = model_id or current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        logger.info(
            "[ModelRouterService._call_claude] Calling Claude — model=%s  prompt_len=%d",
            model, len(prompt),
        )
        kwargs = {
            'model': model,
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        if system_prompt:
            kwargs['system'] = system_prompt
        try:
            response = client.messages.create(**kwargs)
            text = response.content[0].text
            logger.info(
                "[ModelRouterService._call_claude] Response received — "
                "model=%s  response_len=%d  stop_reason=%s",
                model, len(text), getattr(response, 'stop_reason', 'unknown'),
            )
            return text
        except anthropic.APIStatusError as exc:
            logger.error(
                "[ModelRouterService._call_claude] APIStatusError — "
                "model=%s  status=%s  message=%s\n%s",
                model, exc.status_code, exc.message, traceback.format_exc(),
            )
            raise
        except Exception as exc:
            logger.error(
                "[ModelRouterService._call_claude] FAILED — model=%s  error=%s\n%s",
                model, exc, traceback.format_exc(),
            )
            raise

    def _call_openai(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        client = self._get_openai_client()
        if not client:
            raise RuntimeError(
                '[ModelRouterService._call_openai] OpenAI API key not configured (OPENAI_API_KEY missing)'
            )
        model = model_id or current_app.config.get('OPENAI_MODEL', 'gpt-4o')
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        logger.info(
            "[ModelRouterService._call_openai] Calling OpenAI — model=%s  prompt_len=%d",
            model, len(prompt),
        )
        try:
            response = client.chat.completions.create(model=model, messages=messages, max_tokens=4096)
            text = response.choices[0].message.content
            logger.info(
                "[ModelRouterService._call_openai] Response received — "
                "model=%s  response_len=%d  finish_reason=%s",
                model, len(text), response.choices[0].finish_reason,
            )
            return text
        except Exception as exc:
            logger.error(
                "[ModelRouterService._call_openai] FAILED — model=%s  error=%s\n%s",
                model, exc, traceback.format_exc(),
            )
            raise

    def _call_copilot(self, prompt: str, model_id: str, system_prompt: str) -> str:
        endpoint = current_app.config.get('COPILOT_ENDPOINT')
        api_key  = current_app.config.get('COPILOT_API_KEY', '')
        model    = current_app.config.get('COPILOT_MODEL', 'claude-3-5-haiku-20241022')

        if not endpoint:
            raise RuntimeError(
                '[ModelRouterService._call_copilot] COPILOT_ENDPOINT not configured'
            )

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        payload = {'model': model, 'messages': messages, 'max_tokens': 4096}

        logger.info(
            "[ModelRouterService._call_copilot] POST %s  model=%s  prompt_len=%d",
            endpoint, model, len(prompt),
        )
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=120)
            logger.debug(
                "[ModelRouterService._call_copilot] HTTP %s from %s",
                resp.status_code, endpoint,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['message']['content']
            logger.info(
                "[ModelRouterService._call_copilot] Response received — "
                "model=%s  response_len=%d", model, len(text),
            )
            return text
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "[ModelRouterService._call_copilot] HTTP error — "
                "status=%s  body=%.300s  error=%s\n%s",
                exc.response.status_code if exc.response is not None else 'unknown',
                exc.response.text[:300] if exc.response is not None else '',
                exc, traceback.format_exc(),
            )
            raise
        except (KeyError, TypeError, IndexError) as exc:
            logger.error(
                "[ModelRouterService._call_copilot] Response parse error — "
                "body=%.300r  error=%s\n%s",
                resp.text if 'resp' in dir() else '',
                exc, traceback.format_exc(),
            )
            raise
        except Exception as exc:
            logger.error(
                "[ModelRouterService._call_copilot] FAILED — error=%s\n%s",
                exc, traceback.format_exc(),
            )
            raise

    def _call_ollama(self, prompt: str, model_id: Optional[str], system_prompt: str) -> str:
        base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')

        model_name = model_id.replace('ollama:', '') if model_id and model_id.startswith('ollama:') else None

        if not model_name:
            if self._cached_ollama_models:
                model_name = self._cached_ollama_models[0].id.replace('ollama:', '')
                logger.debug(
                    "[ModelRouterService._call_ollama] No explicit model — "
                    "using cached first model: %s", model_name,
                )
            else:
                models = self.discover_ollama_models()
                if models:
                    model_name = models[0]['id'].replace('ollama:', '')
                    logger.debug(
                        "[ModelRouterService._call_ollama] No cache — "
                        "discovered and using: %s", model_name,
                    )
                else:
                    model_name = current_app.config.get('OLLAMA_MODEL', 'llama2')
                    logger.warning(
                        "[ModelRouterService._call_ollama] No Ollama models discovered — "
                        "falling back to config default: %s", model_name,
                    )

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        logger.info(
            "[ModelRouterService._call_ollama] POST %s/api/chat  model=%s  prompt_len=%d",
            base_url, model_name, len(prompt),
        )
        try:
            resp = requests.post(
                f'{base_url}/api/chat',
                json={
                    'model': model_name,
                    'messages': messages,
                    'stream': False,
                    'options': {
                        'num_ctx': 8192,
                        'num_predict': 4096,
                        'temperature': 0.3,
                        'repeat_penalty': 1.1,
                    },
                },
                timeout=300,
            )
            logger.debug(
                "[ModelRouterService._call_ollama] HTTP %s from %s",
                resp.status_code, base_url,
            )
            resp.raise_for_status()
            text = resp.json()['message']['content']
            logger.info(
                "[ModelRouterService._call_ollama] Response received — "
                "model=%s  response_len=%d", model_name, len(text),
            )
            return text
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 'unknown'
            body   = exc.response.text[:300] if exc.response is not None else ''
            logger.error(
                "[ModelRouterService._call_ollama] HTTP error — "
                "status=%s  model=%s  body=%.300s  error=%s\n%s",
                status, model_name, body, exc, traceback.format_exc(),
            )
            # Retry with first available cached model if 404
            if status == 404 and self._cached_ollama_models:
                fallback_model = self._cached_ollama_models[0].id.replace('ollama:', '')
                logger.warning(
                    "[ModelRouterService._call_ollama] Model '%s' not found (404) — "
                    "retrying with first available model '%s'", model_name, fallback_model,
                )
                resp2 = requests.post(
                    f'{base_url}/api/chat',
                    json={'model': fallback_model, 'messages': messages, 'stream': False},
                    timeout=300,
                )
                resp2.raise_for_status()
                return resp2.json()['message']['content']
            raise
        except (KeyError, TypeError) as exc:
            logger.error(
                "[ModelRouterService._call_ollama] Response parse error — "
                "model=%s  error=%s\n%s", model_name, exc, traceback.format_exc(),
            )
            raise
        except Exception as exc:
            logger.error(
                "[ModelRouterService._call_ollama] FAILED — model=%s  error=%s\n%s",
                model_name, exc, traceback.format_exc(),
            )
            raise
