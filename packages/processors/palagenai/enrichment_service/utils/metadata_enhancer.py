"""
Metadata Enhancer - Week 1 Critical Fixes for Searchability

Enhancements:
1. Generate unique IDs (metadata.id, collection_id)
2. Populate full_text from OCR
3. Extract dates from filename and content
4. Fix correspondence sender/recipient mapping
5. Integrate AMI metadata parser
6. Add temporal markers (year, decade, era)
7. Generate basic facets
8. Calculate completeness scores
9. Add searchability metadata
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataEnhancer:
    """Enhances enriched metadata with searchability features"""

    def __init__(self, ami_parser=None):
        """
        Initialize metadata enhancer

        Args:
            ami_parser: Optional AMI filename parser instance
        """
        self.ami_parser = ami_parser

    def enhance_metadata(
        self,
        enriched_data: Dict[str, Any],
        ocr_data: Dict[str, Any],
        filename: str,
        document_id: Optional[str] = None,
        collection_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply all Week 1 enhancements to enriched metadata

        Args:
            enriched_data: Merged results from agent orchestrator
            ocr_data: Original OCR data with text
            filename: Original filename
            document_id: Optional pre-generated document ID
            collection_id: Optional collection ID

        Returns:
            Enhanced metadata with searchability features
        """
        logger.info(f"Enhancing metadata for: {filename}")

        # Make a copy to avoid modifying original
        enhanced = enriched_data.copy()

        # 1. Generate unique IDs
        if not document_id:
            document_id = str(uuid.uuid4())
        enhanced['metadata']['id'] = document_id
        logger.debug(f"✓ Generated document ID: {document_id}")

        # Extract collection_id from path or use provided
        if not collection_id:
            collection_id = self._extract_collection_id(filename)
        enhanced['metadata']['collection_id'] = collection_id
        logger.debug(f"✓ Set collection ID: {collection_id}")

        # 2. Populate full_text from OCR
        ocr_text = ocr_data.get('ocr_text', '') or ocr_data.get('text', '')
        if ocr_text and not enhanced['content'].get('full_text'):
            enhanced['content']['full_text'] = ocr_text
            logger.debug(f"✓ Populated full_text ({len(ocr_text)} chars)")

        # 3. Extract and enhance dates
        enhanced = self._enhance_dates(enhanced, filename, ocr_text)

        # 4. Fix correspondence sender/recipient
        enhanced = self._fix_correspondence(enhanced)

        # 5. Integrate AMI metadata
        if self.ami_parser:
            enhanced = self._add_ami_metadata(enhanced, filename)

        # 6. Add temporal markers
        enhanced = self._add_temporal_markers(enhanced)

        # 7. Add classification metadata
        enhanced = self._add_classification(enhanced)

        # 8. Generate facets for search
        enhanced = self._generate_facets(enhanced)

        # 9. Add searchability metadata
        enhanced = self._add_searchability_metadata(enhanced, filename)

        # 10. Calculate completeness score
        enhanced = self._calculate_completeness(enhanced)

        logger.info(f"✓ Metadata enhancement complete for {filename}")
        return enhanced

    def _extract_collection_id(self, filename: str) -> str:
        """
        Extract collection ID from filename or path

        Examples:
            "MSALTMEBA00100004.00_..." → "MSALTMEBA"
            "/path/to/collection/file.pdf" → "collection"
        """
        # Try to extract from filename pattern
        path = Path(filename)

        # Check for AMI pattern (letters at start)
        ami_match = re.match(r'^([A-Z]+)', path.stem)
        if ami_match:
            return ami_match.group(1)

        # Use parent directory name if available
        if path.parent and path.parent.name not in ['.', '', '/']:
            return path.parent.name

        # Default fallback
        return "default_collection"

    def _enhance_dates(
        self,
        data: Dict[str, Any],
        filename: str,
        ocr_text: str
    ) -> Dict[str, Any]:
        """
        Extract dates from filename and content

        Patterns to match:
        - Filename: "29 sep 1969 New Delhi.pdf"
        - Content: "29th September 1969"
        """
        # Extract date from filename
        filename_date = self._extract_date_from_filename(filename)

        # Extract date from content header (first 500 chars)
        content_date = self._extract_date_from_content(ocr_text[:500] if ocr_text else '')

        # Use best available date
        best_date = filename_date or content_date

        if best_date:
            if 'date' not in data['document']:
                data['document']['date'] = {}

            data['document']['date']['creation_date'] = best_date
            data['document']['date']['sent_date'] = best_date
            data['document']['date']['date_precision'] = 'exact' if filename_date else 'inferred'
            data['document']['date']['date_source'] = 'filename' if filename_date else 'content'
            data['document']['date']['date_display'] = self._format_date_display(best_date)

            logger.debug(f"✓ Extracted date: {best_date}")

        return data

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract date from filename patterns

        Examples:
            "29 sep 1969 New Delhi" → "1969-09-29"
            "15 Jan 2020" → "2020-01-15"
        """
        # Pattern: DD MMM YYYY or DD Month YYYY
        date_pattern = r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})'

        match = re.search(date_pattern, filename, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).lower()
            year = match.group(3)

            # Convert month name to number
            month_map = {
                'jan': '01', 'january': '01',
                'feb': '02', 'february': '02',
                'mar': '03', 'march': '03',
                'apr': '04', 'april': '04',
                'may': '05',
                'jun': '06', 'june': '06',
                'jul': '07', 'july': '07',
                'aug': '08', 'august': '08',
                'sep': '09', 'september': '09',
                'oct': '10', 'october': '10',
                'nov': '11', 'november': '11',
                'dec': '12', 'december': '12'
            }

            month_num = month_map.get(month, '01')
            return f"{year}-{month_num}-{day}"

        # Pattern: YYYY-MM-DD or YYYY_MM_DD
        iso_pattern = r'(\d{4})[-_](\d{2})[-_](\d{2})'
        match = re.search(iso_pattern, filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

        return None

    def _extract_date_from_content(self, content: str) -> Optional[str]:
        """Extract date from document header/content"""
        # Similar pattern matching in content
        date_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'

        match = re.search(date_pattern, content, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).lower()
            year = match.group(3)

            month_map = {
                'january': '01', 'february': '02', 'march': '03',
                'april': '04', 'may': '05', 'june': '06',
                'july': '07', 'august': '08', 'september': '09',
                'october': '10', 'november': '11', 'december': '12'
            }

            month_num = month_map.get(month, '01')
            return f"{year}-{month_num}-{day}"

        return None

    def _format_date_display(self, iso_date: str) -> str:
        """Format ISO date for display"""
        try:
            dt = datetime.strptime(iso_date, '%Y-%m-%d')
            return dt.strftime('%d %B %Y')
        except:
            return iso_date

    def _fix_correspondence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix correspondence sender/recipient mapping

        Maps:
        - Sender name from signature
        - Recipient name from salutation
        - Removes duplicate nesting
        """
        # Get current values
        signature = data['content'].get('signature', '')
        salutation = data['content'].get('salutation', '')

        # Remove "Dear " and trailing comma/punctuation from salutation
        recipient_name = re.sub(r'^Dear\s+', '', salutation, flags=re.IGNORECASE)
        recipient_name = re.sub(r'[,;:]$', '', recipient_name).strip()

        # Fix nested correspondence structure
        if 'correspondence' in data['document']:
            corresp = data['document']['correspondence']

            # Remove duplicate nesting if present
            if 'correspondence' in corresp:
                corresp = corresp['correspondence']
                data['document']['correspondence'] = corresp

            # Update sender
            if signature and 'sender' in corresp:
                if not corresp['sender'].get('name'):
                    corresp['sender']['name'] = signature
                    logger.debug(f"✓ Set sender name from signature: {signature}")

            # Update recipient
            if recipient_name and 'recipient' in corresp:
                if not corresp['recipient'].get('name') or corresp['recipient']['name'] == 'Last':
                    corresp['recipient']['name'] = recipient_name
                    logger.debug(f"✓ Set recipient name from salutation: {recipient_name}")

            # Rename 'organization' to 'affiliation' if present
            for party in ['sender', 'recipient']:
                if party in corresp and 'organization' in corresp[party]:
                    if 'affiliation' not in corresp[party]:
                        corresp[party]['affiliation'] = corresp[party].pop('organization')

        return data

    def _add_ami_metadata(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Add AMI filename metadata if parser available
        """
        if not self.ami_parser:
            return data

        try:
            ami_result = self.ami_parser.parse(filename)

            if ami_result.get('parsed'):
                data['metadata']['ami_metadata'] = {
                    'master_identifier': ami_result.get('master_identifier'),
                    'collection': ami_result.get('collection'),
                    'series': ami_result.get('series'),
                    'page_number': ami_result.get('page_number'),
                    'sequence_id': ami_result.get('sequence'),
                    'document_type_code': ami_result.get('document_type'),
                    'medium_code': ami_result.get('medium'),
                    'year': ami_result.get('year')
                }

                # Also populate storage_location if available
                if ami_result.get('master_identifier'):
                    data['metadata']['storage_location']['box_number'] = f"Box {ami_result.get('collection', '')}"
                    data['metadata']['storage_location']['folder_number'] = f"Folder {ami_result.get('series', '')}"

                logger.debug(f"✓ Added AMI metadata: {ami_result.get('master_identifier')}")
        except Exception as e:
            logger.warning(f"Failed to parse AMI filename: {e}")

        return data

    def _add_temporal_markers(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add temporal markers for easier filtering

        Adds: year, decade, era, quarter, etc.
        """
        date_str = data['document'].get('date', {}).get('creation_date')

        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')

                if 'date' not in data['document']:
                    data['document']['date'] = {}

                data['document']['date']['temporal_markers'] = {
                    'year': dt.year,
                    'month': dt.month,
                    'day': dt.day,
                    'decade': f"{(dt.year // 10) * 10}s",
                    'quarter': f"Q{(dt.month - 1) // 3 + 1}",
                    'day_of_week': dt.strftime('%A'),
                    'is_approximate': False
                }

                logger.debug(f"✓ Added temporal markers for {dt.year}")
            except Exception as e:
                logger.warning(f"Failed to parse date for temporal markers: {e}")

        return data

    def _add_classification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add classification metadata based on content
        """
        # Extract topics from keywords
        keywords = data.get('analysis', {}).get('keywords', [])
        topics = [kw.get('keyword', '') for kw in keywords[:5] if kw.get('keyword')]

        # Extract subjects
        subjects = data.get('analysis', {}).get('subjects', [])
        subject_names = [subj.get('subject', '') for subj in subjects if subj.get('subject')]

        data['metadata']['classification'] = {
            'primary_subject': subject_names[0] if subject_names else '',
            'secondary_subjects': subject_names[1:4] if len(subject_names) > 1 else [],
            'topics': topics,
            'themes': [],  # Can be enhanced later
            'genre': self._infer_genre(data)
        }

        logger.debug("✓ Added classification metadata")
        return data

    def _infer_genre(self, data: Dict[str, Any]) -> str:
        """Infer document genre from type and content"""
        doc_type = data['metadata'].get('document_type', '').lower()

        genre_map = {
            'letter': 'personal_correspondence',
            'memo': 'official_communication',
            'telegram': 'urgent_communication',
            'email': 'electronic_correspondence'
        }

        return genre_map.get(doc_type, 'correspondence')

    def _generate_facets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate pre-computed facets for search
        """
        facets = {}

        # Decade facet
        temporal = data['document'].get('date', {}).get('temporal_markers', {})
        if temporal.get('decade'):
            facets['decade'] = temporal['decade']

        # Document type facet
        if data['metadata'].get('document_type'):
            facets['document_type'] = data['metadata']['document_type']

        # Language facet
        languages = data['document'].get('languages', [])
        if languages:
            facets['language'] = languages[0] if isinstance(languages, list) else languages

        # Collection facet
        if data['metadata'].get('collection_id'):
            facets['collection'] = data['metadata']['collection_id']

        # Count facets
        facets['person_count'] = len(data.get('analysis', {}).get('people', []))
        facets['location_count'] = len(data.get('analysis', {}).get('locations', []))
        facets['organization_count'] = len(data.get('analysis', {}).get('organizations', []))
        facets['event_count'] = len(data.get('analysis', {}).get('events', []))

        # Boolean facets
        facets['has_images'] = False  # Can detect from OCR metadata
        facets['has_attachments'] = len(data['content'].get('attachments', [])) > 0

        if 'searchability' not in data:
            data['searchability'] = {}
        data['searchability']['facets'] = facets

        logger.debug(f"✓ Generated {len(facets)} facets")
        return data

    def _add_searchability_metadata(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Add searchability-specific metadata
        """
        if 'searchability' not in data:
            data['searchability'] = {}

        # Generate tags from keywords and subjects
        tags = set()

        # From keywords
        keywords = data.get('analysis', {}).get('keywords', [])
        for kw in keywords[:10]:
            if kw.get('keyword'):
                tags.add(kw['keyword'])

        # From subjects
        subjects = data.get('analysis', {}).get('subjects', [])
        for subj in subjects:
            if subj.get('subject'):
                # Convert snake_case to Title Case
                tag = subj['subject'].replace('_', ' ').title()
                tags.add(tag)

        # From temporal
        temporal = data['document'].get('date', {}).get('temporal_markers', {})
        if temporal.get('year'):
            tags.add(str(temporal['year']))
        if temporal.get('decade'):
            tags.add(temporal['decade'])

        # From people (first 3)
        people = data.get('analysis', {}).get('people', [])
        for person in people[:3]:
            if person.get('name'):
                tags.add(person['name'])

        data['searchability']['tags'] = sorted(list(tags))
        data['searchability']['verification_status'] = 'auto'
        data['searchability']['last_indexed'] = datetime.utcnow().isoformat() + 'Z'
        data['searchability']['index_version'] = 'v2.0'
        data['searchability']['search_boost'] = 1.0

        logger.debug(f"✓ Generated {len(tags)} search tags")
        return data

    def _calculate_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate metadata completeness score

        Checks presence of critical fields
        """
        required_fields = [
            ('metadata', 'id'),
            ('metadata', 'collection_id'),
            ('metadata', 'document_type'),
            ('content', 'full_text'),
            ('content', 'summary'),
            ('document', 'date', 'creation_date'),
            ('document', 'correspondence', 'sender', 'name'),
            ('document', 'correspondence', 'recipient', 'name'),
            ('analysis', 'people'),
            ('analysis', 'keywords')
        ]

        present = 0
        total = len(required_fields)

        for field_path in required_fields:
            current = data
            exists = True
            for key in field_path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    exists = False
                    break

            if exists and current:
                present += 1

        score = present / total if total > 0 else 0.0

        if 'searchability' not in data:
            data['searchability'] = {}

        data['searchability']['completeness_score'] = round(score, 2)
        data['searchability']['quality_score'] = round(score * 0.95, 2)  # Slightly conservative

        logger.debug(f"✓ Completeness score: {score:.2%} ({present}/{total} fields)")
        return data


def enhance_enriched_metadata(
    enriched_data: Dict[str, Any],
    ocr_data: Dict[str, Any],
    filename: str,
    document_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    ami_parser=None
) -> Dict[str, Any]:
    """
    Convenience function to enhance metadata

    Args:
        enriched_data: Merged results from orchestrator
        ocr_data: Original OCR data
        filename: Original filename
        document_id: Optional document ID
        collection_id: Optional collection ID
        ami_parser: Optional AMI parser instance

    Returns:
        Enhanced metadata
    """
    enhancer = MetadataEnhancer(ami_parser=ami_parser)
    return enhancer.enhance_metadata(
        enriched_data,
        ocr_data,
        filename,
        document_id,
        collection_id
    )
