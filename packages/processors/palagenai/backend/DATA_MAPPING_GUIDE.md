# Data Mapping Guide: OCR Format to Archipelago Commons

This guide explains how to map data from your input OCR format to Archipelago Commons format before uploading.

## Overview

The system now includes a **DataMapper** service that automatically converts data from your OCR format (as in [input_ocr_data.json](input_ocr_data.json)) to the Archipelago template format (as in [archipelago-template.json](archipelago-template.json)).

## Key Components

### 1. DataMapper Service
Location: [app/services/data_mapper.py](app/services/data_mapper.py)

The `DataMapper` class provides methods to:
- Map individual OCR data items to Archipelago format
- Map bulk OCR data collections
- Create collection-level metadata

### 2. Updated ArchipelagoService
Location: [app/services/archipelago_service.py](app/services/archipelago_service.py)

New methods added:
- `create_digital_object_from_ocr_data()` - Upload single OCR data item
- `create_bulk_from_ocr_data()` - Upload multiple OCR data items as a collection

## Field Mapping

### Input Format (OCR Data)
```json
{
    "name": "document_name.jpg",
    "text": "OCR extracted text...",
    "@type": "DigitalDocument",
    "label": "Document Label",
    "description": "Document description",
    "keywords": ["keyword1", "keyword2"],
    "dateCreated": "2025-11-20T03:53:18.961216",
    "file_info": {
        "filename": "document.jpg",
        "file_path": "path/to/document.jpg"
    },
    "ocr_metadata": {
        "provider": "chrome_lens",
        "confidence": 0.85,
        "language": "en",
        "word_count": 180,
        "character_count": 1006
    },
    "source_info": {
        "collection": "collection-uuid",
        "folder_path": "./path/to/folder"
    }
}
```

### Output Format (Archipelago)
```json
{
    "label": "Document Label",
    "note": "OCR extracted text (first 5000 chars)...",
    "type": "DigitalDocument",
    "description": "Auto-generated or provided description",
    "language": ["English"],
    "date_created": "2025-11-20T03:53:18.961216",
    "ismemberof": [110],
    "documents": [49],
    "as:document": {
        "urn:uuid:...": {
            "url": "s3://files/document.jpg",
            "name": "document.jpg",
            "type": "Document",
            "dr:fid": 49,
            "dr:mimetype": "image/jpeg"
        }
    },
    "subjects_local": "keyword1, keyword2",
    "as:generator": { /* metadata about processing */ },
    /* ... all other Archipelago template fields ... */
}
```

## Field Mapping Details

| OCR Field | Archipelago Field | Transformation |
|-----------|-------------------|----------------|
| `name` | `label` | Direct mapping |
| `text` | `note` | Truncated to 5000 chars |
| `description` | `description` | Auto-generated if not provided |
| `@type` | `type` | Direct mapping |
| `dateCreated` | `date_created` | Direct mapping |
| `keywords` | `subjects_local` | Joined with commas |
| `ocr_metadata.language` | `language` | Code → Full name (en → English) |
| `file_info` | `as:document` | Structured file metadata |
| Collection ID | `ismemberof` | Array with collection ID |
| File ID | `documents` | Array with file ID |

### Language Code Mapping
- `en` → `English`
- `hi` → `Hindi`
- `es` → `Spanish`
- `fr` → `French`
- `de` → `German`
- And more...

## Usage Examples

### Example 1: Upload Single Document

```python
from app.services.archipelago_service import ArchipelagoService

# Your OCR data
ocr_data = {
    "name": "document.jpg",
    "text": "Extracted text here...",
    "label": "My Document",
    "description": "A scanned document",
    "keywords": ["history", "archive"],
    "dateCreated": "2025-11-20T10:00:00",
    "file_info": {
        "filename": "document.jpg",
        "file_path": "path/to/document.jpg"
    },
    "ocr_metadata": {
        "provider": "chrome_lens",
        "confidence": 0.92,
        "language": "en",
        "word_count": 500,
        "character_count": 3000
    }
}

# Upload to Archipelago
service = ArchipelagoService()
result = service.create_digital_object_from_ocr_data(
    ocr_data=ocr_data,
    collection_id=110,  # Optional: link to collection
    file_id=49  # Optional: file reference ID
)

if result:
    print(f"Document created: {result['url']}")
    print(f"Node ID: {result['node_id']}")
```

### Example 2: Bulk Upload Multiple Documents

