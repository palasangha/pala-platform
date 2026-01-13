#!/usr/bin/env python3
"""
Test script for image resize functionality in Google Lens provider
"""
import os
import sys
from PIL import Image
import io

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image(size_mb, filename):
    """Create a test image of approximately the given size in MB"""
    # Approximate dimensions for target file size
    # A 24-bit RGB image has 3 bytes per pixel
    target_bytes = size_mb * 1024 * 1024
    pixels_needed = target_bytes // 3

    # Square image dimensions
    dimension = int(pixels_needed ** 0.5)

    print(f"Creating test image: {dimension}x{dimension} (~{size_mb}MB)")

    # Create a gradient image
    img = Image.new('RGB', (dimension, dimension))
    pixels = img.load()

    for i in range(dimension):
        for j in range(dimension):
            # Create a gradient pattern
            r = int((i / dimension) * 255)
            g = int((j / dimension) * 255)
            b = int(((i + j) / (2 * dimension)) * 255)
            pixels[i, j] = (r, g, b)

    # Save as JPEG
    img.save(filename, 'JPEG', quality=95)
    actual_size = os.path.getsize(filename) / (1024 * 1024)
    print(f"Created {filename}: {actual_size:.2f}MB")
    return filename

def test_resize_logic():
    """Test the resize logic from google_lens_provider"""
    from app.services.ocr_providers.google_lens_provider import GoogleLensProvider

    # Create test directory
    test_dir = '/tmp/gvpocr_resize_test'
    os.makedirs(test_dir, exist_ok=True)

    # Test 1: Small image (should not be resized)
    print("\n=== Test 1: Small image (2MB) ===")
    small_image = create_test_image(2, os.path.join(test_dir, 'small_test.jpg'))

    provider = GoogleLensProvider()
    if provider.is_available():
        content = provider._resize_image_if_needed(small_image, max_size_mb=5)
        result_size = len(content) / (1024 * 1024)
        print(f"Result size: {result_size:.2f}MB (should be ~2MB, no resize)")
    else:
        print("Google Lens provider not available, testing resize logic only")
        with open(small_image, 'rb') as f:
            original_size = len(f.read()) / (1024 * 1024)
            print(f"Original size: {original_size:.2f}MB")

    # Test 2: Large image (should be resized)
    print("\n=== Test 2: Large image (8MB) ===")
    large_image = create_test_image(8, os.path.join(test_dir, 'large_test.jpg'))

    if provider.is_available():
        content = provider._resize_image_if_needed(large_image, max_size_mb=5)
        result_size = len(content) / (1024 * 1024)
        print(f"Result size: {result_size:.2f}MB (should be <5MB, resized)")

        # Verify content is valid JPEG
        try:
            img = Image.open(io.BytesIO(content))
            print(f"Resized image dimensions: {img.size}")
            print(f"Resized image format: {img.format}")
        except Exception as e:
            print(f"Error validating resized image: {e}")
    else:
        print("Google Lens provider not available")

    # Test 3: Very large image (should be heavily compressed)
    print("\n=== Test 3: Very large image (15MB) ===")
    huge_image = create_test_image(15, os.path.join(test_dir, 'huge_test.jpg'))

    if provider.is_available():
        content = provider._resize_image_if_needed(huge_image, max_size_mb=5)
        result_size = len(content) / (1024 * 1024)
        print(f"Result size: {result_size:.2f}MB (should be <5MB, heavily resized)")
    else:
        print("Google Lens provider not available")

    print(f"\n=== Test complete ===")
    print(f"Test files located in: {test_dir}")

    # Cleanup option
    cleanup = input("\nDelete test files? (y/n): ").strip().lower()
    if cleanup == 'y':
        import shutil
        shutil.rmtree(test_dir)
        print("Test files deleted")

if __name__ == '__main__':
    test_resize_logic()
