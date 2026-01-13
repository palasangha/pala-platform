# Archipelago AMI Set Endpoints - Complete Guide

## 📋 Overview

This project adds three new endpoints to upload OCR data to Archipelago Commons using AMI Sets workflow. No pre-existing bulk jobs required.

**Location:** `http://127.0.0.1:8000/api/archipelago/`

## 🚀 Quick Links

1. **[Quick Start Guide](AMISET_QUICK_START.md)** - Get started in 5 minutes
2. **[Complete API Guide](AMISET_ENDPOINT_GUIDE.md)** - Full API reference
3. **[Technical Summary](AMISET_BUILD_SUMMARY.md)** - Architecture & integration
4. **[Change Log](CHANGELOG_AMISET.md)** - What was added/changed
5. **[Test Client](test_amiset_endpoints.py)** - Python client for testing

## 📚 The Three Endpoints

### 1️⃣ Create AMI Set
```
POST /api/archipelago/amiset/add
```
Upload OCR data and create an AMI Set in Archipelago.

**Request:**
```json
{
  "ocr_data": [
    {
      "name": "doc1",
      "label": "My Document",
      "text": "Full OCR text...",
      "file_info": {
        "filename": "document.pdf",
        "file_path": "/path/to/document.pdf"
      },
      "ocr_metadata": {
        "provider": "tesseract",
        "confidence": 0.95,
        "language": "en"
      }
    }
  ],
  "collection_title": "Optional Collection"
}
```

**Response:**
```json
{
  "success": true,
  "ami_set_id": "123",
  "csv_fid": "456",
  "zip_fid": "789"
}
```

### 2️⃣ Check Status
```
GET /api/archipelago/amiset/status/{ami_set_id}
```
Check the processing status of an AMI Set.

**Response:**
```json
{
  "success": true,
  "status": "processing",
  "created": "2025-12-08T06:20:19Z"
}
```

### 3️⃣ Process AMI Set
```
POST /api/archipelago/amiset/process/{ami_set_id}
```
Trigger the ingestion workflow in Archipelago.

**Response:**
```json
{
  "success": true,
  "message": "AMI Set processing initiated",
  "ami_set_url": "http://archipelago.example.com/amiset/123"
}
```

## ⚡ Quick Start (30 seconds)

### Step 1: Create AMI Set
```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_data": [{
      "name": "doc1",
      "label": "Document",
      "text": "OCR text here",
      "file_info": {
        "filename": "file.pdf",
        "file_path": "/path/file.pdf"
      },
      "ocr_metadata": {"provider": "tesseract"}
    }],
    "collection_title": "My Collection"
  }'
```

### Step 2: Check Status
```bash
curl http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 3: Process
```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/process/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{}'
```

## 🐍 Using Python Client

```bash
# Install (if needed)
pip install requests

# Run test script
python test_amiset_endpoints.py --token YOUR_TOKEN --action full

# Or use as library
from test_amiset_endpoints import ArcipelagoAMIClient

client = ArcipelagoAMIClient(auth_token='TOKEN')
result = client.add_amiset(ocr_data_list=[...])
print(result['ami_set_id'])
```

## 📖 Documentation Files

### AMISET_QUICK_START.md
- 3-step setup guide
- cURL examples
- Troubleshooting
- Tips and tricks

### AMISET_ENDPOINT_GUIDE.md
- Complete API reference
- Request/response schemas
- Error codes and handling
- Integration examples (React, Python, cURL)
- Configuration guide
- Full workflow examples

### AMISET_BUILD_SUMMARY.md
- Technical architecture
- File structure details
- Integration points
- Testing instructions
- Feature list

### CHANGELOG_AMISET.md
- What was added
- File changes
- Configuration requirements
- Migration info

## 🔧 Setup

### Requirements
```bash
ARCHIPELAGO_ENABLED=true
ARCHIPELAGO_BASE_URL=http://archipelago.example.com
ARCHIPELAGO_USERNAME=admin
ARCHIPELAGO_PASSWORD=password
```

### Docker
```bash
docker-compose up backend
# API available at http://127.0.0.1:8000/api/archipelago
```

## ✅ What Happens

When you POST to `/amiset/add`, the system:

1. **Validates** all source files exist
2. **Generates** CSV metadata file (Archipelago format)
3. **Creates** ZIP archive with all files
4. **Copies** source documents
5. **Extracts** OCR text to separate files
6. **Creates** metadata JSON for each document
7. **Generates** thumbnail images
8. **Uploads** CSV and ZIP to Archipelago
9. **Creates** AMI Set entity
10. **Returns** AMI Set ID for processing

Then use `/amiset/status/{id}` to monitor progress and `/amiset/process/{id}` to trigger ingestion.

## 🎯 Key Features

✅ **Direct Upload** - No bulk job needed
✅ **Batch Processing** - Handle multiple documents
✅ **Auto Metadata** - CSV generation automatic
✅ **Status Tracking** - Monitor progress
✅ **Error Handling** - Comprehensive validation
✅ **Token Auth** - JWT authentication
✅ **File Management** - Organized structure
✅ **Async Processing** - Non-blocking workflow

## 📁 Files Created

```
project-root/
├── AMISET_README.md                    (this file)
├── AMISET_QUICK_START.md               (quick guide)
├── AMISET_ENDPOINT_GUIDE.md            (complete API docs)
├── AMISET_BUILD_SUMMARY.md             (technical info)
├── CHANGELOG_AMISET.md                 (changes)
├── test_amiset_endpoints.py            (test client)
└── backend/app/routes/archipelago.py   (modified - new endpoints)
```

## 🐛 Troubleshooting

### 401 Unauthorized
- Check token: `Authorization: Bearer TOKEN`
- Verify token is valid

### 400 Missing ocr_data
- Ensure `ocr_data` key exists
- Ensure it's an array: `[...]`
- Array must not be empty

### File not found
- Use absolute paths: `/path/to/file.pdf`
- Or relative to GVPOCR_PATH
- Check file permissions: `ls -la /path/to/file.pdf`

### Archipelago connection failed
- Check Archipelago is running
- Check URL: `curl http://archipelago.example.com`
- Verify credentials

