# SerpAPI Google Lens Provider Setup Guide

## Overview

The **SerpAPI Google Lens Provider** adds advanced OCR capabilities to your project with specific support for:
- **Hindi and English text extraction** (with Hinglish detection)
- **Handwritten and typed text recognition**
- **Metadata extraction** from letters and documents
- **Fallback support** using Google Gemini API when SerpAPI is unavailable

## Features

### 1. Multi-Language Support
- **English** (en)
- **Hindi** (hi)
- **Hinglish** (en-hi) - Hindi + English mix
- Automatic language detection from extracted text
- Character set support:
  - Latin script (English, Latin-based languages)
  - Devanagari script (Hindi, Sanskrit, Marathi, etc.)

### 2. Text Recognition
- **Typed Text**: Full support for printed documents
- **Handwritten Text**: Recognition of handwritten letters and documents
- **Mixed Content**: Documents with both typed and handwritten text
- **Structure Preservation**: Maintains original layout and formatting

### 3. Metadata Extraction
From letters and documents, automatically extracts:
- **Sender Information**: Name, email, phone, address
- **Recipient Information**: Name, address, email, phone
- **Date Information**: Multiple date format support
- **Document Type**: Letter, invoice, receipt, form, contract, email
- **Key Fields**: Reference, subject, invoice #, amount, due date
- **Language Detection**: Identifies language(s) present in document
- **Content Analysis**: Detects Hinglish content ratio

## Prerequisites

### API Keys Required (Choose One)

#### Option 1: SerpAPI (Primary)
```bash
# Get API key from: https://serpapi.com
SERPAPI_API_KEY=your_serpapi_api_key_here
```

#### Option 2: Google Generative AI (Fallback)
```bash
# Get API key from: https://makersuite.google.com/app/apikey
GOOGLE_GENERATIVE_AI_API_KEY=your_google_generative_ai_key_here
```

### Python Dependencies
The following packages need to be installed:

```bash
pip install -r requirements.txt
```

**Key packages:**
- `requests` - For API calls to SerpAPI
- `google-generativeai` - For Gemini fallback processing
- `google-lens-api-py` - Optional Google Lens integration
- `python-dotenv` - For environment variable management

## Installation Steps

### 1. Install Dependencies
```bash
# From the backend directory
cd backend
pip install -r requirements.txt

# Or install specific packages
pip install requests google-generativeai google-lens-api-py
```

### 2. Configure Environment Variables

Create or update `.env` file in the `backend` directory:

```env
# SerpAPI Configuration
SERPAPI_API_KEY=your_api_key_here
SERPAPI_GOOGLE_LENS_ENABLED=true

# Google Gemini Fallback Configuration
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_api_key_here
USE_LOCAL_LENS_PROCESSING=false

# Optional: Set as default provider
DEFAULT_OCR_PROVIDER=serpapi_google_lens
```

### 3. Verify Installation

Test the provider is working:

```bash
python -c "
from app.services.ocr_service import OCRService
service = OCRService()
providers = service.get_available_providers()
serpapi = [p for p in providers if p['name'] == 'serpapi_google_lens']
print('✓ SerpAPI Provider Available' if serpapi and serpapi[0]['available'] else '✗ Not Available')
"
```

## Usage Examples

### Basic Usage

```python
from app.services.ocr_service import OCRService

# Initialize service
ocr_service = OCRService()

# Process image with SerpAPI provider
result = ocr_service.process_image(
    image_path='path/to/letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi'],  # Support both English and Hindi
    handwriting=True  # Enable handwriting detection
)

# Access results
print(f"Text: {result['text']}")
print(f"Language: {result.get('detected_language', 'en')}")
print(f"Metadata: {result.get('metadata', {})}")
```

### Extract Metadata from Letter

