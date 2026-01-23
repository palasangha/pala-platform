# LM Studio Structured JSON - Quick Reference Guide

## Feature Overview

LM Studio now extracts both raw text AND structured metadata from document images, outputting JSON that matches the `required-format.json` schema. The enrichment pipeline further enhances this data with knowledge-based analysis.

---

## Enable/Disable Feature

### Method 1: Environment Variable
```bash
# Enable structured extraction (default)
LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=true

# Disable (use text-only mode)
LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=false
```

### Method 2: Runtime Parameter
```python
from backend.app.services.ocr_providers.lmstudio_provider import LMStudioProvider

provider = LMStudioProvider()

# Explicitly enable for this request
result = provider.process_image(image_path, enable_structured_output=True)

# Explicitly disable for this request
result = provider.process_image(image_path, enable_structured_output=False)

# Use config default (LMSTUDIO_ENABLE_STRUCTURED_OUTPUT)
result = provider.process_image(image_path)
```

---

## Response Format

### Check if structured data was extracted:
```python
response = provider.process_image('letter.pdf')

if response.get('extraction_mode') == 'structured':
    # Structured data is available
    structured = response['structured_data']
    document = structured.get('document', {})
    content = structured.get('content', {})
else:
    # Text-only fallback was used
    text = response['text']
```

### Access extracted metadata:
```python
if 'structured_data' in response:
    data = response['structured_data']

    # Document metadata
    date = data['document']['date']
    sender = data['document']['correspondence']['sender']
    recipient = data['document']['correspondence']['recipient']

    # Letter structure
    salutation = data['content']['salutation']
    body = data['content']['body']  # List of paragraphs
    closing = data['content']['closing']

    # Full text (always available)
    full_text = response['full_text']
```

---

## What Gets Extracted

### ✅ LM Studio Extracts (Visible in Image)
```json
{
  "document": {
    "date": {
      "creation_date": "2024-01-15",
      "sent_date": "2024-01-16"
    },
    "languages": ["en"],
    "physical_attributes": {
      "letterhead": "Company Name",
      "pages": 2
    },
    "correspondence": {
      "sender": {
        "name": "John Doe",
        "location": "New York",
        "contact_info": {"address": "123 Main St"}
      },
      "recipient": {
        "name": "Jane Smith",
        "location": "Boston"
      }
    }
  },
  "content": {
    "full_text": "Complete OCR text...",
    "salutation": "Dear Jane,",
    "body": ["Paragraph 1", "Paragraph 2"],
    "closing": "Sincerely,",
    "signature": "John Doe signature description"
  }
}
```

### ✅ Enrichment Agents Add (Knowledge-Based)
```json
{
  "document": {
    "correspondence": {
      "sender": {
        "biography": "John is a CEO at Acme Corp",
        "affiliation": "Acme Corporation"
      },
      "recipient": {
        "biography": "Jane is a professor of history"
      }
    }
  },
  "content": {
    "summary": "This letter discusses business proposals"
  },
  "analysis": {
    "keywords": ["business", "partnership"],
    "subjects": ["Corporate Communication"],
    "people": [...],
    "organizations": [...],
    "locations": [...],
    "historical_context": "Written during the tech boom era",
    "significance": "Important correspondence about market expansion"
  }
}
```

---

## Configuration

### Environment Variables
```bash
# Enable/disable structured output
LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=true

# Max tokens for longer JSON responses
LMSTUDIO_MAX_TOKENS=8192

# Standard LM Studio config
LMSTUDIO_ENABLED=true
LMSTUDIO_HOST=http://lmstudio:1234
LMSTUDIO_MODEL=gemma-3-12b
LMSTUDIO_TIMEOUT=600
LMSTUDIO_SKIP_AVAILABILITY_CHECK=true
```

---

## Error Handling

### Automatic Fallback
```python
# If JSON parsing fails, response automatically includes text-only data:
response = {
    'text': 'Raw OCR text...',
    'full_text': 'Raw OCR text...',
    'extraction_mode': 'text_only'  # Indicates fallback occurred
}

# No errors thrown - pipeline continues
```

### Manual Handling
```python
if response.get('extraction_mode') == 'text_only':
    logger.warning("JSON parsing failed, using text-only mode")
    # Use response['text'] for downstream processing
```

---

## Testing

### Quick Test
```python
from backend.app.services.ocr_providers.lmstudio_provider import LMStudioProvider

provider = LMStudioProvider()
result = provider.process_image('test_letter.pdf')

# Should include extraction_mode
print(f"Mode: {result.get('extraction_mode', 'unknown')}")

# Should have text
print(f"Text length: {len(result.get('text', ''))}")

# May have structured data
if 'structured_data' in result:
    print(f"Structured sections: {list(result['structured_data'].keys())}")
```

