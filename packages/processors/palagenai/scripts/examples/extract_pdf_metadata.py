#!/usr/bin/env python3
"""
PDF Metadata Extraction Script
Sends PDF files to LM Studio and extracts structured metadata in JSON format

Usage:
    python extract_pdf_metadata.py <pdf_file> [metadata_type] [custom_prompt_file]

Metadata types:
    - invoice: Extract invoice data (number, date, vendor, customer, amounts)
    - contract: Extract contract data (parties, dates, financial terms)
    - form: Extract form data (fields, sections, answers)
    - generic: Extract general metadata (title, date, pages, amounts, action items)
    - custom: Use custom prompt from file

Examples:
    python extract_pdf_metadata.py invoice.pdf invoice
    python extract_pdf_metadata.py contract.pdf contract
    python extract_pdf_metadata.py document.pdf generic
    python extract_pdf_metadata.py document.pdf custom custom_prompt.txt
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Predefined metadata extraction prompts for different document types
METADATA_PROMPTS = {
    'invoice': """You are an expert invoice analyst. Analyze this invoice image and extract ALL invoice metadata.
Return ONLY a valid JSON object (no markdown, no code blocks, no explanations).

{
  "document_type": "invoice",
  "invoice_details": {
    "invoice_number": "the invoice/reference number",
    "invoice_date": "the invoice date (YYYY-MM-DD format if possible)",
    "due_date": "the due date (YYYY-MM-DD format if possible)",
    "invoice_period": "the billing period if shown"
  },
  "vendor_information": {
    "vendor_name": "vendor/supplier company name",
    "vendor_address": "complete address",
    "vendor_phone": "phone number if shown",
    "vendor_email": "email address if shown",
    "vendor_tax_id": "tax ID, EIN, or registration number"
  },
  "customer_information": {
    "customer_name": "customer/purchaser name",
    "customer_address": "customer address",
    "customer_phone": "customer phone if shown",
    "customer_email": "customer email if shown",
    "customer_id": "customer reference if shown"
  },
  "line_items": [
    {
      "item_number": "item sequence number",
      "description": "product or service description",
      "quantity": "quantity ordered",
      "unit_of_measure": "unit (pieces, hours, etc)",
      "unit_price": "price per unit",
      "line_total": "quantity × unit price"
    }
  ],
  "financial_summary": {
    "subtotal": "subtotal before tax/discounts",
    "discount_amount": "discount amount if any",
    "discount_percentage": "discount percentage if any",
    "subtotal_after_discount": "subtotal after discount",
    "tax_name": "type of tax (VAT, GST, Sales Tax, etc)",
    "tax_amount": "total tax amount",
    "tax_percentage": "tax rate percentage",
    "shipping_charges": "shipping/delivery charges if any",
    "other_charges": "any other charges",
    "total_amount": "final total invoice amount",
    "amount_paid": "amount already paid if shown",
    "balance_due": "remaining balance due",
    "currency": "currency code (USD, EUR, GBP, etc)"
  },
  "payment_information": {
    "payment_terms": "payment terms (Net 30, Due Upon Receipt, etc)",
    "payment_methods_accepted": "payment methods (Bank Transfer, Credit Card, etc)",
    "bank_details": "bank account details if shown",
    "payment_instructions": "special payment instructions"
  },
  "additional_information": {
    "po_number": "purchase order number if referenced",
    "delivery_address": "delivery address if different from customer",
    "notes": "any notes, terms, or conditions",
    "late_payment_penalty": "penalty for late payment if specified"
  }
}""",

    'contract': """You are an expert contract analyst. Analyze this contract image and extract ALL contract metadata.
Return ONLY a valid JSON object (no markdown, no code blocks, no explanations).

