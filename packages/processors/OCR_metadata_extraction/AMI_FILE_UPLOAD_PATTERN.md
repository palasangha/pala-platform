# AMI File Upload Pattern Implementation

This document explains how to upload files to Archipelago using the AMI (Archipelago Multi-Importer) pattern, which matches the PHP/Drupal workflow you provided.

## Overview

The AMI pattern differs from the standard approach by uploading files **BEFORE** creating metadata:

```
Standard Pattern:           AMI Pattern (PHP example):
1. Create metadata          1. Upload file → Get FID
2. Upload file              2. Map FID to metadata field
3. Link file to metadata    3. Create metadata with FID included
```

## The PHP Pattern You Provided

Your PHP code shows this workflow:

```php
// 1. Upload file with curl
$args = [
    'curl', '-L',
    '-H "Accept: application/vnd.api+json;"',
    '-H "Content-Type: application/octet-stream;"',
    '-H "Content-Disposition: attachment; filename=\"' . urlencode($file->filename) . '\""',
    '--data-binary @"' . $file->uri.'"',
];

// 2. Get FID from response
$response = json_decode($process->getOutput(), TRUE);
$fid = $response['data']['attributes']['drupal_internal__fid'];

// 3. Map MIME type to field name
$mime_type = $response['data']['attributes']['filemime'];
$as_file_type = explode('/', $mime_type);
$as_file_type = ($as_file_type != 'application') ? $as_file_type : 'document';

// 4. Add FID to appropriate metadata array
if (isset($data[$as_specific . 's']) && ($data[$as_specific . 's'] == NULL || is_array($data[$as_specific . 's']))) {
    $data[$as_specific . 's'][] = $fid;
} else {
    $data[$as_file_type . 's'][] = $fid;
}
```

## Python Implementation

We've implemented this exact pattern in Python:

### 1. Upload File Before Metadata

```python
from app.services.archipelago_service import ArchipelagoService

service = ArchipelagoService()

# Login first
csrf_token = service._login()

# Upload file and get FID
result = service.upload_file_before_metadata(
    file_path="eng-typed/document.pdf",
    csrf_token=csrf_token
)

# Result contains:
{
    'fid': 123,                    # Drupal internal file ID
    'filename': 'document.pdf',
    'filesize': 563750,
    'filemime': 'application/pdf',
    'field_name': 'documents',     # Auto-mapped from MIME type
    'uri': 's3://...'
}
```

### 2. MIME Type to Field Mapping

The implementation automatically maps MIME types to Archipelago fields, following the PHP logic:

```python
# MIME type → Field name mapping
'application/pdf'     → 'documents'
'image/jpeg'          → 'images'
'image/png'           → 'images'
'video/mp4'           → 'videos'
'audio/mp3'           → 'audios'
'model/gltf+json'     → 'models'
'text/plain'          → 'documents'
```

The mapping follows these rules (from PHP):
1. Split MIME type by '/' → `['application', 'pdf']`
2. Use first part as type → `'application'`
3. If type is 'application', map to 'document' → `'document'`
4. Pluralize → `'documents'`

### 3. Create Digital Object with Files

**Simple approach** - automatic field mapping:

```python
service = ArchipelagoService()

metadata = {
    "@context": "http://schema.org",
    "@type": "DigitalDocument",
    "label": "My Document",
    "description": "Test document with files",
    "language": ["English"],
    "owner": "VRI",
    # File arrays will be populated automatically
}

result = service.create_digital_object_with_files(
    metadata=metadata,
    file_paths=[
        "eng-typed/document.pdf",    # → adds to metadata['documents']
        "eng-typed/image.jpg",        # → adds to metadata['images']
        "eng-typed/video.mp4"         # → adds to metadata['videos']
    ]
)
```

**Result**:
```python
{
    'success': True,
    'node_id': '550e8400-e29b-41d4-a716-446655440000',
    'url': 'http://localhost:8001/do/123',
    'files_attached': 3,
    'file_mapping': {
        'documents': [123],
        'images': [124],
        'videos': [125]
    },
    'uploaded_files': [
        {'fid': 123, 'filename': 'document.pdf', ...},
        {'fid': 124, 'filename': 'image.jpg', ...},
        {'fid': 125, 'filename': 'video.mp4', ...}
    ]
}
```

## Key Implementation Details

### Headers Used (Matching PHP)

```python
headers = {
    'Accept': 'application/vnd.api+json',
    'Content-Type': 'application/octet-stream',      # Exactly as in PHP
    'Content-Disposition': f'attachment; filename="{filename}"',
    'X-CSRF-Token': csrf_token
}
```

### Upload Endpoint

```python
# Uploads to field endpoint (matches AMI pattern)
POST {base_url}/jsonapi/node/digital_object/field_file_drop
```

### FID Extraction

The implementation handles multiple response formats:

```python
def _extract_fid_from_response(self, result: Dict) -> Optional[int]:
    # Format 1: {"fid": [{"value": 123}]}
    if 'fid' in result:
        fid_data = result['fid']
        if isinstance(fid_data, list) and len(fid_data) > 0:
            return fid_data[0].get('value')
        elif isinstance(fid_data, int):
            return fid_data

    # Format 2: {"drupal_internal__fid": 123}
    for field in ['drupal_internal__fid', 'id', 'file_id']:
        if field in result:
            value = result[field]
            if isinstance(value, int):
                return value

    return None
```

## Complete Example

Here's a complete example matching your PHP workflow:

```python
#!/usr/bin/env python3
from app.services.archipelago_service import ArchipelagoService

def upload_documents_ami_pattern():
    """Upload documents using AMI pattern (PHP style)"""

    service = ArchipelagoService()

    # Prepare metadata (without file IDs)
    metadata = {
        "@context": "http://schema.org",
        "@type": "DigitalDocument",
        "label": "Manuscript Collection",
        "description": "OCR processed manuscript",
        "language": ["English", "Hindi"],
        "owner": "Vipassana Research Institute",
        "creator": "VRI",
        "rights": "All rights reserved",

        # OCR metadata
        "ocr_text_preview": "Full OCR text content...",
        "ocr_provider": "google_vision",
        "ocr_confidence": 0.95,
        "ocr_language": "English",
        "ocr_processing_date": "2025-12-15"
    }

    # Files to upload
    files = [
        "eng-typed/manuscript_page1.pdf",
        "eng-typed/manuscript_page2.pdf",
        "eng-typed/manuscript_thumb.jpg"
    ]

    # Create digital object with files (AMI pattern)
    result = service.create_digital_object_with_files(
        metadata=metadata,
        file_paths=files
    )

    if result and result['success']:
        print(f"✓ Created digital object: {result['url']}")
        print(f"  Files attached: {result['files_attached']}")
        print(f"  Documents: {result['file_mapping'].get('documents', [])}")
        print(f"  Images: {result['file_mapping'].get('images', [])}")
        return result
    else:
        print("✗ Failed to create digital object")
        return None

if __name__ == '__main__':
    upload_documents_ami_pattern()
```

## Comparison: PHP vs Python

| Aspect | PHP (Your Code) | Python (Our Implementation) |
|--------|-----------------|----------------------------|
| Upload method | `curl` with `--data-binary` | `requests.post()` with binary data |
| Headers | `application/octet-stream` | `application/octet-stream` ✓ |
| MIME mapping | Manual logic with `explode()` | `_map_mime_to_field()` method |
| Field arrays | Manual `$data[$field][] = $fid` | Automatic append to metadata dict |
| Error handling | PHP exceptions | Python try/except with logging |

## Testing

Run the test suite:

```bash
# Test MIME type mapping (no connection required)
python3 test_ami_file_upload.py

# Test single file upload (requires Archipelago)
# Uncomment test_single_file_upload() in main()

# Test full AMI pattern (requires Archipelago + files)
# Uncomment test_ami_file_upload() in main()
```

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Upload Files First                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  document.pdf  ──→  Upload  ──→  FID: 123                  │
│  image.jpg     ──→  Upload  ──→  FID: 124                  │
│  video.mp4     ──→  Upload  ──→  FID: 125                  │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Map MIME Types to Fields                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FID 123 (application/pdf) → documents array                │
│  FID 124 (image/jpeg)      → images array                   │
│  FID 125 (video/mp4)       → videos array                   │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Build Metadata with FIDs                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  {                                                          │
│    "label": "My Document",                                  │
│    "description": "...",                                    │
│    "documents": [123],       ← FID added                    │
│    "images": [124],          ← FID added                    │
│    "videos": [125],          ← FID added                    │
│    "ocr_text_preview": "...",                               │
│    ...                                                      │
│  }                                                          │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Create Digital Object                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  POST /jsonapi/node/digital_object                          │
│  {                                                          │
│    "data": {                                                │
│      "type": "node--digital_object",                        │
│      "attributes": {                                        │
│        "title": "My Document",                              │
│        "field_descriptive_metadata": {                      │
│          "value": JSON(metadata)  ← Includes FIDs           │
│        }                                                    │
│      }                                                      │
│    }                                                        │
│  }                                                          │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                          │
                          ↓
                   ┌──────────────┐
                   │ Digital      │
                   │ Object       │
                   │ Created ✓    │
                   │              │
                   │ Files: 3     │
                   │ FIDs linked  │
                   └──────────────┘
```

## Benefits of This Pattern

1. **File IDs Known Before Metadata Creation**: You have FIDs before creating the node
2. **Explicit Field Mapping**: Clear mapping from MIME type to metadata field
3. **Atomic Operation**: Metadata already contains file references when node is created
4. **Matches Drupal AMI**: Follows established Archipelago Multi-Importer patterns
5. **Error Recovery**: Failed file uploads don't create orphaned nodes

## Error Handling

The implementation handles various error cases:

```python
# File not found
if not os.path.exists(file_path):
    logger.error(f"File not found: {file_path}")
    return None

# Upload failed
if response.status_code not in [200, 201]:
    logger.warning(f"Upload failed with status {response.status_code}")
    return None

# No FID in response
fid = self._extract_fid_from_response(result)
if not fid:
    logger.warning(f"Response missing FID")
    return None

# No files uploaded
if not uploaded_files:
    logger.error("No files were uploaded successfully")
    return None
```

## See Also

- `test_ami_file_upload.py` - Test suite for AMI file upload
- `archipelago_service.py:198` - `upload_file_before_metadata()` method
- `archipelago_service.py:304` - `_map_mime_to_field()` method
- `archipelago_service.py:1927` - `create_digital_object_with_files()` method
- `FILE_UPLOAD_AND_METADATA_LINKING.md` - Complete file upload documentation

## Next Steps

1. Test the implementation with your actual files
2. Verify FID mapping matches your expectations
3. Check that files appear correctly in Archipelago
4. Adjust MIME type mappings if needed for your use case