See **[AMISET_QUICK_START.md](AMISET_QUICK_START.md)** for more troubleshooting tips.

## 💻 Example: Node.js/JavaScript

```javascript
const axios = require('axios');

async function uploadToArchipelago(ocrData) {
  const response = await axios.post(
    'http://127.0.0.1:8000/api/archipelago/amiset/add',
    {
      ocr_data: ocrData,
      collection_title: 'My Collection'
    },
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return response.data;
}

// Usage
const result = await uploadToArchipelago([
  {
    name: 'doc1',
    label: 'Document',
    text: 'OCR text...',
    file_info: {
      filename: 'file.pdf',
      file_path: '/path/file.pdf'
    },
    ocr_metadata: {
      provider: 'tesseract'
    }
  }
]);

console.log('AMI Set ID:', result.ami_set_id);
```

## 📊 Workflow Diagram

```
┌─────────────────────────────────────────────────┐
│  POST /amiset/add                               │
│  (Submit OCR data + files)                      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Validation     │
        │ File Staging   │
        │ CSV Generation │
        │ ZIP Creation   │
        │ Upload to      │
        │ Archipelago    │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Return AMI Set ID  │
        └────────┬───────────┘
                 │
        ┌────────▼──────────┐
        │ Poll Status       │  GET /amiset/status/{id}
        │ (Check Progress)  │
        └────────┬──────────┘
                 │
        ┌────────▼──────────────┐
        │ POST /amiset/process  │
        │ (Start Ingestion)     │
        └────────┬──────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Archipelago         │
        │ Processes & Creates │
        │ Digital Objects     │
        └────────────────────┘
```

## 🔐 Security

✅ **Authentication**: JWT token required
✅ **Validation**: Input validation on all endpoints
✅ **Authorization**: Token scope checking
✅ **Error Handling**: No sensitive info in errors
✅ **File Paths**: Validated and resolved safely

## 📞 Support

1. **Check Documentation**
   - Quick Start: `AMISET_QUICK_START.md`
   - Full Guide: `AMISET_ENDPOINT_GUIDE.md`
   - Technical: `AMISET_BUILD_SUMMARY.md`

2. **Review Logs**
   ```bash
   docker logs gvpocr-backend | tail -50
   ```

3. **Test Connectivity**
   ```bash
   curl http://archipelago.example.com/jsonapi
   ```

4. **Run Test Script**
   ```bash
   python test_amiset_endpoints.py --token TOKEN --action full
   ```

## 📝 Version

- **Version**: 1.0
- **Date**: 2025-12-08
- **Status**: Ready for Production ✅

## 🎓 Learning Resources

1. Start with [AMISET_QUICK_START.md](AMISET_QUICK_START.md) for immediate usage
2. Read [AMISET_ENDPOINT_GUIDE.md](AMISET_ENDPOINT_GUIDE.md) for complete details
3. Check [test_amiset_endpoints.py](test_amiset_endpoints.py) for code examples
4. Review [CHANGELOG_AMISET.md](CHANGELOG_AMISET.md) for technical details

## ✨ Credits

Built for GVPocr - Vipassana Research Institute
Archipelago Commons Integration
December 2025

---

**Ready to get started?** → [Quick Start Guide](AMISET_QUICK_START.md)

**Need details?** → [API Reference](AMISET_ENDPOINT_GUIDE.md)

**Testing?** → `python test_amiset_endpoints.py --help`
