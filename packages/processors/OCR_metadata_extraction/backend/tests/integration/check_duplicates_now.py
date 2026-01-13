#!/usr/bin/env python3
"""
One-time check for duplicate file processing in recent bulk OCR jobs.
"""
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from pymongo import MongoClient
from collections import Counter

def main():
    # Connect to MongoDB
    username = quote_plus("gvpocr_admin")
    password = quote_plus("gvp@123")
    mongo_uri = f"mongodb://{username}:{password}@localhost:27017/gvpocr?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client.gvpocr

    print("="*80)
    print("DUPLICATE FILE PROCESSING CHECK")
    print("="*80)
    print(f"Time: {datetime.now()}")
    print()

    # Get recent jobs (last 24 hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    jobs = list(db.bulk_jobs.find(
        {
            'created_at': {'$gte': cutoff_time},
            'status': {'$in': ['processing', 'completed']}
        },
        {'job_id': 1, 'status': 1, 'created_at': 1, 'checkpoint': 1, 'total_files': 1, 'consumed_count': 1}
    ).sort('created_at', -1))

    print(f"Found {len(jobs)} jobs in the last 24 hours\n")

    total_duplicates = 0
    jobs_with_duplicates = 0

    for job in jobs:
        job_id = job['job_id']
        checkpoint = job.get('checkpoint', {})
        processed_files = checkpoint.get('processed_files', [])
        results = checkpoint.get('results', [])

        # Count file paths in results
        result_file_paths = [r.get('file_path', '') for r in results if r.get('file_path')]
        file_counts = Counter(result_file_paths)
        duplicates = {path: count for path, count in file_counts.items() if count > 1}

        if duplicates:
            jobs_with_duplicates += 1
            total_duplicates += sum(count - 1 for count in duplicates.values())

            status_icon = "✓" if job['status'] == 'completed' else "⏳"
            print(f"{status_icon} Job: {job_id}")
            print(f"   Status: {job['status']}")
            print(f"   Created: {job.get('created_at', 'N/A')}")
            print(f"   Total files: {job.get('total_files', 0)}")
            print(f"   Consumed: {job.get('consumed_count', 0)}")
            print(f"   Processed files array: {len(processed_files)}")
            print(f"   Results array: {len(results)}")
            print(f"   ⚠️  DUPLICATES:")
            for path, count in duplicates.items():
                filename = os.path.basename(path)
                print(f"      - {filename}: {count}x (duplicate {count-1} times)")
            print()

    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total jobs checked: {len(jobs)}")
    print(f"Jobs with duplicates: {jobs_with_duplicates}")
    print(f"Total duplicate instances: {total_duplicates}")

    if jobs_with_duplicates == 0:
        print("\n✅ No duplicates found - the fix is working correctly!")
    else:
        print(f"\n⚠️  Found {jobs_with_duplicates} jobs with {total_duplicates} duplicate file(s)")
        print("   These may be from before the fix was applied.")

    print("="*80)

    client.close()

if __name__ == "__main__":
    main()
