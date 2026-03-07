# AMI Sets Implementation Guide

## Overview

I've implemented Option 2: **Full AMI Sets Integration** for bulk uploading OCR results to Archipelago Commons. This provides proper Drupal file entity creation, automatic metadata extraction, and full Archipelago processing pipeline integration.

## What Was Implemented

### 1. New AMI Service (`backend/app/services/ami_service.py`)

A complete service for creating and managing AMI Sets programmatically:

**Key Methods:**

- `create_csv_from_ocr_data()` - Generates CSV metadata file from OCR results
- `create_zip_from_files()` - Packages source files into ZIP archive
- `upload_file_to_archipelago()` - Uploads files and gets Drupal file entity IDs
- `create_ami_set()` - Creates AMI Set entity with CSV and ZIP files
- `create_bulk_via_ami()` - Complete end-to-end workflow

### 2. New API Endpoint

**`POST /api/archipelago/push-bulk-ami`**

Pushes bulk OCR results to Archipelago using AMI Sets workflow.

**Request Body:**
```json
{
  "job_id": "bulk_job_12345",
  "collection_title": "My Collection Name",
  "collection_id": 123  // Optional: Use existing collection
}
```

**Response:**
```json
{
  "success": true,
  "ami_set_id": 5,
  "ami_set_name": "OCR Bulk Upload 2025-11-29_09-30-00",
  "csv_fid": 310,
  "zip_fid": 311,
  "message": "AMI Set created successfully. Process it at: http://esmero-web:80/amiset/5/process",
  "total_documents": 25
}
```

## How It Works

### Workflow Steps

1. **CSV Generation**
   - Reads OCR results from completed bulk job
   - Creates CSV with columns: `node_uuid`, `type`, `label`, `description`, `documents`, `images`, `language`, `ocr_text`, etc.
   - Maps file types automatically (PDFs → documents column, Images → images column)

2. **ZIP Creation**
   - Packages all source files from the OCR job
   - Uses original filenames (no directory structure)
   - References files by filename in CSV

3. **File Upload to Archipelago**
   - Uploads CSV file → Gets file entity ID (FID)
   - Uploads ZIP file → Gets file entity ID (FID)
   - Archipelago stores these as managed file entities

4. **AMI Set Creation**
   - Creates AMI Set entity via JSON:API
   - Configures mapping: CSV columns → Strawberry Field metadata
   - Sets plugin to 'spreadsheet' mode
   - Links uploaded CSV and ZIP file entities

5. **Manual Processing** (Required)
   - User navigates to: `http://esmero-web:80/amiset/{ami_set_id}/process`
   - Reviews configuration
   - Clicks "Process" to queue the batch
   - Archipelago processes files and creates digital objects with proper file entities

## CSV Format

The generated CSV includes these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `node_uuid` | Auto-generated UUID | `a1b2c3d4-...` |
| `type` | Content type | `DigitalDocument` |
| `label` | Title/label | `Document Title.pdf` |
| `description` | Description | `OCR processed: filename.pdf` |
| `documents` | PDF filename | `document.pdf` |
| `images` | Image filename | `image.jpg` |
| `ismemberof` | Collection ID | `123` |
| `language` | Language | `English` |
| `owner` | Owner | `Vipassana Research Institute` |
| `rights` | Rights | `All rights Owned by VRI` |
| `creator` | Creator | `VRI` |
| `ocr_text` | Full OCR text | First 5000 chars of OCR text |
| `ocr_provider` | OCR provider | `google_vision` |
| `ocr_confidence` | Confidence score | `0.95` |
| `ocr_language` | Detected language | `en` |
| `ocr_processing_date` | Processing date | `2025-11-29T09:30:00Z` |
| `file_path` | Original file path | `eng-typed/file.pdf` |

## Benefits Over Direct API Approach

### ✅ Proper Drupal File Entities
- Files get real Drupal file entity IDs (FIDs)
- No more fake `dr:fid` values
- Single `as:document` entry per file (no duplicates!)

