# Archipelago AMI Set Upload Endpoints

This guide documents the new AMI Set endpoints for uploading OCR data to Archipelago Commons.

## Overview

Three new endpoints have been added to the `/api/archipelago` route:

1. **POST `/api/archipelago/amiset/add`** - Create and upload AMI Set from OCR data
2. **GET `/api/archipelago/amiset/status/<ami_set_id>`** - Get AMI Set status
3. **POST `/api/archipelago/amiset/process/<ami_set_id>`** - Trigger AMI Set processing

## Endpoint Details

### 1. POST `/api/archipelago/amiset/add`

Create and upload OCR data to Archipelago as an AMI Set without requiring a pre-existing bulk job.

#### URL
```
POST http://127.0.0.1:8000/api/archipelago/amiset/add
```

#### Authentication
- Requires valid JWT token in `Authorization` header
- Format: `Authorization: Bearer <token>`

#### Request Body

```json
{
  "ocr_data": [
    {
      "name": "document_identifier",
      "label": "Display Title",
      "text": "Full OCR extracted text content...",
      "description": "Optional description of the document",
      "file_info": {
        "filename": "document.pdf",
        "file_path": "/absolute/path/to/document.pdf"
      },
      "ocr_metadata": {
        "provider": "tesseract",
        "confidence": 0.95,
        "language": "en",
        "processing_date": "2025-12-08T06:20:19.158Z"
      }
    }
  ],
  "collection_title": "Optional Collection Name",
  "collection_id": null
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ocr_data` | Array | Yes | Array of OCR data items (min 1 item) |
| `collection_title` | String | No | Name for the collection (if creating new) |
| `collection_id` | Number | No | Existing Archipelago collection node ID |

#### OCR Data Item Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Unique identifier for document |
| `label` | String | Yes | Display title for the document |
| `text` | String | Yes | Full OCR extracted text |
| `description` | String | No | Document description |
| `file_info` | Object | Yes | File metadata |
| `file_info.filename` | String | Yes | Original filename |
| `file_info.file_path` | String | Yes | File path (absolute or relative) |
| `ocr_metadata` | Object | Yes | OCR processing metadata |
| `ocr_metadata.provider` | String | Yes | OCR provider (e.g., "tesseract") |
| `ocr_metadata.confidence` | Number | No | OCR confidence score (0-1) |
| `ocr_metadata.language` | String | No | Detected language code |
| `ocr_metadata.processing_date` | String | No | ISO 8601 timestamp |

#### Response (Success)

```json
{
  "success": true,
  "ami_set_id": "123",
  "ami_set_name": "Collection Name",
  "csv_fid": "456",
  "zip_fid": "789",
  "message": "AMI Set created successfully. Process it at: http://archipelago.example.com/amiset/123/process",
  "total_documents": 5
}
```

#### Response (Error - Missing ocr_data)

```json
{
  "error": "ocr_data array is required"
}
```

**Status Code: 400**

#### Response (Error - Archipelago not enabled)

```json
{
  "error": "Archipelago integration is not enabled",
  "enabled": false
}
```

**Status Code: 400**

#### Response (Error - Empty ocr_data)

```json
{
  "error": "ocr_data array cannot be empty"
}
```

**Status Code: 400**

#### Example cURL Request

```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_data": [
      {
        "name": "doc001",
        "label": "Important Document",
        "text": "Lorem ipsum dolor sit amet...",
        "description": "An important historical document",
        "file_info": {
          "filename": "document.pdf",
          "file_path": "/path/to/document.pdf"
        },
        "ocr_metadata": {
          "provider": "tesseract",
          "confidence": 0.95,
          "language": "en",
          "processing_date": "2025-12-08T06:20:19.158Z"
        }
      }
    ],
    "collection_title": "Historical Documents",
    "collection_id": null
  }'
```

#### What Happens After Submission

When you POST to `/api/archipelago/amiset/add`, the system:

