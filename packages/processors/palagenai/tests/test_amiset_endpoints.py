#!/usr/bin/env python3
"""
Test script for new Archipelago AMI Set endpoints

This script demonstrates how to use the three new endpoints:
1. POST /api/archipelago/amiset/add - Create and upload AMI Set from OCR data
2. GET /api/archipelago/amiset/status/<ami_set_id> - Get AMI Set status
3. POST /api/archipelago/amiset/process/<ami_set_id> - Process AMI Set
"""

import requests
import json
import argparse
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api"


class ArcipelagoAMIClient:
    """Client for Archipelago AMI Set endpoints"""

    def __init__(self, auth_token=None):
        self.auth_token = auth_token
        self.headers = {
            'Content-Type': 'application/json',
        }
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'

    def _make_request(self, method, endpoint, data=None):
        """Make HTTP request with proper headers"""
        url = f"{API_URL}{endpoint}"
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)

            return response
        except Exception as e:
            print(f"Error making {method} request to {url}: {e}")
            return None

    def add_amiset(self, ocr_data_list, collection_title=None, collection_id=None):
        """
        Create and upload an AMI Set to Archipelago

        Args:
            ocr_data_list: List of OCR data dictionaries
            collection_title: Optional collection name
            collection_id: Optional existing collection ID

        Returns:
            Dictionary with result or None on error
        """
        payload = {
            'ocr_data': ocr_data_list,
            'collection_title': collection_title,
            'collection_id': collection_id
        }

        print("\n" + "="*60)
        print("Creating AMI Set from OCR data...")
        print("="*60)
        print(f"Documents: {len(ocr_data_list)}")
        if collection_title:
            print(f"Collection: {collection_title}")
        print()

        response = self._make_request('POST', '/archipelago/amiset/add', payload)

        if response and response.status_code in [200, 201]:
            result = response.json()
            if result.get('success'):
                print("✓ AMI Set created successfully!")
                print(f"  AMI Set ID: {result.get('ami_set_id')}")
                print(f"  AMI Set Name: {result.get('ami_set_name')}")
                print(f"  CSV File ID: {result.get('csv_fid')}")
                print(f"  ZIP File ID: {result.get('zip_fid')}")
                print(f"  Total Documents: {result.get('total_documents')}")
                print(f"\n  {result.get('message')}")
                return result
            else:
                print(f"✗ Failed to create AMI Set")
                print(f"  Error: {result.get('error')}")
                return None
        else:
            print(f"✗ Request failed")
            if response:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text}")
            return None

    def get_status(self, ami_set_id):
        """Get AMI Set status"""
        print("\n" + "="*60)
        print(f"Getting status for AMI Set: {ami_set_id}")
        print("="*60 + "\n")

        response = self._make_request('GET', f'/archipelago/amiset/status/{ami_set_id}', None)

        if response and response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✓ Status retrieved successfully!")
                print(f"  Name: {result.get('name')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Created: {result.get('created')}")
                print(f"  Updated: {result.get('updated')}")
                if result.get('messages'):
                    print(f"  Messages: {result.get('messages')}")
                print(f"  URL: {result.get('url')}")
                return result
            else:
                print(f"✗ Failed to get status")
                print(f"  Error: {result.get('error')}")
                return None
        else:
            print(f"✗ Request failed")
            if response:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text}")
            return None

    def process_amiset(self, ami_set_id):
        """Trigger processing of an AMI Set"""
        print("\n" + "="*60)
        print(f"Processing AMI Set: {ami_set_id}")
        print("="*60 + "\n")

        response = self._make_request('POST', f'/archipelago/amiset/process/{ami_set_id}', {})

        if response and response.status_code in [200, 201, 202]:
            result = response.json()
            if result.get('success'):
                print("✓ Processing initiated successfully!")
                print(f"  AMI Set ID: {result.get('ami_set_id')}")
                print(f"  Message: {result.get('message')}")
                print(f"  URL: {result.get('ami_set_url')}")
                return result
            else:
                print(f"✗ Failed to process AMI Set")
                print(f"  Error: {result.get('error')}")
                return None
        else:
            print(f"✗ Request failed")
            if response:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text}")
            return None


