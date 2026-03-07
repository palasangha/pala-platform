# Google Lens Integration Guide

## Overview

The Google Lens Provider enables advanced OCR capabilities with automatic metadata extraction from letters and documents. It uses Google Cloud Vision API's powerful text detection and analysis features to extract:

- **Text Content**: Full document text with word-level confidence scores
- **Structured Data**: Blocks, paragraphs, and individual words with bounding boxes
- **Metadata Extraction**:
  - Sender information (name, email, phone, address)
  - Recipient information
  - Document date
  - Document type detection (letter, invoice, receipt, form, contract, email)
  - Key fields (reference, subject, invoice number, amount, due date)
  - Detected language

## Features

### 1. **Text Extraction**
- Full document OCR with character-level precision
- Word-level confidence scores
- Block and paragraph structure preservation
- Bounding box coordinates for each word

### 2. **Metadata Extraction**
- **Sender Info**: Automatically detects sender name, email, phone, and address
- **Recipient Info**: Extracts "To:" and recipient address information
- **Date Detection**: Recognizes multiple date formats
- **Document Type**: Classifies documents as letters, invoices, receipts, forms, contracts, or emails
- **Key Fields**: Extracts common document fields like invoice numbers, amounts, due dates

### 3. **Language Detection**
- Automatic language detection from document
- Multi-language support

## Setup Instructions

### Prerequisites

1. **Google Cloud Project**: Must be set up with Vision API enabled
2. **Service Account**: Create a service account with Vision API permissions
3. **Credentials**: Download the JSON credentials file

### Step 1: Enable Google Cloud Vision API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select your project
3. Enable the Vision API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Cloud Vision API"
   - Click "Enable"

### Step 2: Create a Service Account

1. In Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details
4. Grant the role "Basic > Viewer" or "Vision > Vision API User"
5. Create a JSON key and download it

### Step 3: Configure Environment

Add the following to your `.env` file:

```bash
# Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"

# Enable/disable Google Lens provider
export GOOGLE_LENS_ENABLED=true

# Set as default provider (optional)
export DEFAULT_OCR_PROVIDER=google_lens
```

### Step 4: Place Credentials File

Place your Google service account JSON file at one of these locations:
- `backend/google-credentials.json`
- Path specified in `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Default Google Cloud credentials location

### Step 5: Verify Setup

```python
from app.services.ocr_service import OCRService

ocr_service = OCRService()
providers = ocr_service.get_available_providers()

# Should show google_lens as available
for provider in providers:
    print(f"{provider['display_name']}: {provider['available']}")
```

## Usage

### Using Google Lens Provider in Your Application

#### Option 1: Direct Provider Usage

```python
from app.services.ocr_providers.google_lens_provider import GoogleLensProvider

lens_provider = GoogleLensProvider()

result = lens_provider.process_image(
    image_path='path/to/letter.jpg',
    languages=['en', 'hi'],
    handwriting=False
)

# Access results
print("Text:", result['text'])
print("Metadata:", result['metadata'])
print("Sender:", result['metadata']['sender'])
print("Document Type:", result['metadata']['document_type'])
```

#### Option 2: Using OCR Service

```python
from app.services.ocr_service import OCRService

ocr_service = OCRService()

result = ocr_service.process_image(
    image_path='path/to/letter.jpg',
    provider='google_lens',
    languages=['en', 'hi']
)

print("Text:", result['text'])
print("Metadata:", result['metadata'])
```

#### Option 3: Via REST API

**Get available providers:**
```bash
curl -X GET http://localhost:5000/ocr/providers \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Process image with Google Lens:**
```bash
curl -X POST http://localhost:5000/ocr/process/<image_id> \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google_lens",
    "languages": ["en", "hi"]
  }'
```

## Response Format

### Standard OCR Response

```json
{
  "message": "OCR processing completed",
  "image_id": "123456",
  "text": "Full extracted text here...",
  "confidence": 0.92,
  "blocks": [
    {
      "text": "Block text",
      "confidence": 0.95,
      "bounds": {
        "x1": 100,
        "y1": 200,
        "x2": 300,
        "y2": 350
      }
    }
  ],
  "provider": "google_lens"
}
```

### With Metadata

When using Google Lens, the response includes a `metadata` field:

```json
{
  "text": "Full extracted text...",
  "confidence": 0.92,
  "metadata": {
    "sender": {
      "name": "John Smith",
      "email": "john@example.com",
      "phone": "(555) 123-4567",
      "address": "123 Main St, City, State 12345"
    },
    "recipient": {
      "name": "Jane Doe",
      "email": null,
      "phone": null,
      "address": "456 Oak Ave, City, State 67890"
    },
    "date": "November 14, 2025",
    "document_type": "letter",
    "key_fields": {
      "subject": "Project Proposal",
      "reference": "RE: 2025-001"
    },
    "language": "en",
    "file_info": {
      "filename": "letter.jpg",
      "processed_at": "2025-11-14T10:30:00.000000"
    }
  }
}
```

## Document Type Detection

Google Lens automatically detects the following document types:

