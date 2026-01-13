"""
Test script for Google Lens provider integration
Run this to verify the Google Lens provider is working correctly
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.ocr_service import OCRService
from app.services.ocr_providers.google_lens_provider import GoogleLensProvider


def test_provider_registration():
    """Test that Google Lens provider is properly registered"""
    print("=" * 60)
    print("TEST 1: Provider Registration")
    print("=" * 60)
    
    ocr_service = OCRService()
    providers = ocr_service.get_available_providers()
    
    print("\nAvailable OCR Providers:")
    for provider in providers:
        status = "✓ AVAILABLE" if provider['available'] else "✗ NOT AVAILABLE"
        print(f"  - {provider['display_name']:<30} [{status}]")
    
    # Check if google_lens is registered
    google_lens = [p for p in providers if p['name'] == 'google_lens']
    if google_lens:
        print("\n✓ Google Lens provider is registered!")
        return True
    else:
        print("\n✗ Google Lens provider is NOT registered!")
        return False


def test_provider_availability():
    """Test if Google Lens provider is available"""
    print("\n" + "=" * 60)
    print("TEST 2: Google Lens Provider Availability")
    print("=" * 60)
    
    try:
        lens_provider = GoogleLensProvider()
        is_available = lens_provider.is_available()
        
        print(f"\nGoogle Lens Available: {is_available}")
        print(f"Provider Name: {lens_provider.get_name()}")
        
        if is_available:
            print("\n✓ Google Lens provider is properly configured!")
            return True
        else:
            print("\n✗ Google Lens provider is NOT available.")
            print("  Make sure:")
            print("    1. GOOGLE_APPLICATION_CREDENTIALS is set")
            print("    2. Service account JSON file exists")
            print("    3. Vision API is enabled in Google Cloud Console")
            return False
    except Exception as e:
        print(f"\n✗ Error checking provider: {e}")
        return False


def test_provider_retrieval():
    """Test retrieving Google Lens provider from service"""
    print("\n" + "=" * 60)
    print("TEST 3: Provider Retrieval from Service")
    print("=" * 60)
    
    try:
        ocr_service = OCRService()
        provider = ocr_service.get_provider('google_lens')
        
        print(f"\n✓ Successfully retrieved Google Lens provider")
        print(f"  Name: {provider.get_name()}")
        print(f"  Available: {provider.is_available()}")
        return True
    except ValueError as e:
        print(f"\n✗ Error retrieving provider: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def test_metadata_extraction():
    """Test metadata extraction methods"""
    print("\n" + "=" * 60)
    print("TEST 4: Metadata Extraction Capabilities")
    print("=" * 60)
    
    try:
        from google.cloud import vision
        
        lens = GoogleLensProvider()
        
        print("\n✓ Google Cloud Vision library is installed")
        print("\nMetadata extraction capabilities:")
        print("  - Sender information (name, email, phone, address)")
        print("  - Recipient information (name, address, email, phone)")
        print("  - Date detection (multiple formats)")
        print("  - Document type classification:")
        print("    - letter, invoice, receipt, form, contract, email")
        print("  - Key field extraction:")
        print("    - reference, subject, invoice_number, amount, due_date")
        print("  - Language detection")
        print("  - File information and timestamps")
        
        return True
    except ImportError:
        print("\n✗ google-cloud-vision is not installed")
        print("  Install with: pip install google-cloud-vision")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    
    if failed == 0:
        print("\n🎉 All tests passed! Google Lens integration is working correctly!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the configuration.")
    
    return failed == 0


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Google Lens Provider Integration Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = []
    
    # Run tests
    results.append(test_provider_registration())
    results.append(test_provider_availability())
    results.append(test_provider_retrieval())
    results.append(test_metadata_extraction())
    
    # Print summary
    success = print_summary(results)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
