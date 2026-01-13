# AMI Pattern Integration in Push to Archipelago Flow

This document explains how the AMI file upload pattern (from your PHP code) has been integrated into the push to Archipelago flow, replacing the hardcoded FID 49 with real file IDs.

## What Changed

### Before (Old Method)
```
1. Create metadata JSON
2. Create digital object node in Archipelago
3. Upload file AFTER node creation
4. If upload fails → Use hardcoded FID 49 as fallback
5. PATCH node with file links
```

**Problem**: Hardcoded FID 49 when file upload failed

### After (AMI Pattern - Default)
```
1. Upload file FIRST using AMI pattern (from PHP)
2. Get real FID from Archipelago response
3. Add FID to metadata (documents/images/videos arrays)
4. Create digital object with FID already in metadata
5. ✓ Real FID used (no hardcoded 49!)
```

**Benefit**: Real file IDs from the start, matching your PHP workflow

## Code Changes

### 1. New Parameter: `use_ami_pattern`

The `create_digital_object_from_ocr_data()` method now accepts a `use_ami_pattern` parameter:

```python
def create_digital_object_from_ocr_data(
    self,
    ocr_data: Dict[str, Any],
    collection_id: Optional[str] = None,
    file_id: Optional[int] = None,
    use_ami_pattern: bool = True  # NEW: Default is True (AMI pattern)
) -> Optional[Dict]:
```

**Default**: `True` (AMI pattern enabled by default)

### 2. File Upload Before Metadata Creation

When `use_ami_pattern=True`:

```python
# Upload file FIRST
upload_result = self.upload_file_before_metadata(
    file_path=file_path,
    csrf_token=csrf_token
)

if upload_result:
    drupal_file_id = upload_result['fid']  # Real FID!
    field_name = upload_result['field_name']  # 'documents', 'images', etc.

    # Add FID to metadata BEFORE creating node
    archipelago_data[field_name] = [drupal_file_id]

    # Update as:document with real FID
    archipelago_data['as:document'] = {
        f'urn:uuid:{doc_uuid}': {
            'dr:fid': drupal_file_id,  # ✓ Real FID (not 49)
            'dr:filesize': file_size,
            'dr:mimetype': mime_type,
            # ... other fields
        }
    }
```

### 3. Hardcoded FID 49 Only in Old Method

The hardcoded FID 49 is now **only used** when:
- `use_ami_pattern=False` (explicitly disabled)
- **AND** file upload fails

```python
# This code only runs if use_ami_pattern=False
if not use_ami_pattern and file_path and os.path.exists(file_path):
    # Try old upload methods...
    if drupal_file_id is None:
        doc_entry['dr:fid'] = 49  # Fallback only in old method
```

When AMI pattern is enabled (default), this fallback code **never runs**.

### 4. Enhanced Response

The response now includes information about which method was used:

```python
return {
    'success': True,
    'node_id': node_id,
    'drupal_file_id': 123,  # Real FID!
    'upload_method': 'AMI Pattern (file uploaded BEFORE metadata)',
    'ami_pattern_used': True,
    'note': 'File uploaded via AMI pattern (FID: 123)'
}
```

## Usage Examples

### Example 1: Default Behavior (AMI Pattern Enabled)

```python
from app.services.archipelago_service import ArchipelagoService

service = ArchipelagoService()

ocr_data = {
    'name': 'document.pdf',
    'label': 'My Document',
    'text': 'Full OCR text...',
    'file_info': {
        'filename': 'document.pdf',
        'file_path': 'eng-typed/document.pdf'
    },
    'ocr_metadata': {
        'provider': 'google_vision',
        'confidence': 0.95
    }
}

# Default: use_ami_pattern=True
result = service.create_digital_object_from_ocr_data(ocr_data)

if result:
    print(f"✓ Created: {result['url']}")
    print(f"  FID: {result['drupal_file_id']}")  # Real FID!
    print(f"  Method: {result['upload_method']}")
    # Output:
    # ✓ Created: http://localhost:8001/do/123
    #   FID: 456 (not 49!)
    #   Method: AMI Pattern (file uploaded BEFORE metadata)
```

### Example 2: Disable AMI Pattern (Use Old Method)

```python
# Explicitly use old method
result = service.create_digital_object_from_ocr_data(
    ocr_data,
    use_ami_pattern=False  # Use old method
)

if result:
    print(f"  Method: {result['upload_method']}")
    # Output: Old Method (file uploaded AFTER metadata)
```

### Example 3: Bulk Push to Archipelago

The bulk push endpoints automatically use AMI pattern:

```python
# POST /api/archipelago/push-bulk-job
{
    "job_id": "bulk_123",
    "collection_title": "My Collection"
}

# Each document will use AMI pattern by default
# Real FIDs will be obtained for all files
```

## API Endpoints Affected

All these endpoints now use AMI pattern by default:

### 1. `/api/archipelago/push-bulk-job`
Pushes bulk OCR job results with AMI pattern

### 2. `/api/archipelago/push-project`
Pushes project images with AMI pattern

### 3. `/api/archipelago/push-bulk-ami`
AMI Sets workflow (already uses files-first pattern)

