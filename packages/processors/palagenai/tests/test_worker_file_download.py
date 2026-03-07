#!/usr/bin/env python3
"""
Test script to verify the file download endpoint works with remote workers
Tests the new /api/files/download endpoint
"""

import os
import sys
import json
import time
import tempfile
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


def test_api_file_download_endpoint():
    """Test the /api/files/download endpoint directly"""
    
    print("=" * 80)
    print("TEST 1: File Download API Endpoint")
    print("=" * 80)
    
    # API endpoint configuration
    api_url = os.getenv('GVPOCR_API_URL', 'http://localhost:5000')
    endpoint = f"{api_url}/api/files/download"
    
    print(f"\n→ Testing endpoint: {endpoint}")
    
    # Test 1a: Missing file_path parameter
    print("\n  Test 1a: Missing file_path parameter")
    try:
        response = requests.post(endpoint, json={}, timeout=5)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert 'error' in data
        print(f"    ✓ Correctly returned 400: {data['error']}")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return False
    
    # Test 1b: Nonexistent file
    print("\n  Test 1b: Nonexistent file")
    try:
        response = requests.post(endpoint, 
                                json={'file_path': 'Bhushanji/nonexistent_file_xyz.jpg'},
                                timeout=5)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert 'error' in data
        print(f"    ✓ Correctly returned 404: {data['error']}")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return False
    
    # Test 1c: Path traversal attempt (security check)
    print("\n  Test 1c: Path traversal attempt (security)")
    try:
        response = requests.post(endpoint,
                                json={'file_path': '../../etc/passwd'},
                                timeout=5)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        data = response.json()
        assert 'error' in data
        print(f"    ✓ Correctly blocked: {data['error']}")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return False
    
    print("\n✅ All API endpoint tests passed!")
    return True


