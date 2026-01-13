"""
Example: Using Google Lens Provider for Letter/Document Processing
This example demonstrates how to use the Google Lens provider for
extracting text and metadata from letters and documents.
"""

from app.services.ocr_service import OCRService
import json


def example_1_process_letter():
    """
    Example 1: Basic letter processing with metadata extraction
    """
    print("Example 1: Process Letter with Metadata")
    print("=" * 50)
    
    ocr_service = OCRService()
    
    # Process a letter image
    result = ocr_service.process_image(
        image_path='uploads/sample_letter.jpg',
        provider='google_lens',
        languages=['en', 'hi']
    )
    
    # Print extracted text
    print("\nExtracted Text:")
    print(result['text'])
    
    # Print metadata
    print("\n" + "-" * 50)
    print("Metadata Extracted:")
    print("-" * 50)
    
    metadata = result['metadata']
    
    print("\nDocument Type:", metadata['document_type'])
    print("Detected Language:", metadata['language'])
    print("Processing Date:", metadata['file_info']['processed_at'])
    
    # Sender information
    sender = metadata['sender']
    if sender['name']:
        print("\nSender Information:")
        print(f"  Name: {sender['name']}")
        if sender['email']:
            print(f"  Email: {sender['email']}")
        if sender['phone']:
            print(f"  Phone: {sender['phone']}")
        if sender['address']:
            print(f"  Address: {sender['address']}")
    
    # Recipient information
    recipient = metadata['recipient']
    if recipient['name']:
        print("\nRecipient Information:")
        print(f"  Name: {recipient['name']}")
        if recipient['address']:
            print(f"  Address: {recipient['address']}")
    
    # Date
    if metadata['date']:
        print(f"\nDocument Date: {metadata['date']}")
    
    # Key fields
    if metadata['key_fields']:
        print("\nKey Fields:")
        for field, value in metadata['key_fields'].items():
            print(f"  {field}: {value}")
    
    print(f"\nConfidence Score: {result['confidence']:.2%}")


def example_2_batch_process_documents():
    """
    Example 2: Batch processing multiple documents
    """
    print("\n\nExample 2: Batch Process Multiple Documents")
    print("=" * 50)
    
    from app.models import mongo
    from app.models.image import Image
    from app.models.project import Project
    from bson import ObjectId
    
    ocr_service = OCRService()
    
    # Get project and images
    project_id = ObjectId('your_project_id')
    user_id = ObjectId('your_user_id')
    
    project = Project.find_by_id(mongo, str(project_id), user_id=str(user_id))
    images = Image.find_by_project_id(mongo, str(project_id))
    
    results = []
    
    for image in images:
        try:
            result = ocr_service.process_image(
                image_path=image['filepath'],
                provider='google_lens',
                languages=['en', 'hi']
            )
            
            # Extract key information
            metadata = result['metadata']
            
            results.append({
                'image_id': str(image['_id']),
                'filename': image['filename'],
                'document_type': metadata['document_type'],
                'sender': metadata['sender']['name'],
                'recipient': metadata['recipient']['name'],
                'date': metadata['date'],
                'confidence': result['confidence']
            })
            
            # Update database
            Image.update_ocr_text(mongo, str(image['_id']), result['text'], 'completed')
            
        except Exception as e:
            results.append({
                'image_id': str(image['_id']),
                'filename': image['filename'],
                'error': str(e)
            })
    
    # Print results
    print("\nBatch Processing Results:")
    print(json.dumps(results, indent=2, default=str))


def example_3_extract_specific_metadata():
    """
    Example 3: Extract specific metadata fields
    """
    print("\n\nExample 3: Extract Specific Metadata")
    print("=" * 50)
    
    from app.services.ocr_providers.google_lens_provider import GoogleLensProvider
    
    lens = GoogleLensProvider()
    
    result = lens.process_image(
        image_path='uploads/invoice.jpg',
        languages=['en']
    )
    
    metadata = result['metadata']
    
    # Extract invoice-specific information
    print("\nInvoice Information:")
    print(f"Document Type: {metadata['document_type']}")
    
    key_fields = metadata['key_fields']
    if 'invoice_number' in key_fields:
        print(f"Invoice #: {key_fields['invoice_number']}")
    if 'amount' in key_fields:
        print(f"Amount: {key_fields['amount']}")
    if 'due_date' in key_fields:
        print(f"Due Date: {key_fields['due_date']}")
    
    sender = metadata['sender']
    print(f"\nFrom: {sender['name']}")
    if sender['email']:
        print(f"Email: {sender['email']}")
    if sender['phone']:
        print(f"Phone: {sender['phone']}")


def example_4_compare_providers():
    """
    Example 4: Compare Google Lens with other providers
    """
    print("\n\nExample 4: Compare OCR Providers")
    print("=" * 50)
    
    ocr_service = OCRService()
    providers = ocr_service.get_available_providers()
    
    print("\nAvailable Providers:")
    for provider in providers:
        status = "✓ Available" if provider['available'] else "✗ Unavailable"
        print(f"  {provider['display_name']:<30} [{status}]")
    
    # Process with Google Lens
    image_path = 'uploads/sample_letter.jpg'
    
    print("\nProcessing with Google Lens:")
    try:
        lens_result = ocr_service.process_image(
            image_path=image_path,
            provider='google_lens'
        )
        
        print(f"  Text length: {len(lens_result['text'])} characters")
        print(f"  Confidence: {lens_result['confidence']:.2%}")
        print(f"  Metadata: {bool(lens_result.get('metadata'))}")
        print(f"  Blocks: {len(lens_result.get('blocks', []))}")
        
    except Exception as e:
        print(f"  Error: {e}")
    
    # Compare with Google Vision
    print("\nProcessing with Google Vision:")
    try:
        vision_result = ocr_service.process_image(
            image_path=image_path,
            provider='google_vision'
        )
        
        print(f"  Text length: {len(vision_result['text'])} characters")
        print(f"  Confidence: {vision_result['confidence']:.2%}")
        print(f"  Blocks: {len(vision_result.get('blocks', []))}")
        
    except Exception as e:
        print(f"  Error: {e}")


def example_5_handle_errors():
    """
    Example 5: Error handling and validation
    """
    print("\n\nExample 5: Error Handling")
    print("=" * 50)
    
    ocr_service = OCRService()
    
    # Test 1: Provider not available
    print("\n1. Handle unavailable provider:")
    try:
        provider = ocr_service.get_provider('non_existent_provider')
    except ValueError as e:
        print(f"  ✓ Caught error: {e}")
    
    # Test 2: Check if provider is available before use
    print("\n2. Check provider availability:")
    providers = ocr_service.get_available_providers()
    google_lens = next((p for p in providers if p['name'] == 'google_lens'), None)
    
    if google_lens and google_lens['available']:
        print("  ✓ Google Lens is available")
    else:
        print("  ✗ Google Lens is not available")
        print("    Please check your Google Cloud credentials")
    
    # Test 3: Handle processing errors
    print("\n3. Handle processing errors:")
    try:
        result = ocr_service.process_image(
            image_path='non_existent_file.jpg',
            provider='google_lens'
        )
    except Exception as e:
        print(f"  ✓ Caught error: {e}")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Google Lens Provider - Usage Examples")
    print("=" * 60)
    
    # Uncomment the examples you want to run:
    
    # example_1_process_letter()
    # example_2_batch_process_documents()
    # example_3_extract_specific_metadata()
    example_4_compare_providers()
    example_5_handle_errors()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")
