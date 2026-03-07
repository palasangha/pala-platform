#!/usr/bin/env python3
"""
Test script to verify bulk job database operations
Run this inside the backend container to test MongoDB integration
"""

import sys
import os
from datetime import datetime
from bson import ObjectId

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models import mongo
from app.models.bulk_job import BulkJob

def test_bulk_job_database():
    """Test all bulk job database operations"""

    print("=" * 60)
    print("Testing Bulk Job Database Operations")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # Test data
        test_user_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        test_job_id = "test-job-12345"

        print("\n1. Testing Job Creation...")
        print("-" * 60)
        try:
            job_data = {
                'job_id': test_job_id,
                'folder_path': '/test/folder/path',
                'provider': 'tesseract',
                'languages': ['en', 'es'],
                'handwriting': False,
                'recursive': True,
                'export_formats': ['json', 'csv'],
                'status': 'processing'
            }

            created_job = BulkJob.create(mongo, test_user_id, job_data)
            print(f"✓ Job created successfully!")
            print(f"  - MongoDB _id: {created_job['_id']}")
            print(f"  - Job ID: {created_job['job_id']}")
            print(f"  - Status: {created_job['status']}")
            print(f"  - Created at: {created_job['created_at']}")
        except Exception as e:
            print(f"✗ Failed to create job: {str(e)}")
            return False

        print("\n2. Testing Job Retrieval by job_id...")
        print("-" * 60)
        try:
            retrieved_job = BulkJob.find_by_job_id(mongo, test_job_id, test_user_id)
            if retrieved_job:
                print(f"✓ Job retrieved successfully!")
                print(f"  - Job ID: {retrieved_job['job_id']}")
                print(f"  - Folder: {retrieved_job['folder_path']}")
                print(f"  - Provider: {retrieved_job['provider']}")
                print(f"  - Status: {retrieved_job['status']}")
            else:
                print("✗ Job not found")
                return False
        except Exception as e:
            print(f"✗ Failed to retrieve job: {str(e)}")
            return False

        print("\n3. Testing Progress Update...")
        print("-" * 60)
        try:
            progress_data = {
                'current': 5,
                'total': 10,
                'percentage': 50,
                'filename': 'test_image_5.jpg',
                'status': 'processing'
            }

            result = BulkJob.update_progress(mongo, test_job_id, progress_data)
            print(f"✓ Progress updated successfully!")
            print(f"  - Matched: {result.matched_count}")
            print(f"  - Modified: {result.modified_count}")

            # Verify update
            updated_job = BulkJob.find_by_job_id(mongo, test_job_id)
            print(f"  - Current progress: {updated_job['progress']['current']}/{updated_job['progress']['total']}")
            print(f"  - Percentage: {updated_job['progress']['percentage']}%")
        except Exception as e:
            print(f"✗ Failed to update progress: {str(e)}")
            return False

        print("\n4. Testing Status Update (Completion)...")
        print("-" * 60)
        try:
            results_data = {
                'summary': {
                    'total_files': 10,
                    'successful': 9,
                    'failed': 1,
                    'statistics': {
                        'total_characters': 12345,
                        'average_confidence': 0.95
                    }
                },
                'results_preview': {
                    'successful_samples': [
                        {
                            'file': 'test1.jpg',
                            'text': 'Sample OCR text',
                            'confidence': 0.95
                        }
                    ],
                    'error_samples': []
                },
                'download_url': '/api/bulk/download/test-output'
            }

            result = BulkJob.update_status(mongo, test_job_id, 'completed', results=results_data)
            print(f"✓ Status updated to completed!")
            print(f"  - Matched: {result.matched_count}")
            print(f"  - Modified: {result.modified_count}")

            # Verify update
            completed_job = BulkJob.find_by_job_id(mongo, test_job_id)
            print(f"  - Status: {completed_job['status']}")
            print(f"  - Completed at: {completed_job['completed_at']}")
            print(f"  - Total files: {completed_job['results']['summary']['total_files']}")
            print(f"  - Successful: {completed_job['results']['summary']['successful']}")
        except Exception as e:
            print(f"✗ Failed to update status: {str(e)}")
            return False

        print("\n5. Testing to_dict Conversion...")
        print("-" * 60)
        try:
            job_dict = BulkJob.to_dict(completed_job)
            print(f"✓ Converted to dictionary successfully!")
            print(f"  - Keys: {', '.join(job_dict.keys())}")
            print(f"  - Has results: {'results' in job_dict}")
            print(f"  - Created at (ISO): {job_dict['created_at']}")
            print(f"  - Completed at (ISO): {job_dict['completed_at']}")
        except Exception as e:
            print(f"✗ Failed to convert to dict: {str(e)}")
            return False

        print("\n6. Testing Job Listing...")
        print("-" * 60)
        try:
            jobs = BulkJob.find_by_user(mongo, test_user_id, skip=0, limit=10)
            count = BulkJob.count_by_user(mongo, test_user_id)
            print(f"✓ Retrieved job list successfully!")
            print(f"  - Total jobs for user: {count}")
            print(f"  - Jobs in current page: {len(jobs)}")

            for i, job in enumerate(jobs):
                print(f"  - Job {i+1}: {job['job_id']} ({job['status']})")
        except Exception as e:
            print(f"✗ Failed to retrieve job list: {str(e)}")
            return False

        print("\n7. Testing Error Status Update...")
        print("-" * 60)
        try:
            # Create another test job for error testing
            error_job_id = "test-error-job-67890"
            error_job_data = {
                'job_id': error_job_id,
                'folder_path': '/test/error/path',
                'provider': 'tesseract',
                'languages': ['en'],
                'status': 'processing'
            }
            BulkJob.create(mongo, test_user_id, error_job_data)

            # Update with error
            error_message = "Test error: File not found"
            result = BulkJob.update_status(mongo, error_job_id, 'error', error=error_message)
            print(f"✓ Error status updated successfully!")
            print(f"  - Matched: {result.matched_count}")
            print(f"  - Modified: {result.modified_count}")

            # Verify
            error_job = BulkJob.find_by_job_id(mongo, error_job_id)
            print(f"  - Status: {error_job['status']}")
            print(f"  - Error: {error_job['error']}")
            print(f"  - Completed at: {error_job['completed_at']}")

            # Clean up error test job
            BulkJob.delete_by_job_id(mongo, error_job_id, test_user_id)
            print(f"  - Test error job deleted")
        except Exception as e:
            print(f"✗ Failed error status test: {str(e)}")
            return False

        print("\n8. Testing Job Deletion...")
        print("-" * 60)
        try:
            result = BulkJob.delete_by_job_id(mongo, test_job_id, test_user_id)
            print(f"✓ Job deleted successfully!")
            print(f"  - Deleted count: {result.deleted_count}")

            # Verify deletion
            deleted_job = BulkJob.find_by_job_id(mongo, test_job_id)
            if deleted_job is None:
                print(f"  - Verification: Job no longer exists")
            else:
                print(f"  - Warning: Job still exists after deletion!")
                return False
        except Exception as e:
            print(f"✗ Failed to delete job: {str(e)}")
            return False

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nDatabase Schema Status: WORKING ✓")
        print("\nTested Operations:")
        print("  ✓ Job Creation")
        print("  ✓ Job Retrieval (by job_id)")
        print("  ✓ Progress Updates")
        print("  ✓ Status Updates (Completed)")
        print("  ✓ Status Updates (Error)")
        print("  ✓ Dictionary Conversion")
        print("  ✓ Job Listing & Pagination")
        print("  ✓ Job Count")
        print("  ✓ Job Deletion")
        print("\n" + "=" * 60)

        return True

if __name__ == '__main__':
    try:
        success = test_bulk_job_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
