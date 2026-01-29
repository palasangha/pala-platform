#!/usr/bin/env python3
"""
Regenerate ZIP file with enrichment data included
"""

import os
import sys
import json
import zipfile
from pymongo import MongoClient

# Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp@123@localhost:27017/gvpocr?authSource=admin')
OCR_JOB_ID = 'a347d297-c662-48e7-9d34-a013cb4bf065'
ENRICHMENT_JOB_ID = 'enrich_a347d297-c662-48e7-9d34-a013cb4bf065_1769348540'
ZIP_PATH = f'/app/uploads/bulk_results/{OCR_JOB_ID}/{OCR_JOB_ID}_bulk_ocr_results.zip'
NEW_ZIP_PATH = f'/app/uploads/bulk_results/{OCR_JOB_ID}/{OCR_JOB_ID}_bulk_ocr_results_with_enrichment.zip'

def main():
    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client['gvpocr']
    
    # Fetch enriched documents
    print(f"Fetching enriched documents for job: {ENRICHMENT_JOB_ID}")
    enriched_docs = list(db.enriched_documents.find({
        'enrichment_job_id': ENRICHMENT_JOB_ID
    }))
    
    print(f"Found {len(enriched_docs)} enriched documents")
    
    if len(enriched_docs) == 0:
        print("No enriched documents found!")
        sys.exit(1)
    
    # Check if original ZIP exists
    if not os.path.exists(ZIP_PATH):
        print(f"Original ZIP not found: {ZIP_PATH}")
        sys.exit(1)
    
    print(f"Creating new ZIP with enrichment data: {NEW_ZIP_PATH}")
    
    # Copy original ZIP contents
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_in:
        with zipfile.ZipFile(NEW_ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            # Copy all existing files
            for item in zip_in.namelist():
                data = zip_in.read(item)
                zip_out.writestr(item, data)
            
            print(f"Copied {len(zip_in.namelist())} files from original ZIP")
            
            # Add enriched documents
            enrichment_folder = 'enriched_results'
            added_count = 0
            
            for doc in enriched_docs:
                try:
                    # Get document filename
                    doc_id = doc.get('_id', f'doc_{added_count}')
                    ocr_data = doc.get('ocr_data', {})
                    original_file = ocr_data.get('file', doc_id)
                    base_name = os.path.splitext(original_file)[0]
                    
                    # Create enriched JSON
                    enriched_json = {
                        'document_id': doc_id,
                        'enrichment_job_id': ENRICHMENT_JOB_ID,
                        'ocr_data': ocr_data,
                        'enriched_data': doc.get('enriched_data', {}),
                        'quality_metrics': doc.get('quality_metrics', {}),
                        'enrichment_metadata': doc.get('enrichment_metadata', {}),
                        'review_status': doc.get('review_status', 'not_required'),
                        'created_at': str(doc.get('created_at', '')),
                        'updated_at': str(doc.get('updated_at', ''))
                    }
                    
                    # Add to ZIP
                    arcname = os.path.join(enrichment_folder, f'{base_name}_enriched.json')
                    zip_out.writestr(arcname, json.dumps(enriched_json, indent=2, ensure_ascii=False, default=str))
                    added_count += 1
                    print(f"Added: {arcname}")
                    
                except Exception as e:
                    print(f"Error adding document {doc.get('_id')}: {e}")
            
            print(f"\n✓ Successfully added {added_count} enriched documents to ZIP")
    
    # Show ZIP contents
    print(f"\nNew ZIP contents:")
    with zipfile.ZipFile(NEW_ZIP_PATH, 'r') as zipf:
        for item in zipf.namelist():
            info = zipf.getinfo(item)
            print(f"  {item} ({info.file_size} bytes)")
    
    print(f"\n✓ New ZIP created: {NEW_ZIP_PATH}")
    print(f"File size: {os.path.getsize(NEW_ZIP_PATH)} bytes")

if __name__ == "__main__":
    main()