```python
from app.services.archipelago_service import ArchipelagoService

# List of OCR data items
ocr_data_list = [
    {
        "name": "doc1.jpg",
        "text": "Text from first document...",
        "ocr_metadata": { ... }
    },
    {
        "name": "doc2.jpg",
        "text": "Text from second document...",
        "ocr_metadata": { ... }
    }
]

# Upload as a collection
service = ArchipelagoService()
result = service.create_bulk_from_ocr_data(
    ocr_data_list=ocr_data_list,
    collection_name="My Document Collection",
    collection_metadata={
        "description": "Collection of historical documents",
        "rights": "Public Domain"
    }
)

if result:
    print(f"Collection created: {result['collection_url']}")
    print(f"Documents created: {result['created_documents']}/{result['total_documents']}")
    print(f"Document IDs: {result['document_ids']}")
```

### Example 3: Direct Data Mapping (Without Upload)

```python
from app.services.data_mapper import DataMapper

# Map data without uploading
archipelago_data = DataMapper.map_ocr_to_archipelago(
    ocr_data=your_ocr_data,
    collection_id=110,
    file_id=49
)

# Now you have Archipelago-formatted data
print(archipelago_data['label'])
print(archipelago_data['language'])
print(archipelago_data['description'])
```

## Testing the Mapper

Run the test script to verify the mapping:

```bash
cd /mnt/sda1/mango1_home/gvpocr/backend
python3 test_mapper_standalone.py
```

This will:
1. Load sample data from [input_ocr_data.json](input_ocr_data.json)
2. Map it to Archipelago format
3. Save the result to `mapped_output.json`
4. Display a comparison report

## Metadata Preservation

The mapper preserves all important OCR metadata:
- ✓ OCR provider information
- ✓ Confidence scores
- ✓ Language detection
- ✓ Word and character counts
- ✓ Processing timestamps
- ✓ File information
- ✓ Source collection details

## Auto-Generated Descriptions

If no description is provided, the mapper generates one from OCR metadata:

**Example:**
```
"Processed using Chrome Lens OCR. Confidence: 85.0%. 180 words. 1006 characters."
```

## Collection-Level Metadata

When creating collections, the mapper generates statistics:

```python
collection_metadata = DataMapper.create_archipelago_collection_metadata(
    collection_name="My Collection",
    ocr_data_list=data_list,
    additional_metadata={
        "description": "Custom description",
        "publisher": "My Organization"
    }
)
```

Generates:
- Total item count
- Combined word count
- Combined character count
- Unique languages in collection
- Processing information

## Integration with Existing Code

The new methods are backward-compatible. You can still use:
- `create_digital_object()` - Original method (still works)
- `create_bulk_collection()` - Original method (still works)

New methods:
- `create_digital_object_from_ocr_data()` - With automatic mapping
- `create_bulk_from_ocr_data()` - With automatic mapping

## Error Handling

The mapper includes comprehensive error handling:
- Logs all mapping operations
- Continues bulk operations even if individual items fail
- Provides detailed error messages
- Preserves as much data as possible on partial failures

## Files

- [app/services/data_mapper.py](app/services/data_mapper.py) - Main mapper implementation
- [app/services/archipelago_service.py](app/services/archipelago_service.py) - Updated service with mapping
- [test_mapper_standalone.py](test_mapper_standalone.py) - Standalone test script
- [input_ocr_data.json](input_ocr_data.json) - Sample input format
- [archipelago-template.json](archipelago-template.json) - Target output format
- [mapped_output.json](mapped_output.json) - Example mapped output

## Configuration

The Archipelago service requires these environment variables:
- `ARCHIPELAGO_BASE_URL` - Your Archipelago instance URL
- `ARCHIPELAGO_USERNAME` - API username
- `ARCHIPELAGO_PASSWORD` - API password
- `ARCHIPELAGO_ENABLED` - Set to `true` to enable

## Next Steps

1. Test the mapping with your actual data
2. Review the [mapped_output.json](mapped_output.json) to verify correctness
3. Adjust field mappings if needed in [data_mapper.py](app/services/data_mapper.py)
4. Use the new methods in your application code
5. Monitor logs for any mapping issues

## Support

For issues or questions:
- Check the logs for detailed error messages
- Review the test output from `test_mapper_standalone.py`
- Verify your data format matches the expected structure
- Ensure all required fields are present in OCR data