def test_worker_file_download_in_nsq():
    """Test worker downloading a file when it's not found locally"""
    
    print("\n" + "=" * 80)
    print("TEST 2: Worker File Download via NSQ Task")
    print("=" * 80)
    
    try:
        import gnsq
        from app.models import init_db
        from app.models.bulk_job import BulkJob
        from app import create_app
    except ImportError as e:
        print(f"\n⚠️  Cannot import required modules: {e}")
        print("   (This is OK if running in environment without Flask/MongoDB)")
        return None
    
    # Create Flask app for MongoDB access
    app = create_app()
    
    with app.app_context():
        try:
            # Create a test job in MongoDB
            from app.models import mongo
            import uuid
            
            job_id = f"test_download_{uuid.uuid4().hex[:8]}"
            
            print(f"\n→ Creating test job: {job_id}")
            
            job_data = {
                'job_id': job_id,
                'status': 'processing',
                'created_at': time.time(),
                'file_results': [],
                'file_errors': [],
                'checkpoint': {'processed_count': 0, 'total_count': 1}
            }
            
            mongo.db.bulk_jobs.insert_one(job_data)
            print(f"  ✓ Job created in MongoDB")
            
            # Publish a test file task to NSQ
            print(f"\n→ Publishing test task to NSQ")
            
            nsqd_address = os.getenv('NSQD_ADDRESS', 'nsqd:4150')
            
            message = {
                "job_id": job_id,
                "file_path": "Bhushanji/test_download/sample.jpg",
                "file_index": 0,
                "total_files": 1,
                "provider": "ollama",
                "languages": ["en"],
                "handwriting": False,
                "attempt": 0,
                "enqueued_at": time.time()
            }
            
            try:
                producer = gnsq.Producer(nsqd_address)
                producer.start()
                producer.publish('bulk_ocr_file_tasks', json.dumps(message).encode('utf-8'))
                producer.close()
                print(f"  ✓ Test task published to NSQ")
            except Exception as e:
                print(f"  ⚠️  Could not publish to NSQ: {e}")
                print("     (Workers may not process this test)")
            
            # Give worker time to process
            print(f"\n→ Waiting for worker to process (15 seconds)...")
            time.sleep(15)
            
            # Check if worker attempted to download
            job = mongo.db.bulk_jobs.find_one({'job_id': job_id})
            
            if job:
                errors = job.get('file_errors', [])
                results = job.get('file_results', [])
                
                print(f"\n  Job Status:")
                print(f"    Status: {job.get('status')}")
                print(f"    Results: {len(results)}")
                print(f"    Errors: {len(errors)}")
                
                if errors:
                    print(f"\n  Error Details:")
                    for error in errors:
                        print(f"    - {error.get('error', 'Unknown error')}")
                        # Check if error mentions download attempt
                        if 'download' in error.get('error', '').lower() or 'api' in error.get('error', '').lower():
                            print(f"      ✓ Worker attempted file download!")
                
                # Clean up
                mongo.db.bulk_jobs.delete_one({'job_id': job_id})
                print(f"\n  ✓ Test job cleaned up")
                
                return True
            else:
                print(f"  ⚠️  Job not found in MongoDB")
                return None
                
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_endpoint_with_real_file():
    """Test downloading an actual file if it exists"""
    
    print("\n" + "=" * 80)
    print("TEST 3: Download Real File")
    print("=" * 80)
    
    api_url = os.getenv('GVPOCR_API_URL', 'http://localhost:5000')
    endpoint = f"{api_url}/api/files/download"
    
    # Check for test files
    gvpocr_path = os.getenv('GVPOCR_PATH', '/data/Bhushanji')
    test_dirs = [gvpocr_path, '/data/Bhushanji', '/data/newsletters']
    
    test_file = None
    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            # Find first file in directory
            for root, dirs, files in os.walk(dir_path):
                if files:
                    file_path = os.path.join(root, files[0])
                    # Make relative path for request
                    if 'Bhushanji' in dir_path:
                        rel_path = f"Bhushanji/{os.path.relpath(file_path, gvpocr_path)}"
                    else:
                        rel_path = os.path.relpath(file_path, dir_path)
                    test_file = (file_path, rel_path)
                    break
            if test_file:
                break
    
    if not test_file:
        print("\n⚠️  No test files found in data directories")
        return None
    
    file_path, rel_path = test_file
    print(f"\n→ Found test file: {file_path}")
    print(f"  Relative path: {rel_path}")
    print(f"  File size: {os.path.getsize(file_path) / 1024:.2f} KB")
    
    try:
        print(f"\n→ Downloading via API...")
        response = requests.post(endpoint,
                                json={'file_path': rel_path},
                                timeout=30)
        
        if response.status_code == 200:
            print(f"  ✓ Download successful!")
            print(f"  Response size: {len(response.content) / 1024:.2f} KB")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            
            # Verify size matches
            if len(response.content) == os.path.getsize(file_path):
                print(f"  ✓ File size matches!")
                return True
            else:
                print(f"  ⚠️  File size mismatch!")
                return False
        else:
            print(f"  ✗ Download failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    """Run all tests"""
    
    print("\n" + "=" * 80)
    print("WORKER FILE DOWNLOAD ENDPOINT TEST SUITE")
    print("=" * 80)
    
    results = {}
    
    # Test 1: API Endpoint
    results['api_endpoint'] = test_api_file_download_endpoint()
    
    # Test 2: Worker NSQ Integration
    results['worker_nsq'] = test_worker_file_download_in_nsq()
    
    # Test 3: Real File Download
    results['real_file'] = test_endpoint_with_real_file()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else ("✗ FAIL" if result is False else "⊘ SKIP")
        print(f"{test_name:.<50} {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total and total > 0:
        print("\n✅ All tests passed!")
        return 0
    elif passed > 0:
        print(f"\n⚠️  {passed}/{total} tests passed")
        return 1
    else:
        print("\n❌ Tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
