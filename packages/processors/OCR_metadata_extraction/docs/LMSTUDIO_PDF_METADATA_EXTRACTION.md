# PDF Metadata Extraction with LM Studio

**Complete Guide to Extracting Structured Metadata in JSON Format**

---

## Quick Start - 3 Methods

### Method 1: Using the Application API (Easiest)

```bash
# Send PDF and get metadata in JSON format
curl -X POST http://localhost:5000/api/ocr/process-pdf-metadata \
  -F "file=@invoice.pdf" \
  -F "metadata_prompt=Extract invoice number, date, total amount, vendor name"
```

### Method 2: Using Python with Application Service

```python
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

# Initialize provider
provider = LMStudioProvider()

# Custom prompt to extract metadata as JSON
metadata_prompt = """
You are an expert document analysis system. Analyze this document and extract ALL metadata.
Return ONLY valid JSON with no additional text or markdown.

{
  "document_type": "type of document",
  "metadata": {
    "title": "document title if present",
    "date": "date if present",
    "author": "author if present",
    "pages": "number of pages"
  },
  "extracted_data": {
    "key_field_1": "value",
    "key_field_2": "value"
  }
}
"""

# Process PDF with custom metadata prompt
result = provider.process_image(
    'invoice.pdf',
    custom_prompt=metadata_prompt
)

# Extract JSON from result
import json
try:
    metadata = json.loads(result['text'])
    print(json.dumps(metadata, indent=2))
except json.JSONDecodeError:
    print("Response:", result['text'])
```

### Method 3: Direct HTTP Request to LM Studio

```python
import requests
import base64
import json
from pathlib import Path

def extract_pdf_metadata(pdf_path, host='http://localhost:1234'):
    """
    Extract metadata from PDF using LM Studio directly
    """
    # Convert PDF to images
    from app.services.pdf_service import PDFService
    from app.services.image_optimizer import ImageOptimizer

    page_images = PDFService.pdf_to_images(pdf_path)

    metadata_results = []

    for page_num, page_img in enumerate(page_images, 1):
        # Optimize and encode image
        image_bytes = ImageOptimizer.optimize_and_encode(
            page_img,
            target_size_mb=5.0,
            auto_optimize=True,
            format='JPEG'
        )
        image_data = base64.b64encode(image_bytes).decode('utf-8')

        # Metadata extraction prompt
        prompt = f"""
[Page {page_num}] Analyze this document page and extract ALL metadata in JSON format.
Return ONLY valid JSON with no additional text, markdown, or explanations.

Return this exact structure:
{{
  "page": {page_num},
  "document_type": "identify type: invoice, letter, form, contract, etc",
  "content_summary": "brief summary of page content",
  "metadata": {{
    "title": "if present",
    "date": "if present",
    "author": "if present",
    "reference_number": "if present"
  }},
  "structured_data": {{
    "field_name": "field_value"
  }},
  "key_information": ["item1", "item2"]
}}
"""

        # Send to LM Studio
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(
            f"{host}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=600
        )

        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                try:
                    metadata = json.loads(content)
                    metadata_results.append(metadata)
                except json.JSONDecodeError:
                    metadata_results.append({"page": page_num, "raw_content": content})

    return metadata_results
```

---

## Detailed Examples

### Example 1: Extract Invoice Metadata

**PDF**: `invoice.pdf`

**Prompt**:
```python
invoice_prompt = """
You are an invoice analysis expert. Extract ALL invoice metadata and return ONLY valid JSON.

{
  "document_type": "invoice",
  "invoice_details": {
    "invoice_number": "the invoice number",
    "invoice_date": "the invoice date",
    "due_date": "the due date",
    "invoice_period": "invoice period if present"
  },
  "vendor_info": {
    "vendor_name": "company name",
    "vendor_address": "full address",
    "vendor_phone": "phone number",
    "vendor_email": "email address",
    "tax_id": "tax ID or company registration"
  },
  "customer_info": {
    "customer_name": "customer name",
    "customer_address": "customer address",
    "customer_phone": "customer phone",
    "customer_email": "customer email"
  },
  "items": [
    {
      "description": "item description",
      "quantity": "quantity",
      "unit_price": "unit price",
      "total": "total for item"
    }
  ],
  "financial_summary": {
    "subtotal": "subtotal amount",
    "tax_amount": "tax amount",
    "discount": "discount if present",
    "total_amount": "total invoice amount",
    "currency": "currency code"
  },
  "payment_terms": {
    "payment_method": "payment method",
    "bank_details": "bank details if present",
    "payment_instructions": "any special instructions"
  },
  "notes": "any additional notes or terms"
}
"""

result = provider.process_image('invoice.pdf', custom_prompt=invoice_prompt)
metadata = json.loads(result['text'])
print(json.dumps(metadata, indent=2))
```