## Logging

The new implementation provides detailed logging:

```
=== Using AMI Pattern: Upload file BEFORE creating metadata ===
→ Uploading file: eng-typed/document.pdf
  Response status: 201
✓ File uploaded successfully (AMI pattern)
  FID: 456
  Field: documents
  Added FID to metadata['documents']: [456]
✓ Updated as:document with real FID: 456 (not hardcoded 49)

Successfully created digital object in Archipelago: abc-123-def
✓✓✓ SUCCESS: Real FID 456 used (NOT hardcoded 49)
```

Compare with old method (when AMI disabled):

```
=== Using OLD method: Upload file AFTER node creation ===
→ Attempting to upload file to Archipelago...
⚠ Archipelago file upload returned no result
ℹ No Drupal file ID available (all upload methods failed)
  Using hardcoded fallback dr:fid: 49
```

## Migration Guide

### For Existing Code

**No changes needed!** The AMI pattern is now the default.

If you have existing code calling `create_digital_object_from_ocr_data()`:

```python
# This code continues to work
result = service.create_digital_object_from_ocr_data(ocr_data)

# Now uses AMI pattern by default
# Real FIDs instead of hardcoded 49
```

### If You Want Old Behavior

Explicitly disable AMI pattern:

```python
result = service.create_digital_object_from_ocr_data(
    ocr_data,
    use_ami_pattern=False  # Use old method
)
```

## Verification

### Check if Real FID Was Used

```python
result = service.create_digital_object_from_ocr_data(ocr_data)

if result:
    fid = result.get('drupal_file_id')

    if fid and fid != 49:
        print(f"✓ Real FID obtained: {fid}")
    elif fid == 49:
        print(f"⚠ Fallback FID 49 used (upload may have failed)")
    else:
        print(f"ℹ No FID (file upload skipped)")
```

### Check Upload Method

```python
result = service.create_digital_object_from_ocr_data(ocr_data)

if result:
    method = result.get('upload_method')
    ami_used = result.get('ami_pattern_used')

    print(f"Upload method: {method}")
    print(f"AMI pattern: {'Enabled' if ami_used else 'Disabled'}")
```

## Benefits of AMI Pattern

1. **Real File IDs**: No more hardcoded FID 49
2. **Matches PHP Workflow**: Same pattern as your Drupal AMI code
3. **MIME Type Mapping**: Automatic field mapping (documents/images/videos)
4. **Atomic Operation**: Metadata contains file IDs from the start
5. **Better Error Handling**: Know immediately if file upload failed
6. **Cleaner Logs**: Clear indication of which method was used

## Comparison

| Aspect | Old Method | AMI Pattern (New Default) |
|--------|------------|--------------------------|
| Upload timing | After node creation | Before metadata creation |
| FID availability | After PATCH | Before node creation |
| Hardcoded FID 49 | Used as fallback | Never used |
| Field mapping | Manual | Automatic (by MIME type) |
| PHP compatibility | Different pattern | Matches PHP AMI code |
| Default | No longer default | ✓ Default |

## Troubleshooting

### Issue: Still seeing FID 49

**Possible causes**:
1. File doesn't exist at specified path
2. Network error during upload
3. Archipelago endpoint not responding
4. AMI pattern explicitly disabled

**Solution**: Check logs for upload errors

### Issue: Wrong field mapping

**Example**: PDF uploaded to 'images' instead of 'documents'

**Cause**: MIME type detection issue

**Solution**: Check MIME type mapping in `_map_mime_to_field()` at `archipelago_service.py:304`

### Issue: Want to use old method

**Solution**: Explicitly set `use_ami_pattern=False`

```python
result = service.create_digital_object_from_ocr_data(
    ocr_data,
    use_ami_pattern=False
)
```

## Testing

Test the AMI pattern integration:

```bash
# Run AMI pattern test
python3 test_ami_file_upload.py

# Or test via API
curl -X POST http://localhost:5000/api/archipelago/push-bulk-job \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "job_id": "bulk_123",
    "collection_title": "Test Collection"
  }'
```

Check the response for:
```json
{
  "upload_method": "AMI Pattern (file uploaded BEFORE metadata)",
  "drupal_file_id": 456,
  "ami_pattern_used": true
}
```

## See Also

- `AMI_FILE_UPLOAD_PATTERN.md` - Detailed AMI pattern documentation
- `test_ami_file_upload.py` - Test suite for AMI pattern
- `archipelago_service.py:198` - `upload_file_before_metadata()` implementation
- `archipelago_service.py:1558` - `create_digital_object_from_ocr_data()` with AMI pattern
- `archipelago_service.py:304` - `_map_mime_to_field()` MIME type mapping

## Summary

**The hardcoded FID 49 has been replaced with real file IDs from Archipelago using the AMI pattern from your PHP code.**

- ✓ AMI pattern enabled by default
- ✓ Files uploaded BEFORE metadata creation
- ✓ Real FIDs from Archipelago
- ✓ Automatic MIME type mapping
- ✓ Matches your PHP workflow
- ✓ No more hardcoded 49 (unless explicitly using old method)
