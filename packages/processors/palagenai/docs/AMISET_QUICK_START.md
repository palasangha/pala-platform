# AMISet Endpoints - Quick Start Guide

## 🚀 Three Simple Steps

### Step 1: Create AMI Set
```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
          "language": "en",
          "processing_date": "2025-12-08T06:20:19Z"
        }
      }
    ],
    "collection_title": "My Collection"
  }'
```

**Response:**
```json
{
  "success": true,
  "ami_set_id": "123"
}
```

Save the `ami_set_id` for next steps.

---

### Step 2: Check Status
```bash
curl -X GET http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected status: `pending`

---

### Step 3: Process the AMI Set
```bash
curl -X POST http://127.0.0.1:8000/api/archipelago/amiset/process/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Now Archipelago will start processing your OCR data!

---

## 📊 What Happens Next?

The system will:
1. ✅ Validate all files exist
2. ✅ Generate CSV metadata
3. ✅ Create ZIP archive
4. ✅ Upload to Archipelago
5. ✅ Create digital objects
6. ✅ Populate metadata
7. ✅ Link to collection

---

## 🔍 Monitor Progress

```bash
# Check status every 5 seconds
for i in {1..30}; do
  curl -s http://127.0.0.1:8000/api/archipelago/amiset/status/123 \
    -H "Authorization: Bearer YOUR_TOKEN" | jq .status
  sleep 5
done
```

Status values: `pending` → `processing` → `completed` (or `failed`)

---

## 🐍 Python Client

```python
from test_amiset_endpoints import ArcipelagoAMIClient

client = ArcipelagoAMIClient(auth_token='YOUR_TOKEN')

# Create AMI Set
result = client.add_amiset(
    ocr_data_list=[...],
    collection_title="My Collection"
)
ami_set_id = result['ami_set_id']

# Check status
status = client.get_status(ami_set_id)
print(f"Status: {status['status']}")

# Process it
client.process_amiset(ami_set_id)
```

Or use the test script:
```bash
python test_amiset_endpoints.py --token TOKEN --action full
```

---

## ⚙️ Setup

### Environment Variables
```bash
export ARCHIPELAGO_ENABLED=true
export ARCHIPELAGO_BASE_URL=http://archipelago.example.com
export ARCHIPELAGO_USERNAME=admin
export ARCHIPELAGO_PASSWORD=password
```

### Docker
```bash
docker-compose up backend
# API will be at http://127.0.0.1:8000/api/archipelago
```

---

## 📚 Detailed Documentation

See **`AMISET_ENDPOINT_GUIDE.md`** for:
- Complete API reference
- Error handling
- Integration examples
- Configuration guide

---

## 💡 Tips

### Minimal Request
Only required fields:
```json
{
  "ocr_data": [
    {
      "name": "doc1",
      "label": "Document",
      "text": "OCR text here",
      "file_info": {
        "filename": "file.pdf",
        "file_path": "/path/to/file.pdf"
      },
      "ocr_metadata": {
        "provider": "tesseract"
      }
    }
  ]
}
```

### Bulk Upload
```json
{
  "ocr_data": [
    { ... document 1 ... },
    { ... document 2 ... },
    { ... document 3 ... }
  ],
  "collection_title": "Batch Upload",
  "collection_id": null
}
```

### Link to Existing Collection
```json
{
  "ocr_data": [ ... ],
  "collection_id": 456  // Archipelago node ID
}
```

---

## 🐛 Troubleshooting

### 401 Unauthorized
- Check token is valid
- Check header: `Authorization: Bearer TOKEN`

### 400 Missing ocr_data
- Ensure `ocr_data` key is present
- Ensure it's an array: `[...]`
- Ensure array is not empty

### 404 Not Found (status endpoint)
- Check AMI Set ID is correct
- Check AMI Set hasn't been deleted

### File not found during upload
- Use absolute paths or paths relative to `GVPOCR_PATH`
- Check file permissions
- Run: `ls -la /path/to/file.pdf`

### Archipelago connection failed
- Check Archipelago is running: `curl http://archipelago.example.com`
- Check credentials are correct
- Check `ARCHIPELAGO_BASE_URL` is set correctly

---

## 📞 Support

Check logs:
```bash
docker logs gvpocr-backend | tail -50
```

Test connectivity:
```bash
curl http://archipelago.example.com/jsonapi
```

Run diagnostics:
```bash
python test_amiset_endpoints.py --token TOKEN --action add
```

---

## API Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| `POST` | `/api/archipelago/amiset/add` | Create AMI Set |
| `GET` | `/api/archipelago/amiset/status/{id}` | Check status |
| `POST` | `/api/archipelago/amiset/process/{id}` | Process AMI Set |

---

**Version:** 1.0  
**Last Updated:** 2025-12-08  
**Status:** Ready to use ✅
