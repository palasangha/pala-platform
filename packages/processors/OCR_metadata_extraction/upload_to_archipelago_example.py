#!/usr/bin/env python3
"""
AMI Sets Upload to Archipelago - Python Example
This script demonstrates how to upload OCR documents from Bhushanji folder to Archipelago
using the AMI Sets workflow.

Usage:
    python3 upload_to_archipelago_example.py \
        --backend-url http://localhost:5000 \
        --email user@example.com \
        --password your_password \
        --folder eng-typed \
        --provider google_vision
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

class ArchipelagoUploader:
    """Upload OCR documents to Archipelago using AMI Sets"""
    
    def __init__(self, backend_url: str, email: str, password: str):
        """
        Initialize the uploader
        
        Args:
            backend_url: URL of GVPOCR backend (e.g., http://localhost:5000)
            email: Email for authentication
            password: Password for authentication
        """
        self.backend_url = backend_url.rstrip('/')
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self.session = requests.Session()
        
    def login(self) -> bool:
        """Authenticate and get JWT token"""
        print_info(f"Logging in as {self.email}...")
        
        try:
            response = self.session.post(
                f"{self.backend_url}/api/auth/login",
                json={
                    "email": self.email,
                    "password": self.password
                }
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('access_token')
            
            if not self.token:
                print_error("No token in response")
                return False
            
            print_success(f"Logged in successfully (token: {self.token[:20]}...)")
            return True
            
        except requests.exceptions.RequestException as e:
            print_error(f"Login failed: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def start_bulk_ocr(
        self,
        folder_path: str,
        provider: str = "google_vision",
        limit: Optional[int] = None
    ) -> Optional[str]:
        """
        Start a bulk OCR processing job
        
        Args:
            folder_path: Relative path within Bhushanji (e.g., 'eng-typed')
            provider: OCR provider ('google_vision', 'ollama', 'tesseract')
            limit: Optional limit on number of files to process
            
        Returns:
            Job ID if successful, None otherwise
        """
        print_info(f"Starting bulk OCR for folder: {folder_path}")
        print_info(f"  Provider: {provider}")
        if limit:
            print_info(f"  Limit: {limit} files")
        
        try:
            payload = {
                "folder_path": folder_path,
                "provider": provider
            }
            if limit:
                payload["limit"] = limit
            
            response = self.session.post(
                f"{self.backend_url}/api/bulk/process",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            job_id = data.get('job_id')
            
            if job_id:
                print_success(f"Bulk job started with ID: {job_id}")
                return job_id
            else:
                print_error("No job_id in response")
                return None
                
        except requests.exceptions.RequestException as e:
            print_error(f"Failed to start bulk OCR: {e}")
            return None
    
    def wait_for_job_completion(
        self,
        job_id: str,
        check_interval: int = 5,
        max_wait_time: int = 3600
    ) -> bool:
        """
        Wait for bulk job to complete
        
        Args:
            job_id: ID of the bulk job
            check_interval: How often to check status (seconds)
            max_wait_time: Maximum time to wait (seconds)
            
        Returns:
            True if completed successfully, False if failed or timeout
        """
        print_info(f"Waiting for job {job_id} to complete...")
        
        start_time = time.time()
        last_status = None
        processed_count = 0
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_time:
                print_error(f"Job timeout after {max_wait_time} seconds")
                return False
            
            try:
                response = self.session.get(
                    f"{self.backend_url}/api/bulk/status/{job_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                data = response.json()
                status = data.get('status')
                processed = data.get('processed_count', 0)
                total = data.get('total_count', 0)
                
                # Only print if status changed or new files processed
                if status != last_status or processed != processed_count:
                    last_status = status
                    processed_count = processed
                    
                    if total > 0:
                        percent = (processed / total) * 100
                        bar_length = 30
                        filled = int(bar_length * processed / total)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        print(f"  [{bar}] {processed}/{total} ({percent:.0f}%) - Status: {status}")
                    else:
                        print(f"  Status: {status}")
                
                if status == 'completed':
                    print_success(f"Job completed! {processed}/{total} files processed")
                    return True
                
                if status == 'failed':
                    error_msg = data.get('error', 'Unknown error')
                    print_error(f"Job failed: {error_msg}")
                    return False
                
                time.sleep(check_interval)
                
            except requests.exceptions.RequestException as e:
                print_error(f"Failed to check job status: {e}")
                return False
    
    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the results of a completed job
        
        Args:
            job_id: ID of the bulk job
            
        Returns:
            Job results dictionary if successful, None otherwise
        """
        print_info(f"Fetching results for job {job_id}...")
        
        try:
            response = self.session.get(
                f"{self.backend_url}/api/bulk/status/{job_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Print summary
            results = data.get('results', {})
            summary = results.get('summary', {})
            
            if summary:
                print_success("Job Results:")
                print(f"  Total files: {summary.get('total_files', 0)}")
                print(f"  Successful: {summary.get('successful', 0)}")
                print(f"  Failed: {summary.get('failed', 0)}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print_error(f"Failed to get job results: {e}")
            return None
    
    def upload_to_archipelago(
        self,
        job_id: str,
        collection_title: Optional[str] = None,
        collection_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload bulk job results to Archipelago via AMI Sets
        
        Args:
            job_id: ID of the completed bulk job
            collection_title: Title for the collection in Archipelago
            collection_id: Optional ID of existing collection to add to
            
        Returns:
            AMI Set creation result if successful, None otherwise
        """
        if not collection_title:
            collection_title = f"OCR Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print_info(f"Creating AMI Set in Archipelago...")
        print_info(f"  Collection: {collection_title}")
        if collection_id:
            print_info(f"  Collection ID: {collection_id}")
        
        try:
            payload = {
                "job_id": job_id,
                "collection_title": collection_title
            }
            if collection_id:
                payload["collection_id"] = collection_id
            
            response = self.session.post(
                f"{self.backend_url}/api/archipelago/push-bulk-ami",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                print_success("AMI Set created successfully!")
                print(f"  AMI Set ID: {data.get('ami_set_id')}")
                print(f"  Name: {data.get('ami_set_name')}")
                print(f"  Documents: {data.get('total_documents')}")
                print(f"  CSV File ID: {data.get('csv_fid')}")
                print(f"  ZIP File ID: {data.get('zip_fid')}")
                
                message = data.get('message', '')
                if 'Process it at:' in message:
                    url = message.split('Process it at: ')[1]
                    print_info(f"Processing URL: {url}")
                
                return data
            else:
                error = data.get('error', 'Unknown error')
                print_error(f"AMI Set creation failed: {error}")
                return None
                
        except requests.exceptions.RequestException as e:
            print_error(f"Failed to upload to Archipelago: {e}")
            return None
    
    def verify_files_exist(self, folder_path: str) -> bool:
        """
        Verify that files exist in the Bhushanji folder
        
        Args:
            folder_path: Path relative to Bhushanji (e.g., 'eng-typed')
            
        Returns:
            True if files exist, False otherwise
        """
        # Try common base paths
        possible_bases = [
            Path('./Bhushanji'),
            Path('/app/Bhushanji'),
            Path('/mnt/sda1/mango1_home/Bhushanji'),
            Path(os.path.expanduser('~/Bhushanji'))
        ]
        
        for base in possible_bases:
            target = base / folder_path
            if target.exists() and target.is_dir():
                files = list(target.glob('*.[pP][dD][fF]')) + \
                       list(target.glob('*.[jJ][pP][gG]')) + \
                       list(target.glob('*.[jJ][pP][eE][gG]')) + \
                       list(target.glob('*.[pP][nN][gG]'))
                
                if files:
                    print_success(f"Found folder: {target}")
                    print_success(f"Files found: {len(files)}")
                    return True
        
        print_warning(f"Could not find folder: {folder_path}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Upload OCR documents from Bhushanji to Archipelago using AMI Sets"
    )
    
    parser.add_argument(
        '--backend-url',
        default='http://localhost:5000',
        help='GVPOCR backend URL (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--email',
        required=True,
        help='Email for authentication'
    )
    parser.add_argument(
        '--password',
        required=True,
        help='Password for authentication'
    )
    parser.add_argument(
        '--folder',
        default='eng-typed',
        help='Folder within Bhushanji to process (default: eng-typed)'
    )
    parser.add_argument(
        '--provider',
        default='google_vision',
        choices=['google_vision', 'ollama', 'tesseract'],
        help='OCR provider to use (default: google_vision)'
    )
    parser.add_argument(
        '--collection-title',
        help='Custom collection title in Archipelago'
    )
    parser.add_argument(
        '--collection-id',
        type=int,
        help='Optional existing collection ID to add documents to'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to process'
    )
    parser.add_argument(
        '--skip-wait',
        action='store_true',
        help='Skip waiting for job completion'
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header("Archipelago AMI Sets Upload")
    print(f"Backend:     {args.backend_url}")
    print(f"Folder:      {args.folder}")
    print(f"Provider:    {args.provider}")
    
    # Initialize uploader
    uploader = ArchipelagoUploader(
        backend_url=args.backend_url,
        email=args.email,
        password=args.password
    )
    
    # Step 1: Verify files exist
    print_header("Step 1: Verify Files")
    if not uploader.verify_files_exist(args.folder):
        print_warning("Could not verify files, but continuing anyway...")
    
    # Step 2: Login
    print_header("Step 2: Authentication")
    if not uploader.login():
        print_error("Authentication failed. Exiting.")
        return 1
    
    # Step 3: Start bulk OCR
    print_header("Step 3: Start Bulk OCR")
    job_id = uploader.start_bulk_ocr(
        folder_path=args.folder,
        provider=args.provider,
        limit=args.limit
    )
    
    if not job_id:
        print_error("Failed to start bulk OCR. Exiting.")
        return 1
    
    # Step 4: Wait for completion
    print_header("Step 4: Processing")
    if args.skip_wait:
        print_warning("Skipping wait (use job ID to check later)")
    else:
        if not uploader.wait_for_job_completion(job_id):
            print_error("Job processing failed. Exiting.")
            return 1
    
    # Step 5: Get results
    print_header("Step 5: Job Results")
    results = uploader.get_job_results(job_id)
    if not results:
        print_error("Failed to get job results. Exiting.")
        return 1
    
    # Step 6: Upload to Archipelago
    print_header("Step 6: Upload to Archipelago")
    collection_title = args.collection_title or f"Bhushanji {args.folder} - {datetime.now().strftime('%Y-%m-%d')}"
    
    ami_result = uploader.upload_to_archipelago(
        job_id=job_id,
        collection_title=collection_title,
        collection_id=args.collection_id
    )
    
    if not ami_result:
        print_error("Failed to upload to Archipelago. Exiting.")
        return 1
    
    # Step 7: Final status
    print_header("Complete!")
    print_success(f"Upload complete! Your documents are ready in Archipelago.")
    print(f"\nNext steps:")
    print(f"1. Open the processing URL in your browser")
    print(f"2. Review the AMI Set configuration")
    print(f"3. Click 'Process' to import documents")
    print(f"4. Monitor progress in Archipelago")
    
    if 'message' in ami_result and 'Process it at:' in ami_result['message']:
        url = ami_result['message'].split('Process it at: ')[1]
        print(f"\nProcessing URL: {url}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
