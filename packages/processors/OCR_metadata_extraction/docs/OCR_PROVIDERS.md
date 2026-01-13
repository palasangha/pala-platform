# OCR Providers Guide# OCR Providers Guide



GVPOCR now supports 7 different OCR providers! This document provides a quick reference for setting up and using each provider.GVPOCR now supports 7 different OCR providers! This document provides a quick reference for setting up and using each provider.



## Enabling/Disabling Providers## Enabling/Disabling Providers



You can control which OCR providers are available using environment variables:You can control which OCR providers are available using environment variables:



```bash```bash

# Set in your .env file# Set in your .env file

GOOGLE_VISION_ENABLED=true    # Enable/disable Google VisionGOOGLE_VISION_ENABLED=true    # Enable/disable Google Vision

GOOGLE_LENS_ENABLED=true      # Enable/disable Google Lens (NEW!)GOOGLE_LENS_ENABLED=true      # Enable/disable Google Lens (NEW!)

AZURE_ENABLED=true            # Enable/disable AzureAZURE_ENABLED=true            # Enable/disable Azure

OLLAMA_ENABLED=true           # Enable/disable OllamaOLLAMA_ENABLED=true           # Enable/disable Ollama

VLLM_ENABLED=false            # Enable/disable VLLMVLLM_ENABLED=false            # Enable/disable VLLM

TESSERACT_ENABLED=true        # Enable/disable TesseractTESSERACT_ENABLED=true        # Enable/disable Tesseract

EASYOCR_ENABLED=true          # Enable/disable EasyOCREASYOCR_ENABLED=true          # Enable/disable EasyOCR

``````



## Quick Comparison**Benefits:**

- Disabled providers won't appear in the UI

| Provider | Type | Cost | Speed | Accuracy | Best Use Case |- Saves initialization time and resources

|----------|------|------|-------|----------|---------------|- Prevents errors if a provider isn't configured

| **Google Lens** ⭐ | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Letters, documents with metadata |

| **Google Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Production apps |**Example - Disable VLLM:**

| **Azure Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Handwriting, Enterprise |```bash

| **Ollama** | Self-hosted AI | Free | Medium | ⭐⭐⭐⭐ | Privacy, customization |VLLM_ENABLED=false

| **VLLM** | Self-hosted AI | Free | Very Fast | ⭐⭐⭐⭐ | High throughput |```

| **Tesseract** | Local | Free | Very Fast | ⭐⭐⭐ | Simple docs, offline |

| **EasyOCR** | Local DL | Free | Slow | ⭐⭐⭐⭐ | Multi-language, Asian scripts |Then restart your application - VLLM will not be available.



## Setup Instructions## Quick Comparison



### 1. Google Lens (NEW! - Recommended for Letters & Documents) ⭐| Provider | Type | Cost | Speed | Accuracy | Best Use Case |

|----------|------|------|-------|----------|---------------|

**Features:**| **Google Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Production apps |

- Advanced text extraction with metadata| **Google Lens** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Letters, documents with metadata |

- Automatically detects sender, recipient, date| **Azure Vision** | Cloud API | Pay per use | Fast | ⭐⭐⭐⭐⭐ | Handwriting, Enterprise |

- Classifies document type (letter, invoice, receipt, contract, form, email)| **Ollama** | Self-hosted AI | Free | Medium | ⭐⭐⭐⭐ | Privacy, customization |

- Extracts key fields (reference, subject, amount, due date)| **VLLM** | Self-hosted AI | Free | Very Fast | ⭐⭐⭐⭐ | High throughput |

- Multi-language support| **Tesseract** | Local | Free | Very Fast | ⭐⭐⭐ | Simple docs, offline |

| **EasyOCR** | Local DL | Free | Slow | ⭐⭐⭐⭐ | Multi-language, Asian scripts |

**Setup:**

```bash## Setup Instructions

GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

GOOGLE_LENS_ENABLED=true### 1. Google Lens (NEW! - Recommended for Letters & Documents)

```

**Features:**

**See:** [GOOGLE_LENS_SETUP.md](./GOOGLE_LENS_SETUP.md) for complete documentation- Advanced text extraction with metadata

- Automatically detects sender, recipient, date

---- Classifies document type (letter, invoice, receipt, contract, form, email)

- Extracts key fields (reference, subject, amount, due date)

### 2. Google Cloud Vision (Default)- Multi-language support



```bash**Setup:**

GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json```bash

DEFAULT_OCR_PROVIDER=google_vision# Same credentials as Google Vision

```GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

GOOGLE_LENS_ENABLED=true

No additional dependencies needed!```



### 3. Azure Computer Vision**Usage:**

```bash

```bash# Process with Google Lens

AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/curl -X POST http://localhost:5000/ocr/process/IMAGE_ID \

AZURE_VISION_KEY=your-subscription-key  -H "Authorization: Bearer $TOKEN" \

