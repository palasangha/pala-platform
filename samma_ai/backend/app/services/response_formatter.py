"""
Response Formatter - Format responses according to SOUL.md protocol

This service ensures all responses follow the 4-part Dhamma response
structure and are properly formatted for the Flutter frontend.
"""

from typing import Dict, List


class ResponseFormatter:
    """Format responses for the frontend."""

    def format_dhamma_response(self, response: Dict, passages: List[Dict] = None) -> Dict:
        """
        Format a strict 8-part Dhamma response for the frontend.

        Args:
            response: Raw response from Claude service
            passages: Optional list of passages used

        Returns:
            Formatted response dictionary
        """
        formatted = {
            'direct_definition': self._format_section('DIRECT DEFINITION', response.get('direct_definition', '')),
            'interpretive_insight': self._format_section('INTERPRETIVE INSIGHT', response.get('interpretive_insight', '')),
            'canonical_teachings': [
                self._format_teaching(t)
                for t in response.get('canonical_teachings', [])
            ],
            'commentary': self._format_section('AṬṬHAKATHĀ COMMENTARY', response.get('commentary', '')),
            'tika_clarification': self._format_section('ṬĪKĀ CLARIFICATION', response.get('tika_clarification', '')),
            'lexical_analysis': self._format_section('LEXICAL ANALYSIS', response.get('lexical_analysis', '')),
            'doctrinal_function': self._format_section('DOCTRINAL FUNCTION', response.get('doctrinal_function', '')),
            'final_summary': self._format_section('FINAL SUMMARY', response.get('final_summary', '')),
            'pali_texts': [
                {
                    'pali': p.get('pali_text', ''),
                    'reference': p.get('reference', 'Reference not available'),
                    'pitaka': p.get('pitaka_name', 'N/A'),
                    'nikaya': p.get('nikaya_name', 'N/A'),
                    'book': p.get('book_name', 'N/A'),
                    'sutta': p.get('sutta_name', 'N/A'),
                    'paragraph': p.get('paragraph_number', 'N/A'),
                    'xml_source': p.get('xml_source_file', 'N/A')
                }
                for p in (passages or [])
            ] if passages else [],
            'formatted_text': self._format_full_response(response, passages)
        }
        return formatted

    def _format_section(self, title: str, content: str) -> Dict:
        """Format a section with title and content."""
        return {
            'title': title,
            'content': content.strip() if content else ''
        }

    def _format_teaching(self, teaching) -> Dict:
        """Format a single teaching."""
        return {
            'pali': teaching.get('pali', '').strip(),
            'english': teaching.get('english', '').strip(),
            'explanation': teaching.get('explanation', '').strip(),
            'reference': teaching.get('reference', '').strip()
        }

    def _format_full_response(self, response: Dict, passages: List[Dict] = None) -> str:
        """
        Format the full response as plain text for display.
        Uses Unicode dividers and plain text.
        """
        divider = "━" * 40
        sections = []

        # Part 0: Pali Texts (if passages provided)
        if passages:
            pali_section = f"\n{divider}\n🔤 PĀḶI TEXTS & TRANSLATIONS FROM TIPITAKA\n{divider}\n"
            for i, p in enumerate(passages, 1):
                pali_text = p.get('pali_text', 'N/A')
                eng_text = p.get('english_translation')
                pitaka = p.get('pitaka_name', '')
                nikaya = p.get('nikaya_name', '')
                book = p.get('book_name', '')
                sutta = p.get('sutta_name', '')
                paragraph = p.get('paragraph_number', 'N/A')

                ref_parts = []
                if pitaka: ref_parts.append(f"Pitaka: {pitaka}")
                if nikaya: ref_parts.append(f"Nikaya: {nikaya}")
                if book: ref_parts.append(f"Book: {book}")
                if sutta: ref_parts.append(f"Sutta: {sutta}")
                ref_parts.append(f"Paragraph: {paragraph}")

                detailed_ref = " | ".join(ref_parts)
                pali_section += f"\n[PASSAGE {i}]\n{detailed_ref}\n\n[PALI]\n{pali_text}\n"
                
                if eng_text:
                    pali_section += f"\n[ENGLISH]\n{eng_text}\n"
                
                pali_section += "\n"
            sections.append(pali_section)

        # 1. Direct Definition
        sections.append(f"{divider}\n1. DIRECT DEFINITION\n{divider}\n\n{response.get('direct_definition', '')}\n")

        # 2. Interpretive Insight
        sections.append(f"{divider}\n2. SAMMA AI INTERPRETIVE INSIGHT\n{divider}\n\n{response.get('interpretive_insight', '')}\n")

        # 3. Canonical Teachings
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

        # 4. Commentary
        if response.get('commentary'):
            sections.append(f"{divider}\n4. AṬṬHAKATHĀ COMMENTARY\n{divider}\n\n{response.get('commentary', '')}\n")

        # 5. Tika
        if response.get('tika_clarification'):
            sections.append(f"{divider}\n5. ṬĪKĀ CLARIFICATION\n{divider}\n\n{response.get('tika_clarification', '')}\n")

        # 6. Lexical
        if response.get('lexical_analysis'):
            sections.append(f"{divider}\n6. LEXICAL & PHILOLOGICAL ANALYSIS\n{divider}\n\n{response.get('lexical_analysis', '')}\n")

        # 7. Doctrinal Function
        if response.get('doctrinal_function'):
            sections.append(f"{divider}\n7. DOCTRINAL FUNCTION\n{divider}\n\n{response.get('doctrinal_function', '')}\n")

        # 8. Final Summary
        sections.append(f"{divider}\n8. FINAL VISITS SUMMARY\n{divider}\n\n{response.get('final_summary', '')}\n")

        return '\n'.join(sections)

    def format_simple_response(self, content: str, source: str = None) -> Dict:
        """Format a simple non-Dhamma response."""
        return {
            'content': content,
            'source': source,
            'formatted_text': content
        }

    def format_error_response(self, error: str, suggestion: str = None) -> Dict:
        """Format an error response."""
        response = {
            'error': True,
            'message': error,
            'formatted_text': f"An error occurred: {error}"
        }

        if suggestion:
            response['suggestion'] = suggestion
            response['formatted_text'] += f"\n\nSuggestion: {suggestion}"

        return response
