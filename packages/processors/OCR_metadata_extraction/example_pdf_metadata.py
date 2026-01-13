#!/usr/bin/env python3
"""
Simple Example: Extract PDF Metadata using LM Studio

This example shows the easiest way to extract structured metadata from a PDF.
"""

import json
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider


# Example 1: Extract Invoice Metadata
def example_invoice_extraction():
    """Extract metadata from an invoice PDF"""

    print("\n" + "="*70)
    print("EXAMPLE 1: INVOICE METADATA EXTRACTION")
    print("="*70 + "\n")

    # Initialize the provider
    provider = LMStudioProvider()

    # Check if provider is available
    if not provider.is_available():
        print("✗ LM Studio is not running. Start it with:")
        print("  docker-compose up -d lmstudio")
        return

    # Custom prompt for invoice metadata
    invoice_prompt = """You are an invoice expert. Extract ALL invoice metadata from this image.
Return ONLY valid JSON with no explanations or markdown.

{
  "document_type": "invoice",
  "invoice_number": "the invoice number",
  "invoice_date": "the invoice date",
  "due_date": "the due date",
  "vendor_name": "vendor/supplier name",
  "vendor_address": "vendor address",
  "customer_name": "customer name",
  "customer_address": "customer address",
  "items": [
    {
      "description": "item description",
      "quantity": "quantity",
      "unit_price": "unit price",
      "total": "total amount"
    }
  ],
  "subtotal": "subtotal amount",
  "tax_amount": "tax amount",
  "total_amount": "total invoice amount",
  "currency": "currency code"
}"""

    # Process the PDF
    print("Processing invoice.pdf...")
    try:
        result = provider.process_image(
            'invoice.pdf',
            custom_prompt=invoice_prompt
        )

        # Parse the JSON response
        metadata = json.loads(result['text'])

        print("\n✓ Invoice metadata extracted:\n")
        print(json.dumps(metadata, indent=2))

        # Save to file
        with open('invoice_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        print("\n✓ Saved to invoice_metadata.json")

    except FileNotFoundError:
        print("✗ File not found: invoice.pdf")
    except json.JSONDecodeError as e:
        print(f"✗ Response was not valid JSON: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


# Example 2: Extract Contract Metadata
def example_contract_extraction():
    """Extract metadata from a contract PDF"""

    print("\n" + "="*70)
    print("EXAMPLE 2: CONTRACT METADATA EXTRACTION")
    print("="*70 + "\n")

    provider = LMStudioProvider()

    if not provider.is_available():
        print("✗ LM Studio is not running")
        return

    contract_prompt = """You are a contract expert. Extract ALL contract metadata from this image.
Return ONLY valid JSON with no explanations or markdown.

{
  "document_type": "contract",
  "contract_title": "contract title",
  "contract_date": "effective date",
  "contract_number": "contract number",
  "party_1_name": "first party name",
  "party_1_role": "first party role",
  "party_2_name": "second party name",
  "party_2_role": "second party role",
  "contract_value": "total contract value",
  "currency": "currency code",
  "start_date": "contract start date",
  "end_date": "contract end date",
  "key_obligations": "main obligations listed",
  "governing_law": "which law governs",
  "termination_clause": "how it can be terminated"
}"""

    print("Processing contract.pdf...")
    try:
        result = provider.process_image(
            'contract.pdf',
            custom_prompt=contract_prompt
        )

        metadata = json.loads(result['text'])

        print("\n✓ Contract metadata extracted:\n")
        print(json.dumps(metadata, indent=2))

        with open('contract_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        print("\n✓ Saved to contract_metadata.json")

    except FileNotFoundError:
        print("✗ File not found: contract.pdf")
    except json.JSONDecodeError as e:
        print(f"✗ Response was not valid JSON: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


# Example 3: Extract Generic Document Metadata
def example_generic_extraction(pdf_file='document.pdf'):
    """Extract metadata from any document type"""

    print("\n" + "="*70)
    print("EXAMPLE 3: GENERIC DOCUMENT METADATA EXTRACTION")
    print("="*70 + "\n")

    provider = LMStudioProvider()

    if not provider.is_available():
        print("✗ LM Studio is not running")
        return

    generic_prompt = """Analyze this document and extract ALL available metadata.
Return ONLY valid JSON with no explanations or markdown.

{
  "document_type": "identify the type (invoice, contract, letter, form, report, etc)",
  "document_title": "title if present",
  "document_date": "date on document",
  "total_pages": "number of pages",
  "main_parties": ["names of organizations/people involved"],
  "key_amounts": [
    {
      "value": "numeric value",
      "description": "what it represents"
    }
  ],
  "action_items": [
    {
      "action": "what needs to be done",
      "owner": "responsible party",
      "deadline": "deadline if specified"
    }
  ],
  "key_contacts": [
    {
      "name": "contact name",
      "role": "their role",
      "phone": "phone number",
      "email": "email address"
    }
  ]
}"""

    print(f"Processing {pdf_file}...")
    try:
        result = provider.process_image(
            pdf_file,
            custom_prompt=generic_prompt
        )

        metadata = json.loads(result['text'])

        print("\n✓ Document metadata extracted:\n")
        print(json.dumps(metadata, indent=2))

        output_file = pdf_file.replace('.pdf', '_metadata.json')
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"\n✓ Saved to {output_file}")

    except FileNotFoundError:
        print(f"✗ File not found: {pdf_file}")
    except json.JSONDecodeError as e:
        print(f"✗ Response was not valid JSON: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


# Example 4: Batch Extract from Multiple PDFs
def example_batch_extraction(pdf_files):
    """Extract metadata from multiple PDF files"""

    print("\n" + "="*70)
    print("EXAMPLE 4: BATCH METADATA EXTRACTION")
    print("="*70 + "\n")

    provider = LMStudioProvider()

    if not provider.is_available():
        print("✗ LM Studio is not running")
        return

    # Simple metadata prompt for batch processing
    simple_prompt = """Extract key metadata from this document.
Return ONLY valid JSON with no explanations.

{
  "document_type": "document type",
  "title": "document title",
  "date": "document date",
  "total_pages": "number of pages",
  "key_amount": "any monetary amount if present"
}"""

    all_metadata = []

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file}...", end=" ")

        try:
            result = provider.process_image(
                pdf_file,
                custom_prompt=simple_prompt
            )

            metadata = json.loads(result['text'])
            metadata['source_file'] = pdf_file
            all_metadata.append(metadata)

            print("✓")

        except Exception as e:
            print(f"✗ ({e})")

    # Save all results
    print("\n✓ Batch extraction complete")
    print(f"Successfully extracted from {len(all_metadata)} files\n")

    with open('batch_metadata.json', 'w') as f:
        json.dump(all_metadata, f, indent=2)
    print("✓ All results saved to batch_metadata.json")

    # Print summary
    print("\nSummary:")
    for item in all_metadata:
        print(f"  - {item.get('source_file')}: {item.get('document_type', 'unknown type')}")


# Example 5: Custom Metadata Fields
def example_custom_fields_extraction():
    """Extract specific custom fields from a document"""

    print("\n" + "="*70)
    print("EXAMPLE 5: CUSTOM FIELDS EXTRACTION")
    print("="*70 + "\n")

    provider = LMStudioProvider()

    if not provider.is_available():
        print("✗ LM Studio is not running")
        return

    # Custom prompt for specific fields
    custom_prompt = """Extract the following specific fields from this document.
If a field is not present, use null.
Return ONLY valid JSON with no explanations.

{
  "extraction_fields": {
    "id_number": "any ID, reference, or ticket number",
    "sender_name": "who sent or created this document",
    "recipient_name": "who this document is addressed to",
    "creation_date": "when was this created",
    "total_amount": "any monetary amount",
    "status": "any status indicator",
    "priority": "priority level if mentioned",
    "approver_name": "who needs to approve this",
    "deadline": "any deadline mentioned"
  }
}"""

    print("Processing document with custom fields...")
    try:
        result = provider.process_image(
            'document.pdf',
            custom_prompt=custom_prompt
        )

        metadata = json.loads(result['text'])

        print("\n✓ Custom fields extracted:\n")
        print(json.dumps(metadata, indent=2))

    except FileNotFoundError:
        print("✗ File not found: document.pdf")
    except json.JSONDecodeError as e:
        print(f"✗ Response was not valid JSON: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("PDF METADATA EXTRACTION EXAMPLES")
    print("="*70)

    # Run examples
    # Uncomment the example you want to run:

    # Example 1: Invoice
    # example_invoice_extraction()

    # Example 2: Contract
    # example_contract_extraction()

    # Example 3: Generic (any document type)
    # example_generic_extraction('your_document.pdf')

    # Example 4: Batch process multiple files
    # example_batch_extraction(['invoice.pdf', 'contract.pdf', 'form.pdf'])

    # Example 5: Custom fields
    # example_custom_fields_extraction()

    # For quick testing, run this:
    print("\nTo use these examples:")
    print("1. Uncomment the example you want to run at the bottom of this file")
    print("2. Make sure LM Studio is running: docker-compose up -d lmstudio")
    print("3. Place your PDF files in the current directory")
    print("4. Run: python example_pdf_metadata.py")

    print("\nQuick test - check provider availability:")
    provider = LMStudioProvider()
    if provider.is_available():
        print("✓ LM Studio is available and ready!")
    else:
        print("✗ LM Studio is not available. Make sure it's running at http://localhost:1234")
