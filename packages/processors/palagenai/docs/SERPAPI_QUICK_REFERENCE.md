# ⚡ SerpAPI Google Lens - Quick Reference Card

**Print this page or save as PDF for quick access**

---

## 🚀 Quick Start (Copy-Paste Ready)

### Installation
```bash
pip install -r requirements.txt
export SERPAPI_API_KEY="your_api_key"
export GOOGLE_GENERATIVE_AI_API_KEY="your_gemini_key"
```

### Test It Works
```python
from app.services.ocr_service import OCRService
service = OCRService()
result = service.process_image('letter.jpg', provider='serpapi_google_lens')
print(result['text'])
```

---

## 📝 Common Code Snippets

### Basic Usage
```python
result = service.process_image(
    image_path='letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi'],
    handwriting=True
)
```

### English Only
```python
result = service.process_image(
    'letter.jpg',
    provider='serpapi_google_lens',
    languages=['en']
)
```

### Hindi Only
```python
result = service.process_image(
    'hindi_letter.jpg',
    provider='serpapi_google_lens',
    languages=['hi']
)
```

### Detect Language
```python
language = result['detected_language']  # 'en', 'hi', or 'en-hi'
```

### Extract Metadata
```python
metadata = result['metadata']
sender = metadata['sender']
recipient = metadata['recipient']
date = metadata['date']
doc_type = metadata['document_type']
```

### Check for Handwriting
```python
if result['file_info']['handwriting_detected']:
    print("Handwritten text found")
```

### Check Hinglish
```python
hinglish = result['metadata']['hinglish_content']
if hinglish['is_hinglish']:
    print(f"Hindi: {hinglish['hindi_content_ratio']:.0%}")
    print(f"English: {hinglish['english_content_ratio']:.0%}")
```

### Batch Processing
```python
from pathlib import Path
for image_file in Path('letters/').glob('*.jpg'):
    result = service.process_image(
        str(image_file),
        provider='serpapi_google_lens'
    )
    print(f"{image_file.name}: {result['detected_language']}")
```

### Error Handling
```python
try:
    result = service.process_image('letter.jpg', provider='serpapi_google_lens')
except Exception as e:
    print(f"Error: {e}")
    # Try fallback provider
    result = service.process_image('letter.jpg', provider='google_vision')
```

---

## 🔍 Response Structure

```python
result = {
    'text': str,                      # Full extracted text
    'full_text': str,                 # Same as text
    'blocks': [                       # Paragraphs
        {
            'text': str,
            'confidence': float,      # 0-1
            'language': str           # 'en', 'hi', 'en-hi'
        }
    ],
    'words': [                        # Individual words
        {'text': str, 'confidence': float}
    ],
    'confidence': float,              # Overall confidence
    'detected_language': str,         # 'en', 'hi', 'en-hi'
    'supported_languages': list,      # Requested languages
    'metadata': {
        'sender': {
            'name': str or None,
            'email': str or None,
            'phone': str or None,
            'address': str or None
        },
        'recipient': {...},           # Same structure as sender
        'date': str or None,
        'document_type': str,         # 'letter', 'invoice', etc.
        'key_fields': dict,           # Custom fields
        'language': str,              # 'en' or 'hi'
        'hinglish_content': {
            'is_hinglish': bool,
            'hindi_content_ratio': float,
            'english_content_ratio': float
        }
    },
    'file_info': {
        'filename': str,
        'processed_at': str,          # ISO timestamp
        'handwriting_detected': bool
    },
    'provider': str                   # 'serpapi_google_lens'
}
```

---

## 🎯 Parameter Reference

```python
service.process_image(
    image_path: str,              # Required: Path to image
    languages: List[str] = None,  # Optional: ['en', 'hi']
                                  # Default: ['en', 'hi']
    handwriting: bool = False,    # Optional: Detect handwriting
    custom_prompt: str = None     # Optional: Gemini custom prompt
)
```

---

## 📊 Document Types

| Type | Keywords |
|------|----------|
| letter | dear, sincerely, regards, yours |
| invoice | invoice, bill, amount due, चालान |
| receipt | receipt, thank you, रसीद |
| form | form, application, फॉर्म |
| contract | agreement, contract, संविदा |
| email | from:, to:, subject: |

---

## 🔑 Environment Variables

```env
# Required
SERPAPI_API_KEY=your_key_here

# Optional
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_key
SERPAPI_GOOGLE_LENS_ENABLED=true
USE_LOCAL_LENS_PROCESSING=false
DEFAULT_OCR_PROVIDER=serpapi_google_lens
```

