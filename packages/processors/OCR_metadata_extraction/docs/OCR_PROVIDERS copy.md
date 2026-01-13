# OCR Providers Guide

GVPOCR now supports 7 different OCR providers! This document provides a quick reference for setting up and using each provider.

## Enabling/Disabling Providers

You can control which OCR providers are available using environment variables:

```bash
# Set in your .env file
GOOGLE_VISION_ENABLED=true    # Enable/disable Google Vision
GOOGLE_LENS_ENABLED=true      # Enable/disable Google Lens (NEW!)
AZURE_ENABLED=true            # Enable/disable Azure
OLLAMA_ENABLED=true           # Enable/disable Ollama
VLLM_ENABLED=false            # Enable/disable VLLM
TESSERACT_ENABLED=true        # Enable/disable Tesseract
EASYOCR_ENABLED=true          # Enable/disable EasyOCR
```

**Benefits:**
- Disabled providers won't appear in the UI
- Saves initialization time and resources
- Prevents errors if a provider isn't configured

**Example - Disable VLLM:**
```bash
VLLM_ENABLED=false
```

Then restart your application - VLLM will not be available.

## Quick Comparison

| Provider | Type | Cost | Speed | Accuracy | Best Use Case |
|----------|------|------|-------|----------|---------------|
| **Google Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Production apps |
| **Google Lens** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Letters, documents with metadata |
| **Azure Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Handwriting, Enterprise |
| **Ollama** | Self-hosted AI | Free | Medium | ⭐⭐⭐⭐ | Privacy, customization |
| **VLLM** | Self-hosted AI | Free | Very Fast | ⭐⭐⭐⭐ | High throughput |
| **Tesseract** | Local | Free | Very Fast | ⭐⭐⭐ | Simple docs, offline |
| **EasyOCR** | Local DL | Free | Slow | ⭐⭐⭐⭐ | Multi-language, Asian scripts |

## Setup Instructions

### 1. Google Lens (NEW! - Recommended for Letters & Documents)

**Features:**
- Advanced text extraction with metadata
- Automatically detects sender, recipient, date
- Classifies document type (letter, invoice, receipt, contract, form, email)
- Extracts key fields (reference, subject, amount, due date)
- Multi-language support

**Setup:**
```bash
# Same credentials as Google Vision
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_LENS_ENABLED=true
```

**Usage:**
```bash
# Process with Google Lens
curl -X POST http://localhost:5000/ocr/process/IMAGE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "google_lens",
    "languages": ["en", "hi"]
  }'
```

**See:** [GOOGLE_LENS_SETUP.md](./GOOGLE_LENS_SETUP.md) for detailed documentation

---

### 2. Google Cloud Vision (Default)

```bash
# Already configured in your .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
DEFAULT_OCR_PROVIDER=google_vision
```

**No additional dependencies needed** - works out of the box!

### 2. Google Cloud Vision (Default)

```bash
# Add to your .env
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_VISION_KEY=your-subscription-key
DEFAULT_OCR_PROVIDER=azure
```

**Install dependencies:**
```bash
pip install -r requirements-azure.txt
```

### 3. Azure Computer Vision

```bash
# Server setup (on 172.12.0.83)
ollama pull llama3.2-vision

# Add to your .env
OLLAMA_HOST=http://172.12.0.83:11434
OLLAMA_MODEL=llama3.2-vision
DEFAULT_OCR_PROVIDER=ollama
```

**No Python dependencies needed** - uses HTTP API!

### 4. Ollama (Gemma3)

```bash
# Add to your .env
VLLM_HOST=http://172.12.0.132:8000
VLLM_MODEL=llama-3.2-11b-vision-instruct
DEFAULT_OCR_PROVIDER=vllm
```

**No Python dependencies needed** - uses HTTP API!

### 5. VLLM

```bash
# Add to your .env
VLLM_HOST=http://172.12.0.132:8000
VLLM_MODEL=llama-3.2-11b-vision-instruct
DEFAULT_OCR_PROVIDER=vllm
```

**No Python dependencies needed** - uses HTTP API!

### 6. Tesseract OCR

```bash
# Install Tesseract (system package)
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin

# Add to your .env
TESSERACT_CMD=/usr/bin/tesseract
DEFAULT_OCR_PROVIDER=tesseract
```

**Install Python wrapper:**
```bash
pip install -r requirements-tesseract.txt
```

**Docker:** Already included! No setup needed.

### 6. EasyOCR

```bash
# Add to your .env
EASYOCR_GPU=True  # or False if no GPU
DEFAULT_OCR_PROVIDER=easyocr
```

