#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://esmero-web:80"
USERNAME = "admin"
PASSWORD = "archipelago"

# Login
login_response = requests.post(
    f"{BASE_URL}/user/login?_format=json",
    json={'name': USERNAME, 'pass': PASSWORD},
    headers={'Content-Type': 'application/json'}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    exit(1)

cookies = login_response.cookies

# Get latest 3 nodes
response = requests.get(
    f'{BASE_URL}/jsonapi/node/digital_object?sort=-drupal_internal__nid&page[limit]=3',
    cookies=cookies,
    headers={'Accept': 'application/vnd.api+json'}
)

if response.status_code != 200:
    print(f"Failed to fetch nodes: {response.status_code}")
    exit(1)

data = response.json()

for node in data.get('data', []):
    nid = node['attributes']['drupal_internal__nid']
    title = node['attributes']['title']
    metadata = json.loads(node['attributes']['field_descriptive_metadata']['value'])

    print(f"\n{'='*80}")
    print(f"Node {nid}: {title}")
    print(f"{'='*80}")

    # Check as:document
    as_doc = metadata.get('as:document', {})
    print(f"\nNumber of documents in as:document: {len(as_doc)}")

    for doc_uuid, doc_info in as_doc.items():
        print(f"\nDocument UUID: {doc_uuid}")
        print(f"  Name: {doc_info.get('name')}")
        print(f"  URL: {doc_info.get('url')}")
        print(f"  dr:fid: {doc_info.get('dr:fid', 'NOT SET')}")
        print(f"  dr:filesize: {doc_info.get('dr:filesize')}")
        print(f"  Has flv:exif: {'flv:exif' in doc_info}")
        print(f"  Has flv:pdfinfo: {'flv:pdfinfo' in doc_info}")
        if 'flv:exif' in doc_info:
            print(f"  Page count: {doc_info['flv:exif'].get('PageCount')}")

    # Check documents array
    docs_array = metadata.get('documents', [])
    print(f"\nDocuments array: {docs_array}")