---

## ⚙️ Configuration

### Get API Keys
- **SerpAPI**: https://serpapi.com → Register → API Keys
- **Gemini**: https://makersuite.google.com/app/apikey

### Set Environment Variables
```bash
# Linux/Mac
export SERPAPI_API_KEY="your_key"
export GOOGLE_GENERATIVE_AI_API_KEY="your_gemini_key"

# Windows (PowerShell)
$env:SERPAPI_API_KEY="your_key"
$env:GOOGLE_GENERATIVE_AI_API_KEY="your_gemini_key"

# .env file (backend directory)
SERPAPI_API_KEY=your_key
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_key
```

---

## 🧪 Testing

### Run Test Suite
```bash
pytest backend/test/test_serpapi_google_lens.py -v
```

### Run Specific Test
```bash
pytest backend/test/test_serpapi_google_lens.py::TestSerpAPIGoogleLensProvider::test_language_detection_hindi -v
```

### Run Examples
```bash
cd backend
python examples_serpapi_google_lens.py
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Provider not available | Check SERPAPI_API_KEY is set |
| Hindi not detected | Include 'hi' in languages list |
| Handwriting not recognized | Set handwriting=True parameter |
| Rate limiting | Add time.sleep(1) between calls |
| Import error | Run: pip install google-generativeai |
| Module not found | Check requirements.txt is installed |

---

## 📚 Documentation

| Need | File |
|------|------|
| Quick start | SERPAPI_QUICK_START.md |
| Complete setup | SERPAPI_GOOGLE_LENS_SETUP.md |
| Technical details | SERPAPI_IMPLEMENTATION_GUIDE.md |
| Examples | examples_serpapi_google_lens.py |
| Tests | test_serpapi_google_lens.py |
| Overview | README_SERPAPI.md |
| Navigation | SERPAPI_DOCUMENTATION_INDEX.md |

---

## 💡 Tips & Tricks

### Batch Process with Error Handling
```python
from pathlib import Path
import time

results = []
for image_file in Path('letters/').glob('*.jpg'):
    try:
        result = service.process_image(
            str(image_file),
            provider='serpapi_google_lens',
            languages=['en', 'hi']
        )
        results.append({
            'file': image_file.name,
            'text': result['text'][:100],
            'language': result['detected_language']
        })
        time.sleep(1)  # Rate limiting
    except Exception as e:
        print(f"Error processing {image_file.name}: {e}")

# Print results
for r in results:
    print(f"{r['file']}: {r['language']}")
```

### Compare Providers
```python
providers = ['serpapi_google_lens', 'google_vision', 'tesseract']

for provider in providers:
    try:
        result = service.process_image('letter.jpg', provider=provider)
        print(f"{provider}: {result['confidence']:.2%}")
    except Exception as e:
        print(f"{provider}: Failed")
```

### Export to JSON
```python
import json

result = service.process_image('letter.jpg', provider='serpapi_google_lens')

with open('result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

### Language-specific Processing
```python
# Process Hindi document
hindi_result = service.process_image(
    'hindi_letter.jpg',
    provider='serpapi_google_lens',
    languages=['hi']
)

# Process English document
english_result = service.process_image(
    'english_letter.jpg',
    provider='serpapi_google_lens',
    languages=['en']
)

# Process mixed document
mixed_result = service.process_image(
    'mixed_letter.jpg',
    provider='serpapi_google_lens',
    languages=['en', 'hi']
)
```

---

## ✅ Checklist

- [ ] pip install -r requirements.txt
- [ ] Set SERPAPI_API_KEY environment variable
- [ ] Set GOOGLE_GENERATIVE_AI_API_KEY (optional)
- [ ] Read SERPAPI_QUICK_START.md
- [ ] Test with first example
- [ ] Process your documents
- [ ] Review metadata extraction
- [ ] Check language detection
- [ ] Deploy to production

---

## 🚀 Getting Help

```
1. Check SERPAPI_QUICK_START.md (2 min)
2. Check SERPAPI_GOOGLE_LENS_SETUP.md (15 min)
3. Review examples_serpapi_google_lens.py
4. Run test_serpapi_google_lens.py
5. Check troubleshooting section above
```

---

## 📞 Quick Links

- **SerpAPI Docs**: https://serpapi.com/docs/google-lens
- **Gemini API**: https://ai.google.dev
- **Unicode Devanagari**: https://en.wikipedia.org/wiki/Devanagari

---

**Last Updated:** December 2024  
**Status:** ✅ Production Ready  
**Version:** 1.0.0
