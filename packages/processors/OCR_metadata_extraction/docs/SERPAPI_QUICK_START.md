# SerpAPI Google Lens - Quick Start (5 Minutes)

## 1. Install & Configure (1 minute)

```bash
# Install required packages
pip install requests google-generativeai

# Create/update .env in backend directory
echo "SERPAPI_API_KEY=your_api_key_here" >> .env
echo "GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_key_here" >> .env
```

**Get API Keys:**
- SerpAPI: https://serpapi.com (register → get API key)
- Gemini: https://makersuite.google.com/app/apikey

## 2. Test It Works (1 minute)

```python
from app.services.ocr_service import OCRService

service = OCRService()

# Check if available
providers = service.get_available_providers()
serp_provider = [p for p in providers if p['name'] == 'serpapi_google_lens']
print("✓ Available!" if serp_provider[0]['available'] else "✗ Not available")
```

## 3. Process Your First Image (2 minutes)

```python
from app.services.ocr_service import OCRService

service = OCRService()

# Process an image
result = service.process_image(
    image_path='path/to/your/letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi'],  # English & Hindi
    handwriting=True
)

# Get results
print("Extracted Text:")
print(result['text'])

print("\nMetadata:")
print(f"From: {result['metadata']['sender']['name']}")
print(f"Date: {result['metadata']['date']}")
print(f"Type: {result['metadata']['document_type']}")
print(f"Language: {result['detected_language']}")
```

## 4. Key Features

| Feature | Support |
|---------|---------|
| English Text | ✅ Yes |
| Hindi Text | ✅ Yes |
| Hinglish (Mix) | ✅ Auto-detected |
| Handwritten | ✅ Yes (with flag) |
| Typed | ✅ Yes |
| Metadata | ✅ Sender, Recipient, Date, Type |
| Fallback | ✅ Gemini API |

## 5. Common Tasks

### Extract only Hindi text
```python
result = service.process_image(
    image_path='hindi_letter.jpg',
    provider='serpapi_google_lens',
    languages=['hi']
)
```

### Detect language automatically
```python
result = service.process_image(
    image_path='mixed_letter.jpg',
    provider='serpapi_google_lens'
)
language = result['detected_language']  # 'en', 'hi', or 'en-hi'
```

### Process handwritten documents
```python
result = service.process_image(
    image_path='handwritten.jpg',
    provider='serpapi_google_lens',
    handwriting=True
)
```

### Extract metadata
```python
metadata = result['metadata']
print(metadata['sender'])      # Name, email, phone
print(metadata['recipient'])   # Recipient info
print(metadata['document_type'])  # letter, invoice, etc.
```

---

**Next:** See `SERPAPI_GOOGLE_LENS_SETUP.md` for complete documentation.