### ✅ Full Archipelago Processing
- Automatic thumbnail generation
- PDF metadata extraction by Archipelago
- IIIF manifest creation
- Derivative file generation

### ✅ Better File Management
- Files stored in Archipelago's managed storage
- Proper file tracking and lifecycle management
- Integration with all Archipelago features

### ✅ Batch Processing
- Can handle large uploads efficiently
- Queue-based processing
- Progress monitoring through Archipelago UI

## Usage Example

### From Frontend/Postman:

```bash
curl -X POST http://localhost:5000/api/archipelago/push-bulk-ami \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "bulk_abc123",
    "collection_title": "Bhushanji Letters Collection"
  }'
```

### Response:
```json
{
  "success": true,
  "ami_set_id": 5,
  "ami_set_name": "OCR Bulk Upload 2025-11-29_09-30-00",
  "message": "AMI Set created successfully. Process it at: http://esmero-web:80/amiset/5/process",
  "total_documents": 25
}
```

### Next Steps (Manual):

1. Navigate to the processing URL in the message
2. Review the AMI Set configuration
3. Click "Process" to start the batch ingestion
4. Monitor progress in Archipelago admin interface
5. Once complete, view the created digital objects

## Comparison: Old vs New Workflow

### Old Direct API Workflow (FIXED but Limited)
```
OCR Results → MinIO Upload → Create Node with S3 URL → Done
```
- ✅ No duplicates (after fix)
- ❌ No Drupal file entities
- ❌ No thumbnails
- ❌ No Archipelago processing

### New AMI Sets Workflow
```
OCR Results → CSV + ZIP → Upload to Archipelago → Create AMI Set → Process → Digital Objects
```
- ✅ No duplicates
- ✅ Real Drupal file entities
- ✅ Full thumbnails and derivatives
- ✅ Complete Archipelago processing
- ✅ Better long-term maintainability

## File Locations

- **AMI Service**: `/mnt/sda1/mango1_home/gvpocr/backend/app/services/ami_service.py`
- **API Route**: `/mnt/sda1/mango1_home/gvpocr/backend/app/routes/archipelago.py` (line 332+)

## Testing

To test the new AMI Sets workflow:

1. Complete a bulk OCR job
2. Call the new endpoint:
   ```bash
   POST /api/archipelago/push-bulk-ami
   {
     "job_id": "your_bulk_job_id",
     "collection_title": "Test Collection"
   }
   ```
3. Check response for AMI Set ID
4. Navigate to processing URL
5. Process the AMI Set in Archipelago UI
6. Verify digital objects are created with proper file entities

## Troubleshooting

### CSV Upload Fails
- Check file permissions
- Verify GVPOCR_PATH environment variable
- Ensure source files exist at specified paths

### ZIP Upload Fails
- Check file sizes (default 512MB limit)
- Verify files can be read from GVPOCR_PATH

### AMI Set Creation Fails
- Check Archipelago credentials
- Verify JSON:API is enabled
- Check Archipelago logs for errors

### Processing Fails
- Review CSV format for errors
- Check file references match ZIP contents
- Verify metadata mappings in AMI configuration

## Future Enhancements

Possible improvements for the AMI Sets integration:

1. **Automatic Processing**: Trigger AMI Set processing programmatically via API
2. **Status Monitoring**: Poll AMI Set status to detect completion
3. **Error Handling**: Better error reporting from AMI processing
4. **Metadata Templates**: Support for custom Twig templates
5. **Collection Auto-Creation**: Create collection within AMI workflow
6. **Progress Notifications**: Webhook or callback when processing completes

## Conclusion

The AMI Sets integration provides a production-ready, maintainable solution for bulk uploads to Archipelago Commons. It follows Archipelago's recommended workflow and provides full integration with all platform features.

**Status**: ✅ Implemented and ready for testing