**Expected Output**:
```json
{
  "document_type": "invoice",
  "invoice_details": {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "invoice_period": "January 2024"
  },
  "vendor_info": {
    "vendor_name": "ABC Company Ltd",
    "vendor_address": "123 Business Street, New York, NY 10001",
    "vendor_phone": "+1-555-0123",
    "vendor_email": "billing@abccompany.com",
    "tax_id": "EIN: 12-3456789"
  },
  "customer_info": {
    "customer_name": "John Doe",
    "customer_address": "456 Client Avenue, Boston, MA 02101",
    "customer_phone": "+1-555-9876",
    "customer_email": "john@client.com"
  },
  "items": [
    {
      "description": "Consulting Services - January",
      "quantity": "160",
      "unit_price": "$50.00",
      "total": "$8,000.00"
    }
  ],
  "financial_summary": {
    "subtotal": "$8,000.00",
    "tax_amount": "$640.00",
    "discount": "none",
    "total_amount": "$8,640.00",
    "currency": "USD"
  },
  "payment_terms": {
    "payment_method": "Bank Transfer",
    "bank_details": "ABC Bank, Account: 1234567890",
    "payment_instructions": "Please include invoice number in transfer reference"
  },
  "notes": "Thank you for your business"
}
```

### Example 2: Extract Contract Metadata

**PDF**: `contract.pdf`

**Prompt**:
```python
contract_prompt = """
You are a contract analysis expert. Extract ALL contract metadata and return ONLY valid JSON.

{
  "document_type": "contract",
  "basic_info": {
    "contract_title": "title",
    "contract_date": "effective date",
    "contract_id": "contract number or reference",
    "amendment_number": "if this is an amendment"
  },
  "parties": [
    {
      "party_name": "name",
      "party_role": "party role",
      "party_type": "individual/company",
      "address": "address",
      "contact_info": {
        "phone": "phone",
        "email": "email"
      }
    }
  ],
  "scope": {
    "contract_subject": "what the contract is about",
    "services_provided": ["service 1", "service 2"],
    "deliverables": ["deliverable 1", "deliverable 2"],
    "term": "contract duration"
  },
  "financial_terms": {
    "total_value": "total contract value",
    "currency": "currency",
    "payment_schedule": "payment terms",
    "payment_method": "how payment is made",
    "late_payment_penalty": "if specified"
  },
  "key_dates": {
    "start_date": "contract start",
    "end_date": "contract end",
    "renewal_date": "renewal date if applicable",
    "termination_date": "early termination if applicable"
  },
  "obligations": {
    "party_1_obligations": ["obligation 1"],
    "party_2_obligations": ["obligation 1"]
  },
  "intellectual_property": {
    "ip_ownership": "who owns IP",
    "confidentiality": "confidentiality terms"
  },
  "liability_and_insurance": {
    "liability_cap": "maximum liability",
    "indemnification": "indemnification clause",
    "insurance_required": "insurance requirements"
  },
  "termination": {
    "termination_clauses": "how contract can be terminated",
    "notice_period": "notice period required",
    "post_termination_obligations": "obligations after termination"
  },
  "dispute_resolution": {
    "governing_law": "which law governs",
    "jurisdiction": "jurisdiction",
    "arbitration": "arbitration clause if present"
  },
  "signatories": [
    {
      "name": "signer name",
      "title": "signer title",
      "date_signed": "date signed",
      "authorized": "authorized to sign"
    }
  ]
}
"""
```

### Example 3: Extract Form Data

**PDF**: `form.pdf`

