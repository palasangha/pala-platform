"""
Complete Examples for SerpAPI Google Lens Provider
Demonstrates OCR with Hindi and English support for typed and handwritten letters
"""

from app.services.ocr_service import OCRService
import json
from datetime import datetime


def example_1_basic_english_letter():
    """
    Example 1: Process a basic English typed letter
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic English Letter Processing")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/english_letter.jpg',
        provider='serpapi_google_lens',
        languages=['en']  # English only
    )
    
    print(f"\n✓ Processing Complete!")
    print(f"\nExtracted Text:")
    print(f"{result['text'][:200]}...")
    
    print(f"\nDocument Metadata:")
    metadata = result['metadata']
    print(f"  From: {metadata['sender']['name']}")
    print(f"  Email: {metadata['sender']['email']}")
    print(f"  To: {metadata['recipient']['name']}")
    print(f"  Date: {metadata['date']}")
    print(f"  Type: {metadata['document_type']}")
    print(f"  Confidence: {result['confidence']:.2%}")


def example_2_hindi_letter():
    """
    Example 2: Process a Hindi letter (Hindi text only)
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Hindi Letter Processing")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/hindi_letter.jpg',
        provider='serpapi_google_lens',
        languages=['hi']  # Hindi only
    )
    
    print(f"\n✓ Processing Complete!")
    print(f"\nExtracted Text (Hindi):")
    print(f"{result['text'][:200]}...")
    
    print(f"\nLanguage Detection:")
    print(f"  Detected Language: {result['detected_language']}")
    print(f"  Supported Languages: {result['supported_languages']}")
    
    metadata = result['metadata']
    print(f"\nDocument Type: {metadata['document_type']}")


def example_3_hinglish_mixed_language():
    """
    Example 3: Process a document with mixed Hindi and English (Hinglish)
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Hinglish (Hindi + English) Document")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/hinglish_letter.jpg',
        provider='serpapi_google_lens',
        languages=['en', 'hi']  # Both languages
    )
    
    print(f"\n✓ Processing Complete!")
    print(f"\nExtracted Text:")
    print(f"{result['text'][:300]}...")
    
    print(f"\nLanguage Analysis:")
    detected = result.get('detected_language')
    print(f"  Detected: {detected}")
    
    hinglish = result['metadata'].get('hinglish_content', {})
    print(f"  Is Hinglish: {hinglish.get('is_hinglish', False)}")
    print(f"  Hindi Content: {hinglish.get('hindi_content_ratio', 0):.1%}")
    print(f"  English Content: {hinglish.get('english_content_ratio', 0):.1%}")


def example_4_handwritten_letter():
    """
    Example 4: Process a handwritten letter
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Handwritten Letter Recognition")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/handwritten_letter.jpg',
        provider='serpapi_google_lens',
        languages=['en', 'hi'],
        handwriting=True  # Explicitly enable handwriting detection
    )
    
    print(f"\n✓ Processing Complete!")
    print(f"\nHandwriting Detection:")
    print(f"  Detected: {result['file_info'].get('handwriting_detected', False)}")
    
    print(f"\nExtracted Text:")
    print(f"{result['text'][:300]}...")
    
    print(f"\nWord-level Confidence:")
    for word in result['words'][:10]:
        print(f"  '{word['text']}': {word['confidence']:.2%}")
    
    print(f"\nMetadata:")
    metadata = result['metadata']
    print(f"  Document Type: {metadata['document_type']}")
    print(f"  From: {metadata['sender']['name']}")
    print(f"  Language: {metadata['language']}")


