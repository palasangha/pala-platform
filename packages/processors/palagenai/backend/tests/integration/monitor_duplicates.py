#!/usr/bin/env python3
"""
Real-time monitoring script to detect duplicate file processing in bulk OCR jobs.
Monitors both MongoDB checkpoint data and worker logs.
"""
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus
from pymongo import MongoClient
from collections import Counter

def check_job_for_duplicates(db, job_id):
    """Check a specific job for duplicates"""
    job = db.bulk_jobs.find_one({'job_id': job_id})
    if not job:
        return None

    checkpoint = job.get('checkpoint', {})
    processed_files = checkpoint.get('processed_files', [])
    results = checkpoint.get('results', [])

    # Count file paths in results
    result_file_paths = [r.get('file_path', '') for r in results]
    file_counts = Counter(result_file_paths)
    duplicates = {path: count for path, count in file_counts.items() if count > 1}

    return {
        'job_id': job_id,
        'status': job.get('status'),
        'total_files': job.get('total_files', 0),
        'consumed_count': job.get('consumed_count', 0),
        'published_count': job.get('published_count', 0),
        'processed_files_count': len(processed_files),
        'results_count': len(results),
        'duplicates': duplicates,
        'has_duplicates': len(duplicates) > 0
    }

def monitor_duplicates(interval=10, limit=5):
    """Monitor for duplicate file processing"""

    # Connect to MongoDB
    username = quote_plus("gvpocr_admin")
    password = quote_plus("gvp@123")
    mongo_uri = f"mongodb://{username}:{password}@localhost:27017/gvpocr?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client.gvpocr

    print("="*80)
    print("DUPLICATE FILE PROCESSING MONITOR")
    print("="*80)
    print(f"Started at: {datetime.now()}")
    print(f"Check interval: {interval} seconds")
    print(f"Monitoring last {limit} active jobs")
    print("="*80)
    print()

    seen_jobs = set()

    try:
        while True:
            # Get recent processing jobs
            jobs = list(db.bulk_jobs.find(
                {'status': {'$in': ['processing', 'completed']}},
                {'job_id': 1, 'status': 1, 'created_at': 1}
            ).sort('created_at', -1).limit(limit))

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking {len(jobs)} jobs...")

            duplicates_found = False

            for job in jobs:
                job_id = job['job_id']
                result = check_job_for_duplicates(db, job_id)

                if result:
                    # Print job info if new or has duplicates
                    if job_id not in seen_jobs or result['has_duplicates']:
                        status_icon = "✓" if result['status'] == 'completed' else "⏳"
                        print(f"\n{status_icon} Job: {job_id[:20]}... ({result['status']})")
                        print(f"  Files: {result['consumed_count']}/{result['total_files']}")
                        print(f"  Processed files array: {result['processed_files_count']}")
                        print(f"  Results array: {result['results_count']}")

                        if result['has_duplicates']:
                            duplicates_found = True
                            print(f"  ⚠️  DUPLICATES DETECTED:")
                            for path, count in result['duplicates'].items():
                                filename = os.path.basename(path)
                                print(f"    - {filename}: {count}x")
                        elif result['results_count'] != result['processed_files_count']:
                            print(f"  ⚠️  WARNING: Mismatch between results and processed_files!")

                        seen_jobs.add(job_id)

            if not duplicates_found and jobs:
                print("  ✓ No duplicates detected")

            # Sleep before next check
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("Monitoring stopped by user")
        print("="*80)
    finally:
        client.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Monitor for duplicate file processing')
    parser.add_argument('--interval', type=int, default=10, help='Check interval in seconds (default: 10)')
    parser.add_argument('--limit', type=int, default=5, help='Number of recent jobs to monitor (default: 5)')
    args = parser.parse_args()

    monitor_duplicates(interval=args.interval, limit=args.limit)
