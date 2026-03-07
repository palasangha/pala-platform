"""
Response Formatter - Format responses according to SOUL.md protocol

This service ensures all responses follow the 4-part Dhamma response
structure and are properly formatted for the Flutter frontend.
"""

import logging
import traceback
from typing import Dict, List

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Format responses for the frontend."""

    def format_dhamma_response(self, response: Dict, passages: List[Dict] = None) -> Dict:
        """
        Format a strict 8-part Dhamma response for the frontend.
        """
        logger.info(
            "[ResponseFormatter.format_dhamma_response] Formatting response — "
            "passages=%d  canonical_teachings=%d  raw_response_len=%d",
            len(passages) if passages else 0,
            len(response.get('canonical_teachings', [])),
            len(response.get('raw_response', '')),
        )

        # Log which sections are empty before formatting
        empty_in = [k for k, v in response.items()
                    if k not in ('raw_response', 'canonical_teachings') and not v]
        if empty_in:
            logger.warning(
                "[ResponseFormatter.format_dhamma_response] Input has empty sections: %s. "
                "These will produce empty formatted output.", empty_in,
            )
        if not response.get('canonical_teachings'):
            logger.warning(
                "[ResponseFormatter.format_dhamma_response] canonical_teachings is EMPTY. "
                "Section 3 will have no teaching blocks in the formatted output."
            )

        try:
            formatted = {
                'direct_definition':  self._format_section('DIRECT DEFINITION',        response.get('direct_definition', '')),
                'interpretive_insight': self._format_section('INTERPRETIVE INSIGHT',   response.get('interpretive_insight', '')),
                'canonical_teachings': [
                    self._format_teaching(t)
                    for t in response.get('canonical_teachings', [])
                ],
                'commentary':         self._format_section('AṬṬHAKATHĀ COMMENTARY',    response.get('commentary', '')),
                'tika_clarification': self._format_section('ṬĪKĀ CLARIFICATION',       response.get('tika_clarification', '')),
                'lexical_analysis':   self._format_section('LEXICAL ANALYSIS',         response.get('lexical_analysis', '')),
                'doctrinal_function': self._format_section('DOCTRINAL FUNCTION',       response.get('doctrinal_function', '')),
                'final_summary':      self._format_section('FINAL SUMMARY',            response.get('final_summary', '')),
                'pali_texts': [
                    {
                        'pali':      p.get('pali_text', ''),
                        'reference': p.get('reference', 'Reference not available'),
                        'pitaka':    p.get('pitaka_name', 'N/A'),
                        'nikaya':    p.get('nikaya_name', 'N/A'),
                        'book':      p.get('book_name', 'N/A'),
                        'sutta':     p.get('sutta_name', 'N/A'),
                        'paragraph': p.get('paragraph_number', 'N/A'),
                        'xml_source': p.get('xml_source_file', 'N/A'),
                    }
                    for p in (passages or [])
                ] if passages else [],
                'formatted_text': self._format_full_response(response, passages),
            }

            empty_out = [k for k, v in formatted.items()
                         if k not in ('pali_texts', 'formatted_text', 'canonical_teachings')
                         and isinstance(v, dict) and not v.get('content')]
            if empty_out:
                logger.warning(
                    "[ResponseFormatter.format_dhamma_response] Output sections with empty content: %s",
                    empty_out,
                )

            logger.info(
                "[ResponseFormatter.format_dhamma_response] Done — "
                "canonical_teachings_out=%d  pali_texts=%d  formatted_text_len=%d",
                len(formatted['canonical_teachings']),
                len(formatted['pali_texts']),
                len(formatted['formatted_text']),
            )
            return formatted

        except Exception as exc:
            logger.error(
                "[ResponseFormatter.format_dhamma_response] FAILED — error=%s\n%s",
                exc, traceback.format_exc(),
            )
            raise

    def _format_section(self, title: str, content: str) -> Dict:
        """Format a section with title and content."""
        result = {'title': title, 'content': content.strip() if content else ''}
        if not result['content']:
            logger.debug(
                "[ResponseFormatter._format_section] Section '%s' has empty content.", title,
            )
        return result

    def _format_teaching(self, teaching) -> Dict:
        """Format a single teaching."""
        formatted = {
            'pali':        teaching.get('pali', '').strip(),
            'english':     teaching.get('english', '').strip(),
            'explanation': teaching.get('explanation', '').strip(),
            'reference':   teaching.get('reference', '').strip(),
        }
        missing = [k for k, v in formatted.items() if not v]
        if missing:
            logger.debug(
                "[ResponseFormatter._format_teaching] Teaching missing fields: %s", missing,
            )
        return formatted

    def _format_full_response(self, response: Dict, passages: List[Dict] = None) -> str:
        """Format the full response as plain text for display."""
        logger.debug("[ResponseFormatter._format_full_response] Building full text...")
        divider = "━" * 40
        sections = []

        try:
            # Part 0: Pali Texts
            if passages:
                pali_section = f"\n{divider}\n🔤 PĀḶI TEXTS & TRANSLATIONS FROM TIPITAKA\n{divider}\n"
                for i, p in enumerate(passages, 1):
                    ref_parts = []
                    if p.get('pitaka_name'): ref_parts.append(f"Pitaka: {p['pitaka_name']}")
                    if p.get('nikaya_name'): ref_parts.append(f"Nikaya: {p['nikaya_name']}")
                    if p.get('book_name'):   ref_parts.append(f"Book: {p['book_name']}")
                    if p.get('sutta_name'):  ref_parts.append(f"Sutta: {p['sutta_name']}")
                    ref_parts.append(f"Paragraph: {p.get('paragraph_number', 'N/A')}")

                    pali_section += f"\n[PASSAGE {i}]\n{' | '.join(ref_parts)}\n\n[PALI]\n{p.get('pali_text', 'N/A')}\n"
                    if p.get('english_translation'):
                        pali_section += f"\n[ENGLISH]\n{p['english_translation']}\n"
                    pali_section += "\n"
                sections.append(pali_section)

            sections.append(f"{divider}\n1. DIRECT DEFINITION\n{divider}\n\n{response.get('direct_definition', '')}\n")
            sections.append(f"{divider}\n2. SAMMA AI INTERPRETIVE INSIGHT\n{divider}\n\n{response.get('interpretive_insight', '')}\n")

            teachings = response.get('canonical_teachings', [])
            if teachings:
                sections.append(f"{divider}\n3. CANONICAL TEACHINGS\n{divider}\n")
                for i, t in enumerate(teachings, 1):
                    sections.append(f"""