```python
result = ocr_service.process_image(
    image_path='letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi']
)

metadata = result['metadata']

# Sender information
print(f"From: {metadata['sender']['name']}")
print(f"Email: {metadata['sender']['email']}")
print(f"Phone: {metadata['sender']['phone']}")

# Recipient information
print(f"To: {metadata['recipient']['name']}")

# Document details
print(f"Date: {metadata['date']}")
print(f"Type: {metadata['document_type']}")
print(f"Language: {metadata['language']}")
```

### Detect Language in Document

```python
result = ocr_service.process_image(
    image_path='hindi_letter.jpg',
    provider='serpapi_google_lens'
)

# Check detected language
language = result.get('detected_language')
print(f"Detected Language: {language}")  # 'en', 'hi', or 'en-hi'

# Check Hinglish content
hinglish = result['metadata'].get('hinglish_content', {})
print(f"Is Hinglish: {hinglish.get('is_hinglish', False)}")
print(f"Hindi Content: {hinglish.get('hindi_content_ratio', 0):.2%}")
print(f"English Content: {hinglish.get('english_content_ratio', 0):.2%}")
```

### Handle Handwritten Documents

```python
result = ocr_service.process_image(
    image_path='handwritten_letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi'],
    handwriting=True  # Explicitly request handwriting detection
)

# Check if handwriting was detected
if result['file_info'].get('handwriting_detected'):
    print("✓ Handwritten text detected and extracted")

# Access words with confidence
for word in result['words']:
    print(f"{word['text']}: {word['confidence']:.2%}")
```

### Batch Processing

```python
from pathlib import Path

image_dir = Path('letters/')
results = []

for image_file in image_dir.glob('*.jpg'):
    result = ocr_service.process_image(
        image_path=str(image_file),
        provider='serpapi_google_lens',
        languages=['en', 'hi']
    )
    
    results.append({
        'file': image_file.name,
        'text': result['text'][:100],  # First 100 chars
        'language': result.get('detected_language'),
        'sender': result['metadata']['sender']['name'],
        'date': result['metadata']['date']
    })

# Display results
for r in results:
    print(f"File: {r['file']}")
    print(f"  Language: {r['language']}")
    print(f"  From: {r['sender']}")
    print(f"  Date: {r['date']}")
```

### Using with REST API

```bash
# Send POST request to your backend endpoint
curl -X POST http://localhost:5000/api/ocr/process \
  -F "file=@letter.jpg" \
  -F "provider=serpapi_google_lens" \
  -F "languages=en,hi" \
  -F "handwriting=true"
```

## Response Structure

### Standard Response

```json
{
  "text": "Full extracted text from image...",
  "full_text": "Same as text field",
  "blocks": [
    {
      "text": "First paragraph...",
      "confidence": 0.85,
      "language": "en"
    },
    {
      "text": "Second paragraph...",
      "confidence": 0.85,
      "language": "hi"
    }
  ],
  "words": [
    {
      "text": "First",
      "confidence": 0.85
    },
    {
      "text": "word",
      "confidence": 0.85
    }
  ],
  "confidence": 0.85,
  "detected_language": "en",
  "supported_languages": ["en", "hi"],
  "metadata": {
    "sender": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "9876543210",
      "address": null
    },
    "recipient": {
      "name": "Jane Smith",
      "email": null,
      "phone": null,
      "address": null
    },
    "date": "12/01/2024",
    "document_type": "letter",
    "key_fields": {
      "subject": "Project Proposal"
    },
    "language": "en",
    "hinglish_content": {
      "is_hinglish": false,
      "hindi_content_ratio": 0.0,
      "english_content_ratio": 0.85
    }
  },
  "file_info": {
    "filename": "letter.jpg",
    "processed_at": "2024-12-01T10:30:45.123456",
    "handwriting_detected": false
  },
  "provider": "serpapi_google_lens"
}
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERPAPI_API_KEY` | (required) | Your SerpAPI API key |
| `SERPAPI_GOOGLE_LENS_ENABLED` | `true` | Enable/disable the provider |
| `GOOGLE_GENERATIVE_AI_API_KEY` | (optional) | Gemini API key for fallback |
| `USE_LOCAL_LENS_PROCESSING` | `false` | Force use of Gemini fallback |
| `DEFAULT_OCR_PROVIDER` | `google_vision` | Default provider for processing |

