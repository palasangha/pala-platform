#!/usr/bin/env python3
"""
Fix Node 18 by adding the missing as:document field
"""

import requests
import json
import uuid

# Archipelago connection
BASE_URL = "http://esmero-web:80"
USERNAME = "admin"
PASSWORD = "archipelago"

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
    headers = {
        'Content-Type': 'application/vnd.api+json',
        'X-CSRF-Token': token
    }

    # Get current metadata
    print("\nFetching Node 18 metadata...")
    response = requests.get(
        f"{BASE_URL}/jsonapi/node/digital_object",
        params={
            'filter[drupal_internal__nid]': '18'
        },
        cookies=cookies,
        headers={'Accept': 'application/vnd.api+json'}
    )

    if response.status_code != 200:
        print(f"Failed to fetch node: {response.status_code}")
        return

    data = response.json()
    if not data.get('data'):
        print("Node 18 not found!")
        return

    node = data['data'][0]
    node_uuid = node['id']

    # Get current metadata
    current_metadata = json.loads(node['attributes']['field_descriptive_metadata']['value'])

    print(f"\nNode UUID: {node_uuid}")
    print(f"Current title: {current_metadata.get('label')}")
    print(f"Has as:document: {'as:document' in current_metadata}")

    # Add the as:document field
    doc_uuid = str(uuid.uuid4())
    filename = "From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf"

    # Use file ID 49 (existing file entity in Archipelago)
    file_id = 49

    current_metadata['as:document'] = {
        f"urn:uuid:{doc_uuid}": {
            'url': f"s3://archipelago/{filename}",
            'name': filename,
            'tags': [],
            'type': 'Document',
            'dr:fid': file_id,
            'dr:for': 'documents',
            'dr:uuid': doc_uuid,
            'checksum': '',
            'sequence': 1,
            'dr:filesize': 563750,  # Actual size from MinIO
            'dr:mimetype': 'application/pdf',
            'crypHashFunc': 'md5'
        }
    }

    # IMPORTANT: Add file_id to the documents array
    current_metadata['documents'] = [file_id]

    # Also fix ismemberof to use integer instead of UUID
    if 'ismemberof' in current_metadata:
        # Get the collection node ID for this UUID
        coll_uuid = current_metadata['ismemberof']
        if isinstance(coll_uuid, str) and '-' in coll_uuid:  # It's a UUID
            print(f"\nFixing ismemberof: {coll_uuid} -> looking up node ID...")

            coll_response = requests.get(
                f"{BASE_URL}/jsonapi/node/digital_object_collection/{coll_uuid}",
                cookies=cookies,
                headers={'Accept': 'application/vnd.api+json'}
            )

            if coll_response.status_code == 200:
                coll_data = coll_response.json()
                coll_nid = coll_data['data']['attributes']['drupal_internal__nid']
                current_metadata['ismemberof'] = [coll_nid]
                print(f"  Updated to: [{coll_nid}]")
            else:
                print(f"  Could not find collection, removing ismemberof")
                current_metadata['ismemberof'] = []

    # Update the node
    print("\nUpdating node metadata...")
    update_data = {
        'data': {
            'type': 'node--digital_object',
            'id': node_uuid,
            'attributes': {
                'field_descriptive_metadata': {
                    'value': json.dumps(current_metadata)
                }
            }
        }
    }

    update_response = requests.patch(
        f"{BASE_URL}/jsonapi/node/digital_object/{node_uuid}",
        json=update_data,
        cookies=cookies,
        headers=headers
    )

    if update_response.status_code in [200, 204]:
        print("✓ Node 18 updated successfully!")
        print(f"\nView at: {BASE_URL}/node/18")
        print(f"\nThe PDF should now be visible in Archipelago")
    else:
        print(f"✗ Update failed: {update_response.status_code}")
        print(update_response.text[:500])

if __name__ == '__main__':
    main()