def create_sample_ocr_data():
    """Create sample OCR data for testing"""
    timestamp = datetime.utcnow().isoformat() + 'Z'

    return [
        {
            "name": "document_001",
            "label": "Sample Document 1",
            "text": "This is the full OCR extracted text from the first document. "
                   "It contains multiple paragraphs and detailed information. "
                   "The OCR confidence is high and the text is clear and readable. "
                   * 10,  # Repeat for more realistic size
            "description": "Sample OCR processed document 1",
            "file_info": {
                "filename": "sample_doc_001.pdf",
                "file_path": "/path/to/sample_doc_001.pdf"
            },
            "ocr_metadata": {
                "provider": "tesseract",
                "confidence": 0.95,
                "language": "en",
                "processing_date": timestamp
            }
        },
        {
            "name": "document_002",
            "label": "Sample Document 2",
            "text": "This is the OCR text from the second document. "
                   "It demonstrates the ability to handle multiple documents in bulk. "
                   "Each document can have its own metadata and processing information. "
                   * 10,
            "description": "Sample OCR processed document 2",
            "file_info": {
                "filename": "sample_doc_002.pdf",
                "file_path": "/path/to/sample_doc_002.pdf"
            },
            "ocr_metadata": {
                "provider": "tesseract",
                "confidence": 0.92,
                "language": "en",
                "processing_date": timestamp
            }
        },
        {
            "name": "document_003",
            "label": "Sample Document 3",
            "text": "This is the third sample document with OCR text. "
                   "It showcases the ability to handle different document types and layouts. "
                   "The system can process PDFs, images, and other document formats. "
                   * 10,
            "description": "Sample OCR processed document 3",
            "file_info": {
                "filename": "sample_doc_003.jpg",
                "file_path": "/path/to/sample_doc_003.jpg"
            },
            "ocr_metadata": {
                "provider": "tesseract",
                "confidence": 0.88,
                "language": "en",
                "processing_date": timestamp
            }
        }
    ]


def main():
    parser = argparse.ArgumentParser(description='Test Archipelago AMI Set endpoints')
    parser.add_argument('--token', type=str, help='Authentication token (if required)')
    parser.add_argument('--action', choices=['add', 'status', 'process', 'full'],
                       default='full', help='Action to perform')
    parser.add_argument('--ami-set-id', type=str, help='AMI Set ID for status/process actions')
    parser.add_argument('--collection-title', type=str, help='Collection title for new AMI Set')
    parser.add_argument('--collection-id', type=int, help='Collection ID for new AMI Set')
    parser.add_argument('--data-file', type=str, help='JSON file with OCR data (instead of sample data)')

    args = parser.parse_args()

    client = ArcipelagoAMIClient(auth_token=args.token)

    if args.action == 'add' or args.action == 'full':
        # Load or create OCR data
        if args.data_file:
            try:
                with open(args.data_file, 'r') as f:
                    ocr_data = json.load(f)
                    if isinstance(ocr_data, dict) and 'ocr_data' in ocr_data:
                        ocr_data = ocr_data['ocr_data']
            except Exception as e:
                print(f"Error loading data file: {e}")
                return
        else:
            ocr_data = create_sample_ocr_data()

        # Create AMI Set
        result = client.add_amiset(
            ocr_data_list=ocr_data,
            collection_title=args.collection_title,
            collection_id=args.collection_id
        )

        if result and args.action == 'full':
            ami_set_id = result.get('ami_set_id')
            args.ami_set_id = ami_set_id

    if args.action == 'status' or (args.action == 'full' and args.ami_set_id):
        if not args.ami_set_id:
            print("Error: --ami-set-id is required for status action")
            return

        client.get_status(args.ami_set_id)

    if args.action == 'process' or (args.action == 'full' and args.ami_set_id):
        if not args.ami_set_id:
            print("Error: --ami-set-id is required for process action")
            return

        client.process_amiset(args.ami_set_id)

    print("\n" + "="*60)
    print("Test completed!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
