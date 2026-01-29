"""
Metadata Writer - Writes enriched metadata to file system

This tool takes enriched metadata and writes it to JSON files alongside
the original documents. Supports both single file and batch operations.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Writes enriched metadata to JSON files"""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize MetadataWriter

        Args:
            base_path: Base directory for metadata files (defaults to /data)
        """
        self.base_path = base_path or os.getenv('METADATA_BASE_PATH', '/data')
        self.enabled = True
        logger.info(f"MetadataWriter initialized with base path: {self.base_path}")

    def write_metadata(
        self,
        file_path: str,
        metadata: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write metadata to a JSON file

        Args:
            file_path: Path to the original file (used to determine output location)
            metadata: Metadata dictionary to write
            output_filename: Optional custom output filename (defaults to {original}_metadata.json)

        Returns:
            Dictionary with success status, output path, and any errors
        """
        try:
            # Resolve the file path
            original_path = Path(file_path)

            # Determine output path
            if output_filename:
                output_path = original_path.parent / output_filename
            else:
                # Create metadata filename: {original_stem}_metadata.json
                output_path = original_path.parent / f"{original_path.stem}_metadata.json"

            # Ensure the directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Add timestamp to metadata
            enriched_metadata = {
                **metadata,
                '_metadata_written_at': datetime.utcnow().isoformat(),
                '_original_file': str(original_path),
                '_metadata_file': str(output_path)
            }

            # Write to file with pretty formatting
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Metadata written to {output_path}")

            return {
                'success': True,
                'output_path': str(output_path),
                'original_file': str(original_path),
                'bytes_written': output_path.stat().st_size,
                'metadata_keys': list(metadata.keys())
            }

        except Exception as e:
            error_msg = f"Failed to write metadata for {file_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'original_file': file_path
            }

    def write_batch_metadata(
        self,
        batch: List[Dict[str, Any]],
        base_output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write metadata for multiple files in batch

        Args:
            batch: List of dicts with 'file_path' and 'metadata' keys
            base_output_dir: Optional base directory for all outputs

        Returns:
            Dictionary with batch results summary
        """
        results = {
            'total': len(batch),
            'successful': 0,
            'failed': 0,
            'outputs': [],
            'errors': []
        }

        for item in batch:
            file_path = item.get('file_path')
            metadata = item.get('metadata', {})

            if not file_path:
                results['failed'] += 1
                results['errors'].append({
                    'error': 'Missing file_path in batch item',
                    'item': item
                })
                continue

            # Override output directory if specified
            if base_output_dir:
                original_filename = Path(file_path).name
                file_path = str(Path(base_output_dir) / original_filename)

            result = self.write_metadata(file_path, metadata)

            if result['success']:
                results['successful'] += 1
                results['outputs'].append(result)
            else:
                results['failed'] += 1
                results['errors'].append(result)

        logger.info(f"Batch write completed: {results['successful']}/{results['total']} successful")
        return results

    def update_metadata(
        self,
        metadata_file_path: str,
        updates: Dict[str, Any],
        merge: bool = True
    ) -> Dict[str, Any]:
        """
        Update an existing metadata file

        Args:
            metadata_file_path: Path to existing metadata JSON file
            updates: Dictionary of fields to update
            merge: If True, merge with existing data; if False, replace entirely

        Returns:
            Dictionary with success status and updated metadata
        """
        try:
            metadata_path = Path(metadata_file_path)

            if not metadata_path.exists():
                return {
                    'success': False,
                    'error': f'Metadata file not found: {metadata_file_path}'
                }

            # Read existing metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)

            # Merge or replace
            if merge:
                updated_metadata = {**existing_metadata, **updates}
            else:
                updated_metadata = updates

            # Add update timestamp
            updated_metadata['_metadata_updated_at'] = datetime.utcnow().isoformat()

            # Write back
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(updated_metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Metadata updated: {metadata_path}")

            return {
                'success': True,
                'metadata_path': str(metadata_path),
                'updated_fields': list(updates.keys()),
                'merge_mode': merge
            }

        except Exception as e:
            error_msg = f"Failed to update metadata at {metadata_file_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def read_metadata(self, metadata_file_path: str) -> Dict[str, Any]:
        """
        Read metadata from a JSON file

        Args:
            metadata_file_path: Path to metadata JSON file

        Returns:
            Dictionary with metadata or error
        """
        try:
            metadata_path = Path(metadata_file_path)

            if not metadata_path.exists():
                return {
                    'success': False,
                    'error': f'Metadata file not found: {metadata_file_path}'
                }

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            return {
                'success': True,
                'metadata': metadata,
                'metadata_path': str(metadata_path)
            }

        except Exception as e:
            error_msg = f"Failed to read metadata from {metadata_file_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def delete_metadata(self, metadata_file_path: str) -> Dict[str, Any]:
        """
        Delete a metadata file

        Args:
            metadata_file_path: Path to metadata JSON file

        Returns:
            Dictionary with success status
        """
        try:
            metadata_path = Path(metadata_file_path)

            if not metadata_path.exists():
                return {
                    'success': False,
                    'error': f'Metadata file not found: {metadata_file_path}'
                }

            metadata_path.unlink()
            logger.info(f"✓ Metadata deleted: {metadata_path}")

            return {
                'success': True,
                'deleted_path': str(metadata_path)
            }

        except Exception as e:
            error_msg = f"Failed to delete metadata at {metadata_file_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def write_metadata_to_file(
    file_path: str,
    metadata: Dict[str, Any],
    output_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to write metadata to file

    Args:
        file_path: Path to the original file
        metadata: Metadata dictionary
        output_filename: Optional custom output filename

    Returns:
        Result dictionary
    """
    writer = MetadataWriter()
    return writer.write_metadata(file_path, metadata, output_filename)


# Example usage and testing
if __name__ == "__main__":
    # Test metadata writing
    test_metadata = {
        'document_type': 'Letter',
        'sender': 'John Doe',
        'recipient': 'Jane Smith',
        'date': '1990-05-15',
        'subjects': ['Buddhism', 'Meditation'],
        'summary': 'A letter discussing meditation practices.',
        'historical_context': 'Written during the period of...'
    }

    writer = MetadataWriter(base_path='/tmp/test_metadata')

    # Test single file write
    result = writer.write_metadata(
        '/tmp/test_metadata/sample_letter.jpg',
        test_metadata
    )

    print("Write Result:")
    print(json.dumps(result, indent=2))

    # Test batch write
    batch = [
        {
            'file_path': '/tmp/test_metadata/letter1.jpg',
            'metadata': {**test_metadata, 'document_id': 'DOC001'}
        },
        {
            'file_path': '/tmp/test_metadata/letter2.jpg',
            'metadata': {**test_metadata, 'document_id': 'DOC002'}
        }
    ]

    batch_result = writer.write_batch_metadata(batch)
    print("\nBatch Write Result:")
    print(json.dumps(batch_result, indent=2))