def example_5_metadata_extraction():
    """
    Example 5: Comprehensive metadata extraction from a business letter
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Complete Metadata Extraction")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/business_letter.jpg',
        provider='serpapi_google_lens',
        languages=['en', 'hi']
    )
    
    print(f"\n✓ Processing Complete!")
    
    metadata = result['metadata']
    
    print(f"\nSender Information:")
    sender = metadata['sender']
    print(f"  Name: {sender['name']}")
    print(f"  Email: {sender['email']}")
    print(f"  Phone: {sender['phone']}")
    print(f"  Address: {sender['address']}")
    
    print(f"\nRecipient Information:")
    recipient = metadata['recipient']
    print(f"  Name: {recipient['name']}")
    print(f"  Address: {recipient['address']}")
    print(f"  Email: {recipient['email']}")
    print(f"  Phone: {recipient['phone']}")
    
    print(f"\nDocument Details:")
    print(f"  Type: {metadata['document_type']}")
    print(f"  Date: {metadata['date']}")
    print(f"  Language: {metadata['language']}")
    
    print(f"\nKey Fields:")
    for field, value in metadata['key_fields'].items():
        print(f"  {field}: {value}")
    
    print(f"\nProcessing Info:")
    print(f"  File: {result['file_info']['filename']}")
    print(f"  Processed: {result['file_info']['processed_at']}")
    print(f"  Overall Confidence: {result['confidence']:.2%}")


def example_6_batch_processing():
    """
    Example 6: Batch process multiple letters
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Batch Processing Multiple Letters")
    print("="*60)
    
    import os
    from pathlib import Path
    
    service = OCRService()
    
    # Get list of image files
    uploads_dir = Path('uploads')
    image_files = list(uploads_dir.glob('*.jpg')) + list(uploads_dir.glob('*.png'))
    
    results_summary = []
    
    for image_file in image_files[:5]:  # Process first 5 images
        print(f"\nProcessing: {image_file.name}...", end=' ')
        
        try:
            result = service.process_image(
                image_path=str(image_file),
                provider='serpapi_google_lens',
                languages=['en', 'hi'],
                handwriting=True
            )
            
            summary = {
                'filename': image_file.name,
                'text_length': len(result['text']),
                'language': result.get('detected_language'),
                'sender': result['metadata']['sender']['name'],
                'date': result['metadata']['date'],
                'document_type': result['metadata']['document_type'],
                'confidence': result['confidence']
            }
            
            results_summary.append(summary)
            print(f"✓ Success")
            
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
    
    # Display summary
    print(f"\n\nBatch Processing Summary:")
    print(f"-" * 80)
    for summary in results_summary:
        print(f"File: {summary['filename']}")
        print(f"  Text: {summary['text_length']} chars | Language: {summary['language']}")
        print(f"  From: {summary['sender']} | Date: {summary['date']}")
        print(f"  Type: {summary['document_type']} | Confidence: {summary['confidence']:.2%}")
        print()


def example_7_provider_comparison():
    """
    Example 7: Compare results from different OCR providers
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: Provider Comparison")
    print("="*60)
    
    service = OCRService()
    image_path = 'uploads/test_letter.jpg'
    
    providers_to_compare = [
        'serpapi_google_lens',
        'google_lens',
        'google_vision'
    ]
    
    comparison_results = {}
    
    for provider_name in providers_to_compare:
        print(f"\nProcessing with {provider_name}...", end=' ')
        
        try:
            result = service.process_image(
                image_path=image_path,
                provider=provider_name,
                languages=['en', 'hi']
            )
            
            comparison_results[provider_name] = {
                'status': '✓ Success',
                'text_length': len(result['text']),
                'confidence': result['confidence'],
                'language': result.get('detected_language', 'N/A'),
                'blocks': len(result['blocks']),
                'words': len(result['words'])
            }
            print('✓')
            
        except Exception as e:
            comparison_results[provider_name] = {
                'status': f'✗ Error: {str(e)[:30]}...',
            }
            print('✗')
    
    # Display comparison
    print(f"\n\nComparison Results:")
    print(f"-" * 100)
    print(f"{'Provider':<25} {'Status':<20} {'Text Length':<15} {'Confidence':<12} {'Language':<10}")
    print(f"-" * 100)
    
    for provider, results in comparison_results.items():
        status = results.get('status', 'N/A')
        text_len = results.get('text_length', 'N/A')
        confidence = f"{results.get('confidence', 0):.2%}" if isinstance(results.get('confidence'), float) else 'N/A'
        language = results.get('language', 'N/A')
        print(f"{provider:<25} {status:<20} {str(text_len):<15} {confidence:<12} {language:<10}")


def example_8_error_handling():
    """
    Example 8: Proper error handling and fallback strategies
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: Error Handling & Fallback")
    print("="*60)
    
    service = OCRService()
    image_path = 'uploads/test_letter.jpg'
    
    # List of providers in order of preference
    providers = ['serpapi_google_lens', 'google_lens', 'google_vision', 'tesseract']
    
    result = None
    used_provider = None
    
    for provider_name in providers:
        print(f"\nTrying provider: {provider_name}...", end=' ')
        
        try:
            result = service.process_image(
                image_path=image_path,
                provider=provider_name,
                languages=['en', 'hi']
            )
            used_provider = provider_name
            print(f"✓ Success!")
            break
            
        except Exception as e:
            print(f"✗ Failed ({str(e)[:40]}...)")
            continue
    
    if result:
        print(f"\n✓ Processing completed with: {used_provider}")
        print(f"\nResults:")
        print(f"  Text: {result['text'][:150]}...")
        print(f"  Language: {result.get('detected_language', 'unknown')}")
        print(f"  Confidence: {result['confidence']:.2%}")
    else:
        print(f"\n✗ All providers failed. Please check:")
        print(f"  1. API keys are configured")
        print(f"  2. Image file exists: {image_path}")
        print(f"  3. Internet connection is active")


