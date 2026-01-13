# LM Studio OCR Provider - Quick Start Guide

## 5-Minute Setup

### 1. Enable LM Studio Server

```bash
# In LM Studio Application:
1. Load a vision model (e.g., llava, minicpm-v)
2. Go to: Developer → Local Server
3. Click "Start Server"
4. Verify running at: http://localhost:1234
```

### 2. Configure Environment

Add to `.env`:

```bash
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=local-model
DEFAULT_OCR_PROVIDER=lmstudio
```

### 3. Restart Application

```bash
docker-compose restart backend
# or
python backend/run.py
```

### 4. Test

```bash
curl -X GET http://localhost:5000/api/ocr/providers | grep lmstudio
```

## Using the Provider

### Extract Text from Image

```python
from app.services.ocr_service import OCRService

ocr = OCRService()
result = ocr.process_image(
    'path/to/image.jpg',
    provider='lmstudio'
)
print(result['text'])
```

### Extract Metadata

```python
result = ocr.process_image(
    'letter.jpg',
    provider='lmstudio',
    custom_prompt="""Extract:
    - Sender name
    - Date
    - Subject
    - Key points"""
)
print(result['text'])
```

### Process PDF

```python
result = ocr.process_image(
    'document.pdf',
    provider='lmstudio',
    languages=['en']
)
# Automatically handles all pages
print(f"Pages: {result.get('pages_processed')}")
```

### Via API

```bash
curl -X POST http://localhost:5000/api/ocr/process/IMAGE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "lmstudio",
    "languages": ["en"],
    "handwriting": false
  }'
```

## Configuration Reference

| Setting | Default | Notes |
|---------|---------|-------|
| `LMSTUDIO_ENABLED` | `false` | Set to `true` to enable |
| `LMSTUDIO_HOST` | `localhost:1234` | LM Studio server address |
| `LMSTUDIO_MODEL` | `local-model` | Model loaded in LM Studio |
| `LMSTUDIO_TIMEOUT` | `600s` | Request timeout |
| `LMSTUDIO_MAX_TOKENS` | `4096` | Max response length |

## Recommended Models

```
llava           → Best overall balance
minicpm-v       → Excellent multilingual
llama2-vision   → High quality extraction
qwen-vl         → Fast + accurate
```

## Troubleshooting

### Connection Failed
```bash
# Check server running
curl http://localhost:1234/v1/models

# Enable in config
LMSTUDIO_ENABLED=true

# Restart app
docker-compose restart backend
```

### Timeout Errors
```bash
# Increase timeout
LMSTUDIO_TIMEOUT=1200

# Check if model loaded in LM Studio
# Check system resources (CPU/GPU/RAM)
```

### No Model Response
```bash
# Restart LM Studio
# Reload model in LM Studio
# Try different model
# Check logs for errors
```

## Environment Variables Template

```bash
# LM Studio Configuration
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=local-model
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_TIMEOUT=600
LMSTUDIO_MAX_TOKENS=4096

# Make it default provider (optional)
DEFAULT_OCR_PROVIDER=lmstudio
```

## Files Added/Modified

```
Added:
  ✓ backend/app/services/ocr_providers/lmstudio_provider.py
  ✓ LMSTUDIO_SETUP.md (detailed guide)
  ✓ LMSTUDIO_QUICK_START.md (this file)

Modified:
  ✓ backend/app/services/ocr_service.py
  ✓ backend/app/services/ocr_providers/__init__.py
  ✓ backend/app/config.py
```

## Next Steps

1. See `LMSTUDIO_SETUP.md` for detailed documentation
2. Review provider examples in the full guide
3. Configure custom prompts for your use case
4. Test with sample documents

## Support

For issues:
1. Check `LMSTUDIO_SETUP.md` troubleshooting section
2. Verify LM Studio server running
3. Check environment variables
4. Review application logs

---

Ready to use! Start with the test command in step 4 above.
