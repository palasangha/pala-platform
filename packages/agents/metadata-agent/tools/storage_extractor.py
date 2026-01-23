"""
Storage Information Extractor - Extracts archive and storage location information
Parses archive names, collection IDs, box/folder numbers from text and file paths
"""

import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StorageExtractor:
    """Extracts storage location information from documents and file paths"""

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'llama3.2'):
        """
        Initialize extractor

        Args:
            ollama_host: Ollama API host URL
            model: Model name for semantic extraction
        """
        self.ollama_host = ollama_host
        self.model = model
        logger.info("StorageExtractor initialized")

    async def extract(self, text: str, file_path: str = '', metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract storage location information from text and file path

        Args:
            text: OCR text from document
            file_path: File path where document is stored
            metadata: Optional file metadata dictionary

        Returns:
            {
                "archive_name": str,
                "collection_name": str,
                "box_number": str,
                "folder_number": str,
                "digital_repository": str
            }
        """
        if metadata is None:
            metadata = {}

        result = {
            'archive_name': '',
            'collection_name': '',
            'box_number': '',
            'folder_number': '',
            'digital_repository': ''
        }

        # Extract from file path (most reliable)
        path_extraction = self._extract_from_path(file_path)
        result.update(path_extraction)

        # Extract from document text (for archive/collection names)
        text_extraction = self._extract_from_text(text)
        # Only override if not already found in path
        if not result['archive_name']:
            result['archive_name'] = text_extraction['archive_name']
        if not result['collection_name']:
            result['collection_name'] = text_extraction['collection_name']

        # Extract from metadata
        metadata_extraction = self._extract_from_metadata(metadata)
        # Only override if not already found
        for key in metadata_extraction:
            if not result[key]:
                result[key] = metadata_extraction[key]

        logger.info(f"Storage extraction: archive={result['archive_name']}, collection={result['collection_name']}")

        return result

    def _extract_from_path(self, file_path: str) -> Dict[str, str]:
        """
        Extract storage info from file path

        Expected patterns:
        - /uploads/goenka_letters/box_001/folder_05/document.jpg
        - /archive/VRI/collection_001/box_01/folder_1/doc.pdf
        """
        result = {
            'archive_name': '',
            'collection_name': '',
            'box_number': '',
            'folder_number': '',
            'digital_repository': ''
        }

        if not file_path:
            return result

        # Try to extract box number
        box_match = re.search(r'box[_-]?(\d+)', file_path, re.IGNORECASE)
        if box_match:
            result['box_number'] = box_match.group(1).zfill(3)

        # Try to extract folder number
        folder_match = re.search(r'folder[_-]?(\d+)', file_path, re.IGNORECASE)
        if folder_match:
            result['folder_number'] = folder_match.group(1).zfill(2)

        # Extract collection name from path (usually a directory name)
        path_parts = file_path.lower().split('/')
        for i, part in enumerate(path_parts):
            if 'collection' in part or 'archive' in part:
                result['collection_name'] = path_parts[i]
            # Archive name might be in a parent directory
            if part in ['vri', 'archive', 'goenka', 'manuscripts', 'collection']:
                result['archive_name'] = part

        # Determine digital repository from path
        if 'uploads' in file_path:
            result['digital_repository'] = 'local_uploads'
        elif 'archive' in file_path:
            result['digital_repository'] = 'archive_server'

        return result

    def _extract_from_text(self, text: str) -> Dict[str, str]:
        """
        Extract storage references from document text

        Looks for patterns like:
        - "VRI Archive", "Vipassana Research Institute"
        - "Collection ID: ...", "Archive No: ..."
        """
        result = {
            'archive_name': '',
            'collection_name': '',
        }

        if not text:
            return result

        text_lower = text.lower()

        # Known archive names (from historical context)
        archive_names = {
            'vri': 'Vipassana Research Institute',
            'vipassana research institute': 'VRI',
            'goenka archive': 'S.N. Goenka Archive',
            'igatpuri collection': 'Igatpuri Archive',
        }

        for key, archive in archive_names.items():
            if key in text_lower:
                result['archive_name'] = archive
                break

        # Look for explicit collection references
        collection_match = re.search(r'collection[:\s]+([A-Za-z0-9\s-]+?)(?:[,\n.]|$)', text, re.IGNORECASE)
        if collection_match:
            result['collection_name'] = collection_match.group(1).strip()

        # Look for archive references
        archive_match = re.search(r'archive[:\s]+([A-Za-z0-9\s-]+?)(?:[,\n.]|$)', text, re.IGNORECASE)
        if archive_match and not result['archive_name']:
            result['archive_name'] = archive_match.group(1).strip()

        return result

    def _extract_from_metadata(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract storage info from file metadata dictionary

        Looks for keys like: archive_name, collection_id, box_number, folder_number
        """
        result = {
            'archive_name': '',
            'collection_name': '',
            'box_number': '',
            'folder_number': '',
            'digital_repository': ''
        }

        # Direct mapping from metadata keys
        key_mapping = {
            'archive_name': 'archive_name',
            'archive_id': 'archive_name',
            'collection_name': 'collection_name',
            'collection_id': 'collection_name',
            'box_number': 'box_number',
            'box_id': 'box_number',
            'folder_number': 'folder_number',
            'folder_id': 'folder_number',
            'repository_name': 'digital_repository',
            'repository_url': 'digital_repository',
        }

        for metadata_key, result_key in key_mapping.items():
            if metadata_key in metadata:
                value = str(metadata[metadata_key])
                if value and result[result_key] == '':
                    result[result_key] = value

        return result