def example_9_hindi_documents():
    """
    Example 9: Specialized handling for Hindi documents
    """
    print("\n" + "="*60)
    print("EXAMPLE 9: Hindi Document Processing")
    print("="*60)
    
    service = OCRService()
    
    # Document types common in Hindi
    hindi_documents = {
        'official_letter': 'uploads/hindi_official_letter.jpg',
        'invoice': 'uploads/hindi_invoice.jpg',
        'form': 'uploads/hindi_form.jpg'
    }
    
    for doc_type, image_path in hindi_documents.items():
        print(f"\nProcessing: {doc_type}...", end=' ')
        
        try:
            result = service.process_image(
                image_path=image_path,
                provider='serpapi_google_lens',
                languages=['hi', 'en']  # Prefer Hindi first
            )
            
            print(f"✓")
            print(f"  Detected Language: {result['detected_language']}")
            print(f"  Document Type: {result['metadata']['document_type']}")
            
            # Show Hindi-specific metadata
            hinglish = result['metadata'].get('hinglish_content', {})
            if hinglish['is_hinglish']:
                print(f"  Content: Hinglish (Hindi {hinglish.get('hindi_content_ratio', 0):.0%} + English {hinglish.get('english_content_ratio', 0):.0%})")
            else:
                print(f"  Content: Pure Hindi")
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")


def example_10_save_results():
    """
    Example 10: Save and export OCR results to JSON
    """
    print("\n" + "="*60)
    print("EXAMPLE 10: Save Results to JSON")
    print("="*60)
    
    service = OCRService()
    
    result = service.process_image(
        image_path='uploads/letter.jpg',
        provider='serpapi_google_lens',
        languages=['en', 'hi']
    )
    
    # Prepare data for JSON export
    export_data = {
        'processing_timestamp': datetime.now().isoformat(),
        'provider': result['provider'],
        'text': result['text'],
        'full_text': result['full_text'],
        'metadata': result['metadata'],
        'language_detected': result.get('detected_language'),
        'confidence': result['confidence'],
        'file_info': result['file_info'],
        'statistics': {
            'text_length': len(result['text']),
            'blocks_count': len(result['blocks']),
            'words_count': len(result['words']),
            'lines_count': len(result['text'].split('\n'))
        }
    }
    
    # Save to file
    output_file = 'ocr_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    print(f"\nExported Data:")
    print(json.dumps(export_data, ensure_ascii=False, indent=2)[:500] + "...")


def main():
    """
    Run all examples
    """
    print("\n" + "="*60)
    print("SerpAPI Google Lens Provider - Complete Examples")
    print("="*60)
    
    examples = [
        ("Basic English Letter", example_1_basic_english_letter),
        ("Hindi Letter Processing", example_2_hindi_letter),
        ("Hinglish Mixed Language", example_3_hinglish_mixed_language),
        ("Handwritten Recognition", example_4_handwritten_letter),
        ("Metadata Extraction", example_5_metadata_extraction),
        ("Batch Processing", example_6_batch_processing),
        ("Provider Comparison", example_7_provider_comparison),
        ("Error Handling", example_8_error_handling),
        ("Hindi Documents", example_9_hindi_documents),
        ("Save to JSON", example_10_save_results),
    ]
    
    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n" + "="*60)
    print("Note: Modify image paths in examples to match your files")
    print("="*60)


if __name__ == '__main__':
    main()
    
    # Uncomment to run specific examples:
    # example_1_basic_english_letter()
    # example_2_hindi_letter()
    # example_3_hinglish_mixed_language()
    # example_4_handwritten_letter()
    # example_5_metadata_extraction()
    # example_6_batch_processing()
    # example_7_provider_comparison()
    # example_8_error_handling()
    # example_9_hindi_documents()
    # example_10_save_results()
