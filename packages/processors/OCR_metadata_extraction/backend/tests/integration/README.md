# Integration Tests - Duplicate File Processing

This directory contains integration tests and monitoring tools for the duplicate file processing race condition fix.

## Overview

These tests verify that the atomic check-and-insert operations prevent multiple workers from processing the same file simultaneously in bulk OCR jobs.

## Test Scripts

### 1. `test_race_condition_fix.py`
**Purpose**: Unit test that simulates the race condition to verify the fix works correctly.

**Usage**:
```bash
cd backend/tests/integration
python3 test_race_condition_fix.py
```

**What it does**:
- Creates a test job in MongoDB
- Simulates 3 workers trying to save results for the same file simultaneously
- Verifies that only 1 result is saved (no duplicates)
- Cleans up test data

**Expected Output**:
```
✅ TEST PASSED - Race condition fix is working!
```

### 2. `check_duplicates_now.py`
**Purpose**: One-time analysis of recent jobs to detect any duplicate file processing.

**Usage**:
```bash
cd backend/tests/integration
python3 check_duplicates_now.py
```

**What it does**:
- Scans all bulk OCR jobs from the last 24 hours
- Checks if any files were processed multiple times
- Reports detailed information about duplicates found
- Shows summary statistics

**Example Output**:
```
================================================================================
DUPLICATE FILE PROCESSING CHECK
================================================================================
Total jobs checked: 11
Jobs with duplicates: 0
Total duplicate instances: 0

✅ No duplicates found - the fix is working correctly!
```

### 3. `monitor_duplicates.py`
**Purpose**: Real-time continuous monitoring of bulk OCR jobs for duplicate processing.

**Usage**:
```bash
cd backend/tests/integration
python3 monitor_duplicates.py [--interval SECONDS] [--limit NUM_JOBS]

# Default: check every 10 seconds, monitor last 5 jobs
python3 monitor_duplicates.py

# Custom: check every 30 seconds, monitor last 10 jobs
python3 monitor_duplicates.py --interval 30 --limit 10
```

**What it does**:
- Continuously monitors recent bulk OCR jobs
- Checks for duplicate entries in real-time
- Displays alerts when duplicates are detected
- Shows job progress and statistics

**Example Output**:
```
[10:29:13] Checking 10 jobs...
✓ Job: d4034d52-... (processing)
  Files: 13/16
  Processed files array: 13
  Results array: 13
  ✓ No duplicates detected
```

**Running in Background**:
```bash
# Start monitoring in background
nohup python3 monitor_duplicates.py --interval 15 --limit 10 > monitor.log 2>&1 &

# Check output
tail -f monitor.log

# Stop monitoring
pkill -f monitor_duplicates.py
```

## Documentation

### `DUPLICATE_FIX_SUMMARY.md`
Comprehensive documentation of:
- The race condition problem
- Root cause analysis
- Solution implementation details
- Testing results
- Benefits and deployment information

## Requirements

These scripts require:
- Python 3.7+
- pymongo library
- MongoDB connection (configured via environment variables)

## MongoDB Connection

The scripts use these environment variables (from `.env`):
```
MONGO_ROOT_USERNAME=gvpocr_admin
MONGO_ROOT_PASSWORD=gvp@123
```

Connection URI is constructed as:
```
mongodb://gvpocr_admin:gvp%40123@localhost:27017/gvpocr?authSource=admin
```

## How the Fix Works

### Before (Vulnerable to Race Condition)
```python
# Worker 1 checks
if not is_file_processed(file_path):  # Returns False
    # Worker 2 checks before Worker 1 saves
    if not is_file_processed(file_path):  # Also returns False
        # Both workers process and save -> DUPLICATE
```

### After (Atomic Check-and-Insert)
```python
# Atomic MongoDB operation
update_result = collection.update_one(
    {
        'job_id': job_id,
        'checkpoint.processed_files': {'$ne': file_path}  # Only if NOT processed
    },
    {
        '$push': {'checkpoint.results': result},
        '$addToSet': {'checkpoint.processed_files': file_path},
        # ...
    }
)

# Only ONE worker's update will match and succeed
if update_result.matched_count == 0:
    # File was already processed by another worker
    return None
```

## Troubleshooting

### Test Fails
If `test_race_condition_fix.py` fails:
1. Check MongoDB connection
2. Verify the fix is deployed in `backend/app/models/bulk_job.py`
3. Check that services are restarted

### Monitoring Shows Duplicates
If duplicates are detected after the fix:
1. Check when the job was created (may be before fix was deployed)
2. Verify worker code is updated
3. Check logs for error messages
4. Review MongoDB write concern settings

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```bash
# Run test as part of deployment verification
python3 backend/tests/integration/test_race_condition_fix.py || exit 1

# Quick check after deployment
python3 backend/tests/integration/check_duplicates_now.py
```

## Related Files

- `backend/app/models/bulk_job.py` - Contains the atomic save operations
- `backend/app/workers/ocr_worker.py` - Worker code that uses the atomic operations
- `docker-compose.yml` - OCR worker service configuration

## Support

For issues or questions:
1. Check the logs: `docker-compose logs ocr-worker`
2. Review `DUPLICATE_FIX_SUMMARY.md` for detailed documentation
3. Run the monitoring script to observe real-time behavior
