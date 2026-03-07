# PDF Metadata Extraction - Quick Reference

## 3 Fastest Ways to Extract JSON Metadata

### Way 1: Using the Script (Easiest)

```bash
# Make script executable
chmod +x extract_pdf_metadata.py

# Extract invoice metadata
python3 extract_pdf_metadata.py invoice.pdf invoice

# Extract contract metadata
python3 extract_pdf_metadata.py contract.pdf contract

# Extract generic metadata (any document)
python3 extract_pdf_metadata.py document.pdf generic

# Results saved to: document_metadata.json
```

### Way 2: Using Python Directly (3 lines)

```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

provider = LMStudioProvider()
result = provider.process_image('invoice.pdf', custom_prompt='Return JSON: {"invoice_number": "...", "total": "..."}')
metadata = json.loads(result['text'])
print(json.dumps(metadata, indent=2))
```

### Way 3: Using Curl (For Integration)

```bash
# First, convert PDF to base64 image and send to LM Studio directly
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Extract invoice metadata. Return only JSON with invoice_number, date, total, currency"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,BASE64_IMAGE_DATA_HERE"}}
      ]
    }],
    "max_tokens": 4096,
    "temperature": 0.1
  }'
```

---

## Metadata Templates You Can Copy

### Invoice Metadata Template
```python
prompt = """Return ONLY this JSON structure:
{
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "vendor_name": "...",
  "customer_name": "...",
  "items": [{"description": "...", "qty": "...", "price": "...", "total": "..."}],
  "subtotal": "...",
  "tax": "...",
  "total": "...",
  "currency": "USD"
}"""
```

### Contract Metadata Template
```python
prompt = """Return ONLY this JSON structure:
{
  "contract_title": "...",
  "contract_date": "YYYY-MM-DD",
  "party_1": "...",
  "party_2": "...",
  "total_value": "...",
  "currency": "...",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "key_terms": "...",
  "governing_law": "..."
}"""
```

### Generic Document Metadata Template
```python
prompt = """Return ONLY this JSON structure:
{
  "document_type": "...",
  "title": "...",
  "date": "YYYY-MM-DD",
  "pages": "...",
  "parties": ["..."],
  "amounts": [{"value": "...", "description": "..."}],
  "action_items": [{"action": "...", "deadline": "YYYY-MM-DD"}]
}"""
```

---

## Common Patterns

### Extract and Save to File
```python
import json
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

provider = LMStudioProvider()
result = provider.process_image('doc.pdf', custom_prompt='Your prompt here')
data = json.loads(result['text'])

with open('output.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### Handle JSON Parsing Errors
```python
import json

try:
    metadata = json.loads(result['text'])
    print("✓ Valid JSON")
except json.JSONDecodeError as e:
    print("✗ Invalid JSON:", e)
    print("Raw response:", result['text'][:200])
```

### Process Multiple PDFs
```python
from pathlib import Path

pdf_files = list(Path('.').glob('*.pdf'))

for pdf_file in pdf_files:
    result = provider.process_image(str(pdf_file), custom_prompt=prompt)
    data = json.loads(result['text'])

    # Save each to separate file
    output = pdf_file.stem + '_metadata.json'
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
```

### Validate JSON Structure
```python
def validate_metadata(data, required_fields):
    """Check if extracted metadata has required fields"""
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"⚠ Missing fields: {missing}")
    else:
        print("✓ All required fields present")
    return len(missing) == 0

# Usage
validate_metadata(metadata, ['invoice_number', 'total_amount', 'date'])
```

---

## Important Tips

### 1. Always Ask for JSON Only
❌ Bad:
```python
prompt = "Extract invoice details"
```

✓ Good:
```python
prompt = "Extract invoice details. Return ONLY valid JSON with no explanations or markdown."
```

### 2. Specify the Exact JSON Structure
❌ Bad:
```python
prompt = "Extract metadata as JSON"
```

✓ Good:
```python
prompt = """Return ONLY this JSON:
{
  "field1": "value",
  "field2": "value"
}"""
```

### 3. Make Fields Optional
```python
prompt = """Return JSON with these fields (use null if not present):
{
  "required_field": "...",
  "optional_field": "... or null",
  "another_optional": "... or null"
}"""
```

### 4. No Markdown or Code Blocks
Always add to prompt:
```
"Do not include markdown, code blocks, triple backticks, or explanations"
```

### 5. Date Format Specification
Always specify format:
```python
prompt = """Use this format for dates: YYYY-MM-DD
Example: 2024-01-15
...."""
```

---

## Troubleshooting

### Problem: "Invalid JSON"
```
Error: json.JSONDecodeError: Expecting value
```

**Solution**: Check if response has markdown:
```python
# Remove markdown if present
response = result['text']
if response.startswith('```json'):
    response = response[7:-3]  # Remove ```json and ```
