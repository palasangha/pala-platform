"""
Tipitaka Service - Interface to the Tipitaka SQLite database

This service provides access to the canonical Buddhist texts stored in
tipitaka_ultimate.db (1.1 GB, 73,765 Pali passages, 74,050 English translations).
"""

import sqlite3
from flask import current_app
from typing import List, Dict, Optional
import re


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
        Search for passages relevant to a query.
        Handles Pali diacritical marks and alternative spellings.

        Args:
            query: The search query
            limit: Maximum number of results

        Returns:
            List of passage dictionaries with pali_text, english_translation, references
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory

        try:
            cursor = conn.cursor()

            # Extract key terms from query
            terms = self._extract_search_terms(query)

            # Add diacritical mark variations
            expanded_terms = []
            for term in terms:
                expanded_terms.append(term)
                # Add common diacritical variations
                diacritical_variants = self._get_pali_diacritical_variants(term)
                expanded_terms.extend(diacritical_variants)

            # Build search query with OR conditions
            where_clauses = []
            params = []

            for term in expanded_terms:
                where_clauses.append(
                    "(pali_text LIKE ? OR html_content LIKE ?)"
                )
                params.extend([f'%{term}%', f'%{term}%'])

            if not where_clauses:
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
                    n.name_english as nikaya_name,
                    b.name_english as book_name,
                    s.name_english as sutta_name
                FROM paragraphs par
                LEFT JOIN books b ON par.book_id = b.id
                LEFT JOIN nikayas n ON b.nikaya_id = n.id
                LEFT JOIN pitakas pk ON b.pitaka_id = pk.id
                LEFT JOIN suttas s ON par.sutta_id = s.id
                WHERE {' OR '.join(where_clauses)}
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(sql, params)
            passages = cursor.fetchall()

            # Build complete reference for each passage
            for passage in passages:
                passage['reference'] = self._build_reference(passage)

            return passages

        finally:
            conn.close()

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
