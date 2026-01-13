#!/usr/bin/env python3
"""
Upload files from ./Bhushanji folder to Archipelago using AMI Sets
Simple, practical script with minimal dependencies
"""

import requests
import time
import sys
import os
from pathlib import Path
from datetime import datetime

class ArchipelagoAMIUploader:
    def __init__(self, backend_url="http://localhost:5000", email=None, password=None):
        self.backend_url = backend_url.rstrip('/')
        self.email = email
        self.password = password
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self):
        """Login and get authentication token"""
        print("\n[1/5] Authenticating...")
        print(f"     Email: {self.email}")
        print(f"     Backend: {self.backend_url}/api/auth/login")
        try:
            resp = self.session.post(f"{self.backend_url}/api/auth/login", json={
                "email": self.email,
                "password": self.password
            })
            print(f"     Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"     Response body: {resp.text}")
            resp.raise_for_status()
            self.token = resp.json()['access_token']
            print(f"✅ Authenticated (token: {self.token[:20]}...)")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print(f"     Tip: Make sure the user exists. Register with:")
            print(f"     curl -X POST {self.backend_url}/api/auth/register \\")
            print(f'       -H "Content-Type: application/json" \\')
            print(f'       -d \'{{"email": "{self.email}", "password": "YOUR_PASSWORD", "name": "Your Name"}}\'')
            return False
    
    def get_headers(self):
        """Get HTTP headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def start_ocr(self, folder_path, provider="google_vision", limit=None):
        """Start bulk OCR processing on folder"""
        print(f"\n[2/5] Starting OCR on folder: {folder_path}")
        print(f"     Provider: {provider}")
        if limit:
            print(f"     Limit: {limit} files")

        try:
            payload = {
                "folder_path": folder_path,
                "provider": provider
            }
            if limit:
                payload["limit"] = limit

            print(f"     Sending request to: {self.backend_url}/api/bulk/process")
            resp = self.session.post(
                f"{self.backend_url}/api/bulk/process",
                json=payload,
                headers=self.get_headers()
            )

            if resp.status_code != 200:
                print(f"     Response status: {resp.status_code}")
                print(f"     Response body: {resp.text}")

            resp.raise_for_status()
            job_id = resp.json()['job_id']
            print(f"✅ OCR job started (ID: {job_id})")
            return job_id
        except Exception as e:
            print(f"❌ Failed to start OCR: {e}")
            return None
    
    def wait_for_completion(self, job_id, check_interval=5):
        """Wait for OCR job to complete"""
        print(f"\n[3/5] Processing files...")
        
        try:
            while True:
                resp = self.session.get(
                    f"{self.backend_url}/api/bulk/status/{job_id}",
                    headers=self.get_headers()
                )
                resp.raise_for_status()
                
                data = resp.json()
                status = data.get('status')
                processed = data.get('processed_count', 0)
                total = data.get('total_count', 0)
                
                if total > 0:
                    percent = (processed / total) * 100
                    bar_length = 20
                    filled = int(bar_length * processed / total)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"     [{bar}] {processed}/{total} ({percent:.0f}%)", end='\r')
                
                if status == 'completed':
                    print(f"\n✅ OCR completed ({processed}/{total} files)")
                    return True
                
                if status == 'failed':
                    print(f"\n❌ OCR failed: {data.get('error', 'Unknown error')}")
                    return False
                
                time.sleep(check_interval)
        except Exception as e:
            print(f"\n❌ Error checking status: {e}")
            return False
    
    def upload_to_archipelago(self, job_id, collection_title=None):
        """Upload OCR results to Archipelago via AMI Sets"""
        print(f"\n[4/5] Creating AMI Set in Archipelago...")
        
        if not collection_title:
            collection_title = f"OCR Upload - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"     Collection: {collection_title}")
        
        try:
            resp = self.session.post(
                f"{self.backend_url}/api/archipelago/push-bulk-ami",
                json={
                    "job_id": job_id,
                    "collection_title": collection_title
                },
                headers=self.get_headers()
            )
            resp.raise_for_status()
            
            result = resp.json()
            
            if result.get('success'):
                ami_id = result['ami_set_id']
                total_docs = result['total_documents']
                csv_fid = result.get('csv_fid')
                zip_fid = result.get('zip_fid')
                
                print(f"✅ AMI Set created successfully!")
                print(f"     AMI Set ID: {ami_id}")
                print(f"     Documents: {total_docs}")
                print(f"     CSV File ID: {csv_fid}")
                print(f"     ZIP File ID: {zip_fid}")
                
                return result
            else:
                print(f"❌ AMI Set creation failed: {result.get('error')}")
                return None
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return None
    
    def print_summary(self, result):
        """Print final summary"""
        print(f"\n[5/5] Summary")
        print("=" * 60)
        print(f"✅ SUCCESS! Your files are ready in Archipelago")
        print("=" * 60)
        
        ami_id = result['ami_set_id']
        message = result.get('message', '')
        
        if 'Process it at:' in message:
            url = message.split('Process it at: ')[1]
        else:
            url = f"http://localhost:8001/amiset/{ami_id}/process"
        
        print(f"\nProcessing URL: {url}")
        print(f"\nNext steps:")
        print(f"1. Open the URL above in your browser")
        print(f"2. Review the AMI Set configuration")
        print(f"3. Click the 'Process' tab")
        print(f"4. Choose 'Process via Queue' (recommended)")
        print(f"5. Monitor progress in Archipelago")
        print(f"\nView your documents at:")
        print(f"  http://localhost:8001/admin/content")


def verify_bhushanji_folder(folder_name="eng-typed"):
    """Verify that the Bhushanji folder exists and has files"""
    print("Verifying Bhushanji folder...")

    possible_paths = [
        Path("./Bhushanji") / folder_name,
        Path("/app/Bhushanji") / folder_name,
        Path("/mnt/sda1/mango1_home/Bhushanji") / folder_name,
        Path.home() / "Bhushanji" / folder_name,
    ]

    for path in possible_paths:
        if path.exists() and path.is_dir():
            # Count files
            files = list(path.glob('*.[pP][dD][fF]')) + \
                   list(path.glob('*.[jJ][pP][gG]')) + \
                   list(path.glob('*.[jJ][pP][eE][gG]')) + \
                   list(path.glob('*.[pP][nN][gG]'))

            if files:
                print(f"✅ Found folder: {path}")
                print(f"✅ Files found: {len(files)}")
                return str(path.absolute())  # Return absolute path

    print(f"⚠️  Could not find {folder_name} folder in Bhushanji")
    print(f"    Make sure you have files in: ./Bhushanji/{folder_name}/")
    return None  # Return None instead of False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload files from Bhushanji folder to Archipelago using AMI Sets"
    )
    parser.add_argument("--email", required=True, help="Email for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--folder", default="eng-typed", help="Folder within Bhushanji (default: eng-typed)")
    parser.add_argument("--provider", default="google_vision", help="OCR provider (default: google_vision)")
    parser.add_argument("--backend", default="http://localhost:5000", help="Backend URL")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")
    parser.add_argument("--collection-title", help="Custom collection title")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Upload Bhushanji to Archipelago via AMI Sets")
    print("=" * 60)

    # Verify folder exists and get absolute path
    folder_absolute_path = verify_bhushanji_folder(args.folder)
    if not folder_absolute_path:
        print("❌ Error: Could not find folder. Exiting.")
        return 1

    # Initialize uploader
    uploader = ArchipelagoAMIUploader(
        backend_url=args.backend,
        email=args.email,
        password=args.password
    )

    # Step 1: Authenticate
    if not uploader.authenticate():
        return 1

    # Step 2: Start OCR (use absolute path)
    # # job_id = uploader.start_ocr(
    # #     folder_path=folder_absolute_path,
    # #     provider=args.provider,
    # #     limit=args.limit
    # # )
    # if not job_id:
    #     return 1
    
    # Step 3: Wait for completion
    # if not uploader.wait_for_completion(job_id):
    #     return 1
    
    # Step 4: Upload to Archipelago
    collection_title = args.collection_title or f"Bhushanji {args.folder} - {datetime.now().strftime('%Y-%m-%d')}"
    result = uploader.upload_to_archipelago("1", collection_title)
    if not result:
        return 1
    
    # Step 5: Print summary
    uploader.print_summary(result)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
