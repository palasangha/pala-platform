"""
AMI Metadata Parser - Extracts metadata from AMI Master naming convention
"""

import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AMIMetadataParser:
    """
    Parses filenames based on AMI Master naming convention to extract structured metadata.

    Example filename: MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG

    Pattern breakdown:
    - Master Identifier: MSALTMEBA00100004.00
    - Page/Sequence: (01_02_0071) - Collection_Series_Page
    - Document Type: LT (Letter)
    - Medium: MIX (Mixed media)
    - Date: 1990
    - Sender/From: BK MODI
    - Recipient/To: REVSNGOENKA
    """

    # Document type codes from AMI Master
    DOCUMENT_TYPES = {
        'LT': 'Letter',
        'BK': 'Book',
        'NB': 'Notebook',
        'DY': 'Diary',
        'NL': 'Newsletter',
        'TR': 'Transcript',
        'MG': 'Magazine',
        'NP': 'Newspaper',
        'PC': 'Postcard',
        'PH': 'Photograph',
        'AU': 'Audio',
        'VD': 'Video',
        'DC': 'Document',
        'PM': 'Palm Leaf Manuscript',
        'PT': 'Painting'
    }

    # Medium types
    MEDIUM_TYPES = {
        'MIX': 'Mixed',
        'PEN': 'Pen',
        'PENCIL': 'Pencil',
        'TYPE': 'Typewriter',
        'PRINT': 'Printed',
        'HAND': 'Handwritten',
        'CARVE': 'Carved',
        'CHALK': 'Chalk',
        'MARKER': 'Marker'
    }

    def __init__(self):
        """Initialize the AMI metadata parser"""
        self.enabled = True
        logger.info("AMIMetadataParser initialized")

    def parse(self, filename: str) -> Dict[str, Any]:
        """
        Parse AMI filename and extract metadata

        Args:
            filename: The filename to parse (with or without extension)

        Returns:
            Dictionary containing extracted metadata
        """
        try:
            # Remove file extension
            name_without_ext = Path(filename).stem

            # Initialize metadata dictionary
            metadata = {
                'filename': filename,
                'parsed': False,
                'master_identifier': None,
                'collection': None,
                'series': None,
                'page_number': None,
                'sequence': None,
                'document_type': None,
                'document_type_full': None,
                'medium': None,
                'medium_full': None,
                'date': None,
                'year': None,
                'sender': None,
                'recipient': None,
                'from_person': None,
                'to_person': None,
                'parsing_notes': []
            }

            # Parse using regex patterns
            metadata.update(self._parse_filename(name_without_ext))

            return metadata

        except Exception as e:
            logger.error(f"Error parsing filename '{filename}': {e}")
            return {
                'filename': filename,
                'parsed': False,
                'error': str(e)
            }

    def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """
        Internal method to parse filename components

        Expected pattern:
        {MASTER_ID}_{(COL_SER_PAGE)}_{DOCTYPE}_{MEDIUM}_{YEAR}_{FROM}_TO_{RECIPIENT}

        Example: MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA
        """
        result = {'parsed': False, 'parsing_notes': []}

        try:
            # 1. Extract Master Identifier (everything before the first parenthesis or first underscore after dot)
            master_id_match = re.match(r'^([^_\(]+\.\d+)', filename)
            if master_id_match:
                master_id = master_id_match.group(1)
                result['master_identifier'] = master_id
                result['parsing_notes'].append(f'Master ID: {master_id}')
            else:
                # Fallback: use first part before underscore
                master_id = filename.split('_')[0] if '_' in filename else filename.split('(')[0]
                result['master_identifier'] = master_id
                result['parsing_notes'].append(f'Master ID (fallback): {master_id}')

            # 2. Extract Collection/Series/Page (if present in parentheses)
            sequence_pattern = r'\((\d+)_(\d+)_(\d+)\)'
            sequence_match = re.search(sequence_pattern, filename)
            if sequence_match:
                result['collection'] = sequence_match.group(1)
                result['series'] = sequence_match.group(2)
                result['page_number'] = sequence_match.group(3)
                result['sequence'] = f"Collection {sequence_match.group(1)}, Series {sequence_match.group(2)}, Page {sequence_match.group(3)}"
                result['parsing_notes'].append(f'Sequence: {result["sequence"]}')

            # 3. Extract Document Type (2-letter code, typically LT, BK, etc.)
            # Look for 2-letter uppercase codes
            doc_type_pattern = r'_([A-Z]{2})_'
            doc_type_match = re.search(doc_type_pattern, filename)
            if doc_type_match:
                doc_type = doc_type_match.group(1)
                if doc_type in self.DOCUMENT_TYPES:
                    result['document_type'] = doc_type
                    result['document_type_full'] = self.DOCUMENT_TYPES[doc_type]
                    result['parsing_notes'].append(f'Document Type: {result["document_type_full"]} ({doc_type})')

            # 4. Extract Medium (typically MIX, PEN, etc.)
            # Look for known medium codes after document type
            for medium_code in self.MEDIUM_TYPES.keys():
                if f'_{medium_code}_' in filename:
                    result['medium'] = medium_code
                    result['medium_full'] = self.MEDIUM_TYPES[medium_code]
                    result['parsing_notes'].append(f'Medium: {result["medium_full"]} ({medium_code})')
                    break

            # 5. Extract Year (4-digit number, but avoid page numbers in parentheses)
            # Remove the parentheses part first
            temp_filename = re.sub(r'\(\d+_\d+_\d+\)', '', filename)
            year_pattern = r'_(\d{4})_'
            year_match = re.search(year_pattern, temp_filename)
            if year_match:
                result['year'] = year_match.group(1)
                result['date'] = result['year']
                result['parsing_notes'].append(f'Year: {result["year"]}')

            # 6. Extract Sender/From and Recipient/To
            # Pattern: {FROM}_TO_{RECIPIENT}
            # Handle spaces in names (like "BK MODI")
            to_pattern = r'_TO[_\s]+([A-Z][A-Z\s]+?)(?:\.[\w]+)?$'
            to_match = re.search(to_pattern, filename, re.IGNORECASE)
            if to_match:
                recipient = to_match.group(1).strip()
                result['recipient'] = recipient
                result['to_person'] = recipient
                result['parsing_notes'].append(f'Recipient: {recipient}')

                # Extract sender (between year and TO)
                # Handle spaces in sender name
                if result.get('year'):
                    from_pattern = rf'_{result["year"]}_(.+?)_TO[_\s]'
                    from_match = re.search(from_pattern, filename, re.IGNORECASE)
                    if from_match:
                        sender = from_match.group(1).strip().replace('_', ' ')
                        result['sender'] = sender
                        result['from_person'] = sender
                        result['parsing_notes'].append(f'Sender: {sender}')

            # Mark as successfully parsed if we got key components
            if result.get('master_identifier') and (result.get('document_type') or result.get('year')):
                result['parsed'] = True

        except Exception as e:
            logger.error(f"Error in _parse_filename: {e}")
            result['parsing_notes'].append(f'Parsing error: {str(e)}')

        return result

    def format_metadata_summary(self, metadata: Dict[str, Any]) -> str:
        """
        Format parsed metadata into a human-readable summary

        Args:
            metadata: Parsed metadata dictionary

        Returns:
            Formatted string summary
        """
        if not metadata.get('parsed'):
            return f"Unable to parse filename: {metadata.get('filename', 'unknown')}"

        lines = [
            f"Filename: {metadata.get('filename', 'N/A')}",
            f"Master Identifier: {metadata.get('master_identifier', 'N/A')}",
        ]

        if metadata.get('sequence'):
            lines.append(f"Sequence: {metadata['sequence']}")

        if metadata.get('document_type_full'):
            lines.append(f"Document Type: {metadata['document_type_full']} ({metadata.get('document_type', 'N/A')})")

        if metadata.get('medium_full'):
            lines.append(f"Medium: {metadata['medium_full']} ({metadata.get('medium', 'N/A')})")

        if metadata.get('year'):
            lines.append(f"Date: {metadata['year']}")

        if metadata.get('sender'):
            lines.append(f"From: {metadata['sender']}")

        if metadata.get('recipient'):
            lines.append(f"To: {metadata['recipient']}")

        return "\n".join(lines)

    def get_archipelago_fields(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map parsed metadata to Archipelago fields based on AMI Master schema

        Args:
            metadata: Parsed metadata dictionary

        Returns:
            Dictionary with Archipelago field mappings
        """
        if not metadata.get('parsed'):
            return {}

        archipelago_fields = {
            'master_identifier': metadata.get('master_identifier'),
            'page_no': metadata.get('page_number'),
            'sequence_id': metadata.get('sequence'),
            'item_type': metadata.get('document_type_full'),
            'medium': metadata.get('medium_full'),
            'original_date': metadata.get('year'),
        }

        # Add letter-specific fields if document type is Letter
        if metadata.get('document_type') == 'LT':
            archipelago_fields['letter_from'] = metadata.get('sender')
            archipelago_fields['letter_to'] = metadata.get('recipient')
            archipelago_fields['subject'] = f"Letter from {metadata.get('sender', 'Unknown')} to {metadata.get('recipient', 'Unknown')}"

        # Add creator field
        if metadata.get('sender'):
            archipelago_fields['creator'] = metadata.get('sender')

        # Remove None values
        return {k: v for k, v in archipelago_fields.items() if v is not None}


def parse_ami_filename(filename: str) -> Dict[str, Any]:
    """
    Convenience function to parse an AMI filename

    Args:
        filename: The filename to parse

    Returns:
        Dictionary containing parsed metadata
    """
    parser = AMIMetadataParser()
    return parser.parse(filename)


# Example usage and testing
if __name__ == "__main__":
    # Test with the provided example
    test_filename = "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"

    parser = AMIMetadataParser()
    result = parser.parse(test_filename)

    print("Parsed Metadata:")
    print("=" * 60)
    print(parser.format_metadata_summary(result))
    print("\n" + "=" * 60)
    print("\nArchipelago Fields:")
    print(parser.get_archipelago_fields(result))
    print("\n" + "=" * 60)
    print("\nParsing Notes:")
    for note in result.get('parsing_notes', []):
        print(f"  - {note}")
