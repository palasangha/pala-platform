#!/usr/bin/env python3
"""Fetch digital object metadata from Archipelago"""
import sys
import json
import requests

# Configuration
BASE_URL = "http://esmero-web:80"
USERNAME = "admin"
PASSWORD = "archipelago"
NODE_UUID = "b98b061d-96e9-4692-b859-6981cf2c3136"

def login():
    """Login to Archipelago"""
    session = requests.Session()
    login_url = f"{BASE_URL}/user/login?_format=json"
    login_data = {"name": USERNAME, "pass": PASSWORD}
    headers = {"Content-Type": "application/json"}

    response = session.post(login_url, json=login_data, headers=headers)
    response.raise_for_status()

    result = response.json()
    csrf_token = result.get('csrf_token')
    return session, csrf_token

def fetch_node(session, node_uuid):
    """Fetch node metadata"""
    url = f"{BASE_URL}/jsonapi/node/digital_object/{node_uuid}"
    response = session.get(url)
    response.raise_for_status()
    return response.json()

def main():
    try:
        session, csrf_token = login()
        print("✓ Logged in successfully", file=sys.stderr)

        node_data = fetch_node(session, NODE_UUID)

        # Extract field_descriptive_metadata
        attributes = node_data.get('data', {}).get('attributes', {})
        metadata_field = attributes.get('field_descriptive_metadata', {})
        metadata_json = metadata_field.get('value', '{}')

        # Parse and pretty print
        metadata = json.loads(metadata_json)

        print("\n=== Digital Object Metadata ===")
        print(f"Title: {attributes.get('title', 'N/A')}")
        print(f"\n=== as:document field ===")
        print(json.dumps(metadata.get('as:document', {}), indent=2))

        print(f"\n=== documents field ===")
        print(json.dumps(metadata.get('documents', []), indent=2))

        print(f"\n=== file_info field ===")
        print(json.dumps(metadata.get('file_info', {}), indent=2))

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
