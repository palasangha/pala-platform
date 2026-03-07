"""
AMI Filename Generator - Generates standardized filenames from enriched document metadata
following the AMI Master naming convention.

Example output:
    MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG

Segment breakdown:
    Master Identifier   MSALTMEBA00100004.00    Original filename (if AMI format) or XXXX
    Sequence            (01_02_0071)            Original filename (if AMI format) or (XXXX_XXXX_XXXX)
    Document Type code  LT                      metadata.document_type → reverse-mapped to 2-letter code
    Medium code         MIX                     document.physical_attributes.medium or XXXX
    Year                1990                    document.date.temporal_markers.year or XXXX
    Sender              BK MODI                 document.correspondence.sender.name (uppercased)
    Recipient           REVSNGOENKA             document.correspondence.recipient.name (uppercased)
    Extension           .JPG                    Preserved from original filename
"""

import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AMIFilenameGenerator:
    """
    Generates AMI Master-compliant filenames from enriched document metadata.

    Fields that cannot be determined from document metadata are represented as XXXX.
    """

    # Reverse map: full document type name (lowercase) → 2-letter code
    DOCUMENT_TYPE_CODES: Dict[str, str] = {
        'letter': 'LT',
        'book': 'BK',
        'notebook': 'NB',
        'diary': 'DY',
        'newsletter': 'NL',
        'transcript': 'TR',
        'magazine': 'MG',
        'newspaper': 'NP',
        'postcard': 'PC',
        'photograph': 'PH',
        'photo': 'PH',
        'audio': 'AU',
        'video': 'VD',
        'document': 'DC',
        'palm leaf manuscript': 'PM',
        'painting': 'PT',
        'memo': 'DC',
        'telegram': 'DC',
        'fax': 'DC',
        'email': 'DC',
        'invitation': 'DC',
    }

    # Reverse map: full medium name (lowercase) → code
    MEDIUM_CODES: Dict[str, str] = {
        'mixed': 'MIX',
        'pen': 'PEN',
        'pencil': 'PENCIL',
        'typewriter': 'TYPE',
        'typed': 'TYPE',
        'printed': 'PRINT',
        'handwritten': 'HAND',
        'handwriting': 'HAND',
        'carved': 'CARVE',
        'chalk': 'CHALK',
        'marker': 'MARKER',
    }

    # Regex to extract master identifier: e.g. MSALTMEBA00100004.00
    _MASTER_ID_RE = re.compile(r'^([^_\(]+\.\d+)')

    # Regex to extract sequence: e.g. (01_02_0071)
    _SEQUENCE_RE = re.compile(r'(\(\d+_\d+_\d+\))')

    # Regex to extract a 4-digit year (not inside parentheses)
    _YEAR_RE = re.compile(r'_(\d{4})_')

    def generate(self, enriched_data: Dict[str, Any], original_filename: str = '') -> Dict[str, Any]:
        """
        Generate an AMI-standard filename from enriched document metadata.

        Args:
            enriched_data: Enriched document data dict containing metadata, document,
                           content, analysis sections.
            original_filename: The original filename (used to salvage master_id and
                               sequence if it follows AMI format).

        Returns:
            Dict with keys:
                'generated_filename'            The assembled filename string.
                'components'                    Dict of each component for transparency.
        """
        components: Dict[str, str] = {}

        # --- Parse original filename for AMI components ---
        parsed = self._parse_original_filename(original_filename)

        # 1. Master identifier
        components['master_identifier'] = parsed.get('master_identifier', 'XXXX')

        # 2. Sequence
        components['sequence'] = parsed.get('sequence', '(XXXX_XXXX_XXXX)')

        # 3. Document type code
        components['document_type'] = self._extract_document_type(enriched_data)

        # 4. Medium code
        components['medium'] = self._extract_medium(enriched_data)

        # 5. Year
        components['year'] = self._extract_year(enriched_data, original_filename)

        # 6. Sender
        components['sender'] = self._extract_sender(enriched_data)

        # 7. Recipient
        components['recipient'] = self._extract_recipient(enriched_data)

        # 8. Extension
        components['extension'] = self._extract_extension(original_filename)

        # --- Assemble filename ---
        generated = (
            f"{components['master_identifier']}_"
            f"{components['sequence']}_"
            f"{components['document_type']}_"
            f"{components['medium']}_"
            f"{components['year']}_"
            f"{components['sender']}_TO_"
            f"{components['recipient']}"
            f"{components['extension']}"
        )

        return {
            'generated_filename': generated,
            'components': components,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_original_filename(self, original_filename: str) -> Dict[str, str]:
        """
        Attempt to parse the original filename as an AMI-format name.
        Returns a dict with 'master_identifier' and 'sequence' if found.
        """
        result: Dict[str, str] = {}
        if not original_filename:
            return result

        # Work on stem (no extension)
        stem = os.path.splitext(original_filename)[0]

        master_match = self._MASTER_ID_RE.match(stem)
        if master_match:
            result['master_identifier'] = master_match.group(1)

        seq_match = self._SEQUENCE_RE.search(stem)
        if seq_match:
            result['sequence'] = seq_match.group(1)

        return result

    def _extract_document_type(self, enriched_data: Dict[str, Any]) -> str:
        """Map metadata.document_type to a 2-letter code, fallback 'XX'."""
        raw = (
            (enriched_data.get('metadata') or {}).get('document_type') or ''
        )
        if not raw:
            return 'XX'
        code = self.DOCUMENT_TYPE_CODES.get(raw.lower().strip())
        return code if code else 'XX'

    def _extract_medium(self, enriched_data: Dict[str, Any]) -> str:
        """Map document.physical_attributes.medium to a medium code, fallback 'XXXX'."""
        raw = (
            ((enriched_data.get('document') or {}).get('physical_attributes') or {}).get('medium') or ''
        )
        if not raw:
            return 'XXXX'
        code = self.MEDIUM_CODES.get(raw.lower().strip())
        return code if code else 'XXXX'

    def _get_correspondence(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return the correspondence dict, handling both expected and double-nested layouts.

        Expected layout (schema):
            document.correspondence.sender.name

        Actual layout seen in real enriched data (merged from parse_correspondence result):
            document.correspondence.correspondence.sender.name

        Both are supported transparently.
        """
        outer = (enriched_data.get('document') or {}).get('correspondence') or {}
        # If the dict has a 'correspondence' key, unwrap one level
        if 'correspondence' in outer and isinstance(outer['correspondence'], dict):
            return outer['correspondence']
        return outer

    def _extract_year(self, enriched_data: Dict[str, Any], original_filename: str = '') -> str:
        """
        Extract year from (in priority order):
          1. document.date.temporal_markers.year
          2. creation_date / sent_date ISO string inside document.date or document
          3. correspondence date string
          4. 4-digit year found anywhere in the original filename stem
        Fallback: 'XXXX'.
        """
        doc = enriched_data.get('document') or {}

        # 1. Explicit year field
        year = (
            ((doc.get('date') or {}).get('temporal_markers') or {}).get('year')
        )
        if year:
            return str(year)

        # 2. Parse from ISO-style date strings nested inside document.date or document root
        for date_key in ('creation_date', 'sent_date'):
            for container in ((doc.get('date') or {}), doc):
                date_val = container.get(date_key) or ''
                if date_val:
                    m = re.match(r'(\d{4})', str(date_val))
                    if m:
                        return m.group(1)

        # 3. Correspondence date string (e.g. "29th September 1969")
        corr_date = (self._get_correspondence(enriched_data) or {}).get('date') or ''
        if corr_date:
            m = re.search(r'\b(\d{4})\b', str(corr_date))
            if m:
                return m.group(1)

        # 4. Any 4-digit year in the original filename
        # Use digit-boundary lookahead/lookbehind (not \b) so that _1990_ and
        # concatenated forms like "September1970" are matched correctly.
        if original_filename:
            stem = os.path.splitext(original_filename)[0]
            m = re.search(r'(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)', stem)
            if m:
                return m.group(1)

        return 'XXXX'

    def _extract_sender(self, enriched_data: Dict[str, Any]) -> str:
        """Extract and format sender name, fallback 'XXXX'."""
        corr = self._get_correspondence(enriched_data)
        name = (corr.get('sender') or {}).get('name') or ''
        return self._format_name(name) or 'XXXX'

    def _extract_recipient(self, enriched_data: Dict[str, Any]) -> str:
        """Extract and format recipient name, fallback 'XXXX'."""
        corr = self._get_correspondence(enriched_data)
        name = (corr.get('recipient') or {}).get('name') or ''
        return self._format_name(name) or 'XXXX'

    def _format_name(self, name: str) -> str:
        """
        Uppercase name, collapse whitespace, strip non-alphanumeric except spaces.
        Returns empty string if name is empty/whitespace after cleaning.
        """
        if not name:
            return ''
        # Strip non-alphanumeric except spaces (preserves word boundaries)
        cleaned = re.sub(r'[^\w\s]', '', name, flags=re.UNICODE)
        # Collapse whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned.upper()

    def _extract_extension(self, original_filename: str) -> str:
        """Return uppercase extension (e.g. '.JPG'), fallback '.JPG'."""
        if not original_filename:
            return '.JPG'
        _, ext = os.path.splitext(original_filename)
        return ext.upper() if ext else '.JPG'
