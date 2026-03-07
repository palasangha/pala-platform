"""
Translation Service — Pali to English translation using Ollama + Deepseek

Handles:
- Caching translated Pali passages in SQLite (7-day TTL)
- Calling Deepseek via Ollama for missing translations
- Graceful fallback if Ollama unavailable
- Batch enrichment of passages with translations
"""

import sqlite3
import logging
import time
import traceback
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)


class TranslationService:
    """Translate Pali passages to English using Deepseek via Ollama with caching."""

    def __init__(self):
        """Initialize translation service."""
        self.enabled = current_app.config.get('OLLAMA_TRANSLATION_ENABLED', True)
        self.ollama_endpoint = current_app.config.get('OLLAMA_TRANSLATION_ENDPOINT', 'http://localhost:11434')
        self.model = current_app.config.get('OLLAMA_TRANSLATION_MODEL', 'deepseek-r1:32b')
        self.timeout = current_app.config.get('OLLAMA_TRANSLATION_TIMEOUT', 90)
        self.max_concurrent = current_app.config.get('OLLAMA_TRANSLATION_MAX_CONCURRENT', 1)
        self.cache_ttl = current_app.config.get('TRANSLATION_CACHE_TTL', 604800)  # 7 days
        self.db_path = current_app.config.get('TIPITAKA_DB_PATH', 'database/tipitaka_ultimate.db')

        logger.info(
            "[TranslationService.__init__] Initialized — enabled=%s  model=%s  "
            "endpoint=%s  timeout=%ds  cache_ttl=%ds",
            self.enabled, self.model, self.ollama_endpoint, self.timeout, self.cache_ttl
        )

    def translate_pali_passage(self, pali_text: str, reference: str = None) -> str:
        """
        Translate Pali to English with caching.

        Returns original Pali if:
        - Translation disabled
        - Ollama unavailable
        - Translation fails
        """
        if not self.enabled:
            logger.debug("[TranslationService.translate_pali_passage] Translation disabled")
            return pali_text

        if not pali_text or not pali_text.strip():
            return pali_text

        try:
            # 1. Check cache first
            cached = self._check_cache(pali_text)
            if cached:
                logger.debug(
                    "[TranslationService.translate_pali_passage] Cache hit for pali=%.40s",
                    pali_text
                )
                return cached

            # 2. If Ollama unavailable, return original
            if not self._is_ollama_available():
                logger.warning(
                    "[TranslationService.translate_pali_passage] Ollama unavailable — "
                    "returning original Pali. pali=%.40s", pali_text
                )
                return pali_text

            # 3. Call Deepseek with timeout
            logger.info(
                "[TranslationService.translate_pali_passage] Calling Deepseek for pali=%.40s",
                pali_text
            )
            translation = self._call_deepseek(pali_text)

            # 4. Cache result
            self._save_to_cache(pali_text, translation, reference)
            logger.info(
                "[TranslationService.translate_pali_passage] Translation successful. "
                "pali=%.40s  translation_len=%d", pali_text, len(translation)
            )
            return translation

        except Exception as e:
            logger.warning(
                "[TranslationService.translate_pali_passage] Translation failed — "
                "returning original Pali. pali=%.40s  error=%s",
                pali_text, e
            )
            return pali_text

    def enrich_passages_with_translations(
        self, passages: List[Dict]
    ) -> List[Dict]:
        """
        Ensure all passages have english_text.

        For passages with missing english_text, attempts to translate pali_text.
        Adds 'translation_source' field: 'db' or 'ollama'.
        """
        if not passages:
            return passages

        logger.info(
            "[TranslationService.enrich_passages_with_translations] "
            "Enriching %d passages with translations", len(passages)
        )

        for passage in passages:
            # Mark source as 'db' if already has english_text
            if passage.get('english_text'):
                passage['translation_source'] = 'db'
            else:
                # Attempt translation
                pali = passage.get('pali_text', '')
                if pali.strip():
                    english = self.translate_pali_passage(pali)
                    passage['english_text'] = english
                    passage['translation_source'] = 'ollama'
                else:
                    passage['english_text'] = ''
                    passage['translation_source'] = 'none'

        translated_count = sum(
            1 for p in passages if p.get('translation_source') == 'ollama'
        )
        logger.info(
            "[TranslationService.enrich_passages_with_translations] "
            "Enriched %d passages. translated_with_ollama=%d",
            len(passages), translated_count
        )
        return passages

    # ─────────────────────────── Private methods ────────────────────────────────

    def _check_cache(self, pali_text: str) -> Optional[str]:
        """Check if translation exists in SQLite cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT english_translation, expires_at
                FROM pali_translations
                WHERE pali_text = ?
                LIMIT 1
                """,
                (pali_text,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            english, expires_at_str = row

            # Check if expired
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() > expires_at:
                    logger.debug(
                        "[TranslationService._check_cache] Cache entry expired for pali=%.40s",
                        pali_text
                    )
                    return None

            return english

        except Exception as e:
            logger.warning(
                "[TranslationService._check_cache] Failed to check cache — %s", e
            )
            return None

    def _is_ollama_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            import requests
            response = requests.get(
                f"{self.ollama_endpoint}/api/tags",
                timeout=5
            )
            is_available = response.status_code == 200
            logger.debug(
                "[TranslationService._is_ollama_available] Ollama available=%s",
                is_available
            )
            return is_available
        except Exception as e:
            logger.debug(
                "[TranslationService._is_ollama_available] Ollama check failed — %s", e
            )
            return False

    def _call_deepseek(self, pali_text: str, max_retries: int = 3) -> str:
        """
        Call Deepseek via Ollama to translate Pali passage.

        Returns the translation text or empty string on failure.
        """
        try:
            import requests

            prompt = f"""Translate this Pali text to English. Provide only the English translation, no explanations:

Pali: {pali_text}

English translation:"""

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            logger.debug(
                "[TranslationService._call_deepseek] Calling Ollama at %s with model=%s",
                self.ollama_endpoint, self.model
            )

            response = requests.post(
                f"{self.ollama_endpoint}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                translation = result.get('response', '').strip()
                logger.info(
                    "[TranslationService._call_deepseek] Success. pali=%.40s  translation_len=%d",
                    pali_text, len(translation)
                )
                return translation
            else:
                logger.warning(
                    "[TranslationService._call_deepseek] Non-200 status. "
                    "status=%d  response=%.100s",
                    response.status_code, response.text
                )
                return ""

        except requests.Timeout:
            logger.warning(
                "[TranslationService._call_deepseek] Timeout after %ds. pali=%.40s",
                self.timeout, pali_text
            )
            return ""
        except Exception as e:
            logger.error(
                "[TranslationService._call_deepseek] Failed — pali=%.40s  error=%s\n%s",
                pali_text, e, traceback.format_exc()
            )
            return ""

    def _save_to_cache(self, pali_text: str, english_translation: str, reference: str = None) -> bool:
        """Save translation to SQLite cache with TTL."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(seconds=self.cache_ttl)

            cursor.execute(
                """
                INSERT OR REPLACE INTO pali_translations
                (pali_text, english_translation, reference, model_used, source, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pali_text,
                    english_translation,
                    reference,
                    self.model,
                    'ollama',
                    datetime.utcnow().isoformat(),
                    expires_at.isoformat()
                )
            )
            conn.commit()
            conn.close()

            logger.debug(
                "[TranslationService._save_to_cache] Cached translation for pali=%.40s "
                "expires_at=%s", pali_text, expires_at.isoformat()
            )
            return True

        except Exception as e:
            logger.warning(
                "[TranslationService._save_to_cache] Failed to save to cache — %s", e
            )
            return False
