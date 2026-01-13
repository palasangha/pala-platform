# Claude AI OCR Provider

## Overview
A new OCR provider using Claude AI (Anthropic) has been added to the system. Claude provides excellent vision capabilities for text extraction from images and PDFs.

## Setup

### 1. Install Dependencies
```bash
cd backend
pip install anthropic>=0.39.0
```

Or rebuild your Docker containers to pick up the updated `requirements.txt`:
```bash
docker-compose build backend
docker-compose up -d
```

### 2. Configure Environment Variables

Add to your `.env` file:
```bash
# Enable Claude Provider
CLAUDE_ENABLED=true

# Anthropic API Key (required)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Model to use (optional, defaults to claude-3-5-sonnet-20241022)
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

**Get your API key:**
- Sign up at https://console.anthropic.com/
- Create an API key in the Settings section
- Copy the key to your `.env` file

### 3. Set as Default (Optional)
```bash
DEFAULT_OCR_PROVIDER=claude
```

## Usage

### Via API
```bash
# Process an image with Claude
curl -X POST http://localhost:5000/api/ocr/process/IMAGE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "claude",
    "languages": ["en", "hi"],
    "handwriting": false,
    "custom_prompt": "Extract all text from this image"
  }'
```

### Via Python Code
```python
from app.services.ocr_service import OCRService

ocr_service = OCRService()

# Process with Claude
result = ocr_service.process_image(
    image_path="/path/to/image.jpg",
    provider="claude",
    languages=["en", "hi"],
    handwriting=False
)

print(result['text'])
print(f"Provider used: {result['provider']}")
print(f"Confidence: {result['confidence']}")
```

## Features

- ✅ **Vision Model**: Uses Claude 3.5 Sonnet (latest) for high-quality OCR
- ✅ **Multilingual Support**: Supports English, Hindi, and 10+ other languages
- ✅ **Handwriting Detection**: Special prompts for handwritten text
- ✅ **PDF Support**: Processes multi-page PDFs page by page
- ✅ **Custom Prompts**: Allows custom extraction prompts
- ✅ **Image Optimization**: Automatically optimizes images up to 5MB
- ✅ **Indic Script Support**: Enhanced support for Devanagari and other Indic scripts

## Supported Languages

The provider has enhanced support for:
- English (en)
- Hindi / Devanagari (hi)
- Spanish (es)
- French (fr)
- German (de)
- Chinese (zh)
- Japanese (ja)
- Arabic (ar)
- Bengali (bn)
- Telugu (te)
- Tamil (ta)
- Marathi (mr)
- Urdu (ur)

## Supported Models

You can configure which Claude model to use via the `CLAUDE_MODEL` environment variable:

- `claude-3-5-sonnet-20241022` (default, recommended for OCR)
- `claude-3-opus-20240229` (highest accuracy)
- `claude-3-sonnet-20240229` (balanced performance)
- `claude-3-haiku-20240307` (fastest, lower cost)

## Cost Considerations

Claude is a paid API service. Pricing varies by model:
- Claude 3.5 Sonnet: ~$3 per million input tokens
- Images count as tokens based on size

For cost optimization:
1. Use smaller images when possible (auto-optimized to 5MB)
2. Consider Claude Haiku for high-volume, simple text
3. Use batch processing when available

## Troubleshooting

### Provider Not Available
**Error**: "Claude provider is not available"
**Solution**:
- Ensure `ANTHROPIC_API_KEY` is set in your `.env` file
- Verify the API key is valid
- Check that `CLAUDE_ENABLED=true`
- Restart the backend service

### Import Error
**Error**: "No module named 'anthropic'"
**Solution**:
```bash
pip install anthropic>=0.39.0
# or rebuild Docker containers
docker-compose build backend
```

### API Errors
**Error**: "Claude API error: ..."
**Solution**:
- Verify your API key is correct
- Check your Anthropic account has credits
- Ensure you're not hitting rate limits

## Provider Information

**File Location**: `/backend/app/services/ocr_providers/claude_provider.py`

**Class**: `ClaudeProvider`

**Methods**:
- `process_image(image_path, languages, handwriting, custom_prompt)` - Process single image
- `is_available()` - Check if provider is configured and ready
- `get_name()` - Returns "claude"

## Testing

Verify the provider is working:
```bash
docker exec gvpocr-backend bash -c "cd /app/backend && python3 -c '
from app.services.ocr_service import OCRService
ocr = OCRService()
providers = ocr.get_available_providers()
claude = [p for p in providers if p[\"name\"] == \"claude\"]
print(f\"Claude available: {claude[0][\"available\"] if claude else False}\")
'"
```

Expected output:
```
Claude available: True  # if API key is set
Claude available: False # if API key is not set
```
