#!/usr/bin/env python3
"""
Test Script - Upload Bhushanji to Archipelago using AMI Sets
Uses built-in test credentials (bhushan0508@gmail.com / abc@123)

Usage:
    python3 test_ami_upload.py [options]

Example:
    python3 test_ami_upload.py --folder eng-typed --limit 5
"""

import sys
import argparse

# Import the uploader from ami_upload_bhushanji
from ami_upload_bhushanji import ArchipelagoAMIUploader

# Test credentials (from test_archipelago_integration.sh)
TEST_EMAIL = "admin"
TEST_PASSWORD = "archipelago"
TEST_BACKEND = "http://localhost:5000"


def main():
    parser = argparse.ArgumentParser(
        description="Test AMI Sets upload with built-in test credentials"
    )
    parser.add_argument(
        "--folder",
        default="eng-typed",
        help="Folder within Bhushanji to process (default: eng-typed)"
    )
    parser.add_argument(
        "--provider",
        default="google_vision",
        help="OCR provider (default: google_vision)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process (for testing)"
    )
    parser.add_argument(
        "--skip-wait",
        action="store_true",
        help="Skip waiting for job completion"
    )
    parser.add_argument(
        "--backend",
        default=TEST_BACKEND,
        help=f"Backend URL (default: {TEST_BACKEND})"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("AMI Sets Upload - Test Mode")
    print("=" * 60)
    print(f"\nEmail:    {TEST_EMAIL}")
    print(f"Folder:   {args.folder}")
    print(f"Provider: {args.provider}")
    if args.limit:
        print(f"Limit:    {args.limit} files (test mode)")
    
    # Initialize uploader with test credentials
    uploader = ArchipelagoAMIUploader(
        backend_url=args.backend,
        email=TEST_EMAIL,
        password=TEST_PASSWORD
    )
    
    # Step 1: Authenticate
    print("\n" + "=" * 60)
    print("Step 1: Authenticating")
    print("=" * 60)
    if not uploader.authenticate():
        return 1
    
    # Step 2: Start OCR
    print("\n" + "=" * 60)
    print("Step 2: Starting OCR")
    print("=" * 60)
    job_id = uploader.start_ocr(
        folder_path=args.folder,
        provider=args.provider,
        limit=args.limit
    )
    if not job_id:
        return 1
    
    # Step 3: Wait for completion (unless skipped)
    if not args.skip_wait:
        print("\n" + "=" * 60)
        print("Step 3: Processing Files")
        print("=" * 60)
        if not uploader.wait_for_completion(job_id):
            return 1
    else:
        print(f"\nSkipping wait. Job ID: {job_id}")
        print("You can check status later with:")
        print(f"  curl http://localhost:5000/api/bulk/status/{job_id}")
    
    # Step 4: Get results
    print("\n" + "=" * 60)
    print("Step 4: Job Results")
    print("=" * 60)
    results = uploader.get_job_results(job_id)
    if not results:
        return 1
    
    # Step 5: Upload to Archipelago
    print("\n" + "=" * 60)
    print("Step 5: Upload to Archipelago")
    print("=" * 60)
    result = uploader.upload_to_archipelago(
        job_id=job_id,
        collection_title=f"Test - {args.folder}"
    )
    if not result:
        return 1
    
    # Step 6: Print summary
    print("\n" + "=" * 60)
    print("SUCCESS! ✅")
    print("=" * 60)
    uploader.print_summary(result)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
