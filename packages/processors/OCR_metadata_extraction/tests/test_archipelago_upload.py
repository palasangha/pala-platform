#!/usr/bin/env python3
"""
Test Archipelago file upload with the fixed Content-Type
"""
import os
import sys
import json
import tempfile
import requests
from pathlib import Path

# Test configuration
ARCHIPELAGO_URL = os.getenv('ARCHIPELAGO_URL', 'http://localhost:8001')
USERNAME = os.getenv('ARCHIPELAGO_USER', 'admin')
PASSWORD = os.getenv('ARCHIPELAGO_PASSWORD', 'admin')

def test_file_upload():
    """Test uploading a file to Archipelago with correct Content-Type"""
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║        Testing Archipelago File Upload (Fixed HTTP 415)        ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    # Create a session
    session = requests.Session()
    
    # Step 1: Login to get CSRF token
    print("Step 1: Logging in to Archipelago...")
    login_url = f"{ARCHIPELAGO_URL}/user/login"
    login_data = {
        'name': USERNAME,
        'pass': PASSWORD,
        'form_id': 'user_login'
    }
    
    try:
        # First, get the login form to extract CSRF token
        login_page = session.get(login_url)
        print(f"  GET {login_url} -> {login_page.status_code}")
        
        # Try to extract CSRF token from cookies
        if 'XSRF-TOKEN' in session.cookies:
            csrf_token = session.cookies['XSRF-TOKEN']
            print(f"  ✓ Got CSRF token: {csrf_token[:20]}...")
        else:
            print("  ⚠ No CSRF token in cookies, will try without")
            csrf_token = None
        
        # Attempt login
        response = session.post(login_url, data=login_data)
        print(f"  POST {login_url} -> {response.status_code}")
        
        if response.status_code not in [200, 201, 303]:
            print(f"  ❌ Login failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
        
        print("  ✓ Login successful")
        
    except Exception as e:
        print(f"  ❌ Login error: {e}")
        return False
    
    # Step 2: Create test files
    print("\nStep 2: Creating test files...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test CSV file
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write("title,description\n")
            f.write("Test Doc 1,This is a test document\n")
            f.write("Test Doc 2,Another test document\n")
        
        csv_size = os.path.getsize(csv_path)
        print(f"  Created: test.csv ({csv_size} bytes)")
        
        # Create a test ZIP file
        zip_path = os.path.join(tmpdir, "test.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file1.txt", "Test file 1 content")
            zf.writestr("file2.txt", "Test file 2 content")
        
        zip_size = os.path.getsize(zip_path)
        print(f"  Created: test.zip ({zip_size} bytes)")
        
        # Step 3: Upload CSV with application/octet-stream
        print("\nStep 3: Uploading CSV file...")
        print(f"  File: test.csv")
        print(f"  Size: {csv_size} bytes")
        print(f"  Content-Type: application/octet-stream (REQUIRED for Archipelago)")
        
        headers = {
            'Content-Type': 'application/octet-stream',  # CRITICAL FIX
            'Accept': 'application/vnd.api+json',
            'Content-Disposition': 'file; filename="test.csv"'
        }
        
        with open(csv_path, 'rb') as f:
            csv_content = f.read()
        
        try:
            response = session.post(
                f"{ARCHIPELAGO_URL}/jsonapi/file/file",
                data=csv_content,
                headers=headers,
                timeout=30
            )
            
            print(f"  Response: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                print(f"  ❌ CSV upload failed!")
                print(f"  Response text: {response.text[:300]}")
                
                # Parse JSON error if available
                try:
                    error_json = response.json()
                    if 'errors' in error_json:
                        for error in error_json['errors']:
                            print(f"  Error: {error.get('detail', 'Unknown error')}")
                except:
                    pass
                
                return False
            
            # Parse response
            result = response.json()
            csv_fid = result.get('data', {}).get('attributes', {}).get('drupal_internal__fid')
            
            if csv_fid:
                print(f"  ✓ CSV uploaded successfully!")
                print(f"  File ID (FID): {csv_fid}")
            else:
                print(f"  ❌ No FID in response: {result}")
                return False
            
        except Exception as e:
            print(f"  ❌ CSV upload error: {e}")
            return False
        
        # Step 4: Upload ZIP with application/octet-stream
        print("\nStep 4: Uploading ZIP file...")
        print(f"  File: test.zip")
        print(f"  Size: {zip_size} bytes")
        print(f"  Content-Type: application/octet-stream (REQUIRED for Archipelago)")
        
        headers = {
            'Content-Type': 'application/octet-stream',  # CRITICAL FIX
            'Accept': 'application/vnd.api+json',
            'Content-Disposition': 'file; filename="test.zip"'
        }
        
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        try:
            response = session.post(
                f"{ARCHIPELAGO_URL}/jsonapi/file/file",
                data=zip_content,
                headers=headers,
                timeout=30
            )
            
            print(f"  Response: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                print(f"  ❌ ZIP upload failed!")
                print(f"  Response text: {response.text[:300]}")
                
                # Parse JSON error if available
                try:
                    error_json = response.json()
                    if 'errors' in error_json:
                        for error in error_json['errors']:
                            print(f"  Error: {error.get('detail', 'Unknown error')}")
                except:
                    pass
                
                return False
            
            # Parse response
            result = response.json()
            zip_fid = result.get('data', {}).get('attributes', {}).get('drupal_internal__fid')
            
            if zip_fid:
                print(f"  ✓ ZIP uploaded successfully!")
                print(f"  File ID (FID): {zip_fid}")
            else:
                print(f"  ❌ No FID in response: {result}")
                return False
            
        except Exception as e:
            print(f"  ❌ ZIP upload error: {e}")
            return False
    
    print("\n" + "═" * 68)
    print("✅ ALL TESTS PASSED - Files uploaded successfully!")
    print("═" * 68)
    print(f"\nResults:")
    print(f"  CSV FID: {csv_fid}")
    print(f"  ZIP FID: {zip_fid}")
    print(f"\nContent-Type used: application/octet-stream")
    print(f"This is the ONLY Content-Type Archipelago accepts for file uploads.")
    
    return True


if __name__ == '__main__':
    try:
        success = test_file_upload()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
