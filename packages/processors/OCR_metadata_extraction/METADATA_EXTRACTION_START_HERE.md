# Start Here: PDF Metadata Extraction with LM Studio

**Quick answer to: "How to send PDF file to LMStudio and ask it to extract all metadata in JSON format?"**

---

## The Quickest Way (60 seconds)

### Step 1: Make sure LM Studio is running
```bash
docker-compose up -d lmstudio
```

### Step 2: Run the extraction script
```bash
python3 extract_pdf_metadata.py invoice.pdf invoice
```

### Step 3: Get your JSON results
```bash
cat invoice_metadata.json
```

**Done!** Your metadata is in JSON format.

---

## 5-Minute Setup for Developers

### Option A: Using the Pre-Built Script

```bash
# For invoices
python3 extract_pdf_metadata.py invoice.pdf invoice

# For contracts
python3 extract_pdf_metadata.py contract.pdf contract

# For any document
python3 extract_pdf_metadata.py document.pdf generic
```

**That's it!** Results saved to `document_metadata.json`

### Option B: Writing Your Own Code (5 lines)

```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

provider = LMStudioProvider()
result = provider.process_image('invoice.pdf', custom_prompt='Return JSON: {"invoice_number": "...", "total": "...", "currency": "..."}')
metadata = json.loads(result['text'])
print(json.dumps(metadata, indent=2))
```

---

## How It Works

```
Your PDF File
     ↓
Convert to Image(s)
     ↓
Send to LM Studio with JSON Prompt
     ↓
LM Studio Extracts Data
     ↓
Returns JSON Response
     ↓
Your Structured Metadata
```

---

## Files You Need to Know

| File | Purpose |
|------|---------|
| **extract_pdf_metadata.py** | Main extraction script - run this! |
| **example_pdf_metadata.py** | 5 working examples to learn from |
| **PDF_METADATA_QUICK_REFERENCE.md** | Quick commands and patterns |
| **LMSTUDIO_PDF_METADATA_EXTRACTION.md** | Complete detailed guide |

---

## Copy-Paste Examples

### Invoice Extraction
```bash
python3 extract_pdf_metadata.py invoice.pdf invoice
```

### Contract Extraction
```bash
python3 extract_pdf_metadata.py contract.pdf contract
```

### Custom Extraction
Create a `my_prompt.txt`:
```
Return ONLY valid JSON with these fields:
{
  "field_1": "value from document",
  "field_2": "another value",
  "field_3": "one more value"
}
```

Then run:
```bash
python3 extract_pdf_metadata.py document.pdf custom my_prompt.txt
```

### Python Code
```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

provider = LMStudioProvider()

# Invoice example
invoice_prompt = """Extract invoice data. Return ONLY JSON:
{
  "invoice_number": "...",
  "date": "...",
  "total": "...",
  "currency": "..."
}"""

result = provider.process_image('invoice.pdf', custom_prompt=invoice_prompt)
metadata = json.loads(result['text'])
print(json.dumps(metadata, indent=2))
```

---

## What Gets Extracted

### Invoices
- Invoice number
- Invoice date & due date
- Vendor & customer information
- Line items (description, qty, price)
- Subtotal, tax, total
- Currency

### Contracts
- Contract title & date
- Party names & roles
- Contract value & currency
- Start & end dates
- Key obligations
- Governing law

### Generic Documents
- Document type
- Title & date
- Pages
- Main parties involved
- Key amounts
- Action items

---

## Common Questions

### Q: What if I get JSON parsing error?
```python
try:
    metadata = json.loads(result['text'])
except json.JSONDecodeError:
    print("Response was:", result['text'])
    # Fix your prompt to request JSON-only response
```

### Q: How do I extract from multiple PDFs?
```bash
python3 extract_pdf_metadata.py invoice1.pdf invoice
python3 extract_pdf_metadata.py invoice2.pdf invoice
python3 extract_pdf_metadata.py invoice3.pdf invoice

# Then combine results:
cat *_metadata.json
```

### Q: Can I use my own field names?
Yes! Just update the prompt:
```python
prompt = """Extract data. Return JSON:
{
  "my_field_1": "description",
  "my_field_2": "another description"
}"""
```

### Q: Does it work with multi-page PDFs?
Yes! Each page is processed separately and aggregated.

### Q: What if LM Studio is slow?
```bash
# Increase timeout
export LMSTUDIO_TIMEOUT=1200

# Then run extraction
python3 extract_pdf_metadata.py document.pdf invoice
```

---

## Verification Checklist

Before you start, verify:

- [ ] LM Studio is running: `curl http://localhost:1234/v1/models`
- [ ] You have a PDF file ready
- [ ] Python 3.6+ installed: `python3 --version`
- [ ] Extract script exists: `ls extract_pdf_metadata.py`
- [ ] You're in the right directory: `pwd`

---

## Troubleshooting

### Problem: "LM Studio is not running"
```bash
docker-compose up -d lmstudio
# Wait 30 seconds for it to start
curl http://localhost:1234/v1/models
```

### Problem: "File not found"
```bash
# Check file exists
ls -la invoice.pdf

# Use full path if needed
python3 extract_pdf_metadata.py /full/path/to/invoice.pdf invoice
```

### Problem: "Invalid JSON response"
```python
# Try simpler prompt
prompt = '{"field1": "...", "field2": "..."}'
```

### Problem: "Timeout"
```bash
export LMSTUDIO_TIMEOUT=1200
# Try again with longer timeout
```

---

## Next: Learn More

- **Quick Reference**: See `PDF_METADATA_QUICK_REFERENCE.md`
- **Complete Guide**: See `LMSTUDIO_PDF_METADATA_EXTRACTION.md`
- **Examples**: Run `python3 example_pdf_metadata.py`

---

## One More Thing: Custom Metadata

Want to extract specific fields? Easy:

```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

provider = LMStudioProvider()

# Define what you want to extract
my_fields_prompt = """Extract these specific fields. Return ONLY JSON:
{
  "field_1_name": "extract this",
  "field_2_name": "and this",
  "field_3_name": "and this too",
  "field_4_name": "use null if not found"
}"""

result = provider.process_image('mydocument.pdf', custom_prompt=my_fields_prompt)
data = json.loads(result['text'])

# Use your data
print(f"Field 1: {data['field_1_name']}")
print(f"Field 2: {data['field_2_name']}")
```

---

## Summary

| Task | Command |
|------|---------|
| Extract invoice | `python3 extract_pdf_metadata.py file.pdf invoice` |
| Extract contract | `python3 extract_pdf_metadata.py file.pdf contract` |
| Extract any doc | `python3 extract_pdf_metadata.py file.pdf generic` |
| Use Python | See code examples above |
| Learn more | Read `PDF_METADATA_QUICK_REFERENCE.md` |
| Full guide | Read `LMSTUDIO_PDF_METADATA_EXTRACTION.md` |

---

## Ready?

1. **Run this now**: `python3 extract_pdf_metadata.py invoice.pdf invoice`
2. **Check output**: `cat invoice_metadata.json`
3. **Modify for your needs**: Update the prompt in the script
4. **Integrate into app**: Copy the Python pattern into your code

**Questions?** Check `LMSTUDIO_PDF_METADATA_EXTRACTION.md` for detailed examples and troubleshooting.

Happy extracting! 🎉