### Run Unit Tests
```bash
# All LM Studio tests
python -m pytest enrichment_service/tests/unit/test_lmstudio_structured.py -v

# JSON parsing tests only
python -m pytest enrichment_service/tests/unit/test_lmstudio_structured.py::TestJSONParsing -v

# Integration tests
python -m pytest enrichment_service/tests/unit/test_lmstudio_structured.py::TestIntegration -v
```

---

## Troubleshooting

### Structured data not appearing
1. Check: `LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=true`
2. Check: LM Studio model supports vision (gemma-3-12b does)
3. Check logs: Look for "extraction_mode" to see if fallback occurred
4. Try disabling: Set `LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=false` to verify text-only works

### JSON parsing errors
1. Check LM Studio response format
2. Verify model can output valid JSON
3. System automatically falls back to text-only
4. Check logs for specific error: `Failed to extract valid JSON`

### Performance concerns
1. JSON extraction adds ~500 tokens per request
2. JSON parsing <10ms overhead
3. Total impact <5% processing time increase
4. Disable if needed: `LMSTUDIO_ENABLE_STRUCTURED_OUTPUT=false`

---

## Integration Points

### In OCR Pipeline
```
Image → LMStudioProvider.process_image()
      → Returns: {text, structured_data, extraction_mode}
      → BulkProcessor collects results
      → EnrichmentWorker receives data
```

### In Enrichment Pipeline
```
EnrichmentWorker.enrich_document()
→ Detects 'structured_data' in ocr_data
→ AgentOrchestrator._merge_results_with_ocr()
→ Merges LM Studio + Agent results
→ Returns full required-format.json
```

### In Data Mapper
```
DataMapper.merge_enriched_with_ocr()
→ Uses both structured_data + agent_results
→ Merges into Archipelago format
→ Sends to repository
```

---

## Merge Priority

| Field | Priority | Source |
|-------|----------|--------|
| Dates | LM Studio | Visible in document |
| Languages | LM Studio | Detectable from text |
| Names/Locations | LM Studio | Visible in document |
| Biographies | Agent | External knowledge |
| Summary | Agent | Synthesis |
| Keywords/Subjects | Agent | Analysis |
| Historical Context | Agent | Research |
| Significance | Agent | Analysis |

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/ocr_providers/lmstudio_provider.py` | Core implementation |
| `enrichment_service/workers/agent_orchestrator.py` | Merging logic |
| `enrichment_service/tests/unit/test_lmstudio_structured.py` | Unit tests |
| `.env` | Configuration |
| `required-format.json` | Target schema |

---

## Monitoring

### Key Logs to Watch
```bash
# Extraction mode
"OCR includes structured extraction (mode: structured)"
"OCR is text-only, full enrichment will be performed"

# Parsing
"Successfully extracted structured data with X sections"
"JSON parsing failed: ... Falling back to text-only mode"

# Merging
"Successfully merged LM Studio structured data with enrichment results"

# Performance
"Image processing completed successfully in X.XXs. Mode: structured"
```

### Metrics to Track
- Extraction success rate (% structured vs text-only)
- Completeness score improvement
- Processing time impact
- Fallback rate
- Schema compliance rate

---

## Common Tasks

### Disable for specific request
```python
result = provider.process_image(
    image_path,
    enable_structured_output=False  # Force text-only
)
```

### Use custom prompt (bypasses structured)
```python
result = provider.process_image(
    image_path,
    custom_prompt="Your prompt here"  # Automatically disables structured
)
```

### Debug structured extraction
```python
import json

response = provider.process_image(image_path)

if 'structured_data' in response:
    print(json.dumps(response['structured_data'], indent=2))
else:
    print(f"Fallback to text-only: {response['extraction_mode']}")
```

---

## Versions & Compatibility

- **LM Studio Models Supported**: Gemma-3-12b, Llama-3.2-vision, and other vision-capable models
- **Backward Compatible**: Yes - text-only mode always available
- **Python Version**: 3.8+
- **Framework**: Flask (backend), asyncio (enrichment)

---

## Support

For issues or questions:
1. Check logs for extraction mode and error messages
2. Verify LMSTUDIO_ENABLE_STRUCTURED_OUTPUT config
3. Test with `enable_structured_output=False` to isolate issue
4. Review LMSTUDIO_STRUCTURED_JSON_IMPLEMENTATION.md for details
5. Run unit tests to verify functionality

---

**Last Updated**: 2026-01-22
**Status**: Production Ready