**Install dependencies** (large download ~2GB):
```bash
pip install -r requirements-easyocr.txt
```

**Note:** First run downloads language models (~100MB per language)

## Usage in Code

### Backend API

```python
# Process with specific provider
result = ocr_service.process_image(
    image_path='/path/to/image.jpg',
    languages=['en', 'hi'],
    handwriting=False,
    provider='tesseract'  # or 'azure', 'easyocr', etc.
)
```

### Frontend API

```typescript
// Get available providers
const { providers } = await ocrAPI.getProviders();

// Process with specific provider
const result = await ocrAPI.processImage(imageId, {
  languages: ['en', 'hi'],
  handwriting: false,
  provider: 'easyocr'
});
```

### REST API

```bash
# Get available providers
curl http://localhost:5000/api/ocr/providers \
  -H "Authorization: Bearer $TOKEN"

# Process image with specific provider
curl -X POST http://localhost:5000/api/ocr/process/IMAGE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "languages": ["en", "hi"],
    "handwriting": false,
    "provider": "tesseract"
  }'
```

## Choosing the Right Provider

### For Maximum Accuracy
→ **Google Vision** or **Azure Vision**
- Best for production applications
- Handles complex documents well
- Good language support

### For Handwriting
→ **Azure Vision** or **EasyOCR**
- Azure has excellent handwriting support
- EasyOCR works well for handwritten text

### For Privacy/Offline Use
→ **Tesseract** or **EasyOCR**
- All processing happens locally
- No data leaves your infrastructure
- No internet required

### For Speed
→ **Tesseract** or **VLLM**
- Tesseract is fastest for simple documents
- VLLM is fastest for AI-based OCR

### For Asian Languages
→ **EasyOCR** or **Google Vision**
- EasyOCR has excellent CJK support
- Supports Hindi, Tamil, Telugu, Bengali, etc.

### For Cost Optimization
→ **Tesseract** (free, fast) for simple docs
→ **EasyOCR** (free, accurate) for complex docs
→ **Ollama/VLLM** (free, flexible) for custom models

## Performance Tips

### Tesseract
- Use high-resolution images (300 DPI recommended)
- Ensure good contrast
- Works best with clean, printed text

### EasyOCR
- Enable GPU for much faster processing
- First run downloads models (be patient)
- Cache can be large (~1GB per language set)

### Azure/Google
- Use batch processing for multiple images
- Consider caching results
- Monitor usage for cost control

### Ollama/VLLM
- Requires GPU on server for good performance
- Tune temperature parameter for accuracy
- Consider batch processing for efficiency

## Troubleshooting

### Provider Shows Unavailable
```bash
# Check provider status
curl http://localhost:5000/api/ocr/providers

# Test Tesseract
tesseract --version

# Test Ollama
curl http://172.12.0.83:11434/api/tags

# Test VLLM
curl http://172.12.0.132:8000/v1/models
```

### EasyOCR Memory Issues
```bash
# Disable GPU if needed
export EASYOCR_GPU=False

# Or reduce image size before processing
```

### Tesseract Poor Accuracy
```bash
# Install language data
sudo apt-get install tesseract-ocr-hin tesseract-ocr-spa

# Try different PSM modes (in code)
```

## Migration Guide

### From Single Provider to Multi-Provider

The application automatically detects available providers. To migrate:

1. **Update `.env`** with new provider settings
2. **Install dependencies** for providers you want
3. **Restart backend** - providers auto-register
4. **Select provider** in UI dropdown

### Switching Default Provider

```bash
# In .env
DEFAULT_OCR_PROVIDER=tesseract  # Change this

# Restart backend
docker-compose restart backend
```

## Docker Deployment

All providers except Ollama/VLLM work in Docker:

```yaml
# docker-compose.yml already configured with:
- Tesseract (pre-installed)
- Azure (via env vars)
- Google Vision (via credentials)
- EasyOCR (via requirements.txt)

# For Ollama/VLLM, point to external servers
OLLAMA_HOST=http://172.12.0.83:11434
VLLM_HOST=http://172.12.0.132:8000
```

## License Considerations

- **Google Vision**: Commercial, pay-per-use
- **Azure Vision**: Commercial, pay-per-use
- **Tesseract**: Apache 2.0 (free, open-source)
- **EasyOCR**: Apache 2.0 (free, open-source)
- **Ollama**: MIT (free, open-source)
- **VLLM**: Apache 2.0 (free, open-source)

Check individual model licenses when using Ollama/VLLM!