{
  "document_type": "contract",
  "basic_information": {
    "contract_title": "contract title",
    "contract_type": "type of contract (Service Agreement, NDA, Purchase Agreement, etc)",
    "contract_number": "contract number or reference ID",
    "contract_date": "contract effective date (YYYY-MM-DD format)",
    "last_amended": "last amendment date if applicable"
  },
  "parties": [
    {
      "party_name": "legal name of party",
      "party_type": "individual/company/organization",
      "party_role": "role in contract (Service Provider, Client, Vendor, etc)",
      "address": "full address",
      "contact_person": "contact person name if shown",
      "phone": "phone number",
      "email": "email address"
    }
  ],
  "contract_scope": {
    "subject": "what the contract covers",
    "services_to_provide": ["list of services"],
    "deliverables": ["list of deliverables"],
    "geographic_scope": "geographic area covered",
    "exclusions": "what is not included"
  },
  "timeline": {
    "start_date": "contract start date (YYYY-MM-DD format)",
    "end_date": "contract end date (YYYY-MM-DD format)",
    "contract_duration": "duration in months/years",
    "renewal_terms": "automatic renewal terms if any",
    "notice_for_termination": "notice period required for termination",
    "key_milestone_dates": ["important dates in contract"]
  },
  "financial_terms": {
    "total_contract_value": "total value of contract",
    "currency": "currency code",
    "payment_schedule": "how payments are made",
    "payment_frequency": "frequency (monthly, quarterly, etc)",
    "payment_method": "method of payment",
    "late_payment_interest": "interest rate for late payments",
    "price_adjustment_terms": "how prices may be adjusted",
    "invoicing_details": "invoicing terms and procedures"
  },
  "key_obligations": {
    "party_a_obligations": ["primary party's key responsibilities"],
    "party_b_obligations": ["other party's key responsibilities"],
    "shared_obligations": ["mutual responsibilities"]
  },
  "intellectual_property": {
    "ip_ownership": "who owns intellectual property",
    "ip_created_during_contract": "ownership of IP created during term",
    "confidentiality_clause": "confidentiality terms",
    "non_disclosure_period": "duration of NDA if applicable"
  },
  "liability": {
    "liability_cap": "maximum liability amount",
    "indemnification": "indemnification clause summary",
    "warranty": "warranty terms",
    "insurance_requirements": "insurance required"
  },
  "termination": {
    "termination_for_cause": "reasons for immediate termination",
    "termination_for_convenience": "can either party terminate without cause",
    "termination_notice_period": "how much notice required",
    "survival_clauses": "what continues after termination"
  },
  "dispute_resolution": {
    "governing_law": "which jurisdiction's laws apply",
    "jurisdiction": "which court has jurisdiction",
    "arbitration_clause": "arbitration terms if any",
    "mediation_requirement": "must parties attempt mediation first"
  },
  "signatories": [
    {
      "signer_name": "name of person signing",
      "signer_title": "title/position",
      "company": "company they represent",
      "signature_date": "date signed (YYYY-MM-DD format)",
      "authorized_to_sign": "yes/no - can they legally sign"
    }
  ],
  "special_provisions": {
    "amendments": "any amendments listed",
    "exhibits_attachments": ["list of attached exhibits/exhibits"],
    "schedule_changes": "schedule of price/scope changes",
    "special_terms": "any unusual or special terms"
  }
}""",

    'form': """You are an expert form analyzer. Analyze this form image and extract ALL form data.
Return ONLY a valid JSON object (no markdown, no code blocks, no explanations).

{
  "document_type": "form",
  "form_information": {
    "form_name": "name of the form",
    "form_number": "form number or ID",
    "form_version": "version number if shown",
    "form_date": "form creation date",
    "total_pages": "total number of pages"
  },
  "form_sections": [
    {
      "section_number": "section number if shown",
      "section_title": "section heading/title",
      "section_required": "required/optional",
      "fields": [
        {
          "field_number": "field ID or number",
          "field_label": "label text for the field",
          "field_type": "type of field (text, checkbox, radio, dropdown, date, signature, etc)",
          "field_value": "the filled-in value or selected option",
          "placeholder_text": "placeholder text if shown",
          "is_required": "true/false - is field required",
          "validation_rules": "any validation rules shown (e.g., 'numbers only')"
        }
      ]
    }
  ],
  "form_completion": {
    "completed_by_name": "name of person completing form",
    "completed_by_title": "their title/position",
    "completed_by_organization": "their organization",
    "date_completed": "date form was completed (YYYY-MM-DD format)",
    "signature_present": "true/false - is form signed"
  },
  "approvals": [
    {
      "approver_name": "approver name",
      "approver_title": "approver title",
      "approval_date": "approval date (YYYY-MM-DD format)",
      "signature_present": "true/false"
    }
  ],
  "document_routing": {
    "next_step": "where form goes next",
    "submission_instructions": "how to submit the form",
    "submission_deadline": "deadline for submission if any"
  },
  "attachments": ["list of required or mentioned attachments"],
  "notes_and_instructions": ["any notes, instructions, or special requirements"]
}""",

    'generic': """You are a universal document analyzer. Analyze this document image and extract ALL available metadata.