1. **Validates** all source files exist
2. **Creates** a dedicated AMI set directory
3. **Copies** source files to staging area
4. **Generates** OCR text files (`.txt`)
5. **Generates** metadata JSON files (`.json`)
6. **Generates** thumbnail images (`.jpg`)
7. **Creates** CSV file with metadata (AMI format)
8. **Creates** ZIP archive with all files
9. **Uploads** CSV and ZIP to Archipelago
10. **Creates** AMI Set entity in Archipelago

The response includes the AMI Set ID, which can be used to:
- Check status via `/api/archipelago/amiset/status/<ami_set_id>`
- Process the set via `/api/archipelago/amiset/process/<ami_set_id>`

---

### 2. GET `/api/archipelago/amiset/status/<ami_set_id>`

Get the current status of an AMI Set in Archipelago.

#### URL
```
GET http://127.0.0.1:8000/api/archipelago/amiset/status/123
```

#### Authentication
- Requires valid JWT token in `Authorization` header

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ami_set_id` | String/Number | Yes | The Archipelago AMI Set ID |

#### Response (Success)

```json
{
  "success": true,
  "ami_set_id": "123",
  "name": "Collection Name",
  "status": "processing",
  "created": "2025-12-08T06:20:19Z",
  "updated": "2025-12-08T06:25:30Z",
  "messages": [
    "Ingestion started",
    "Processing documents..."
  ],
  "url": "http://archipelago.example.com/amiset/123"
}
```

#### Response (Error - Not Found)

```json
{
  "error": "AMI Set not found"
}
```

**Status Code: 404**

#### Status Values

- `pending` - Waiting to be processed
- `processing` - Currently being processed
- `completed` - Processing completed successfully
- `failed` - Processing failed
- `unknown` - Status cannot be determined

#### Example cURL Request

```bash
curl -X GET http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

#### Polling for Status

For automated workflows, you can poll this endpoint every 5-10 seconds:

```bash
#!/bin/bash
AMI_SET_ID=$1
TOKEN=$2
MAX_ATTEMPTS=60

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  response=$(curl -s -X GET \
    http://127.0.0.1:8000/api/archipelago/amiset/status/$AMI_SET_ID \
    -H "Authorization: Bearer $TOKEN")
  
  status=$(echo $response | jq -r '.status')
  
  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    echo "Final status: $status"
    echo $response | jq .
    break
  fi
  
  echo "Attempt $i: $status"
  sleep 10
done
```

---

### 3. POST `/api/archipelago/amiset/process/<ami_set_id>`

Trigger the processing/ingestion of an AMI Set in Archipelago. This initiates the workflow that converts the CSV and ZIP files into digital objects.

#### URL
```
POST http://127.0.0.1:8000/api/archipelago/amiset/process/123
```

#### Authentication
- Requires valid JWT token in `Authorization` header

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ami_set_id` | String/Number | Yes | The Archipelago AMI Set ID |

#### Request Body

Empty or minimal:
```json
{}
```

#### Response (Success)

```json
{
  "success": true,
  "message": "AMI Set processing initiated",
  "ami_set_id": "123",
  "ami_set_url": "http://archipelago.example.com/amiset/123"
}
```

#### Response (Error - Not Found)

```json
{
  "error": "AMI Set not found"
}
```

**Status Code: 404**

#### Response (Error - Processing Failed)

```json
{
  "error": "Failed to process AMI Set",
  "status_code": 500,
  "details": "Error message from Archipelago"
}
```

**Status Code: 500**

#### Example cURL Request

```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/process/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Processing Workflow

After calling this endpoint, Archipelago will:

1. **Validate** the CSV file structure
2. **Extract** files from the ZIP archive
3. **Create** digital object nodes for each row in CSV
4. **Upload** files to file field (field_file_drop)
5. **Extract** metadata from CSV columns
6. **Populate** Strawberry Field JSON metadata
7. **Assign** file IDs (fid) to documents array
8. **Link** to collection (if specified)
9. **Index** for search

The processing is asynchronous. You can check progress using the status endpoint.

---

## Complete Workflow Example

