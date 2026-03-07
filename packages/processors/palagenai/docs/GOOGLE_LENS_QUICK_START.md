# Google Lens Integration - Quick Reference

## 🚀 Get Started in 2 Minutes

### 1. Set Credentials
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### 2. Enable Provider
```bash
export GOOGLE_LENS_ENABLED=true
```

### 3. Use It
```python
from app.services.ocr_service import OCRService
ocr = OCRService()
result = ocr.process_image('letter.jpg', provider='google_lens')
```

---

## 📋 What It Does

Extracts from letters and documents:

| Data | Example |
|------|---------|
| **Text** | Full letter content with confidence |
| **Sender** | "John Smith, john@example.com, (555) 123-4567" |
| **Recipient** | "Jane Doe, 456 Oak Ave" |
| **Date** | "November 14, 2025" |
| **Type** | letter, invoice, receipt, form, contract, email |
| **Fields** | reference, subject, amount, due_date |
| **Language** | en, hi, es, etc. |

---

## 🔌 REST API

```bash
# Process with Google Lens
curl -X POST http://localhost:5000/ocr/process/IMAGE_ID \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google_lens",
    "languages": ["en", "hi"]
  }'
```

Response includes:
```json
{
  "text": "Full extracted text...",
  "metadata": {
    "sender": {...},
    "recipient": {...},
    "date": "...",
    "document_type": "letter"
  }
}
```

---

## 🐍 Python API

```python
# Simple usage
result = ocr_service.process_image(
    image_path='letter.jpg',
    provider='google_lens'
)

# With options
result = ocr_service.process_image(
    image_path='letter.jpg',
    provider='google_lens',
    languages=['en', 'hi'],
    handwriting=False
)

# Direct provider access
from app.services.ocr_providers import GoogleLensProvider
lens = GoogleLensProvider()
result = lens.process_image('letter.jpg')
```

---

## 📂 Files Reference

| File | Purpose |
|------|---------|
| `google_lens_provider.py` | Main implementation |
| `GOOGLE_LENS_SETUP.md` | Complete setup guide |
| `GOOGLE_LENS_IMPLEMENTATION.md` | Technical details |
| `examples_google_lens.py` | Code examples |
| `test_google_lens.py` | Test suite |
| `IMPLEMENTATION_CHECKLIST.md` | What was done |

---

## 🔍 Check Status

```python
from app.services.ocr_service import OCRService

ocr = OCRService()
providers = ocr.get_available_providers()

for p in providers:
    if p['name'] == 'google_lens':
        print(f"Google Lens: {p['available']}")  # True or False
```

---

## ❓ Troubleshooting

**Not available?**
- Check: `echo $GOOGLE_APPLICATION_CREDENTIALS`
- Verify Vision API enabled in Google Cloud Console
- Test: `python -c "from google.cloud import vision; print('OK')"`

**Poor results?**
- Use high-quality images (300+ DPI)
- Ensure clear, legible text
- Use standard document formats

---

## 📊 Response Fields

### metadata.sender
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "(555) 123-4567",
  "address": "123 Main St, Boston, MA"
}
```

### metadata.document_type
```
"letter" | "invoice" | "receipt" | "form" | "contract" | "email" | "document"
```

### metadata.key_fields
```json
{
  "reference": "RE: 2025-001",
  "subject": "Project Proposal",
  "invoice_number": "INV-001",
  "amount": "$5,000",
  "due_date": "12/15/2025"
}
```

---

## 💡 Use Cases

1. **Automated Letter Processing**
   ```python
   result = ocr.process_image('letter.jpg', provider='google_lens')
   sender = result['metadata']['sender']['email']  # Auto-extract
   ```

2. **Invoice Processing**
   ```python
   result = ocr.process_image('invoice.jpg', provider='google_lens')
   amount = result['metadata']['key_fields']['amount']
   ```

3. **Batch Document Organization**
   ```python
   for doc in documents:
       result = ocr.process_image(doc, provider='google_lens')
       doc_type = result['metadata']['document_type']
       # Route to appropriate folder
   ```

4. **Multi-Language Support**
   ```python
   result = ocr.process_image('letter.jpg', 
       provider='google_lens',
       languages=['en', 'hi', 'es'])
   ```

---

## ✅ Features Checklist

- ✅ Text extraction with confidence
- ✅ Sender information detection
- ✅ Recipient information extraction
- ✅ Date recognition (multiple formats)
- ✅ Document type classification
- ✅ Key field extraction
- ✅ Language detection
- ✅ Word-level bounding boxes
- ✅ Error handling
- ✅ Multi-language support

---

## 🔗 Links

- [Complete Setup Guide](./GOOGLE_LENS_SETUP.md)
- [Implementation Details](./GOOGLE_LENS_IMPLEMENTATION.md)
- [Code Examples](./backend/examples_google_lens.py)
- [Test Suite](./test_google_lens.py)
- [All Providers](./OCR_PROVIDERS.md)

---

## 💬 Support

See [GOOGLE_LENS_SETUP.md](./GOOGLE_LENS_SETUP.md) for:
- Detailed setup instructions
- Troubleshooting guide
- Performance tips
- Error handling examples

See [backend/examples_google_lens.py](./backend/examples_google_lens.py) for:
- Complete code examples
- Usage patterns
- Best practices