**Prompt**:
```python
form_prompt = """
You are a form processing expert. Extract ALL form data and return ONLY valid JSON.

{
  "document_type": "form",
  "form_name": "name of form",
  "form_number": "form ID or reference number",
  "form_date": "form creation date",
  "form_version": "version if indicated",
  "sections": [
    {
      "section_name": "section title",
      "section_number": "section number if present",
      "fields": [
        {
          "field_name": "field label",
          "field_type": "text/checkbox/dropdown/date/signature",
          "field_value": "the filled value",
          "field_required": "yes/no",
          "page_number": "which page"
        }
      ]
    }
  ],
  "completed_by": {
    "name": "name of person completing form",
    "title": "their title",
    "organization": "organization",
    "date_completed": "date completed",
    "signature": "signature present or not"
  },
  "approvals": [
    {
      "approver_name": "approver name",
      "approver_title": "approver title",
      "approval_date": "approval date",
      "signature": "signature present or not"
    }
  ],
  "total_pages": "total form pages",
  "attachments": ["list of attachments mentioned"],
  "notes_and_comments": ["any notes or comments"]
}
"""
```

### Example 4: Extract All Metadata (Generic)

**Works with any document type**

**Prompt**:
```python
generic_metadata_prompt = """
You are a universal document analyzer. Extract ALL metadata from this document.
Return ONLY valid JSON with no additional text, explanations, or markdown.

{
  "analysis_metadata": {
    "document_type": "identify the type: invoice, contract, letter, form, report, etc",
    "document_title": "title if present",
    "document_date": "date on document",
    "document_author": "author or creator",
    "document_language": "language of document",
    "total_pages": "number of pages in document",
    "estimated_reading_time_minutes": "estimated reading time"
  },
  "identifiers": {
    "document_number": "any document number, ID, or reference",
    "version": "version number if present",
    "revision": "revision number if present",
    "classification": "confidential/public/internal etc if marked"
  },
  "parties_involved": [
    {
      "name": "organization or person name",
      "role": "their role in document",
      "contact": "phone, email, address if present"
    }
  ],
  "key_dates": [
    {
      "date": "the date",
      "description": "what the date represents"
    }
  ],
  "key_amounts_and_figures": [
    {
      "amount": "numeric value",
      "description": "what it represents",
      "currency": "currency if applicable"
    }
  ],
  "key_terms_and_definitions": [
    {
      "term": "term used",
      "definition": "definition or meaning in this context"
    }
  ],
  "action_items": [
    {
      "action": "action required",
      "owner": "person responsible",
      "deadline": "deadline if specified"
    }
  ],
  "file_metadata": {
    "creation_date": "when document was created",
    "modification_date": "when last modified",
    "file_size": "if visible",
    "format": "PDF, Word, etc"
  },
  "extracted_text_preview": "first 500 characters of document content"
}
"""
```

---

## Using with Application API

### Endpoint 1: Process PDF and Extract Metadata

```bash
POST /api/ocr/process-metadata
Content-Type: multipart/form-data

Parameters:
- file: The PDF file
- provider: "lmstudio" (optional, defaults to configured provider)
- metadata_type: "invoice", "contract", "form", "generic" (optional)
- custom_prompt: Custom metadata extraction prompt (optional)

Example:
curl -X POST http://localhost:5000/api/ocr/process-metadata \
  -F "file=@invoice.pdf" \
  -F "metadata_type=invoice" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Endpoint 2: Batch Process Multiple PDFs

```bash
POST /api/ocr/batch-extract-metadata
Content-Type: multipart/form-data

Parameters:
- files: Multiple PDF files
- metadata_type: Type of metadata to extract

Example:
curl -X POST http://localhost:5000/api/ocr/batch-extract-metadata \
  -F "files=@invoice1.pdf" \
  -F "files=@invoice2.pdf" \
  -F "metadata_type=invoice"
```

---

## Python Script - Complete Implementation

```python
#!/usr/bin/env python3
"""
PDF Metadata Extraction Script
Sends PDF files to LM Studio and extracts structured metadata in JSON format
"""

import json
import sys
from pathlib import Path
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider

# Predefined prompts for different document types
METADATA_PROMPTS = {
    'invoice': """You are an expert invoice analyst. Extract ALL invoice metadata and return ONLY valid JSON (no markdown, no explanations).

{
  "document_type": "invoice",
  "invoice_details": {
    "invoice_number": "the invoice number",
    "invoice_date": "the invoice date (YYYY-MM-DD format)",
    "due_date": "the due date (YYYY-MM-DD format)"
  },
  "vendor_info": {
    "vendor_name": "vendor company name",
    "vendor_address": "complete address",
    "vendor_tax_id": "tax ID or registration number"
  },
  "customer_info": {
    "customer_name": "customer name",
    "customer_address": "customer address"
  },
  "financial_summary": {
    "subtotal": "subtotal amount",
    "tax_amount": "tax amount",
    "total_amount": "total invoice amount",
    "currency": "currency code (USD, EUR, etc)"
  },
  "items": [
    {
      "description": "item description",
      "quantity": "quantity",
      "unit_price": "unit price",
      "total": "total amount"
    }
  ]
}""",

    'contract': """You are an expert contract analyst. Extract ALL contract metadata and return ONLY valid JSON (no markdown, no explanations).

{
  "document_type": "contract",
  "contract_info": {
    "contract_title": "contract title",
    "contract_date": "effective date (YYYY-MM-DD format)",
    "contract_id": "contract number or reference"
  },
  "parties": [
    {
      "party_name": "party name",
      "party_role": "party role (e.g., Vendor, Client)"
    }
  ],
  "financial_terms": {
    "total_value": "total contract value",
    "currency": "currency code",
    "payment_schedule": "payment terms description"
  },
  "key_dates": {
    "start_date": "contract start date (YYYY-MM-DD format)",
    "end_date": "contract end date (YYYY-MM-DD format)",
    "renewal_date": "renewal date if applicable (YYYY-MM-DD format)"
  },
  "signatories": [
    {
      "name": "signer name",
      "title": "signer title",
      "date_signed": "date signed (YYYY-MM-DD format)"
    }
  ]
}""",

    'generic': """You are a universal document analyzer. Extract ALL metadata from this document and return ONLY valid JSON (no markdown, no explanations).

{
  "document_metadata": {
    "document_type": "identify type: invoice, contract, letter, form, report, etc",
    "document_title": "document title if present",
    "document_date": "document date (YYYY-MM-DD format)",
    "total_pages": "number of pages"
  },
  "key_identifiers": {
    "document_number": "any document/reference number",
    "version": "version if present",
    "classification": "confidential, public, internal, etc if marked"
  },
  "parties": [
    {
      "name": "organization or person name",
      "role": "their role"
    }
  ],
  "key_amounts": [
    {
      "value": "numeric value",
      "description": "what it represents",
      "currency": "currency if applicable"
    }
  ],
  "action_items": [
    {
      "action": "action required",
      "owner": "responsible party if specified",
      "deadline": "deadline if specified (YYYY-MM-DD format)"
    }
  ]
}"""
}

def extract_metadata(pdf_path: str, metadata_type: str = 'generic', custom_prompt: str = None) -> dict:
    """
    Extract metadata from PDF using LM Studio

    Args:
        pdf_path: Path to PDF file
        metadata_type: Type of metadata ('invoice', 'contract', 'generic')
        custom_prompt: Custom extraction prompt (overrides metadata_type)

    Returns:
        Dictionary with extracted metadata
    """

    # Validate PDF exists
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {"error": f"PDF file not found: {pdf_path}"}

    if not pdf_file.suffix.lower() == '.pdf':
        return {"error": f"File is not a PDF: {pdf_path}"}

    # Initialize provider
    provider = LMStudioProvider()

    if not provider.is_available():
        return {"error": "LM Studio provider is not available. Make sure LM Studio is running."}

    # Select prompt
    prompt = custom_prompt or METADATA_PROMPTS.get(metadata_type, METADATA_PROMPTS['generic'])

    try:
        # Process PDF with metadata extraction prompt
        print(f"Processing PDF: {pdf_path}")
        print(f"Extraction type: {metadata_type}")
        print("Sending to LM Studio...")

        result = provider.process_image(
            str(pdf_file.absolute()),
            custom_prompt=prompt
        )

        # Extract and parse JSON from response
        extracted_text = result.get('text', '')

        try:
            # Try to parse as JSON
            metadata = json.loads(extracted_text)
            return {
                "status": "success",
                "pdf_file": str(pdf_file),
                "metadata_type": metadata_type,
                "metadata": metadata,
                "pages_processed": result.get('pages_processed', 1)
            }
        except json.JSONDecodeError as e:
            # If not valid JSON, return raw text
            return {
                "status": "partial",
                "pdf_file": str(pdf_file),
                "message": "Response was not valid JSON format",
                "raw_response": extracted_text[:1000],  # First 1000 chars
                "pages_processed": result.get('pages_processed', 1)
            }

    except Exception as e:
        return {
            "status": "error",
            "pdf_file": str(pdf_file),
            "error": str(e)
        }

