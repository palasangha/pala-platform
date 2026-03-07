"""
Claude Service - Integration with Anthropic's Claude API

This service handles communication with Claude API and implements
the 4-part Dhamma response protocol defined in SOUL.md.
"""

import traceback
import logging
import anthropic
import requests
from flask import current_app
from typing import List, Dict

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            if not api_key:
                logger.warning(
                    "[ClaudeService.client] ANTHROPIC_API_KEY is not set — "
                    "Claude API calls will fail. Set the key in .env."
                )
                return None
            try:
                self._client = anthropic.Anthropic(api_key=api_key)
                logger.debug("[ClaudeService.client] Anthropic client initialised.")
            except Exception as exc:
                logger.error(
                    "[ClaudeService.client] Failed to initialise Anthropic client — "
                    "error=%s\n%s", exc, traceback.format_exc(),
                )
                return None
        return self._client

    def generate_dhamma_response(
        self,
        question: str,
        passages: List[Dict],
    ) -> Dict:
        """
        Generate a strict 8-part Dhamma response using Claude, with Ollama fallback.
        """
        model      = current_app.config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        api_key    = current_app.config.get('ANTHROPIC_API_KEY')
        response_text = None

        logger.info(
            "[ClaudeService.generate_dhamma_response] question=%.80r  passages=%d  model=%s",
            question, len(passages), model,
        )

        if not passages:
            logger.warning(
                "[ClaudeService.generate_dhamma_response] No passages provided — "
                "LLM will receive no Tipitaka context for question=%.80r", question,
            )

        # ── Build context ─────────────────────────────────────────────────────
        try:
            passage_context = self._format_passages_for_context(passages)
            logger.debug(
                "[ClaudeService.generate_dhamma_response] Passage context built — "
                "len=%d", len(passage_context),
            )
        except Exception as exc:
            logger.error(
                "[ClaudeService.generate_dhamma_response] _format_passages_for_context FAILED — "
                "error=%s\n%s", exc, traceback.format_exc(),
            )
            raise

        system_prompt   = self._get_system_prompt()
        user_prompt     = self._build_user_prompt(question, passage_context)

        logger.debug(
            "[ClaudeService.generate_dhamma_response] system_prompt_len=%d  "
            "user_prompt_len=%d", len(system_prompt), len(user_prompt),
        )

        # ── STEP 1: Try Claude ────────────────────────────────────────────────
        if api_key and self.client:
            logger.info(
                "[ClaudeService.generate_dhamma_response] STEP 1 — calling Claude API "
                "model=%s ...", model,
            )
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                response_text = response.content[0].text
                logger.info(
                    "[ClaudeService.generate_dhamma_response] STEP 1 OK — "
                    "model=%s  response_len=%d  stop_reason=%s",
                    model, len(response_text),
                    getattr(response, 'stop_reason', 'unknown'),
                )
            except anthropic.APIStatusError as exc:
                logger.warning(
                    "[ClaudeService.generate_dhamma_response] STEP 1 FAILED (APIStatusError) — "
                    "model=%s  status=%s  message=%s\n%s  — will attempt Ollama fallback.",
                    model, exc.status_code, exc.message, traceback.format_exc(),
                )
            except anthropic.APIConnectionError as exc:
                logger.warning(
                    "[ClaudeService.generate_dhamma_response] STEP 1 FAILED (connection) — "
                    "model=%s  error=%s\n%s  — will attempt Ollama fallback.",
                    model, exc, traceback.format_exc(),
                )
            except Exception as exc:
                logger.warning(
                    "[ClaudeService.generate_dhamma_response] STEP 1 FAILED (unexpected) — "
                    "model=%s  error=%s\n%s  — will attempt Ollama fallback.",
                    model, exc, traceback.format_exc(),
                )
        else:
            logger.warning(
                "[ClaudeService.generate_dhamma_response] STEP 1 SKIPPED — "
                "ANTHROPIC_API_KEY not set or client not initialised. "
                "Will attempt Ollama fallback."
            )

        # ── STEP 2: Ollama fallback ───────────────────────────────────────────
        if response_text is None:
            ollama_enabled = current_app.config.get('OLLAMA_ENABLED')
            if ollama_enabled:
                ollama_model = current_app.config.get('OLLAMA_MODEL', 'llama2')
                logger.info(
                    "[ClaudeService.generate_dhamma_response] STEP 2 — trying Ollama "
                    "model=%s ...", ollama_model,
                )
                try:
                    ollama_full_prompt = f"{system_prompt}\n\n{user_prompt}"
                    response_text = self._generate_ollama_response(ollama_full_prompt)
                    logger.info(
                        "[ClaudeService.generate_dhamma_response] STEP 2 OK — "
                        "Ollama model=%s  response_len=%d",
                        ollama_model, len(response_text),
                    )
                except Exception as exc:
                    logger.error(
                        "[ClaudeService.generate_dhamma_response] STEP 2 FAILED — "
                        "Ollama model=%s  error=%s\n%s",
                        ollama_model, exc, traceback.format_exc(),
                    )
                    raise RuntimeError(
                        "Failed to generate response from both Claude and Ollama."
                    ) from exc
            else:
                logger.error(
                    "[ClaudeService.generate_dhamma_response] STEP 2 SKIPPED — "
                    "OLLAMA_ENABLED=False and Claude failed. No model available. "
                    "Set ANTHROPIC_API_KEY or enable Ollama in .env."
                )
                raise RuntimeError(
                    "Anthropic API key is not configured and Ollama is not enabled or failed."
                )

        # ── STEP 3: Parse ─────────────────────────────────────────────────────
        logger.info(
            "[ClaudeService.generate_dhamma_response] STEP 3 — parsing response_len=%d ...",
            len(response_text),
        )
        try:
            parsed = self._parse_dhamma_response(response_text)
            empty = [k for k, v in parsed.items()
                     if k not in ('raw_response', 'canonical_teachings') and not v]
            logger.info(
                "[ClaudeService.generate_dhamma_response] STEP 3 OK — "
                "canonical_teachings=%d  empty_sections=%s",
                len(parsed.get('canonical_teachings', [])), empty,
            )
            if empty:
                logger.warning(
                    "[ClaudeService.generate_dhamma_response] STEP 3 WARNING — "
                    "empty sections: %s. Check if LLM followed the 8-part format. "
                    "raw_response (first 400 chars): %.400s",
                    empty, response_text,
                )
            return parsed
        except Exception as exc:
            logger.error(
                "[ClaudeService.generate_dhamma_response] STEP 3 FAILED — "
                "_parse_dhamma_response raised.  error=%s\n%s",
                exc, traceback.format_exc(),
            )
            raise

    def _build_user_prompt(self, question: str, passage_context: str) -> str:
        return f"""
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

    def _generate_ollama_response(self, prompt: str) -> str:
        """Generate response using Ollama API."""
        if not hasattr(self, '_ollama_base_url') or self._ollama_base_url is None:
            self._ollama_enabled  = current_app.config.get('OLLAMA_ENABLED', False)
            self._ollama_base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            self._ollama_model    = current_app.config.get('OLLAMA_MODEL', 'llama2')

        if not self._ollama_enabled:
            raise RuntimeError("[ClaudeService._generate_ollama_response] Ollama is not enabled in configuration.")

        ollama_url = f"{self._ollama_base_url}/api/chat"
        payload = {
            "model":    self._ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream":   False,
        }
        logger.info(
            "[ClaudeService._generate_ollama_response] POST %s  model=%s  prompt_len=%d",
            ollama_url, self._ollama_model, len(prompt),
        )
        try:
            response = requests.post(
                ollama_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            logger.debug(
                "[ClaudeService._generate_ollama_response] HTTP %s from %s",
                response.status_code, ollama_url,
            )
            response.raise_for_status()
            data = response.json()
            text = data['message']['content']
            logger.info(
                "[ClaudeService._generate_ollama_response] Response received — "
                "model=%s  response_len=%d", self._ollama_model, len(text),
            )
            return text
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 'unknown'
            body   = exc.response.text[:300] if exc.response is not None else ''
            logger.error(
                "[ClaudeService._generate_ollama_response] HTTP error — "
                "url=%s  model=%s  status=%s  body=%.300s  error=%s\n%s",
                ollama_url, self._ollama_model, status, body, exc, traceback.format_exc(),
            )
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error(
                "[ClaudeService._generate_ollama_response] Connection refused — "
                "url=%s  Is Ollama running?  error=%s\n%s",
                ollama_url, exc, traceback.format_exc(),
            )
            raise
        except requests.exceptions.Timeout as exc:
            logger.error(
                "[ClaudeService._generate_ollama_response] Timeout after 300s — "
                "url=%s  model=%s  error=%s", ollama_url, self._ollama_model, exc,
            )
            raise
        except (KeyError, TypeError) as exc:
            logger.error(
                "[ClaudeService._generate_ollama_response] Response parse error — "
                "model=%s  error=%s\n%s", self._ollama_model, exc, traceback.format_exc(),
            )
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
3–6 lines. Technical and doctrinally precise.
No storytelling. No personal interpretation.

------------------------------------------------------------
2. Samma AI Interpretive Insight (Pre-Canonical Reflection)
------------------------------------------------------------
Samma AI's synthesized understanding.
Integrates doctrinal principles across Nikāyas.
Clearly label: "Interpretive Insight (Samma AI Synthesis)"
This is NOT canonical text.

------------------------------------------------------------
3. Canonical Teachings (Mūla Pāḷi Only)
------------------------------------------------------------
For each teaching:

Teaching 1
----------
A. Pāḷi Text (short excerpt only)
B. English Translation (from TPR only)
C. Doctrinal Explanation (2–5 lines)
D. TPR Structured Reference Path

------------------------------------------------------------
4. Aṭṭhakathā Commentary
------------------------------------------------------------
A. Pāḷi excerpt
B. Concise English conceptual summary (NOT translation)
C. TPR Structured Reference Path (Commentary hierarchy)

------------------------------------------------------------
5. Ṭīkā Clarification (If Doctrinally Relevant)
------------------------------------------------------------
Short Pāḷi excerpt + Conceptual clarification + TPR reference.

------------------------------------------------------------
6. Lexical & Philological Analysis
------------------------------------------------------------
Root (Dhātu), Morphology, Literal meaning, Technical doctrinal meaning.

------------------------------------------------------------
7. Doctrinal Function
------------------------------------------------------------
How the concept functions within Four Noble Truths, Dependent Origination,
Three Characteristics, Path factors.

------------------------------------------------------------
8. Final Teaching Summary (Samma AI Guided Reflection)
------------------------------------------------------------
Integrative explanation. Practical orientation.
Kalyāṇamitta tone. End with orientation toward Nibbāna.
Label clearly: "Final Guided Reflection (Samma AI)"
"""

    def _format_passages_for_context(self, passages: List[Dict]) -> str:
        """Format database passages for Claude context."""
        if not passages:
            logger.warning(
                "[ClaudeService._format_passages_for_context] No passages — "
                "returning 'No relevant passages found in the database.'"
            )
            return "No relevant passages found in the database."

        formatted = []
        for i, p in enumerate(passages, 1):
            pali     = p.get('pali_text', 'N/A')
            english  = p.get('english_translation', '')
            source   = p.get('xml_source_file', 'N/A')
            para     = p.get('paragraph_number', 'N/A')
            title    = p.get('sutta_name', 'N/A')
            path     = f"{p.get('nikaya_name', '')} > {p.get('book_name', '')}"

            text = f"\n--- Passage {i} ---\nPali: {pali}\n"
            if english:
                text += f"English: {english}\n"
            text += f"XML Source: {source}\nParagraph: {para}\nTitle: {title}\nPath: {path}\n"

            if not english:
                logger.debug(
                    "[ClaudeService._format_passages_for_context] Passage %d (id=%s) "
                    "has no English translation.", i, p.get('id'),
                )
            formatted.append(text)

        result = "\n".join(formatted)
        logger.debug(
            "[ClaudeService._format_passages_for_context] Built context — "
            "passages=%d  context_len=%d", len(passages), len(result),
        )
        return result

    def _parse_dhamma_response(self, response_text: str) -> Dict:
        """Parse strict 8-part response."""
        import re

        logger.debug(
            "[ClaudeService._parse_dhamma_response] Parsing response_len=%d",
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
            (r'1\.\s+Direct Definition',               'direct_definition'),
            (r'2\.\s+Samma AI Interpretive Insight',   'interpretive_insight'),
            (r'3\.\s+Canonical Teachings',             'canonical_teachings'),
            (r'4\.\s+Aṭṭhakathā Commentary',          'commentary'),
            (r'5\.\s+Ṭīkā Clarification',             'tika_clarification'),
            (r'6\.\s+Lexical & Philological Analysis', 'lexical_analysis'),
            (r'7\.\s+Doctrinal Function',              'doctrinal_function'),
            (r'8\.\s+Final Teaching Summary',          'final_summary'),
        ]

        def get_start_index(key_idx, content):
            match = re.search(patterns[key_idx][0], content, re.IGNORECASE)
            if match:
                return match.start()
            logger.debug(
                "[ClaudeService._parse_dhamma_response] Header NOT FOUND: %r",
                patterns[key_idx][0],
            )
            return -1

        found = []
        for i in range(len(patterns)):
            key       = patterns[i][1]
            start_idx = get_start_index(i, text)
            if start_idx == -1:
                logger.warning(
                    "[ClaudeService._parse_dhamma_response] Section %d (%s) MISSING — "
                    "header not found. LLM did not follow 8-part format.", i + 1, key,
                )
                continue

            end_idx = len(text)
            for j in range(i + 1, len(patterns)):
                ns = get_start_index(j, text)
                if ns != -1:
                    end_idx = ns
                    break

            hm      = re.search(patterns[i][0], text[start_idx:], re.IGNORECASE)
            hend    = start_idx + hm.end() if hm else start_idx
            content = re.sub(r'^-+$', '', text[hend:end_idx].strip(), flags=re.MULTILINE).strip()

            if key == 'canonical_teachings':
                teachings = self._parse_canonical_teachings(content)
                parts['canonical_teachings'] = teachings
                found.append(f"canonical_teachings({len(teachings)})")
                if not teachings:
                    logger.warning(
                        "[ClaudeService._parse_dhamma_response] Section 3 found but "
                        "0 teachings parsed.  content_len=%d  preview=%.200r",
                        len(content), content,
                    )
            else:
                parts[key] = content
                found.append(key if content else f"{key}(EMPTY)")
                if not content:
                    logger.warning(
                        "[ClaudeService._parse_dhamma_response] Section '%s' header found "
                        "but content is empty.", key,
                    )

        logger.info(
            "[ClaudeService._parse_dhamma_response] Parse complete — found=%s", found,
        )
        return parts

    def _parse_canonical_teachings(self, content: str) -> List[Dict]:
        """Parse the Canonical Teachings section."""
        import re
        teachings = []

        blocks = re.split(r'Teaching\s+\d+', content)
        real   = [b for b in blocks if b.strip() and b.strip().replace('-', '').replace('_', '').strip()]

        if not real:
            logger.warning(
                "[ClaudeService._parse_canonical_teachings] No 'Teaching N' markers found. "
                "content_len=%d  preview=%.200r", len(content), content,
            )
            real = [content] if content.strip() else []

        for idx, block in enumerate(real):
            t = {'pali': '', 'english': '', 'explanation': '', 'reference': ''}

            pali_m = re.search(r'[Aa][\.\):]\s*(?:Pāḷi\s+Text)?[:\.\s]*\n?(.+?)(?=\n\s*[Bb][\.\):])', block, re.DOTALL | re.IGNORECASE)
            eng_m  = re.search(r'[Bb][\.\):]\s*(?:English\s+Translation)?[:\.\s\(\w\)]*\n?(.+?)(?=\n\s*[Cc][\.\):])', block, re.DOTALL | re.IGNORECASE)
            exp_m  = re.search(r'[Cc][\.\):]\s*(?:Doctrinal\s+Explanation)?[:\.\s]*\n?(.+?)(?=\n\s*[Dd][\.\):])', block, re.DOTALL | re.IGNORECASE)
            ref_m  = re.search(r'[Dd][\.\):]\s*(?:TPR\s+Structured\s+Reference)?[:\.\s]*\n?(.+)$', block, re.DOTALL | re.IGNORECASE)

            if pali_m: t['pali']        = re.sub(r'^["\'""]', '', pali_m.group(1).strip())
            if eng_m:  t['english']     = re.sub(r'^["\'""]', '', eng_m.group(1).strip())
            if exp_m:  t['explanation'] = exp_m.group(1).strip()
            if ref_m:  t['reference']   = ref_m.group(1).strip()

            if not t['pali'] and not t['english']:
                quoted = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]{10,})["\u201c\u201d]', block)
                if quoted:
                    t['pali'] = quoted[0].strip()
                    if len(quoted) > 1:
                        t['english'] = quoted[1].strip()
                prose = re.sub(r'["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d]', '', block).strip()
                prose = re.sub(r'\*+', '', prose).strip()
                if prose and not t['explanation']:
                    t['explanation'] = prose[:500]
                logger.debug(
                    "[ClaudeService._parse_canonical_teachings] Block %d: used quoted fallback — "
                    "pali=%s  english=%s", idx, bool(t['pali']), bool(t['english']),
                )

            if t['pali'] or t['english']:
                teachings.append(t)
            else:
                logger.warning(
                    "[ClaudeService._parse_canonical_teachings] Block %d all-empty — "
                    "skipping. preview=%.100r", idx, block,
                )

        logger.info(
            "[ClaudeService._parse_canonical_teachings] Parsed %d teachings from %d blocks.",
            len(teachings), len(real),
        )
        return teachings
