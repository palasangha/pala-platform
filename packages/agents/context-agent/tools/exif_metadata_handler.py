"""
EXIF Metadata Handler - Read and write EXIF/IPTC/XMP metadata to image files

This tool handles embedded metadata in image files, allowing you to:
1. Read existing EXIF/IPTC/XMP metadata
2. Write enriched metadata to image files
3. Create copies of images with embedded metadata
4. Map enriched data to standard metadata fields

Supports: JPEG, TIFF, PNG (limited), and other image formats
Uses: Pillow for basic EXIF, piexif for advanced EXIF editing
"""

import logging
import json
import os
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False
    logging.warning("piexif not available - EXIF writing will be limited")

logger = logging.getLogger(__name__)


class ExifMetadataHandler:
    """Handle EXIF/IPTC/XMP metadata in image files"""

    # Common EXIF tags for document metadata
    EXIF_TAG_MAP = {
        'title': 'ImageDescription',  # EXIF tag 270
        'author': 'Artist',  # EXIF tag 315
        'creator': 'Artist',
        'copyright': 'Copyright',  # EXIF tag 33432
        'date': 'DateTime',  # EXIF tag 306
        'software': 'Software',  # EXIF tag 305
        'user_comment': 'UserComment',  # EXIF tag 37510
    }

    def __init__(self):
        """Initialize EXIF metadata handler"""
        self.enabled = True
        logger.info(f"ExifMetadataHandler initialized (piexif available: {PIEXIF_AVAILABLE})")

    def read_exif(self, image_path: str) -> Dict[str, Any]:
        """
        Read EXIF metadata from an image file

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with EXIF metadata
        """
        try:
            image_path = Path(image_path)

            if not image_path.exists():
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}'
                }

            with Image.open(image_path) as img:
                exif_data = img.getexif()

                if not exif_data:
                    return {
                        'success': True,
                        'image_path': str(image_path),
                        'exif': {},
                        'message': 'No EXIF data found'
                    }

                # Decode EXIF tags
                decoded_exif = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)

                    # Handle bytes values
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)

                    decoded_exif[tag_name] = value

                # Get image info
                image_info = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }

                return {
                    'success': True,
                    'image_path': str(image_path),
                    'exif': decoded_exif,
                    'image_info': image_info
                }

        except Exception as e:
            logger.error(f"Error reading EXIF from {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }

    def write_exif(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write metadata to image EXIF tags

        Args:
            image_path: Path to source image
            metadata: Metadata dictionary to embed
            output_path: Optional output path (defaults to overwrite original)

        Returns:
            Dictionary with success status and output path
        """
        if not PIEXIF_AVAILABLE:
            return {
                'success': False,
                'error': 'piexif library not available - cannot write EXIF metadata'
            }

        try:
            image_path = Path(image_path)

            if not image_path.exists():
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}'
                }

            # Determine output path
            if output_path:
                output_path = Path(output_path)
            else:
                output_path = image_path

            # Load existing EXIF data
            try:
                exif_dict = piexif.load(str(image_path))
            except:
                # Create new EXIF dict if none exists
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            # Map metadata to EXIF tags
            exif_dict = self._map_metadata_to_exif(metadata, exif_dict)

            # Convert to bytes
            exif_bytes = piexif.dump(exif_dict)

            # Save image with EXIF
            with Image.open(image_path) as img:
                img.save(str(output_path), exif=exif_bytes, quality=95)

            logger.info(f"✓ EXIF metadata written to {output_path}")

            return {
                'success': True,
                'output_path': str(output_path),
                'original_path': str(image_path),
                'metadata_keys': list(metadata.keys())
            }

        except Exception as e:
            logger.error(f"Error writing EXIF to {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }

    def create_copy_with_metadata(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        output_dir: Optional[str] = None,
        suffix: str = "_enriched"
    ) -> Dict[str, Any]:
        """
        Create a copy of the image with embedded metadata

        Args:
            image_path: Path to source image
            metadata: Metadata to embed
            output_dir: Directory for output (defaults to same as source)
            suffix: Suffix to add to filename (default: "_enriched")

        Returns:
            Dictionary with paths to both JSON and image copies
        """
        try:
            image_path = Path(image_path)

            if not image_path.exists():
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}'
                }

            # Determine output directory
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = image_path.parent

            # Create output filenames
            base_name = image_path.stem
            extension = image_path.suffix

            # Create enriched image filename
            enriched_image_path = output_dir / f"{base_name}{suffix}{extension}"

            # Create metadata JSON filename
            metadata_json_path = output_dir / f"{base_name}{suffix}_metadata.json"

            # 1. Write JSON metadata file
            enriched_metadata = {
                **metadata,
                '_metadata_written_at': datetime.utcnow().isoformat(),
                '_original_file': str(image_path),
                '_enriched_image': str(enriched_image_path),
                '_metadata_file': str(metadata_json_path)
            }

            with open(metadata_json_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ JSON metadata written to {metadata_json_path}")

            # 2. Create image copy with embedded EXIF
            if PIEXIF_AVAILABLE and extension.lower() in ['.jpg', '.jpeg', '.tiff', '.tif']:
                # Write EXIF metadata
                result = self.write_exif(str(image_path), metadata, str(enriched_image_path))

                if not result['success']:
                    # Fallback: just copy the image
                    shutil.copy2(image_path, enriched_image_path)
                    logger.warning(f"EXIF write failed, created plain copy: {enriched_image_path}")
            else:
                # For unsupported formats, just copy
                shutil.copy2(image_path, enriched_image_path)
                logger.info(f"✓ Image copied (EXIF not supported for {extension}): {enriched_image_path}")

            return {
                'success': True,
                'original_image': str(image_path),
                'enriched_image': str(enriched_image_path),
                'metadata_json': str(metadata_json_path),
                'exif_embedded': PIEXIF_AVAILABLE and extension.lower() in ['.jpg', '.jpeg', '.tiff', '.tif'],
                'file_sizes': {
                    'original': image_path.stat().st_size,
                    'enriched_image': enriched_image_path.stat().st_size,
                    'metadata_json': metadata_json_path.stat().st_size
                }
            }

        except Exception as e:
            logger.error(f"Error creating copy with metadata: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }

    def _map_metadata_to_exif(
        self,
        metadata: Dict[str, Any],
        exif_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map enriched metadata to EXIF tags

        Args:
            metadata: Enriched metadata dictionary
            exif_dict: Existing EXIF dictionary

        Returns:
            Updated EXIF dictionary
        """
        # Map basic fields
        if 'title' in metadata or 'summary' in metadata:
            # ImageDescription (tag 270)
            description = metadata.get('title') or metadata.get('summary', '')[:200]
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')

        if 'sender' in metadata or 'author' in metadata or 'creator' in metadata:
            # Artist (tag 315)
            artist = metadata.get('sender') or metadata.get('author') or metadata.get('creator', '')
            exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode('utf-8')

        if 'date' in metadata or 'original_date' in metadata:
            # DateTime (tag 306)
            date_str = metadata.get('date') or metadata.get('original_date', '')
            if date_str:
                # Format: YYYY:MM:DD HH:MM:SS
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    exif_dict["0th"][piexif.ImageIFD.DateTime] = dt.strftime('%Y:%m:%d %H:%M:%S')
                except:
                    pass

        # Copyright
        if 'copyright' in metadata:
            exif_dict["0th"][piexif.ImageIFD.Copyright] = metadata['copyright'].encode('utf-8')

        # Software (mark as AI-enriched)
        software = f"Heritage Platform - AI Enriched {datetime.utcnow().strftime('%Y-%m-%d')}"
        exif_dict["0th"][piexif.ImageIFD.Software] = software.encode('utf-8')

        # UserComment - store summary or description
        if 'summary' in metadata or 'historical_context' in metadata:
            comment = metadata.get('summary') or metadata.get('historical_context', '')
            # Limit to 500 chars for EXIF
            comment = comment[:500]
            # UserComment needs special encoding - prepend ASCII code
            # Format: ASCII code (0x41534349) + content
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = b'ASCII\x00\x00\x00' + comment.encode('utf-8')[:492]

        # Store structured metadata as JSON in MakerNote (if small enough)
        try:
            # Create minimal metadata for MakerNote
            minimal_metadata = {
                'document_type': metadata.get('document_type'),
                'sender': metadata.get('sender'),
                'recipient': metadata.get('recipient'),
                'date': metadata.get('date'),
                'subjects': metadata.get('subjects', [])[:5],  # Limit array size
            }
            # Remove None values
            minimal_metadata = {k: v for k, v in minimal_metadata.items() if v is not None}

            metadata_json = json.dumps(minimal_metadata)
            if len(metadata_json) < 1024:  # EXIF has size limits
                exif_dict["Exif"][piexif.ExifIFD.MakerNote] = metadata_json.encode('utf-8')
        except:
            pass  # Skip if metadata too large or serialization fails

        return exif_dict

    def batch_create_copies(
        self,
        batch: List[Dict[str, Any]],
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create copies with metadata for multiple images

        Args:
            batch: List of dicts with 'image_path' and 'metadata' keys
            output_dir: Optional output directory

        Returns:
            Batch processing results
        """
        results = {
            'total': len(batch),
            'successful': 0,
            'failed': 0,
            'outputs': [],
            'errors': []
        }

        for item in batch:
            image_path = item.get('image_path')
            metadata = item.get('metadata', {})
            suffix = item.get('suffix', '_enriched')

            if not image_path:
                results['failed'] += 1
                results['errors'].append({
                    'error': 'Missing image_path in batch item',
                    'item': item
                })
                continue

            result = self.create_copy_with_metadata(
                image_path,
                metadata,
                output_dir,
                suffix
            )

            if result['success']:
                results['successful'] += 1
                results['outputs'].append(result)
            else:
                results['failed'] += 1
                results['errors'].append(result)

        logger.info(f"Batch processing completed: {results['successful']}/{results['total']} successful")
        return results


# Convenience functions
def read_image_exif(image_path: str) -> Dict[str, Any]:
    """Read EXIF metadata from image"""
    handler = ExifMetadataHandler()
    return handler.read_exif(image_path)


def create_enriched_copy(
    image_path: str,
    metadata: Dict[str, Any],
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Create enriched copy of image with metadata"""
    handler = ExifMetadataHandler()
    return handler.create_copy_with_metadata(image_path, metadata, output_dir)


# Example usage
if __name__ == "__main__":
    # Test EXIF handling
    test_metadata = {
        'document_type': 'Letter',
        'sender': 'S.N. Goenka',
        'recipient': 'Student',
        'date': '1990-05-15',
        'subjects': ['Buddhism', 'Vipassana', 'Meditation'],
        'summary': 'A letter discussing meditation practices and upcoming courses.',
        'historical_context': 'Written during the period of Vipassana expansion in the West.'
    }

    handler = ExifMetadataHandler()

    # Create test image
    test_image = '/tmp/test_exif_image.jpg'
    img = Image.new('RGB', (800, 600), color='white')
    img.save(test_image, 'JPEG')

    print("="*60)
    print("Testing EXIF Metadata Handler")
    print("="*60)

    # Test 1: Read EXIF
    print("\n1. Reading EXIF from test image:")
    result = handler.read_exif(test_image)
    print(json.dumps(result, indent=2))

    # Test 2: Create copy with metadata
    print("\n2. Creating enriched copy:")
    result = handler.create_copy_with_metadata(
        test_image,
        test_metadata,
        output_dir='/tmp'
    )
    print(json.dumps(result, indent=2))

    # Cleanup
    Path(test_image).unlink(missing_ok=True)
    if result.get('success'):
        Path(result['enriched_image']).unlink(missing_ok=True)
        Path(result['metadata_json']).unlink(missing_ok=True)

    print("\n✓ Tests completed")
