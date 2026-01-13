# Troubleshooting Archipelago Data Mapping and Upload

## Common Issues and Solutions

### 500 Service Unavailable Error

**Symptom:** When uploading to Archipelago Commons, you receive a "500 Service unavailable" error.

**Common Causes:**

#### 1. S3 Storage Not Configured

The most common cause is that the `as:document` field contains S3 file references, but S3 storage is not configured in your Archipelago instance.

**Solution:**
By default, the data mapper now **excludes** file references to avoid this issue. Files should be uploaded separately using Archipelago's file upload API.

```python
# This will NOT include S3 file references (recommended)
archipelago_data = DataMapper.map_ocr_to_archipelago(
    ocr_data=your_data,
    collection_id=110,
    file_id=49,
    include_file_reference=False  # Default
)

# Only set to True if you have S3 configured
archipelago_data = DataMapper.map_ocr_to_archipelago(
    ocr_data=your_data,
    collection_id=110,
    file_id=49,
    include_file_reference=True  # Only if S3 is configured!
)
```

#### 2. Invalid Collection Reference

The `ismemberof` field references a collection that doesn't exist.

**Solution:**
Either create the collection first, or upload without a collection reference:

```python
# Upload without collection
result = service.create_digital_object_from_ocr_data(
    ocr_data=your_data,
    collection_id=None,  # No collection reference
    file_id=None
)
```

#### 3. Empty or Invalid Field Values

Some Archipelago instances may reject documents with certain empty fields.

**Solution:**
Ensure your OCR data has meaningful values for key fields:

```python
ocr_data = {
    "name": "document.jpg",  # Should not be empty
    "text": "Your OCR text here",  # Should have content
    "label": "Document Title",  # Should be descriptive
    "description": "Document description",  # Should explain the document
    # ... other fields
}
```

### Debugging Steps

#### Step 1: Test the Mapping Locally

Run the test script to ensure mapping works:

```bash
cd /mnt/sda1/mango1_home/gvpocr/backend
python3 test_mapper_standalone.py
```

This creates `mapped_output.json` which you can inspect.

#### Step 2: Check Archipelago Logs

Check the Archipelago server logs for more detailed error messages:

```bash
# If using Docker
docker-compose logs archipelago

# Or check Drupal logs in the admin interface
# Navigate to: Reports > Recent log messages
```

#### Step 3: Test Connection

Verify Archipelago is accessible:

```python
from app.services.archipelago_service import ArchipelagoService

service = ArchipelagoService()
if service.check_connection():
    print("✓ Connection successful")
else:
    print("✗ Connection failed")
```

#### Step 4: Simplify the Data

Try uploading with minimal data to isolate the issue:

```python
minimal_ocr_data = {
    "name": "test.jpg",
    "text": "Test document",
    "label": "Test Document",
    "@context": "http://schema.org",
    "@type": "DigitalDocument"
}

result = service.create_digital_object_from_ocr_data(
    ocr_data=minimal_ocr_data,
    collection_id=None,
    file_id=None
)
```

### Recommended Upload Workflow

To avoid the 500 error, follow this workflow:

#### Option 1: Metadata Only (Recommended)

1. Upload document metadata without file references
2. The OCR text will be stored in the `note` field and is fully searchable
3. File can be uploaded separately later if needed

```python
service = ArchipelagoService()

# Upload metadata only (no S3 file reference)
result = service.create_digital_object_from_ocr_data(
    ocr_data=your_ocr_data,
    collection_id=None,  # Or valid collection ID
    file_id=None  # No file reference
)

if result:
    print(f"Document created: {result['url']}")
    print(f"Node UUID: {result['node_uuid']}")
```

#### Option 2: With S3 File Reference (If S3 is Configured)

Only use this if your Archipelago instance has S3 storage properly configured:

```python
service = ArchipelagoService()

# Map with file reference
archipelago_data = DataMapper.map_ocr_to_archipelago(
    ocr_data=your_ocr_data,
    collection_id=110,
    file_id=49,
    include_file_reference=True  # S3 must be configured!
)

# Upload using the mapped data
# ... (use existing upload methods)
```

#### Option 3: Upload File Separately

1. Create the digital object metadata first
2. Upload the file to the created node using file upload API

```python
# Step 1: Create node with metadata
result = service.create_digital_object_from_ocr_data(
    ocr_data=your_ocr_data,
    collection_id=None,
    file_id=None
)

if result:
    node_uuid = result['node_uuid']

    # Step 2: Upload file separately (if you have the file)
    csrf_token = service._login()
    file_result = service._upload_file_to_node(
        file_path="path/to/file.jpg",
        node_uuid=node_uuid,
        csrf_token=csrf_token
    )
```

### Configuration Checklist

Before uploading to Archipelago, verify:

- [ ] `ARCHIPELAGO_BASE_URL` is set correctly
- [ ] `ARCHIPELAGO_USERNAME` has proper permissions
- [ ] `ARCHIPELAGO_PASSWORD` is correct
- [ ] `ARCHIPELAGO_ENABLED` is set to `true`
- [ ] Archipelago instance is running and accessible
- [ ] S3 storage is configured (if using file references)
- [ ] Collection exists (if using collection_id)

### Field Validation

Ensure these fields have appropriate values:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Filename or document name |
| `text` | string | No | OCR extracted text |
| `label` | string | Yes | Document title/label |
| `@type` | string | Yes | Usually "DigitalDocument" |
| `description` | string | Recommended | Auto-generated if not provided |
| `dateCreated` | ISO date | Recommended | ISO 8601 format |

### Error Messages and Solutions

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `500 Service unavailable` | S3 not configured | Set `include_file_reference=False` |
| `401 Unauthorized` | Invalid credentials | Check ARCHIPELAGO_USERNAME/PASSWORD |
| `404 Not Found` | Invalid endpoint | Check ARCHIPELAGO_BASE_URL |
| `422 Unprocessable Entity` | Invalid data format | Validate OCR data structure |
| `403 Forbidden` | Insufficient permissions | Check user permissions in Archipelago |

### Getting Help

If you continue to experience issues:

1. Check the application logs:
   ```bash
   docker-compose logs backend
   ```

2. Review the mapped data:
   ```bash
   cat /mnt/sda1/mango1_home/gvpocr/backend/mapped_output.json
   ```

3. Test with the standalone script:
   ```bash
   python3 test_mapper_standalone.py
   ```

4. Check Archipelago documentation:
   - [Archipelago Deployment](https://archipelago.nyc/)
   - [Strawberry Field Format](https://github.com/esmero/strawberryfield)

### Additional Resources

- [DATA_MAPPING_GUIDE.md](DATA_MAPPING_GUIDE.md) - Complete mapping guide
- [archipelago-template.json](archipelago-template.json) - Target format reference
- [input_ocr_data.json](input_ocr_data.json) - Input format reference
- [app/services/data_mapper.py](app/services/data_mapper.py) - Mapper implementation
- [app/services/archipelago_service.py](app/services/archipelago_service.py) - Service implementation