### Step 1: Create and Upload AMI Set

```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "ocr_data": [
    {
      "name": "doc_001",
      "label": "Historical Document 1",
      "text": "Full OCR text here...",
      "file_info": {
        "filename": "document1.pdf",
        "file_path": "/path/to/document1.pdf"
      },
      "ocr_metadata": {
        "provider": "tesseract",
        "confidence": 0.95,
        "language": "en",
        "processing_date": "2025-12-08T06:20:19.158Z"
      }
    }
  ],
  "collection_title": "Historical Documents Collection"
}
EOF
```

**Response contains:**
- `ami_set_id`: "123"
- `csv_fid`: "456"
- `zip_fid`: "789"

### Step 2: Check Initial Status

```bash
curl -X GET http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected status: `pending`

### Step 3: Trigger Processing

```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/process/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Step 4: Poll for Completion

```bash
# Check status every 5 seconds
for i in {1..20}; do
  curl -s -X GET http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
    -H "Authorization: Bearer YOUR_TOKEN" | jq .
  sleep 5
done
```

### Step 5: Access Results

Once `status` is `completed`, visit the Archipelago URL:
```
http://archipelago.example.com/amiset/123
```

---

## Integration with Frontend

### React Example

```javascript
import axios from 'axios';

class ArchipelagoAMIClient {
  constructor(token) {
    this.token = token;
    this.api = axios.create({
      baseURL: '/api/archipelago',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }

  async createAMISet(ocrDataList, collectionTitle = null) {
    try {
      const response = await this.api.post('/amiset/add', {
        ocr_data: ocrDataList,
        collection_title: collectionTitle,
        collection_id: null
      });
      return response.data;
    } catch (error) {
      console.error('Failed to create AMI Set:', error);
      throw error;
    }
  }

  async getStatus(amiSetId) {
    try {
      const response = await this.api.get(`/amiset/status/${amiSetId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get status:', error);
      throw error;
    }
  }

  async processAMISet(amiSetId) {
    try {
      const response = await this.api.post(`/amiset/process/${amiSetId}`, {});
      return response.data;
    } catch (error) {
      console.error('Failed to process AMI Set:', error);
      throw error;
    }
  }

  async waitForCompletion(amiSetId, maxWaitMs = 300000) {
    const startTime = Date.now();
    const pollInterval = 5000; // 5 seconds

    while (Date.now() - startTime < maxWaitMs) {
      const status = await this.getStatus(amiSetId);
      
      if (status.status === 'completed') {
        return { success: true, status };
      } else if (status.status === 'failed') {
        return { success: false, status };
      }
      
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
    
    return { success: false, error: 'Timeout waiting for completion' };
  }
}

// Usage
const client = new ArchipelagoAMIClient(authToken);

// Create AMI Set
const result = await client.createAMISet(ocrDataArray, 'My Collection');
console.log('AMI Set ID:', result.ami_set_id);

// Process it
await client.processAMISet(result.ami_set_id);

// Wait for completion
const completion = await client.waitForCompletion(result.ami_set_id);
console.log('Processing result:', completion);
```

---

## Error Handling

### Common Errors

#### 400: Missing ocr_data
```json
{
  "error": "ocr_data array is required"
}
```
**Solution:** Ensure `ocr_data` key is present in request body.

#### 400: Empty ocr_data
```json
{
  "error": "ocr_data array cannot be empty"
}
```
**Solution:** Add at least one document to the `ocr_data` array.

#### 400: Invalid data type
```json
{
  "error": "ocr_data must be an array"
}
```
**Solution:** Ensure `ocr_data` is an array `[ ... ]`, not an object.

#### 400: Archipelago not enabled
```json
{
  "error": "Archipelago integration is not enabled",
  "enabled": false
}
```
**Solution:** Set `ARCHIPELAGO_ENABLED=true` in environment and configure credentials.

#### 401: Not authenticated
```json
{
  "error": "Unauthorized"
}
```
**Solution:** Include valid JWT token in `Authorization: Bearer <token>` header.

#### 404: AMI Set not found
```json
{
  "error": "AMI Set not found"
}
```
**Solution:** Verify the `ami_set_id` is correct and exists in Archipelago.

#### 500: Internal server error
Check logs for details:
```bash
docker logs gvpocr-backend
```

---

## Configuration

### Environment Variables

```bash
# Enable Archipelago integration
ARCHIPELAGO_ENABLED=true

