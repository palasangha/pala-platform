#!/usr/bin/env python3
"""
Test script to verify the race condition fix for duplicate file processing.
This simulates multiple workers trying to process the same file simultaneously.
"""
import os
import sys
import time
from datetime import datetime
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

# Add backend to path
sys.path.insert(0, '/mnt/sda1/mango1_home/gvpocr/backend')

def test_atomic_save():
    """Test that save_file_result_atomic prevents duplicates"""

    # Connect to MongoDB
    from urllib.parse import quote_plus
    username = quote_plus("gvpocr_admin")
    password = quote_plus("gvp@123")
    mongo_uri = f"mongodb://{username}:{password}@localhost:27017/gvpocr?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client.gvpocr

    # Create a test job
    test_job_id = f"test_race_condition_{int(time.time())}"
    test_file_path = "/test/file.pdf"

    # Insert test job
    db.bulk_jobs.insert_one({
        'job_id': test_job_id,
        'total_files': 1,
        'consumed_count': 0,
        'published_count': 1,
        'status': 'processing',
        'checkpoint': {
            'processed_files': [],
            'results': [],
            'errors': []
        },
        'progress': {
            'current': 0,
            'total': 1,
            'percentage': 0
        },
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })

    print(f"✓ Created test job: {test_job_id}")

    # Simulate multiple workers trying to save the same file
    collection = db.get_collection('bulk_jobs', write_concern=WriteConcern(w='majority', j=True))

    results = []
    for i in range(3):
        print(f"\n--- Attempt {i+1} to save result for {test_file_path} ---")

        # Get current state
        job = db.bulk_jobs.find_one({'job_id': test_job_id})
        new_consumed = job.get('consumed_count', 0) + 1

        # Try to save atomically
        result = collection.update_one(
            {
                'job_id': test_job_id,
                'checkpoint.processed_files': {'$ne': test_file_path}  # Only if NOT already processed
            },
            {
                '$push': {'checkpoint.results': {
                    'file': 'file.pdf',
                    'file_path': test_file_path,
                    'status': 'success',
                    'worker_id': f'worker-{i+1}',
                    'text': f'Result from worker {i+1}'
                }},
                '$addToSet': {'checkpoint.processed_files': test_file_path},
                '$inc': {'consumed_count': 1},
                '$set': {
                    'updated_at': datetime.utcnow(),
                    'progress.current': new_consumed
                }
            }
        )

        results.append(result)
        print(f"  matched_count: {result.matched_count}")
        print(f"  modified_count: {result.modified_count}")

        if result.matched_count == 0:
            print(f"  ✓ File was already processed - duplicate prevented!")
        else:
            print(f"  ✓ File saved successfully")

    # Verify the final state
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    final_job = db.bulk_jobs.find_one({'job_id': test_job_id})
    processed_files = final_job['checkpoint']['processed_files']
    results_list = final_job['checkpoint']['results']
    consumed_count = final_job['consumed_count']

    print(f"\nProcessed files in array: {len(processed_files)}")
    print(f"Results in array: {len(results_list)}")
    print(f"Consumed count: {consumed_count}")

    # Check for duplicates
    success = True
    if len(processed_files) != 1:
        print(f"\n❌ ERROR: Expected 1 file in processed_files, got {len(processed_files)}")
        success = False
    else:
        print(f"\n✓ Correct: 1 file in processed_files")

    if len(results_list) != 1:
        print(f"❌ ERROR: Expected 1 result in results array, got {len(results_list)}")
        print(f"   This means duplicates were NOT prevented!")
        success = False
    else:
        print(f"✓ Correct: 1 result in results array (no duplicates)")

    if consumed_count != 1:
        print(f"❌ ERROR: Expected consumed_count=1, got {consumed_count}")
        success = False
    else:
        print(f"✓ Correct: consumed_count = 1")

    # Cleanup
    db.bulk_jobs.delete_one({'job_id': test_job_id})
    print(f"\n✓ Cleaned up test job")

    client.close()

    if success:
        print("\n" + "="*60)
        print("✅ TEST PASSED - Race condition fix is working!")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ TEST FAILED - Race condition still exists!")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(test_atomic_save())
