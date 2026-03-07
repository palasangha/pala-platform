"""
Tipitaka Service - Interface to the Tipitaka SQLite database

This service provides access to the canonical Buddhist texts stored in
tipitaka_ultimate.db (1.1 GB, 73,765 Pali passages, 74,050 English translations).

Search strategy (hybrid):
  1. semantic_search() — vector similarity via Qdrant (multilingual-e5-large)
  2. _fts5_search()     — exact Pali terms via SQLite FTS5 (paragraphs_fts)
  3. _reciprocal_rank_fusion() — merge both result lists into a single ranking
"""

import sqlite3
import logging
from flask import current_app
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class TipitakaService:
    """Service for querying the Tipitaka database."""

    def __init__(self):
        self._db_path = None

    @property
    def db_path(self):
        if self._db_path is None:
            self._db_path = current_app.config.get('TIPITAKA_DB_PATH')
        return self._db_path

    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def _dict_factory(self, cursor, row):
        """Convert row to dictionary."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def search_relevant_passages(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Hybrid search: vector (Qdrant) + FTS5 (SQLite), merged via Reciprocal Rank Fusion.

        Falls back to keyword LIKE search if Qdrant is unavailable.
        """
        import traceback
        logger.info(
            "[TipitakaService.search_relevant_passages] query=%.80r  limit=%d",
            query, limit,
        )

        # Step 1: Semantic vector search via Qdrant
        vector_results = []
        try:
            vector_results = self.semantic_search(query, limit=5)
            logger.info(
                "[TipitakaService.search_relevant_passages] Vector search returned %d results.",
                len(vector_results),
            )
        except Exception as exc:
            logger.warning(
                "[TipitakaService.search_relevant_passages] Vector search FAILED — "
                "falling back to keyword search.  error=%s\n%s",
                exc, traceback.format_exc(),
            )
            keyword_results = self._keyword_search(query, limit=limit)
            logger.info(
                "[TipitakaService.search_relevant_passages] Keyword fallback returned %d results.",
                len(keyword_results),
            )
            return keyword_results

        # Step 2: FTS5 exact-term search
        fts_results = self._fts5_search(query, limit=5)
        logger.info(
            "[TipitakaService.search_relevant_passages] FTS5 search returned %d results.",
            len(fts_results),
        )

        # Step 3: Hybrid merge, or last-resort keyword search
        if not vector_results and not fts_results:
            logger.warning(
                "[TipitakaService.search_relevant_passages] Both vector and FTS5 returned "
                "zero results — falling back to keyword LIKE search.  query=%.80r", query,
            )
            keyword_results = self._keyword_search(query, limit=limit)
            logger.info(
                "[TipitakaService.search_relevant_passages] Keyword fallback returned %d results.",
                len(keyword_results),
            )
            return keyword_results

        merged = self._reciprocal_rank_fusion(vector_results, fts_results)
        final = merged[:limit]
        logger.info(
            "[TipitakaService.search_relevant_passages] Hybrid merge: "
            "vector=%d  fts5=%d  merged=%d  returning=%d",
            len(vector_results), len(fts_results), len(merged), len(final),
        )
        return final

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Pure vector search: embed query → Qdrant cosine similarity → fetch full rows.
        """
        import traceback
        logger.debug(
            "[TipitakaService.semantic_search] query=%.80r  limit=%d", query, limit,
        )

        qdrant = current_app.extensions.get('qdrant')
        embedding_service = current_app.extensions.get('embedding_service')
        collection = current_app.config.get('QDRANT_COLLECTION', 'tipitaka_mula')

        if qdrant is None:
            logger.error(
                "[TipitakaService.semantic_search] qdrant extension is None — "
                "Qdrant was not initialised (check startup logs for connection errors)."
            )
            raise RuntimeError("Qdrant client not initialised in app.extensions['qdrant']")

        if embedding_service is None:
            logger.error(
                "[TipitakaService.semantic_search] embedding_service extension is None — "
                "EmbeddingService was not initialised (check startup logs)."
            )
            raise RuntimeError("EmbeddingService not initialised in app.extensions['embedding_service']")

        # Encode the query
        try:
            query_vector = embedding_service.encode_query(query)
            logger.debug(
                "[TipitakaService.semantic_search] Query encoded — vector dim=%d",
                len(query_vector),
            )
        except Exception as exc:
            logger.error(
                "[TipitakaService.semantic_search] Query encoding FAILED — "
                "query=%.80r  error=%s\n%s", query, exc, traceback.format_exc(),
            )
            raise

        # Search Qdrant
        try:
            result = qdrant.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            hits = result.points
            logger.debug(
                "[TipitakaService.semantic_search] Qdrant returned %d hits for collection='%s'",
                len(hits), collection,
            )
        except Exception as exc:
            logger.error(
                "[TipitakaService.semantic_search] Qdrant search FAILED — "
                "collection=%s  error=%s\n%s", collection, exc, traceback.format_exc(),
            )
            raise

        if not hits:
            logger.warning(
                "[TipitakaService.semantic_search] Qdrant returned 0 hits — "
                "collection may be empty.  query=%.80r", query,
            )
            return []

        # Log top-3 hit scores for diagnostics
        for i, h in enumerate(hits[:3]):
            logger.debug(
                "[TipitakaService.semantic_search] Hit %d: passage_id=%s  score=%.4f  "
                "pali_snippet=%.60s",
                i + 1, h.payload.get('passage_id'), h.score,
                h.payload.get('pali_text', ''),
            )

        # Fetch full rows from SQLite by passage_id
        passage_ids = [h.payload['passage_id'] for h in hits]
        try:
            passages = self._fetch_passages_by_ids(passage_ids)
        except Exception as exc:
            logger.error(
                "[TipitakaService.semantic_search] _fetch_passages_by_ids FAILED — "
                "ids=%s  error=%s\n%s", passage_ids, exc, traceback.format_exc(),
            )
            raise

        if len(passages) != len(passage_ids):
            logger.warning(
                "[TipitakaService.semantic_search] Qdrant returned %d hits but only %d "
                "found in SQLite — some passage_ids may be stale.  missing=%s",
                len(passage_ids), len(passages),
                set(passage_ids) - {p['id'] for p in passages},
            )

        # Preserve Qdrant ranking order
        id_order = {pid: idx for idx, pid in enumerate(passage_ids)}
        passages.sort(key=lambda p: id_order.get(p['id'], 999))
        return passages

    def _fts5_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        FTS5 search using the paragraphs_fts virtual table.
        Good for exact Pali term matches and diacritical-normalised queries.
        """
        import traceback
        logger.debug(
            "[TipitakaService._fts5_search] query=%.80r  limit=%d", query, limit,
        )

        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        try:
            cursor = conn.cursor()

            # Build a simple FTS5 query from the first few terms
            terms = self._extract_search_terms(query)
            if not terms:
                logger.debug(
                    "[TipitakaService._fts5_search] No search terms extracted from query=%.80r "
                    "— returning empty.", query,
                )
                return []

            fts_query = ' OR '.join(f'"{t}"' for t in terms[:3])
            logger.debug(
                "[TipitakaService._fts5_search] terms=%s  fts_query=%r",
                terms, fts_query,
            )

            try:
                cursor.execute("""
                    SELECT
                        par.id,
                        par.pali_text,
                        par.html_content,
                        par.xml_source_file,
                        par.paragraph_number,
                        par.book_id,
                        par.sutta_id,
                        pk.name_english  AS pitaka_name,
                        n.name_english   AS nikaya_name,
                        b.name_english   AS book_name,
                        s.name_english   AS sutta_name
                    FROM paragraphs par
                    JOIN paragraphs_fts f ON par.id = f.paragraph_id
                    LEFT JOIN books b     ON par.book_id = b.id
                    LEFT JOIN nikayas n   ON b.nikaya_id = n.id
                    LEFT JOIN pitakas pk  ON b.pitaka_id = pk.id
                    LEFT JOIN suttas s    ON par.sutta_id = s.id
                    WHERE paragraphs_fts MATCH ?
                      AND par.text_layer = 'mula'
                    ORDER BY rank
                    LIMIT ?
                """, [fts_query, limit])
                passages = cursor.fetchall()
                logger.debug(
                    "[TipitakaService._fts5_search] FTS5 returned %d passages for fts_query=%r",
                    len(passages), fts_query,
                )
            except sqlite3.OperationalError as exc:
                logger.warning(
                    "[TipitakaService._fts5_search] FTS5 query FAILED — "
                    "fts_query=%r  error=%s\n%s", fts_query, exc, traceback.format_exc(),
                )
                return []

            for passage in passages:
                passage['reference'] = self._build_reference(passage)
                passage['english_translation'] = self._fetch_translation(
                    cursor, passage['book_id'], passage['paragraph_number']
                )
            return passages
        finally:
            conn.close()

    def _fetch_passages_by_ids(self, passage_ids: List[str]) -> List[Dict]:
        """Fetch full passage rows from SQLite given a list of paragraph IDs."""
        import traceback
        if not passage_ids:
            logger.debug("[TipitakaService._fetch_passages_by_ids] Called with empty id list.")
            return []

        logger.debug(
            "[TipitakaService._fetch_passages_by_ids] Fetching %d passages: %s",
            len(passage_ids), passage_ids,
        )
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        try:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(passage_ids))
            cursor.execute(f"""
                SELECT
                    par.id,
                    par.pali_text,
                    par.html_content,
                    par.xml_source_file,
                    par.paragraph_number,
                    par.book_id,
                    par.sutta_id,
                    pk.name_english  AS pitaka_name,
                    n.name_english   AS nikaya_name,
                    b.name_english   AS book_name,
                    s.name_english   AS sutta_name
                FROM paragraphs par
                LEFT JOIN books b     ON par.book_id = b.id
                LEFT JOIN nikayas n   ON b.nikaya_id = n.id
                LEFT JOIN pitakas pk  ON b.pitaka_id = pk.id
                LEFT JOIN suttas s    ON par.sutta_id = s.id
                WHERE par.id IN ({placeholders})
            """, passage_ids)
            passages = cursor.fetchall()
            logger.debug(
                "[TipitakaService._fetch_passages_by_ids] SQLite returned %d/%d passages.",
                len(passages), len(passage_ids),
            )

            for passage in passages:
                passage['reference'] = self._build_reference(passage)
                passage['english_translation'] = self._fetch_translation(
                    cursor, passage['book_id'], passage['paragraph_number']
                )
            return passages
        except Exception as exc:
            logger.error(
                "[TipitakaService._fetch_passages_by_ids] FAILED — "
                "ids=%s  error=%s\n%s", passage_ids, exc, traceback.format_exc(),
            )
            raise
        finally:
            conn.close()

    def _reciprocal_rank_fusion(self, *result_lists, k: int = 60) -> List[Dict]:
        """
        Merge multiple ranked result lists using Reciprocal Rank Fusion.
        score(d) = Σ 1/(rank(d) + k)
        """
        scores: Dict[str, float] = {}
        id_to_passage: Dict[str, Dict] = {}

        for list_idx, result_list in enumerate(result_lists):
            for rank, passage in enumerate(result_list):
                pid = passage['id']
                contrib = 1.0 / (rank + k)
                scores[pid] = scores.get(pid, 0.0) + contrib
                if pid not in id_to_passage:
                    id_to_passage[pid] = passage
                logger.debug(
                    "[TipitakaService._reciprocal_rank_fusion] list=%d  rank=%d  "
                    "passage_id=%s  contrib=%.5f  total_score=%.5f",
                    list_idx, rank, pid, contrib, scores[pid],
                )

        sorted_ids = sorted(scores, key=lambda pid: scores[pid], reverse=True)
        logger.debug(
            "[TipitakaService._reciprocal_rank_fusion] Merged %d unique passages.",
            len(sorted_ids),
        )
        return [id_to_passage[pid] for pid in sorted_ids]

    def _keyword_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Legacy LIKE-based keyword search — fallback when Qdrant is unavailable.
        """
        import traceback
        logger.info(
            "[TipitakaService._keyword_search] query=%.80r  limit=%d", query, limit,
        )
        conn = self._get_connection()
        conn.row_factory = self._dict_factory

        try:
            cursor = conn.cursor()

            terms = self._extract_search_terms(query)
            logger.debug(
                "[TipitakaService._keyword_search] Extracted terms: %s", terms,
            )

            expanded_terms = []
            for term in terms:
                expanded_terms.append(term)
                expanded_terms.extend(self._get_pali_diacritical_variants(term))

            logger.debug(
                "[TipitakaService._keyword_search] Expanded terms (with diacritics): %s",
                expanded_terms,
            )

            where_clauses = []
            params = []
            for term in expanded_terms:
                where_clauses.append("(pali_text LIKE ? OR html_content LIKE ?)")
                params.extend([f'%{term}%', f'%{term}%'])

            if not where_clauses:
                logger.warning(
                    "[TipitakaService._keyword_search] No where_clauses built — "
                    "terms=%s  query=%.80r", terms, query,
                )
                return []

            sql = f"""
                SELECT
                    par.id,
                    par.pali_text,
                    par.html_content,
                    par.xml_source_file,
                    par.paragraph_number,
                    par.book_id,
                    par.sutta_id,
                    pk.name_english as pitaka_name,
                    n.name_english  as nikaya_name,
                    b.name_english  as book_name,
                    s.name_english  as sutta_name,
                    CASE
                        WHEN b.pitaka_id = 'sutta'  THEN 0
                        WHEN b.pitaka_id = 'vinaya' THEN 1
                        ELSE 2
                    END as pitaka_priority
                FROM paragraphs par
                LEFT JOIN books b    ON par.book_id = b.id
                LEFT JOIN nikayas n  ON b.nikaya_id = n.id
                LEFT JOIN pitakas pk ON b.pitaka_id = pk.id
                LEFT JOIN suttas s   ON par.sutta_id = s.id
                WHERE par.text_layer = 'mula' AND ({' OR '.join(where_clauses)})
                ORDER BY pitaka_priority ASC, par.id ASC
                LIMIT ?
            """
            params.append(limit)

            try:
                cursor.execute(sql, params)
                passages = cursor.fetchall()
            except Exception as exc:
                logger.error(
                    "[TipitakaService._keyword_search] SQL execution FAILED — "
                    "terms=%s  error=%s\n%s", expanded_terms, exc, traceback.format_exc(),
                )
                raise

            logger.info(
                "[TipitakaService._keyword_search] Keyword search returned %d passages "
                "for query=%.80r", len(passages), query,
            )
            if not passages:
                logger.warning(
                    "[TipitakaService._keyword_search] Zero passages found — "
                    "terms=%s  expanded=%s  query=%.80r",
                    terms, expanded_terms, query,
                )

            for passage in passages:
                passage['reference'] = self._build_reference(passage)
                passage['english_translation'] = self._fetch_translation(
                    cursor, passage['book_id'], passage['paragraph_number']
                )

            return passages

        finally:
            conn.close()

    def _get_translation_book_id(self, pali_book_id: str) -> Optional[str]:
        """Map Pali book ID to translation book ID (anya_pe series)."""
        if not pali_book_id:
            return None

        # Remove 'm' suffix (mula) for Sutta Pitaka
        base_id = pali_book_id
        if base_id.endswith('m'):
            base_id = base_id[:-1]

        # Sutta Pitaka mapping (dn1m -> annya_pe_dn1, etc.)
        if base_id.startswith(('dn', 'mn', 'sn', 'an')):
            return f"annya_pe_{base_id}"

        # Vinaya Pitaka mapping (vi1m=Parajika, vi2m=Pacittiya, vi3m=Mahavagga,
        #                         vi4m=Culavagga, vi5m=Parivara)
        vinaya_map = {
            'vi1m': 'annya_pe_parajika',
            'vi2m': 'annya_pe_pacittiya',
            'vi3m': 'annya_pe_mahavagga',
            'vi4m': 'annya_pe_culavagga',
            'vi5m': 'annya_pe_parivara'
        }

        if pali_book_id in vinaya_map:
            return vinaya_map[pali_book_id]

        # Abhidhamma Pitaka mapping
        # Books: abh01 (Dhammasangani), abh02 (Vibhanga), abh03 (Dhatukatha),
        #        abh04 (Puggalapannatti), abh05 (Kathavatthu), abh06 (Yamaka),
        #        abh07 (Patthana)
        abhidhamma_map = {
            'abh01': 'annya_pe_abh01',  # Dhammasangani
            'abh02': 'annya_pe_abh02',  # Vibhanga
            'abh03': 'annya_pe_abh03',  # Dhatukatha
            'abh04': 'annya_pe_abh04',  # Puggalapannatti
            'abh05': 'annya_pe_abh05',  # Kathavatthu
            'abh06': 'annya_pe_abh06',  # Yamaka
            'abh07': 'annya_pe_abh07',  # Patthana
        }

        return abhidhamma_map.get(pali_book_id)

    def _fetch_translation(self, cursor, pali_book_id: str, para_num: int) -> Optional[str]:
        """Fetch English translation from pages table."""
        trans_book_id = self._get_translation_book_id(pali_book_id)
        if not trans_book_id:
            return None

        # paranum in pages is '-N-' — use exact match to avoid false positives
        # e.g. para_num=1 must not match '-11-' or '-21-'
        cursor.execute("""
            SELECT content FROM pages
            WHERE bookid = ? AND paranum = ?
            LIMIT 1
        """, [trans_book_id, f'-{para_num}-'])
        
        result = cursor.fetchone()
        if not result:
            return None
            
        content = result['content']
        # Extract English text from <span class="t1"> or <span class="t5">
        # t1 usually contains the English translation in annya_pe books
        English_matches = re.findall(r'<span class="t1">([^<]+)</span>', content)
        if not English_matches:
            # Fallback to t5 which sometimes has it or other content
            English_matches = re.findall(r'<span class="t5">([^<]+)</span>', content)
            
        if English_matches:
            # Join fragments and clean up
            text = " ".join(English_matches).strip()
            # Remove leading/trailing markers if any
            return text if text else None
            
        return None

    def _get_pali_diacritical_variants(self, term: str) -> List[str]:
        """Get common Pali diacritical mark variants of a term."""
        variants = []

        # Common word-specific Pali diacritical variations
        specific_variants = {
            'anapanasati': ['ānāpānasati', 'anapanāsati'],
            'anapana': ['ānāpāna'],
            'dukkha': ['dukkhā'],
            'sutta': ['suttā', 'suttā'],
            'sati': ['satī'],
            'metta': ['mettā'],
            'jhana': ['jhānā'],
            'nibbana': ['nibbānā'],
            'samadhi': ['samādhī'],
            'panna': ['paññā'],
            'karuna': ['karunā'],
            'sangha': ['saṅghā'],
        }

        term_lower = term.lower()
        if term_lower in specific_variants:
            return specific_variants[term_lower]

        # For other terms, try basic long-vowel variants
        # Only apply to specific common patterns
        basic_map = {
            'sati': 'satī',
            'metta': 'mettā',
            'dukkhā': 'dukkha',
        }

        if term_lower in basic_map:
            variant = basic_map[term_lower]
            if variant != term:
                variants.append(variant)

        return variants

    def _build_reference(self, passage: Dict) -> str:
        """Build complete reference from Pitaka to Paragraph number."""
        parts = []

        # Add Pitaka
        if passage.get('pitaka_name'):
            parts.append(passage['pitaka_name'])

        # Add Nikaya
        if passage.get('nikaya_name'):
            parts.append(passage['nikaya_name'])

        # Add Book
        if passage.get('book_name'):
            parts.append(passage['book_name'])

        # Add Sutta
        if passage.get('sutta_name'):
            parts.append(passage['sutta_name'])

        # Add Paragraph number
        if passage.get('paragraph_number'):
            parts.append(f"Paragraph {passage['paragraph_number']}")

        # Add XML source if available
        if passage.get('xml_source_file'):
            parts.append(f"({passage['xml_source_file']})")

        return " → ".join(parts) if parts else "Reference not available"

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from a query."""
        # Common Buddhist terms to prioritize (with and without diacritics)
        buddhist_terms = {
            'suffering', 'dukkha', 'dukkhā', 'nibbana', 'nibbāna', 'nirvana',
            'metta', 'mettā', 'loving-kindness',
            'mindfulness', 'sati', 'satī', 'meditation', 'jhana', 'jhāna',
            'enlightenment',
            'buddha', 'buddhā', 'dhamma', 'dhammā', 'dharma', 'sangha', 'saṅghā',
            'vinaya', 'vinayā', 'sutta', 'suttā',
            'anicca', 'anicca', 'impermanence', 'anatta', 'anattā', 'non-self',
            'karma', 'kamma', 'kammā',
            'craving', 'tanha', 'taṇhā', 'cessation', 'nirodha', 'niroddhā',
            'path', 'magga', 'maggā',
            'eightfold', 'four noble truths', 'dependent origination',
            'compassion', 'karuna', 'karunā', 'wisdom', 'panna', 'paññā',
            'concentration', 'samadhi', 'samādhī',
            'anapanasati', 'ānāpānasati', 'anapana', 'ānāpāna', 'breathing',
            'satipatthana', 'satipaṭṭhāna', 'mindfulness foundations'
        }

        # Tokenize and filter
        words = re.findall(r'\b\w+\b', query.lower())
        stop_words = {'the', 'is', 'what', 'how', 'why', 'when', 'where', 'a', 'an', 'of', 'in', 'to', 'for', 'and', 'or'}

        terms = []
        for word in words:
            if word in buddhist_terms:
                terms.insert(0, word)  # Prioritize Buddhist terms
            elif word not in stop_words and len(word) > 2:
                terms.append(word)

        return terms[:5]  # Limit to 5 terms

    def lookup_pali_word(self, word: str) -> Optional[Dict]:
        """
        Look up a Pali word in the dictionary.

        Args:
            word: The Pali word to look up

        Returns:
            Dictionary with word, meaning, etymology, occurrences
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory

        try:
            cursor = conn.cursor()

            # Look up in dictionary table (if exists)
            cursor.execute("""
                SELECT * FROM dictionary
                WHERE word LIKE ? OR word LIKE ?
                LIMIT 1
            """, [word, word.lower()])

            result = cursor.fetchone()

            # Count occurrences in paragraphs
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM paragraphs
                WHERE pali_text LIKE ?
            """, [f'%{word}%'])

            occurrence = cursor.fetchone()

            if result:
                result['occurrences'] = occurrence['count'] if occurrence else 0
                return result

            return None

        finally:
            conn.close()

    def get_sutta_by_reference(self, reference: str) -> Optional[Dict]:
        """
        Get a sutta by its reference (e.g., MN 10, DN 22).

        Args:
            reference: The sutta reference

        Returns:
            Dictionary with sutta details and paragraphs
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory

        try:
            cursor = conn.cursor()

            # Parse reference (e.g., "MN 10" -> nikaya="MN", number=10)
            match = re.match(r'([A-Z]+)\s*(\d+)', reference.upper())
            if not match:
                return None

            nikaya_abbrev = match.group(1)
            sutta_num = int(match.group(2))

            # Map abbreviations to nikaya names
            nikaya_map = {
                'DN': 'Digha Nikaya',
                'MN': 'Majjhima Nikaya',
                'SN': 'Samyutta Nikaya',
                'AN': 'Anguttara Nikaya',
                'KN': 'Khuddaka Nikaya'
            }

            nikaya_name = nikaya_map.get(nikaya_abbrev)
            if not nikaya_name:
                return None

            # Query for sutta
            cursor.execute("""
                SELECT s.*, b.name_pali as book_name
                FROM suttas s
                JOIN books b ON s.book_id = b.id
                WHERE s.sutta_number = ? AND b.nikaya_id IN (
                    SELECT id FROM nikayas WHERE name_pali LIKE ?
                )
                LIMIT 1
            """, [sutta_num, f'%{nikaya_name}%'])

            sutta = cursor.fetchone()
            if not sutta:
                return None

            # Get paragraphs
            cursor.execute("""
                SELECT pali_text, html_content, paragraph_number
                FROM paragraphs
                WHERE sutta_id = ?
                ORDER BY paragraph_number
            """, [sutta['id']])

            sutta['paragraphs'] = cursor.fetchall()
            sutta['reference'] = reference.upper()

            return sutta

        finally:
            conn.close()

    def full_text_search(self, query: str, limit: int = 20, offset: int = 0) -> Dict:
        """
        Perform full-text search across the Tipitaka.

        Args:
            query: Search query
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with query, total, and results
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory

        try:
            cursor = conn.cursor()

            # Count total matches
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM paragraphs
                WHERE pali_text LIKE ? OR html_content LIKE ?
            """, [f'%{query}%', f'%{query}%'])

            total = cursor.fetchone()['total']

            # Get results
            cursor.execute("""
                SELECT
                    id,
                    pali_text,
                    html_content,
                    xml_source_file,
                    paragraph_number
                FROM paragraphs
                WHERE pali_text LIKE ? OR html_content LIKE ?
                LIMIT ? OFFSET ?
            """, [f'%{query}%', f'%{query}%', limit, offset])

            results = cursor.fetchall()

            return {
                'query': query,
                'total': total,
                'limit': limit,
                'offset': offset,
                'results': results
            }

        finally:
            conn.close()

    def get_paragraph_count(self) -> int:
        """Get total paragraph count for health check."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM paragraphs")
            return cursor.fetchone()[0]
        finally:
            conn.close()
