# LM Studio OCR Provider Setup Guide

This guide explains how to configure and use the LM Studio provider for OCR and metadata extraction in the gvpocr application.

## Overview

The LM Studio provider enables local OCR processing using models loaded in LM Studio. It uses LM Studio's OpenAI-compatible API to perform text extraction and metadata extraction from scanned documents.

### Key Features

- **Local Processing**: No cloud API keys required, runs entirely on your machine
- **OpenAI-Compatible API**: Uses LM Studio's `/v1/chat/completions` endpoint
- **Image Support**: Handles PNG, JPG, JPEG, TIFF, BMP, GIF formats
- **PDF Support**: Automatically processes multi-page PDFs page by page
- **Multilingual**: Supports language hints for better extraction
- **Handwriting Detection**: Can specifically handle handwritten text
- **Custom Prompts**: Override default OCR prompt with custom instructions

## Prerequisites

1. **LM Studio Installed**: Download from [lmstudio.ai](https://lmstudio.ai)
2. **Model Loaded**: Load a vision-capable model in LM Studio (e.g., llava, minicpm-v)
3. **API Server Enabled**: Start the local API server in LM Studio (default: `http://localhost:1234`)

## Configuration

### 1. Environment Variables

Add these variables to your `.env` file:

```bash
# LM Studio Configuration
LMSTUDIO_ENABLED=true                           # Enable the LM Studio provider
LMSTUDIO_HOST=http://localhost:1234             # LM Studio API server address
LMSTUDIO_MODEL=local-model                      # Model name (or specific model identifier)
LMSTUDIO_API_KEY=lm-studio                      # API key (usually 'lm-studio' or left blank)
LMSTUDIO_TIMEOUT=600                            # Request timeout in seconds (default: 600)
LMSTUDIO_MAX_TOKENS=4096                        # Maximum tokens in response (default: 4096)
```

### 2. Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LMSTUDIO_ENABLED` | `false` | Set to `true` to enable the provider |
| `LMSTUDIO_HOST` | `http://localhost:1234` | LM Studio API server address |
| `LMSTUDIO_MODEL` | `local-model` | Model identifier (shown in LM Studio) |
| `LMSTUDIO_API_KEY` | `lm-studio` | Bearer token for API authentication |
| `LMSTUDIO_TIMEOUT` | `600` | Request timeout in seconds |
| `LMSTUDIO_MAX_TOKENS` | `4096` | Maximum response length |

### 3. Docker Compose Setup

If using Docker, you can run LM Studio in a separate container or access it from the host:

**Option A: Access LM Studio on host machine**
```env
LMSTUDIO_HOST=http://host.docker.internal:1234  # On Windows/Mac
# or
LMSTUDIO_HOST=http://172.17.0.1:1234           # On Linux
```

**Option B: Run LM Studio in Docker**
Add a service to `docker-compose.yml`:
```yaml
lmstudio:
  image: lmstudio:latest
  ports:
    - "1234:1234"
  volumes:
    - ./models:/models
  environment:
    - LMSTUDIO_PORT=1234
```

Then use:
```env
LMSTUDIO_HOST=http://lmstudio:1234
```

## Getting Started

### Step 1: Start LM Studio

1. Launch LM Studio application
2. Load a vision-capable model (e.g., llava, minicpm-v, llama2-vision)
3. Go to Settings → Developer → Local Server
4. Click "Start Server"
5. Verify the server is running on `http://localhost:1234`

### Step 2: Configure Environment

Update your `.env` file:

```bash
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=local-model  # Replace with your actual model name
DEFAULT_OCR_PROVIDER=lmstudio  # Optional: set as default provider
```

### Step 3: Test the Connection

```bash
# Test if LM Studio is running
curl http://localhost:1234/v1/models

# Expected response:
# {"object":"list","data":[{"id":"local-model","object":"model",...}]}
```

Or use Python to test:

```python
import requests

response = requests.get('http://localhost:1234/v1/models')
if response.status_code == 200:
    print("LM Studio is running!")
    print(response.json())
else:
    print(f"Connection failed: {response.status_code}")
```

### Step 4: Use the Provider

#### Via API Endpoint

```bash
# Process an image
curl -X POST http://localhost:5000/api/ocr/process/IMAGE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "lmstudio",
    "languages": ["en"],
    "handwriting": false
  }'
```

#### Via Python

```python
from app.services.ocr_service import OCRService

ocr_service = OCRService()
provider = ocr_service.get_provider('lmstudio')

result = provider.process_image(
    image_path='/path/to/scanned_letter.jpg',
    languages=['en'],
    handwriting=False
)

print(result['text'])  # Extracted text
print(result['full_text'])  # Full extracted text
print(result['confidence'])  # Confidence score
```

## Advanced Usage

### Custom Prompts for Metadata Extraction

Override the default OCR prompt with a custom instruction for metadata extraction:

```python
result = provider.process_image(
    image_path='/path/to/letter.jpg',
    custom_prompt="""Extract the following metadata from this scanned letter:
    - Sender name and address
    - Recipient name and address
    - Date of letter
    - Subject
    - Key points or main content (brief summary)

    Return the extracted metadata in a structured format."""
)
```

### Batch Processing

```python
from app.services.ocr_service import OCRService

ocr_service = OCRService()
image_paths = [
    '/path/to/letter1.jpg',
    '/path/to/letter2.jpg',
    '/path/to/letter3.jpg'
]

results = []
for image_path in image_paths:
    result = ocr_service.process_image(
        image_path=image_path,
        provider='lmstudio',
        languages=['en']
    )
    results.append({
        'file': image_path,
        'text': result['text'],
        'confidence': result['confidence']
    })
```

### Multilingual Support

```python
# Process text in multiple languages
result = provider.process_image(
    image_path='/path/to/multilingual_document.jpg',
    languages=['en', 'hi', 'es'],  # English, Hindi, Spanish
    handwriting=False
)
```

### Handwriting Recognition

```python
# Optimize for handwritten text
result = provider.process_image(
    image_path='/path/to/handwritten_letter.jpg',
    languages=['en'],
    handwriting=True  # Enable handwriting detection
)
```

### PDF Processing

```python
# Automatically processes multi-page PDFs
result = provider.process_image(
    image_path='/path/to/multi_page_letter.pdf',
    languages=['en'],
    handwriting=False
)

# Result includes page information
print(f"Pages processed: {result.get('pages_processed', 1)}")
print(f"Blocks: {result['blocks']}")  # Each block includes page number
```

## Troubleshooting

### "LM Studio provider is not available"

**Issue**: Provider is disabled or server is not running

**Solutions**:
1. Ensure `LMSTUDIO_ENABLED=true` in `.env`
2. Check that LM Studio server is running: `curl http://localhost:1234/v1/models`
3. Verify the host/port is correct in `LMSTUDIO_HOST`
4. Check firewall settings if using remote server

### "Could not connect to LM Studio server"

**Issue**: Network connection failed

**Solutions**:
1. Verify LM Studio is running and server is started
2. Test connectivity: `curl http://localhost:1234/v1/models`
3. Check if using correct host (localhost vs IP address)
4. Ensure no firewall blocking port 1234

### "LM Studio request timed out"

**Issue**: Request took too long

**Solutions**:
1. Increase `LMSTUDIO_TIMEOUT` (e.g., 1200 for 20 minutes)
2. Check if model is loaded in LM Studio
3. Check system resource usage (CPU, memory, GPU)
4. Try with a simpler/smaller model

### "No response from model"

**Issue**: Model loaded but not responding

**Solutions**:
1. Restart LM Studio
2. Reload the model
3. Check system resources (GPU/CPU/RAM)
4. Try a different model
5. Check LM Studio logs for errors

### Model Selection

**Recommended Models for OCR**:
- **llava**: General-purpose vision, good OCR capability
- **minicpm-v**: Excellent multilingual OCR, especially for Hindi
- **llama2-vision**: Good for detailed extraction
- **qwen-vl**: Good for structured data extraction

**Model Loading in LM Studio**:
1. Click "Browse" in LM Studio
2. Search for vision models (e.g., "llava", "minicpm")
3. Select and download
4. Click "Load" to start the model
5. Note the exact model ID shown in the interface

## API Response Format

The provider returns results in this format:

```json
{
  "text": "Extracted text from image",
  "full_text": "Extracted text from image",
  "words": [],
  "blocks": [
    {
      "text": "Extracted text from image",
      "page": 1
    }
  ],
  "confidence": 0.95,
  "pages_processed": 1
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Main extracted text |
| `full_text` | string | Complete extracted text |
| `words` | array | Word-level details (empty for LM Studio) |
| `blocks` | array | Text blocks with page information |
| `confidence` | float | Confidence score (0-1) |
| `pages_processed` | integer | Number of pages processed (PDFs only) |

## Performance Optimization

### Model Selection for Speed vs Quality

| Model | Speed | Quality | Memory | Best For |
|-------|-------|---------|--------|----------|
| llava-7b | Fast | Good | ~8GB | General OCR, good balance |
| minicpm-v | Medium | Excellent | ~5GB | Multilingual, accurate |
| llama2-vision-13b | Medium | Excellent | ~20GB | High-quality extraction |
| qwen-vl-7b | Fast | Good | ~8GB | Structured data |

### Optimization Tips

1. **Use GPU**: Ensure GPU acceleration is enabled in LM Studio
2. **Batch Processing**: Process multiple documents sequentially to reuse model
3. **Adjust Token Limit**: Reduce `LMSTUDIO_MAX_TOKENS` if response is too long
4. **Optimize Images**: Pre-process images to improve quality
5. **Language Hints**: Provide language hints to speed up processing

## Integration with OCR Chains

The LM Studio provider can be used in multi-step OCR chains:

```python
chain_config = {
    "steps": [
        {
            "step_number": 1,
            "provider": "lmstudio",
            "input_source": "original_image",
            "prompt": "Extract text from image"
        },
        {
            "step_number": 2,
            "provider": "lmstudio",
            "input_source": "step_1_output",
            "prompt": "Extract metadata (sender, date, subject) from this text"
        }
    ]
}
```

## Security Considerations

1. **Local Only**: By default, LM Studio runs locally and doesn't send data to cloud
2. **API Key**: Change the default `LMSTUDIO_API_KEY` if running on network
3. **Firewall**: Restrict access to port 1234 if exposed to network
4. **Credentials**: Store sensitive prompts in secure environment variables
5. **Network Security**: Use VPN/firewall if accessing from remote machines

## Logging & Monitoring

The LM Studio provider includes comprehensive logging at multiple levels:

**DEBUG Level**: Detailed information for diagnosing problems
- Provider initialization parameters
- Image optimization details
- API request preparation
- Response parsing

**INFO Level**: High-level operational information
- Provider availability
- Processing start/completion
- Processing duration and statistics
- Text extraction counts

**WARNING Level**: Potentially problematic situations
- Provider not available
- Non-200 status codes
- Missing content extraction

**ERROR Level**: Error conditions preventing operation
- Connection failures
- Timeout errors
- API errors with full details

### Viewing Logs

```bash
# View backend logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# Filter for LM Studio logs
docker-compose logs backend | grep lmstudio

# Filter for errors
docker-compose logs backend | grep ERROR

# View last 50 lines
docker-compose logs --tail=50 backend
```

### Example Log Output

**Successful Processing:**
```
INFO: Starting image processing: /path/to/image.jpg
DEBUG: Image loaded: size=(1920, 1080), format=JPEG
DEBUG: Sending request with model=local-model, max_tokens=4096
DEBUG: API response received in 15.32s (status: 200)
INFO: Image processing completed successfully in 15.45s. Extracted 245 characters
```

**PDF Processing:**
```
INFO: Starting PDF processing: document.pdf
INFO: PDF converted to 3 page(s)
DEBUG: Processing page 1/3
DEBUG: Page 1 API call completed in 12.50s (status: 200)
INFO: PDF processing completed successfully in 42.15s. Processed 3 page(s), extracted 907 characters
```

**Error Handling:**
```
ERROR: LM Studio request timed out (timeout: 600s)
DEBUG: Traceback (most recent call last):
  ...
```

See **LMSTUDIO_LOGGING_GUIDE.md** for detailed logging documentation.

## Metadata Extraction Examples

### Example 1: Extract Letter Metadata

```python
custom_prompt = """Analyze this scanned letter and extract:
1. Sender: Full name and address
2. Recipient: Full name and address
3. Date: When letter was written
4. Subject: Main topic
5. Key information: Important dates, amounts, or details

Return as JSON with keys: sender_name, sender_address, recipient_name, recipient_address, date, subject, key_information"""

result = provider.process_image(
    image_path='letter.jpg',
    custom_prompt=custom_prompt
)

# Parse JSON response
import json
metadata = json.loads(result['text'])
print(metadata)
```

### Example 2: Extract Invoice Data

```python
custom_prompt = """Extract invoice metadata:
- Invoice number
- Invoice date
- Due date
- Vendor name and address
- Customer name and address
- Total amount
- Payment terms

Return as JSON."""

result = provider.process_image(
    image_path='invoice.jpg',
    custom_prompt=custom_prompt
)
```

### Example 3: Extract Contract Terms

```python
custom_prompt = """From this scanned contract, extract:
- Party names
- Effective date
- Expiration date
- Key terms (3-5 most important terms)
- Penalty clauses if any
- Signature lines

Return in structured format."""

result = provider.process_image(
    image_path='contract.pdf',
    custom_prompt=custom_prompt
)
```

## API Endpoints

The LM Studio provider is automatically available through these endpoints:

```
POST /api/ocr/process/<image_id>
GET /api/ocr/providers
POST /api/ocr/batch-process
POST /api/ocr-chains/execute
```

See the main API documentation for detailed endpoint descriptions.

## Support & Additional Resources

- **LM Studio Official**: https://lmstudio.ai
- **Vision Models**: Search for "vision" or "llava" in LM Studio's model browser
- **gvpocr Documentation**: See main README.md
- **Issue Tracking**: Report issues via GitHub issues

## Example .env Configuration

```bash
# LM Studio OCR Provider
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=local-model
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_TIMEOUT=600
LMSTUDIO_MAX_TOKENS=4096

# Optional: Set as default provider
DEFAULT_OCR_PROVIDER=lmstudio
```

---

**Last Updated**: December 2024
**Version**: 1.0