```  -d '{

    "provider": "google_lens",

Install: `pip install -r requirements-azure.txt`    "languages": ["en", "hi"]

  }'

### 4. Ollama (Llama 3.2 Vision)```



```bash**See:** [GOOGLE_LENS_SETUP.md](./GOOGLE_LENS_SETUP.md) for detailed documentation

OLLAMA_HOST=http://172.12.0.83:11434

OLLAMA_MODEL=llama3.2-vision---

```

### 2. Google Cloud Vision (Default)

No Python dependencies - uses HTTP API!

```bash

### 5. VLLM# Already configured in your .env

GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

```bashDEFAULT_OCR_PROVIDER=google_vision

VLLM_HOST=http://172.12.0.132:8000```

VLLM_MODEL=llama-3.2-11b-vision-instruct

```**No additional dependencies needed** - works out of the box!



No Python dependencies - uses HTTP API!### 2. Google Cloud Vision (Default)



### 6. Tesseract OCR```bash

# Add to your .env

```bashAZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/

TESSERACT_CMD=/usr/bin/tesseractAZURE_VISION_KEY=your-subscription-key

```DEFAULT_OCR_PROVIDER=azure

```

Install: `sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin`

**Install dependencies:**

### 7. EasyOCR```bash

pip install -r requirements-azure.txt

```bash```

EASYOCR_GPU=True

```### 3. Azure Computer Vision



Install: `pip install -r requirements-easyocr.txt````bash

# Server setup (on 172.12.0.83)

## Usage Examplesollama pull llama3.2-vision



### Backend API# Add to your .env

OLLAMA_HOST=http://172.12.0.83:11434

```pythonOLLAMA_MODEL=llama3.2-vision

result = ocr_service.process_image(DEFAULT_OCR_PROVIDER=ollama

    image_path='/path/to/image.jpg',```

    provider='google_lens',

    languages=['en', 'hi']**No Python dependencies needed** - uses HTTP API!

)

### 4. Ollama (Gemma3)

# With Google Lens, access metadata:

print(result['metadata']['sender']['name'])```bash

print(result['metadata']['document_type'])# Add to your .env

```VLLM_HOST=http://172.12.0.132:8000

VLLM_MODEL=llama-3.2-11b-vision-instruct

### REST APIDEFAULT_OCR_PROVIDER=vllm

```

```bash

curl -X POST http://localhost:5000/ocr/process/IMAGE_ID \**No Python dependencies needed** - uses HTTP API!

  -H "Authorization: Bearer $TOKEN" \

  -H "Content-Type: application/json" \### 5. VLLM

  -d '{

    "provider": "google_lens",```bash

    "languages": ["en", "hi"]# Add to your .env

  }'VLLM_HOST=http://172.12.0.132:8000

```VLLM_MODEL=llama-3.2-11b-vision-instruct

DEFAULT_OCR_PROVIDER=vllm

## Choosing the Right Provider```



### For Maximum Accuracy with Metadata**No Python dependencies needed** - uses HTTP API!

→ **Google Lens** ⭐ NEW!

- Extracts sender, recipient, date automatically### 6. Tesseract OCR

- Classifies document type

- Best for letters and structured documents```bash

# Install Tesseract (system package)

### For Maximum Accuracy (Text Only)# Ubuntu/Debian:

→ **Google Vision** or **Azure Vision**sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin



### For Handwriting# Add to your .env

→ **Azure Vision** or **EasyOCR**TESSERACT_CMD=/usr/bin/tesseract

DEFAULT_OCR_PROVIDER=tesseract

### For Privacy/Offline```

→ **Tesseract** or **EasyOCR**

**Install Python wrapper:**

### For Speed```bash

→ **Tesseract** or **VLLM**pip install -r requirements-tesseract.txt

```

### For Asian Languages

→ **EasyOCR** or **Google Vision****Docker:** Already included! No setup needed.



### For Cost Optimization### 6. EasyOCR

→ **Tesseract** (free) or **EasyOCR** (free) or **Ollama/VLLM** (free)

```bash

## Docker Deployment# Add to your .env

EASYOCR_GPU=True  # or False if no GPU

```yamlDEFAULT_OCR_PROVIDER=easyocr

# All providers work in Docker except Ollama/VLLM (external servers)```

# docker-compose.yml is pre-configured with:

- Tesseract (pre-installed)**Install dependencies** (large download ~2GB):

- Google Vision/Lens (via credentials)```bash

- Azure (via env vars)pip install -r requirements-easyocr.txt

- EasyOCR (via requirements.txt)```

```

**Note:** First run downloads language models (~100MB per language)

## License Considerations

## Usage in Code

- **Google Lens/Vision**: Commercial, pay-per-use

- **Azure Vision**: Commercial, pay-per-use### Backend API

- **Tesseract**: Apache 2.0 (free, open-source)

- **EasyOCR**: Apache 2.0 (free, open-source)```python

- **Ollama**: MIT (free, open-source)# Process with specific provider

- **VLLM**: Apache 2.0 (free, open-source)result = ocr_service.process_image(

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