Return ONLY a valid JSON object (no markdown, no code blocks, no explanations).

{
  "document_metadata": {
    "document_type": "identified document type (invoice, contract, letter, form, report, memo, etc)",
    "document_title": "document title or subject if present",
    "document_date": "date on document (YYYY-MM-DD format if possible)",
    "document_author": "author, creator, or issuing organization",
    "document_language": "primary language of document",
    "total_pages": "number of pages in document",
    "document_classification": "classification level (Confidential, Public, Internal, etc) if marked"
  },
  "document_identifiers": {
    "document_number": "any document number, reference number, or ID",
    "document_version": "version number if present",
    "document_revision": "revision number if present",
    "series_number": "series number if part of a series",
    "tracking_number": "tracking/case number if present"
  },
  "parties_and_contacts": [
    {
      "party_name": "name of person, company, or organization",
      "party_role": "their role in the document",
      "contact_phone": "phone number if shown",
      "contact_email": "email address if shown",
      "contact_address": "address if shown"
    }
  ],
  "key_dates": [
    {
      "date": "the date (YYYY-MM-DD format)",
      "date_description": "what the date represents (received, due, approved, etc)"
    }
  ],
  "key_monetary_amounts": [
    {
      "amount": "numeric value",
      "amount_description": "what the amount represents (total, fee, payment, etc)",
      "currency": "currency code (USD, EUR, etc)"
    }
  ],
  "key_percentages": [
    {
      "percentage": "percentage value",
      "percentage_description": "what it represents (discount, tax rate, growth, etc)"
    }
  ],
  "key_terms_and_definitions": [
    {
      "term": "key term used in document",
      "definition": "how it is defined or used in this context"
    }
  ],
  "action_items": [
    {
      "action_required": "what action is required",
      "responsible_party": "who is responsible (if specified)",
      "deadline": "deadline for action (YYYY-MM-DD format if present)",
      "priority": "priority level if indicated (High, Medium, Low)"
    }
  ],
  "requirements_and_specifications": ["list of requirements, specifications, or conditions"],
  "extracted_content_preview": "first 1000 characters of main document content"
}"""
}


def load_custom_prompt(prompt_file):
    """Load a custom prompt from a file"""
    try:
        with open(prompt_file, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Custom prompt file not found: {prompt_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading custom prompt file: {e}")
        sys.exit(1)


def extract_metadata(pdf_path, metadata_type='generic', custom_prompt=None):
    """
    Extract metadata from PDF using LM Studio provider

    Args:
        pdf_path: Path to PDF file
        metadata_type: Type of metadata ('invoice', 'contract', 'form', 'generic')
        custom_prompt: Custom extraction prompt (overrides metadata_type)

    Returns:
        Dictionary with extraction results
    """

    try:
        # Import here to avoid import errors if app context not available
        from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
    except ImportError:
        return {
            "status": "error",
            "error": "Cannot import LMStudioProvider. Make sure you're running this from the application directory."
        }

    # Validate PDF exists
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        return {
            "status": "error",
            "error": f"PDF file not found: {pdf_path}"
        }

    if not pdf_file.suffix.lower() == '.pdf':
        return {
            "status": "error",
            "error": f"File is not a PDF: {pdf_path}"
        }

    # Initialize provider
    print(f"\n{'='*70}")
    print("INITIALIZING LM STUDIO PROVIDER")
    print(f"{'='*70}")

    provider = LMStudioProvider()

    if not provider.is_available():
        return {
            "status": "error",
            "error": "LM Studio provider is not available. Make sure LM Studio is running at http://localhost:1234"
        }

    print("✓ LM Studio provider initialized and available")

    # Select prompt
    if custom_prompt:
        prompt = custom_prompt
        print(f"✓ Using custom prompt ({len(prompt)} characters)")
    else:
        prompt = METADATA_PROMPTS.get(metadata_type, METADATA_PROMPTS['generic'])
        print(f"✓ Using '{metadata_type}' metadata template")

    print(f"\n{'='*70}")
    print("PROCESSING PDF")
    print(f"{'='*70}")
    print(f"File: {pdf_file.absolute()}")
    print(f"File size: {pdf_file.stat().st_size / 1024:.1f} KB")
    print("Sending to LM Studio for metadata extraction...")

    try:
        # Process PDF with metadata extraction prompt
        result = provider.process_image(
            str(pdf_file.absolute()),
            custom_prompt=prompt
        )

        print("✓ LM Studio processing completed")

        # Extract text from response
        extracted_text = result.get('text', '')
        pages_processed = result.get('pages_processed', 1)

        print(f"✓ Extracted {len(extracted_text)} characters from {pages_processed} page(s)")

        print(f"\n{'='*70}")
        print("PARSING METADATA")
        print(f"{'='*70}")

        try:
            # Try to parse as JSON
            metadata = json.loads(extracted_text)

            print("✓ Response parsed as valid JSON")

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "pdf_file": str(pdf_file.absolute()),
                "pdf_file_size_kb": pdf_file.stat().st_size / 1024,
                "metadata_type": metadata_type,
                "pages_processed": pages_processed,
                "metadata": metadata,
                "raw_response_length": len(extracted_text)
            }

        except json.JSONDecodeError as e:
            # If not valid JSON, return raw text with note
            print(f"⚠ Response was not valid JSON: {str(e)}")
            print("Returning raw response instead...")

            return {
                "status": "partial",
                "timestamp": datetime.now().isoformat(),
                "pdf_file": str(pdf_file.absolute()),
                "pdf_file_size_kb": pdf_file.stat().st_size / 1024,
                "metadata_type": metadata_type,
                "pages_processed": pages_processed,
                "message": "Response was not in valid JSON format. Raw response provided.",
                "parse_error": str(e),
                "raw_response": extracted_text,
                "response_length": len(extracted_text)
            }

    except Exception as e:
        print(f"✗ Error during processing: {str(e)}")

        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "pdf_file": str(pdf_file.absolute()),
            "metadata_type": metadata_type,
            "error": str(e)
        }


def print_result(result):
    """Pretty print the extraction result"""

    print(f"\n{'='*70}")
    print("EXTRACTION RESULT")
    print(f"{'='*70}\n")

    # Print status
    status = result.get('status', 'unknown')
    status_symbol = '✓' if status == 'success' else ('⚠' if status == 'partial' else '✗')
    print(f"{status_symbol} Status: {status.upper()}")

    # Print metadata info
    if 'pdf_file' in result:
        print(f"  File: {result['pdf_file']}")
    if 'pdf_file_size_kb' in result:
        print(f"  Size: {result['pdf_file_size_kb']:.1f} KB")
    if 'metadata_type' in result:
        print(f"  Type: {result['metadata_type']}")
    if 'pages_processed' in result:
        print(f"  Pages: {result['pages_processed']}")

    # Print error if present
    if 'error' in result:
        print(f"\n✗ Error: {result['error']}")
        return

    # Print metadata if present
    if 'metadata' in result and isinstance(result['metadata'], dict):
        print(f"\n📄 EXTRACTED METADATA:\n")
        print(json.dumps(result['metadata'], indent=2))

    # Print raw response if metadata parsing failed
    if 'raw_response' in result and status == 'partial':
        print(f"\n📝 RAW RESPONSE:\n")
        print(result['raw_response'])

    print(f"\n{'='*70}\n")


def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_file = sys.argv[1]
    metadata_type = sys.argv[2] if len(sys.argv) > 2 else 'generic'
    custom_prompt = None

    # Load custom prompt if specified
    if metadata_type == 'custom' and len(sys.argv) > 3:
        custom_prompt_file = sys.argv[3]
        custom_prompt = load_custom_prompt(custom_prompt_file)

    # Validate metadata type
    if metadata_type not in METADATA_PROMPTS and metadata_type != 'custom':
        print(f"Invalid metadata type: {metadata_type}")
        print(f"Valid types: {', '.join(METADATA_PROMPTS.keys())}")
        sys.exit(1)

    # Extract metadata
    result = extract_metadata(pdf_file, metadata_type, custom_prompt)

    # Print results
    print_result(result)

    # Save to file
    output_file = Path(pdf_file).stem + '_metadata.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"📁 Results saved to: {output_file}\n")


if __name__ == '__main__':
    main()