def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("Usage: python extract_metadata.py <pdf_file> [metadata_type]")
        print("\nMetadata types: invoice, contract, generic")
        print("\nExample:")
        print("  python extract_metadata.py invoice.pdf invoice")
        print("  python extract_metadata.py contract.pdf contract")
        sys.exit(1)

    pdf_file = sys.argv[1]
    metadata_type = sys.argv[2] if len(sys.argv) > 2 else 'generic'

    # Extract metadata
    result = extract_metadata(pdf_file, metadata_type)

    # Print results
    print("\n" + "="*60)
    print("METADATA EXTRACTION RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60)

    # Save to file
    output_file = Path(pdf_file).stem + '_metadata.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nMetadata saved to: {output_file}")

if __name__ == '__main__':
    main()
```

---

## Running the Script

```bash
# Extract invoice metadata
python extract_metadata.py invoice.pdf invoice

# Extract contract metadata
python extract_metadata.py contract.pdf contract

# Extract generic metadata
python extract_metadata.py document.pdf generic

# View saved metadata
cat invoice_metadata.json
```

---

## Tips for Better Metadata Extraction

### 1. Use Specific Prompts
- Generic prompts work but specific ones are more accurate
- Tailor prompts to your document types

### 2. Ensure Valid JSON Format
- Always ask LM Studio to return ONLY valid JSON
- Add "no markdown, no explanations" to prompts
- Validate response with `json.loads()`

### 3. Handle Multi-Page PDFs
- Each page is processed separately
- Results are aggregated by page
- Add page numbers to prompt context

### 4. Validate and Clean Data
```python
def clean_metadata(metadata_dict):
    """Clean and validate extracted metadata"""
    cleaned = {}
    for key, value in metadata_dict.items():
        if isinstance(value, str):
            # Remove extra whitespace
            cleaned[key] = value.strip()
        elif isinstance(value, list):
            # Filter empty items
            cleaned[key] = [item for item in value if item]
        else:
            cleaned[key] = value
    return cleaned
```

### 5. Set Appropriate Timeout
- Complex PDFs may need more time
- Default timeout: 600 seconds
- Increase if needed: `LMSTUDIO_TIMEOUT=1200`

---

## Troubleshooting

### Problem: "LM Studio provider is not available"

**Solution**: Make sure LM Studio is running:
```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# If not running, start it
docker-compose up -d lmstudio
```

### Problem: Invalid JSON in response

**Solution**: Refine your prompt:
```python
# Add explicit instruction for JSON-only response
prompt = """
Extract metadata and return ONLY a valid JSON object.
Do not include markdown, code blocks, or any explanations.
Do not include triple backticks or language specifiers.

{
  "key": "value"
}
"""
```

### Problem: Timeout error for large PDFs

**Solution**: Increase timeout:
```bash
export LMSTUDIO_TIMEOUT=1200  # 20 minutes
python extract_metadata.py large_document.pdf
```

### Problem: Missing fields in extraction

**Solution**: Make fields optional or provide examples:
```python
prompt = """
Extract available metadata in this JSON format.
If a field is not present, use null or omit the field.

{
  "invoice_number": "if present",
  "date": "if present",
  "total": "if present"
}
"""
```

---

## Best Practices

1. **Always validate JSON responses**
   ```python
   try:
       metadata = json.loads(response)
   except json.JSONDecodeError:
       # Handle error
   ```

2. **Save extracted metadata for records**
   ```python
   with open('metadata.json', 'w') as f:
       json.dump(metadata, f, indent=2)
   ```

3. **Use appropriate document-specific prompts**
   - Invoices: Use invoice prompt
   - Contracts: Use contract prompt
   - Other documents: Use generic prompt

4. **Log operations for debugging**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info(f"Extracting metadata from {pdf_path}")
   ```

5. **Handle errors gracefully**
   ```python
   try:
       result = provider.process_image(pdf_path, custom_prompt=prompt)
   except Exception as e:
       logger.error(f"Extraction failed: {e}")
       # Return error response
   ```

---

## Summary

| Method | Use Case | Difficulty |
|--------|----------|-----------|
| **Application API** | Web-based PDF upload | Easy |
| **Python with Provider** | Script integration | Medium |
| **Direct HTTP Request** | Custom implementation | Hard |
| **Batch Processing** | Multiple files | Medium |

All methods support:
- ✅ Structured JSON metadata extraction
- ✅ Document type detection
- ✅ Multi-page PDF processing
- ✅ Custom metadata prompts
- ✅ Error handling and logging

Start with the Python provider method (Method 2) for the best balance of ease and flexibility.
