# Archipelago Commons Integration

This document describes the integration between GVPOCR and Archipelago Commons for publishing OCR-processed documents as digital objects.

## Overview

Archipelago Commons (https://archipelago.nyc/) is an Open Source Digital Objects Repository / DAM Server Architecture based on the popular CMS Drupal. This integration allows you to push OCR-processed documents from GVPOCR directly into Archipelago as digital objects with rich metadata.

## Features

- ✅ Push single processed documents to Archipelago
- ✅ Push entire bulk processing jobs as collections
- ✅ Push project images as collections
- ✅ Automatic metadata mapping with OCR-specific fields
- ✅ Support for tags and custom metadata
- ✅ Strawberry Field (SBF) schema.org compliant metadata
- ✅ Connection testing and status checking

## Configuration

### Environment Variables

Add the following environment variables to your `.env` file or docker-compose configuration:

```bash
# Archipelago Commons Configuration
ARCHIPELAGO_BASE_URL=http://your-archipelago-server:8001
ARCHIPELAGO_USERNAME=your_username
ARCHIPELAGO_PASSWORD=your_password
ARCHIPELAGO_ENABLED=true
```

### Configuration Details

- **ARCHIPELAGO_BASE_URL**: The base URL of your Archipelago Commons instance
- **ARCHIPELAGO_USERNAME**: Username for Archipelago authentication
- **ARCHIPELAGO_PASSWORD**: Password for Archipelago authentication
- **ARCHIPELAGO_ENABLED**: Set to `true` to enable the integration, `false` to disable

## API Endpoints

### 1. Check Connection

Check if Archipelago Commons is configured and reachable.

```http
GET /api/archipelago/check-connection
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "enabled": true,
  "base_url": "http://localhost:8001",
  "message": "Connected successfully"
}
```

### 2. Push Single Document

Push a single processed image/document to Archipelago.

```http
POST /api/archipelago/push-document
Authorization: Bearer <token>
Content-Type: application/json

{
  "image_id": "mongodb_image_id",
  "title": "Document Title",
  "tags": ["ocr", "historical", "manuscript"],
  "custom_metadata": {
    "description": "Custom description",
    "additional_field": "value"
  }
}
```

**Response:**
```json
{
  "success": true,
  "archipelago_node_id": "123",
  "archipelago_url": "http://localhost:8001/do/123",
  "message": "Document successfully pushed to Archipelago Commons"
}
```

### 3. Push Bulk Job as Collection

Push all successful results from a bulk processing job as a collection.

```http
POST /api/archipelago/push-bulk-job
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": "bulk_job_uuid",
  "collection_title": "Historical Documents Collection",
  "collection_description": "OCR processed historical documents from 2025",
  "tags": ["ocr", "bulk", "historical"],
  "include_failed": false
}
```

**Response:**
```json
{
  "success": true,
  "collection_id": "456",
  "collection_url": "http://localhost:8001/do/456",
  "created_documents": 48,
  "total_documents": 50,
  "message": "Successfully created collection with 48 documents"
}
```

### 4. Push Project as Collection

Push all processed images from a project as a collection.

```http
POST /api/archipelago/push-project
Authorization: Bearer <token>
Content-Type: application/json

{
  "project_id": "mongodb_project_id",
  "collection_title": "Project Title",
  "collection_description": "Description of the collection",
  "tags": ["ocr", "project"]
}
```

## Metadata Mapping

### OCR Document Metadata (Strawberry Field Format)

Documents are stored in Archipelago using the Strawberry Field (SBF) format with schema.org vocabulary:

```json
{
  "@context": "http://schema.org",
  "@type": "DigitalDocument",
  "label": "Document Title",
  "name": "Document Title",
  "description": "OCR processed document description",
  "text": "Full OCR extracted text...",
  "dateCreated": "2025-01-19T12:00:00Z",
  "keywords": ["ocr", "tag1", "tag2"],
  "encodingFormat": "image/jpeg",
  "alternateName": "original_filename.jpg",
  "contentSize": "2048576",

  "ocr_metadata": {
    "provider": "chrome_lens",
    "confidence": 0.95,
    "language": "en",
    "processing_date": "2025-01-19T12:00:00Z",
    "character_count": 1234,
    "word_count": 567
  }
}
```

### Collection Metadata

Collections include summary information about the bulk processing:

```json
{
  "@context": "http://schema.org",
  "@type": "Collection",
  "label": "Collection Title",
  "name": "Collection Title",
  "description": "Collection description",
  "dateCreated": "2025-01-19T12:00:00Z",
  "numberOfItems": 50,

  "ocr_summary": {
    "total_files": 50,
    "successful": 48,
    "failed": 2,
    "statistics": {
      "total_characters": 123456,
      "average_confidence": 0.92,
      "average_words": 234,
      "languages": ["en", "es"]
    }
  }
}
```

## User Interface

### Accessing Archipelago Features

1. **Job History View**: Navigate to "Job History" tab in Bulk Processing
2. **Completed Jobs**: Only completed jobs with successful results show the Archipelago button
3. **Purple Upload Icon**: Click the purple upload icon next to completed jobs

### Push to Archipelago Workflow

1. Click the purple upload button on a completed job
2. A modal appears with a pre-filled form:
   - **Collection Title**: Edit or keep the auto-generated title
   - **Description**: Add a description for the collection
   - **Tags**: Comma-separated tags (pre-filled with job metadata)
   - **Job Information**: View summary of files to be uploaded
3. Click "Push to Archipelago" button
4. Wait for the upload to complete
5. Success message shows:
   - Collection ID
   - Number of documents created
   - Direct URL to the collection in Archipelago

### Visual Indicators

- **Purple Upload Button**: Appears only when Archipelago is enabled and connected
- **Connection Status**: Automatically checked on page load
- **Disabled State**: Button disabled if Archipelago is not configured

## Service Architecture

### ArchipelagoService (`backend/app/services/archipelago_service.py`)

The service handles all communication with Archipelago Commons:

**Key Methods:**

- `check_connection()`: Test connection to Archipelago
- `create_digital_object()`: Create a single digital object
- `create_bulk_collection()`: Create a collection with multiple documents
- `_login()`: Authenticate and get CSRF token
- `_upload_file()`: Upload file via JSON:API
- `_prepare_sbf_metadata()`: Convert OCR metadata to SBF format

### API Routes (`backend/app/routes/archipelago.py`)

Flask blueprint with endpoints for:
- Connection checking
- Single document push
- Bulk job push
- Project push

### Frontend Component

The `BulkJobHistory` component includes Archipelago integration:
- Connection status checking
- Push button for completed jobs
- Modal form for collection details
- Progress indicators during upload

## Troubleshooting

### Archipelago Button Not Visible

**Issue**: The purple upload button doesn't appear

**Solutions**:
1. Check that `ARCHIPELAGO_ENABLED=true` in environment variables
2. Verify `ARCHIPELAGO_BASE_URL` is correct
3. Check backend logs for connection errors
4. Test connection: `GET /api/archipelago/check-connection`

### Authentication Failures

**Issue**: "Failed to authenticate with Archipelago"

**Solutions**:
1. Verify `ARCHIPELAGO_USERNAME` and `ARCHIPELAGO_PASSWORD` are correct
2. Ensure the user has permissions to create digital objects in Archipelago
3. Check if Archipelago's authentication endpoint is accessible
4. Review Archipelago logs for authentication errors

### Upload Failures

**Issue**: Documents not uploading to Archipelago

**Solutions**:
1. Check file paths are accessible from backend
2. Verify file formats are supported by Archipelago
3. Check Archipelago disk space
4. Review backend logs for detailed error messages
5. Ensure JSON:API is enabled in Archipelago

### Partial Upload

**Issue**: Some documents uploaded but not all

**Check**:
- Backend logs show which documents failed
- File permissions on failed documents
- File format compatibility
- Archipelago storage limits

## Development

### Adding Custom Metadata Fields

Edit `archipelago_service.py` in the `_prepare_sbf_metadata` method:

```python
sbf_data['custom_field'] = metadata.get('custom_field', 'default_value')
```

### Extending Integration

To add new push sources:

1. Create a new route in `archipelago.py`
2. Fetch data from your source
3. Convert to the expected format
4. Call `service.create_digital_object()` or `service.create_bulk_collection()`

## Security Considerations

- Credentials are stored as environment variables
- Authentication uses basic auth over HTTPS (recommended)
- CSRF tokens are used for all write operations
- User permissions are enforced via token_required decorator
- File paths are validated before upload

## Performance

- Files are uploaded sequentially to avoid overwhelming Archipelago
- Failed uploads are logged but don't stop the batch
- Progress is tracked per-document
- Large batches (>100 files) may take several minutes

## Additional Resources

- Archipelago Commons Documentation: https://archipelago.nyc/
- Archipelago GitHub: https://github.com/esmero/archipelago-deployment
- Strawberry Field Documentation: https://github.com/esmero/strawberryfield
- Schema.org Vocabulary: https://schema.org/

## Support

For issues related to:
- **GVPOCR Integration**: Check backend logs and this documentation
- **Archipelago Setup**: Refer to Archipelago Commons documentation
- **API Errors**: Check both GVPOCR and Archipelago logs

## Future Enhancements

Potential improvements for future versions:

- [ ] Batch upload optimization with parallel requests
- [ ] Support for updating existing digital objects
- [ ] Automatic synchronization of updates
- [ ] Support for Archipelago webforms
- [ ] Advanced metadata mapping UI
- [ ] Preview of metadata before upload
- [ ] Bulk edit of collection metadata
- [ ] Download from Archipelago back to GVPOCR
