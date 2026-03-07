# PDF Metadata Extraction with LM Studio - Complete Guide

## Quick Answer

**Question**: How to send PDF file to LMStudio and ask it to extract all metadata in JSON format?

**Answer**: Use the provided tools below. The simplest way is:

```bash
python3 extract_pdf_metadata.py your_file.pdf invoice
```

This will extract metadata and save it to `your_file_metadata.json`

---

## What You Have

### 🎯 Working System Components

- ✅ LM Studio running locally (http://localhost:1234)
- ✅ Complete PDF metadata extraction tools
- ✅ Multiple integration methods (script, Python API, direct HTTP)
- ✅ Pre-built templates for invoices, contracts, forms, generic documents
- ✅ Comprehensive documentation and examples

### 📦 Files in This Directory

#### Executable Scripts (Ready to Run)
1. **extract_pdf_metadata.py** - Main extraction script
   - Supports: invoice, contract, form, generic, custom
   - Input: PDF file path and document type
   - Output: JSON metadata file
   
2. **example_pdf_metadata.py** - 5 working code examples
   - Invoice extraction
   - Contract extraction
   - Generic extraction
   - Batch processing
   - Custom fields extraction

3. **test_lmstudio_direct.py** - Direct API test
4. **test_lmstudio_fixed.py** - Fixed JSON parser

#### Documentation
- **METADATA_EXTRACTION_START_HERE.md** - 5-minute quick start
- **METADATA_EXTRACTION_VISUAL_GUIDE.txt** - ASCII diagrams and explanations
- **PDF_METADATA_QUICK_REFERENCE.md** - Copy-paste commands and templates
- **LMSTUDIO_PDF_METADATA_EXTRACTION.md** - Complete detailed guide
- **TEST_RESULTS.md** - Results from testing with actual PDF

#### Test Results
- **extracted_metadata.json** - Example output showing extracted metadata

---

## 3 Ways to Use

### Method 1: Command Line (Easiest)

```bash
python3 extract_pdf_metadata.py document.pdf invoice
```

**Output**: `document_metadata.json`

**Supported types**: invoice, contract, form, generic, custom

### Method 2: Python Code (5 lines)

```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
import json

provider = LMStudioProvider()
result = provider.process_image('invoice.pdf', custom_prompt='...')
metadata = json.loads(result['text'])
```

### Method 3: Direct HTTP (Advanced)

```bash
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-3-27b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Extract metadata..."},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }],
    "max_tokens": 4096,
    "temperature": 0.1
  }'
```

---

## Getting Started

### Step 1: Check Prerequisites

```bash
# Verify LM Studio is running
curl http://localhost:1234/v1/models

# Check for PDF file
ls *.pdf
```

### Step 2: Run Extraction

```bash
# For invoices
python3 extract_pdf_metadata.py invoice.pdf invoice

# For contracts
python3 extract_pdf_metadata.py contract.pdf contract

# For any document
python3 extract_pdf_metadata.py document.pdf generic
```

### Step 3: Check Results

```bash
# View extracted metadata
cat document_metadata.json

# Verify JSON is valid
python3 -m json.tool document_metadata.json
```

---

## Example Output

```json
{
  "status": "success",
  "pdf_file": "From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf",
  "metadata": {
    "document_type": "report or memorandum",
    "title": "From Refusals to Last-Minute Rescue",
    "date": "1969-09-29",
    "location": "New Delhi",
    "likely_author": "Indian government official",
    "key_topics": [
      "international relations",
      "diplomacy",
      "crisis negotiation"
    ],
    "document_context": "Details about rejection followed by successful resolution"
  }
}
```

---

## Document Types Supported

| Type | Fields Extracted | Use For |
|------|-----------------|---------|
| **invoice** | Number, date, vendor, customer, items, amounts, tax, currency | Billing documents |
| **contract** | Title, date, parties, value, obligations, governing law | Legal agreements |
| **form** | Fields, values, sections, signatures, completion date | Forms and applications |
| **generic** | Type, title, date, parties, amounts, action items | Any document |
| **custom** | Define your own fields | Specific needs |

---

## Customization

### Create Custom Metadata Template

Edit `extract_pdf_metadata.py` and add your custom prompt:

```python
custom_prompt = """Extract these specific fields:
{
  "field_1": "description",
  "field_2": "description",
  "field_3": "description"
}"""

result = provider.process_image('file.pdf', custom_prompt=custom_prompt)
```

### Create Custom Prompt File

```bash
# Create prompt file
cat > my_prompt.txt << 'EOF'
Extract metadata. Return ONLY JSON:
{
  "my_field_1": "...",
  "my_field_2": "..."
}