TEACHING {i}
----------
A. Pāḷi Text:
{t.get('pali', '')}

B. English Translation:
{t.get('english', '')}

C. Doctrinal Explanation:
{t.get('explanation', '')}

D. Reference:
{t.get('reference', '')}
""")
            else:
                logger.warning(
                    "[ResponseFormatter._format_full_response] Section 3 skipped — "
                    "canonical_teachings is empty. formatted_text will lack teaching blocks."
                )

            if response.get('commentary'):
                sections.append(f"{divider}\n4. AṬṬHAKATHĀ COMMENTARY\n{divider}\n\n{response['commentary']}\n")
            if response.get('tika_clarification'):
                sections.append(f"{divider}\n5. ṬĪKĀ CLARIFICATION\n{divider}\n\n{response['tika_clarification']}\n")
            if response.get('lexical_analysis'):
                sections.append(f"{divider}\n6. LEXICAL & PHILOLOGICAL ANALYSIS\n{divider}\n\n{response['lexical_analysis']}\n")
            if response.get('doctrinal_function'):
                sections.append(f"{divider}\n7. DOCTRINAL FUNCTION\n{divider}\n\n{response['doctrinal_function']}\n")

            sections.append(f"{divider}\n8. FINAL TEACHING SUMMARY\n{divider}\n\n{response.get('final_summary', '')}\n")

            result = '\n'.join(sections)
            logger.debug(
                "[ResponseFormatter._format_full_response] Built %d sections, total_len=%d",
                len(sections), len(result),
            )
            return result

        except Exception as exc:
            logger.error(
                "[ResponseFormatter._format_full_response] FAILED — error=%s\n%s",
                exc, traceback.format_exc(),
            )
            raise

    def format_simple_response(self, content: str, source: str = None) -> Dict:
        """Format a simple non-Dhamma response."""
        return {'content': content, 'source': source, 'formatted_text': content}

    def format_error_response(self, error: str, suggestion: str = None) -> Dict:
        """Format an error response."""
        logger.info("[ResponseFormatter.format_error_response] error=%s", error)
        response = {
            'error': True,
            'message': error,
            'formatted_text': f"An error occurred: {error}",
        }
        if suggestion:
            response['suggestion'] = suggestion
            response['formatted_text'] += f"\n\nSuggestion: {suggestion}"
        return response