metadata = json.loads(response)
```

### Problem: "LM Studio is not available"
```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Start it if needed
docker-compose up -d lmstudio

# Check logs
docker-compose logs lmstudio
```

### Problem: "Missing fields in response"
- Make fields optional in prompt
- Provide example values
- Simplify the JSON structure
- Ask for specific fields only

### Problem: "Timeout error"
```python
# Increase timeout in environment
export LMSTUDIO_TIMEOUT=1200  # 20 minutes

# Or in code
provider = LMStudioProvider()
provider.timeout = 1200
```

---

## Performance Tips

### For Large PDFs
```bash
# Increase timeout
export LMSTUDIO_TIMEOUT=1200

# Reduce max_tokens if response is incomplete
export LMSTUDIO_MAX_TOKENS=2048
```

### For Batch Processing
```python
# Process sequentially (slower but more reliable)
for pdf in pdf_files:
    result = provider.process_image(pdf, custom_prompt=prompt)

# Reduce response size for faster processing
prompt = "Return JSON with only: field1, field2, field3"
```

### For Streaming Results
```python
import json
from pathlib import Path

results = []
for pdf in Path('.').glob('*.pdf'):
    result = provider.process_image(str(pdf), custom_prompt=prompt)
    data = json.loads(result['text'])

    # Process immediately instead of collecting all
    print(f"Processed {pdf.name}")
    results.append(data)
```

---

## Complete Examples

### Example 1: Extract Invoice in One Command
```bash
python3 extract_pdf_metadata.py invoice.pdf invoice
```

Output:
```
======================================================================
INITIALIZING LM STUDIO PROVIDER
======================================================================
✓ LM Studio provider initialized and available

======================================================================
PROCESSING PDF
======================================================================
File: /path/to/invoice.pdf
File size: 245.3 KB
Sending to LM Studio for metadata extraction...
✓ LM Studio processing completed
✓ Extracted 1250 characters from 1 page(s)

======================================================================
PARSING METADATA
======================================================================
✓ Response parsed as valid JSON

======================================================================
EXTRACTION RESULT
======================================================================

✓ Status: SUCCESS
  File: /path/to/invoice.pdf
  Size: 245.3 KB
  Type: invoice
  Pages: 1

📄 EXTRACTED METADATA:

{
  "invoice_number": "INV-2024-001",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-15",
  ...
}

======================================================================
📁 Results saved to: invoice_metadata.json
```

### Example 2: Python Integration
```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

# Initialize
provider = LMStudioProvider()

# Define your extraction prompt
custom_prompt = """Extract invoice metadata. Return ONLY JSON:
{
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "total_amount": "...",
  "currency": "..."
}"""

# Process PDF
result = provider.process_image('invoice.pdf', custom_prompt=custom_prompt)

# Parse and use
metadata = json.loads(result['text'])
print(f"Invoice: {metadata['invoice_number']}")
print(f"Date: {metadata['invoice_date']}")
print(f"Total: {metadata['total_amount']} {metadata['currency']}")

# Save
with open('invoice_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)
```

---

## File Locations

- **Main extraction script**: `extract_pdf_metadata.py`
- **Examples**: `example_pdf_metadata.py`
- **Detailed guide**: `LMSTUDIO_PDF_METADATA_EXTRACTION.md`
- **Provider code**: `backend/app/services/ocr_providers/lmstudio_provider.py`

---

## Supported Document Types

| Type | Use | Template |
|------|-----|----------|
| **invoice** | Extract billing data | Vendor, customer, items, amounts |
| **contract** | Extract legal terms | Parties, dates, obligations, value |
| **form** | Extract form fields | Fields, values, signatures |
| **generic** | Any document | Title, date, parties, amounts |
| **custom** | Specific needs | Define your own fields |

---

## Key Commands

```bash
# Run extraction script
python3 extract_pdf_metadata.py file.pdf invoice

# View results
cat file_metadata.json

# Pretty print JSON
python3 -m json.tool file_metadata.json

# Check LM Studio status
curl http://localhost:1234/v1/models

# View logs
docker-compose logs -f lmstudio
```

---

## Success Indicators

✅ JSON is valid (can parse with json.loads())
✅ All required fields are present
✅ Values match document content
✅ Dates are in consistent format (YYYY-MM-DD)
✅ Currency codes are uppercase
✅ Numbers don't have extra symbols ($, comma in thousands)

---

## Next Steps

1. **Try the script**: `python3 extract_pdf_metadata.py invoice.pdf invoice`
2. **Check the output**: `cat invoice_metadata.json`
3. **Modify the prompt** for your specific needs
4. **Integrate into your application**: Use the LMStudioProvider directly
5. **Batch process**: Use the example script for multiple files

---

Happy metadata extracting! 📄✨