| Type | Keywords Detected |
|------|------------------|
| **letter** | Dear, Sincerely, Regards, Truly Yours |
| **invoice** | Invoice, Bill, Amount Due, Payment, Total |
| **receipt** | Receipt, Payment Received, Thank You |
| **form** | Please Fill, Form, Application, Questionnaire |
| **contract** | Agreement, Contract, Terms and Conditions |
| **email** | From:, To:, Subject:, CC:, BCC: |

## Metadata Fields Extracted

### Sender Information
- **Name**: Detected from first few lines of document
- **Email**: Regex pattern matching for email addresses
- **Phone**: Pattern matching for phone numbers
- **Address**: Extracted from first few lines

### Recipient Information
- **Name**: Extracted after "To:" or "Recipient:" keywords
- **Address**: Following lines after recipient name
- **Email/Phone**: Pattern matching in document

### Key Fields
- **Reference**: `ref`, `reference`, `ref #`
- **Subject**: `subject`, `re`
- **Invoice Number**: `invoice`, `invoice #`
- **Amount**: `amount`, `total`, `total amount`
- **Due Date**: `due`, `due date`

## Environment Variables

```bash
# Enable/disable Google Lens provider
GOOGLE_LENS_ENABLED=true

# Google Cloud credentials file path
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Set Google Lens as default OCR provider
DEFAULT_OCR_PROVIDER=google_lens

# Language hints (optional)
GOOGLE_VISION_LANGUAGE_HINTS=en,hi
```

## Error Handling

The provider handles various error scenarios:

```python
try:
    result = ocr_service.process_image(
        image_path='letter.jpg',
        provider='google_lens'
    )
except ValueError as e:
    # Provider not available or not configured
    print(f"Provider error: {e}")
except Exception as e:
    # OCR processing failed
    print(f"Processing error: {e}")
```

## Performance Considerations

1. **API Costs**: Google Vision API usage is charged per 1,000 requests
2. **Processing Time**: ~2-5 seconds per image depending on size and complexity
3. **Image Quality**: Higher quality images produce better results
4. **Image Size**: Recommended max 20MB

## Troubleshooting

### Provider Shows as Not Available

**Problem**: `google_lens` provider shows as unavailable

**Solutions**:
1. Check Google credentials file exists and is valid
2. Verify `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set
3. Ensure Vision API is enabled in Google Cloud Console
4. Check service account has Vision API permissions

```python
from app.services.ocr_providers.google_lens_provider import GoogleLensProvider

lens = GoogleLensProvider()
print(f"Available: {lens.is_available()}")
```

### Authentication Errors

**Problem**: `Google.auth.exceptions.DefaultCredentialsError`

**Solution**: Ensure credentials file is in correct location:
```bash
# Option 1: Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# Option 2: Place in standard location
cp your-credentials.json ~/.config/gcloud/application_default_credentials.json
```

### Poor Metadata Extraction

**Problem**: Metadata fields are None or incomplete

**Solutions**:
1. Use clear, well-formatted documents
2. Ensure sender/recipient information is on first page
3. Use standard date formats
4. Keep document layout simple

## Testing

### Unit Test Example

```python
import pytest
from app.services.ocr_service import OCRService

def test_google_lens_provider():
    ocr_service = OCRService()
    provider = ocr_service.get_provider('google_lens')
    
    assert provider.is_available()
    assert provider.get_name() == 'google_lens'

def test_process_letter():
    ocr_service = OCRService()
    
    result = ocr_service.process_image(
        image_path='test_letter.jpg',
        provider='google_lens'
    )
    
    assert 'text' in result
    assert 'metadata' in result
    assert 'sender' in result['metadata']
    assert 'document_type' in result['metadata']
```

## API Reference

### GoogleLensProvider Class

```python
class GoogleLensProvider(BaseOCRProvider):
    def __init__(self)
    def get_name() -> str
    def is_available() -> bool
    def process_image(
        image_path: str,
        languages: List[str] = None,
        handwriting: bool = False,
        custom_prompt: str = None
    ) -> dict
```

### Response Structure

```python
{
    'text': str,                          # Full extracted text
    'full_text': str,                     # Same as text
    'words': List[dict],                  # Individual words with confidence
    'blocks': List[dict],                 # Text blocks with bounds
    'confidence': float,                  # Average confidence score
    'metadata': {
        'sender': dict,                   # Sender information
        'recipient': dict,                # Recipient information
        'date': str,                      # Extracted date
        'document_type': str,             # Detected document type
        'key_fields': dict,               # Extracted key fields
        'language': str,                  # Detected language
        'file_info': dict                 # File metadata
    }
}
```

## Best Practices

1. **Document Quality**: Use high-resolution images (minimum 300 DPI)
2. **Lighting**: Ensure good lighting to avoid shadows and glare
3. **Angle**: Scan documents straight-on, not at angles
4. **Format**: PNG or JPEG formats work best
5. **Size**: Keep images under 20MB for optimal performance
6. **Batch Processing**: Use batch API for multiple documents

## Support & Contributions

For issues or feature requests, please refer to the project's GitHub repository or contact support.

## License

This integration follows the same license as the main project.
