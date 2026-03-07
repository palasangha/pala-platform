#!/usr/bin/env python3
"""
Trigger enrichment for a completed OCR job
"""

import sys
import os
sys.path.insert(0, '/app')

from enrichment_service.coordinator.enrichment_coordinator import EnrichmentCoordinator

def main():
    # OCR job ID to enrich
    ocr_job_id = "a347d297-c662-48e7-9d34-a013cb4bf065"
    collection_id = "bhushanji_collection"
    
    print(f"Triggering enrichment for OCR job: {ocr_job_id}")
    
    # Initialize coordinator
    coordinator = EnrichmentCoordinator()
    
    # Create enrichment job
    enrichment_job_id = coordinator.create_enrichment_job(
        ocr_job_id=ocr_job_id,
        collection_id=collection_id,
        collection_metadata={
            "name": "Bhushanji Letters",
            "description": "Historical letters from Bhushanji collection"
        }
    )
    
    if enrichment_job_id:
        print(f"✓ Enrichment job created: {enrichment_job_id}")
        print(f"Tasks published to NSQ topic 'enrichment'")
        print(f"Workers will start processing...")
    else:
        print("✗ Failed to create enrichment job")
        sys.exit(1)

if __name__ == "__main__":
    main()