# Archipelago Commons URL
ARCHIPELAGO_BASE_URL=http://archipelago.example.com

# Archipelago Drupal credentials
ARCHIPELAGO_USERNAME=admin
ARCHIPELAGO_PASSWORD=password

# Upload folder for AMI Sets (optional, defaults to /app/uploads)
UPLOAD_FOLDER=/app/uploads

# GVPOCR data path (for resolving file paths)
GVPOCR_PATH=/path/to/gvpocr/data
```

### Docker Setup

```bash
# In docker-compose.yml
environment:
  - ARCHIPELAGO_ENABLED=true
  - ARCHIPELAGO_BASE_URL=http://archipelago:8000
  - ARCHIPELAGO_USERNAME=admin
  - ARCHIPELAGO_PASSWORD=secure_password
  - UPLOAD_FOLDER=/app/uploads
```

---

## File Structure Created During Upload

When you POST to `/api/archipelago/amiset/add`, the following directory structure is created:

```
/app/uploads/ami_sets/
└── {job_id}/
    ├── ami_set.csv           # Metadata CSV (Archipelago format)
    ├── ami_set.zip           # Flat ZIP with all files
    ├── source_files/         # Original source documents
    │   ├── document1.pdf
    │   ├── document2.pdf
    │   └── ...
    ├── ocr_text/             # Full OCR text extractions
    │   ├── document1_ocr.txt
    │   ├── document2_ocr.txt
    │   └── ...
    ├── ocr_metadata/         # OCR processing metadata (JSON)
    │   ├── document1_metadata.json
    │   ├── document2_metadata.json
    │   └── ...
    └── thumbnails/           # Generated preview images
        ├── document1_thumb.jpg
        ├── document2_thumb.jpg
        └── ...
```

These files are retained for debugging and manual inspection.

---

## Python Client Implementation

See `test_amiset_endpoints.py` for a complete Python client implementation with examples.

### Usage

```bash
# Create AMI Set with sample data
python test_amiset_endpoints.py --token YOUR_TOKEN --action add

# Check status
python test_amiset_endpoints.py --token YOUR_TOKEN --action status --ami-set-id 123

# Process AMI Set
python test_amiset_endpoints.py --token YOUR_TOKEN --action process --ami-set-id 123

# Full workflow (add, status, process)
python test_amiset_endpoints.py --token YOUR_TOKEN --action full

# With custom data file
python test_amiset_endpoints.py --token YOUR_TOKEN --data-file ocr_data.json
```

---

## Related Endpoints

### Existing Archipelago Endpoints

- `POST /api/archipelago/push-document` - Push single document
- `POST /api/archipelago/push-bulk-job` - Push completed bulk job
- `POST /api/archipelago/push-project` - Push entire project
- `POST /api/archipelago/push-bulk-ami` - Push bulk job via AMI (uses `job_id`)
- `GET /api/archipelago/check-connection` - Test Archipelago connectivity

### New Endpoints (This Guide)

- `POST /api/archipelago/amiset/add` - Create AMI Set from OCR data
- `GET /api/archipelago/amiset/status/{ami_set_id}` - Check AMI Set status
- `POST /api/archipelago/amiset/process/{ami_set_id}` - Process AMI Set

---

## Support

For issues or questions:

1. Check the logs: `docker logs gvpocr-backend`
2. Verify Archipelago is accessible: `curl http://archipelago.example.com`
3. Check environment variables are set correctly
4. Review the test script: `test_amiset_endpoints.py`

---

## Version

- API Version: 1.0
- Created: 2025-12-08
- Last Updated: 2025-12-08