### Method Parameters

```python
process_image(
    image_path: str,                    # Path to image file (required)
    languages: List[str] = None,        # ['en', 'hi'] (optional, defaults to both)
    handwriting: bool = False,          # Enable handwriting detection
    custom_prompt: str = None           # Custom extraction prompt (Gemini only)
)
```

## Troubleshooting

### Issue: "SerpAPI provider is not available"

**Solution:**
```bash
# Check if API key is set
echo $SERPAPI_API_KEY

# If empty, set it in .env
SERPAPI_API_KEY=your_key_here

# Verify in Python
import os
print(os.getenv('SERPAPI_API_KEY'))
```

### Issue: "Google Lens provider initialization failed"

**Solution:**
```bash
# Ensure google-generativeai is installed
pip install google-generativeai

# Verify installation
python -c "import google.generativeai; print('✓ Installed')"
```

### Issue: Handwriting not detected

**Solution:**
```python
# Explicitly request handwriting detection
result = ocr_service.process_image(
    image_path='image.jpg',
    provider='serpapi_google_lens',
    handwriting=True  # Enable explicitly
)

# Check result
print(result['file_info']['handwriting_detected'])
```

### Issue: Hindi text not being recognized

**Solution:**
```python
# Ensure Hindi is in the languages list
result = ocr_service.process_image(
    image_path='hindi_letter.jpg',
    provider='serpapi_google_lens',
    languages=['hi', 'en']  # Include 'hi' for Hindi support
)

# Check detected language
print(result['detected_language'])  # Should be 'hi' or 'en-hi'
```

### Issue: API Rate Limiting

**Solution:**
```python
import time

# Add delay between requests
for image in images:
    result = ocr_service.process_image(image, provider='serpapi_google_lens')
    time.sleep(1)  # Wait 1 second between API calls
```

## Performance Notes

### Processing Times
- **Typed Documents**: 2-5 seconds (SerpAPI)
- **Handwritten Documents**: 3-8 seconds (SerpAPI)
- **Fallback (Gemini)**: 4-10 seconds
- **Mixed Content**: 5-10 seconds

### Cost Considerations

**SerpAPI:**
- Pay-per-call pricing (typically $0.005-0.02 per image)
- Check current pricing: https://serpapi.com/pricing

**Google Gemini API:**
- Free tier available with limits
- Check pricing: https://ai.google.dev/pricing

## Advanced Usage

### Custom Text Processing

```python
result = ocr_service.process_image(
    image_path='letter.jpg',
    provider='serpapi_google_lens',
    custom_prompt="""
    Extract the following specific information:
    1. Contract ID
    2. Expiration Date
    3. Signatory Names
    Please format as JSON.
    """
)
```

### Comparison with Other Providers

```python
# Compare results from multiple providers
providers = ['serpapi_google_lens', 'google_lens', 'google_vision']

for provider in providers:
    try:
        result = ocr_service.process_image(
            image_path='letter.jpg',
            provider=provider,
            languages=['en', 'hi']
        )
        print(f"{provider}:")
        print(f"  Text length: {len(result['text'])}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Language: {result.get('detected_language')}")
    except Exception as e:
        print(f"{provider}: Error - {e}")
```

## Getting Help

1. **Check Logs**: Review Flask application logs for detailed error messages
2. **Test Provider Availability**: Use the verification script above
3. **API Documentation**: 
   - SerpAPI: https://serpapi.com/docs/google-lens
   - Gemini: https://ai.google.dev/docs/gemini_api_overview
4. **GitHub Issues**: Report bugs and request features

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Set up environment variables in `.env`
3. ✅ Test provider with verification script
4. ✅ Process your first letter: See "Usage Examples" above
5. ✅ Integrate with your application

---

**Happy OCR-ing! 🎉**
