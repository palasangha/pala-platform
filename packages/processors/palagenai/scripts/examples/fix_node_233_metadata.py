#!/usr/bin/env python3
"""
Fix Node 233 by adding proper PDF metadata (flv:exif and flv:pdfinfo)
"""

import requests
import json
import hashlib
import os

# Archipelago connection
BASE_URL = "http://esmero-web:80"
USERNAME = "admin"
PASSWORD = "archipelago"

def extract_pdf_metadata(file_path):
    """Extract PDF metadata using PyPDF2"""
    try:
        import PyPDF2

        # Calculate MD5 checksum
        with open(file_path, 'rb') as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        file_size = os.path.getsize(file_path)

        # Extract PDF info
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)

            # Build flv:exif metadata
            flv_exif = {
                'MIMEType': 'application/pdf',
                'PageCount': page_count,
                'FileSize': f"{file_size / 1024:.1f} kB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
            }

            # Try to get PDF metadata
            if pdf_reader.metadata:
                if pdf_reader.metadata.title:
                    flv_exif['Title'] = pdf_reader.metadata.title
                if pdf_reader.metadata.author:
                    flv_exif['Author'] = pdf_reader.metadata.author
                if pdf_reader.metadata.creator:
                    flv_exif['Creator'] = pdf_reader.metadata.creator
                if pdf_reader.metadata.producer:
                    flv_exif['Producer'] = pdf_reader.metadata.producer

            # Build flv:pdfinfo with page dimensions
            flv_pdfinfo = {}
            for i, page in enumerate(pdf_reader.pages, 1):
                box = page.mediabox
                width = int(float(box.width))
                height = int(float(box.height))
                flv_pdfinfo[str(i)] = {
                    'width': str(width),
                    'height': str(height),
                    'rotation': '0',
                    'orientation': 'TopLeft'
                }

            # Add pronom info
            flv_pronom = {
                'label': 'Acrobat PDF - Portable Document Format',
                'mimetype': 'application/pdf',
                'pronom_id': 'info:pronom/fmt/18',
                'detection_type': 'signature'
            }

            return {
                'checksum': checksum,
                'filesize': file_size,
                'flv:exif': flv_exif,
                'flv:pdfinfo': flv_pdfinfo,
                'flv:pronom': flv_pronom
            }
    except Exception as e:
        print(f"Error extracting PDF metadata: {e}")
        return None

def main():
    # Login
    print("Logging in to Archipelago...")
    login_response = requests.post(
        f"{BASE_URL}/user/login?_format=json",
        json={'name': USERNAME, 'pass': PASSWORD},
        headers={'Content-Type': 'application/json'}
    )

    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        return

    token = login_response.json()['csrf_token']
    cookies = login_response.cookies

    # Get node 233
    print("\nFetching Node 233...")
    response = requests.get(
        f"{BASE_URL}/jsonapi/node/digital_object?filter[drupal_internal__nid]=233",
        cookies=cookies,
        headers={'Accept': 'application/vnd.api+json'}
    )

    if response.status_code != 200:
        print(f"Failed to fetch node: {response.status_code}")
        return

    data = response.json()
    if not data.get('data'):
        print("Node 233 not found!")
        return

    node = data['data'][0]
    node_uuid = node['id']
    metadata = json.loads(node['attributes']['field_descriptive_metadata']['value'])

    print(f"Node UUID: {node_uuid}")
    print(f"Current title: {metadata.get('label')}")

    # Extract PDF metadata from the actual file
    filename = "From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf"
    file_path = f"/app/Bhushanji/eng-typed/{filename}"

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"\nExtracting PDF metadata from: {filename}")
    pdf_metadata = extract_pdf_metadata(file_path)

    if not pdf_metadata:
        print("Failed to extract PDF metadata")
        return

    print(f"  Pages: {pdf_metadata['flv:exif']['PageCount']}")
    print(f"  Size: {pdf_metadata['flv:exif']['FileSize']}")
    print(f"  Checksum: {pdf_metadata['checksum']}")

    # Update as:document with proper metadata
    # Keep only the correct document entry
    new_as_document = {}
    for uuid_key, doc in metadata.get('as:document', {}).items():
        if 'Refusals' in doc.get('name', ''):
            # Update this entry with proper metadata
            doc['checksum'] = pdf_metadata['checksum']
            doc['dr:filesize'] = pdf_metadata['filesize']
            doc['flv:exif'] = pdf_metadata['flv:exif']
            doc['flv:pdfinfo'] = pdf_metadata['flv:pdfinfo']
            doc['flv:pronom'] = pdf_metadata['flv:pronom']
            # Fix URL encoding - remove %20
            doc['url'] = doc['url'].replace('%20', ' ')
            new_as_document[uuid_key] = doc
            print(f"\nUpdated document entry: {doc['name']}")

    metadata['as:document'] = new_as_document

    # Update the node
    print("\nUpdating node metadata...")
    update_data = {
        'data': {
            'type': 'node--digital_object',
            'id': node_uuid,
            'attributes': {
                'field_descriptive_metadata': {
                    'value': json.dumps(metadata)
                }
            }
        }
    }

    headers = {
        'Content-Type': 'application/vnd.api+json',
        'X-CSRF-Token': token
    }

    update_response = requests.patch(
        f"{BASE_URL}/jsonapi/node/digital_object/{node_uuid}",
        json=update_data,
        cookies=cookies,
        headers=headers
    )

    if update_response.status_code in [200, 204]:
        print("✓ Node 233 updated successfully!")
        print(f"\nView at: {BASE_URL}/node/233")
        print(f"\nThe PDF should now display properly with all {pdf_metadata['flv:exif']['PageCount']} pages visible.")
    else:
        print(f"✗ Update failed: {update_response.status_code}")
        print(update_response.text[:500])

if __name__ == '__main__':
    main()
