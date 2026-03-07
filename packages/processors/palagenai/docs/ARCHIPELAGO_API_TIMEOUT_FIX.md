# Archipelago API Timeout Fix

## Problem
The `/api/archipelago/push-bulk-ami` endpoint was throwing `net::ERR_NETWORK_CHANGED` errors when uploading bulk OCR results to Archipelago Commons. This error typically indicates:

1. **HTTP Timeout**: Long-running file uploads exceeded browser/server timeout limits
2. **Network Interruption**: Network changed during the upload process
3. **Request Cancellation**: Client closed connection while waiting for response

## Root Cause
The original implementation was **blocking** the HTTP request for the entire duration of the AMI Set creation process, which involves:
1. File validation
2. Directory preparation
3. OCR text file generation
4. Metadata JSON generation
5. Thumbnail generation
6. CSV creation
7. ZIP archive creation
8. **File uploads to Archipelago** (5-15 minutes for large files)
9. AMI Set creation
10. Result aggregation

This entire process could take **15-30+ minutes** for large bulk jobs, exceeding typical HTTP timeout limits (usually 30 seconds to 5 minutes).

## Solution: Async Background Task Pattern

### Architecture Change
```
BEFORE (Blocking):
Client → POST /api/archipelago/push-bulk-ami → [WAIT 15-30 mins] → 200 OK/Error
                                                      ↓
                                          HTTP Timeout (usually ~30s)
                                                      ↓
                                          net::ERR_NETWORK_CHANGED

AFTER (Async Background):
Client → POST /api/archipelago/push-bulk-ami → 202 Accepted [RETURNS IMMEDIATELY]
                                                      ↓
                                          Background Thread
                                          [Processing 15-30 mins]
                                                      ↓
                                          Update DB with result
         
Client ← GET /api/bulk/status/{job_id} ← [Polls every 5 seconds]
         ↓
         Shows progress/completion
```

## Implementation Details

### 1. Backend Changes (`routes/archipelago.py`)

**Created helper function for background task:**
```python
def _push_bulk_ami_background(job_id, collection_title, collection_id, user_id):
    """Background task for pushing bulk job to Archipelago via AMI"""
    # Runs in separate thread
    # Includes retry logic with exponential backoff
    # Updates DB with result on completion
```

**Modified endpoint to return immediately:**
```python
@archipelago_bp.route('/push-bulk-ami', methods=['POST'])
@token_required
def push_bulk_ami(current_user_id):
    # ... validation ...
    
    # Start background task
    import threading
    thread = threading.Thread(
        target=_push_bulk_ami_background,
        args=(job_id, collection_title, collection_id, current_user_id),
        daemon=True
    )
    thread.start()
    
    # Return immediately with 202 Accepted
    return jsonify({
        'success': True,
        'message': 'AMI Set creation started. Processing in background...',
        'job_id': job_id,
        'status': 'uploading_to_archipelago'
    }), 202
```

### 2. Database Model Changes (`models/bulk_job.py`)

**Added method to update Archipelago results:**
```python
@staticmethod
def update_archipelago_result(mongo, job_id, archipelago_result):
    """
    Update job with Archipelago upload result
    Stores AMI Set ID, name, and other metadata
    """
```

**Modified status tracking:**
- New status: `'uploading_to_archipelago'` (indicates in-progress Archipelago upload)
- New fields:
  - `archipelago_result`: Complete result from AMI Set creation
  - `archipelago_uploaded_at`: Timestamp of successful upload

### 3. Frontend Changes (`BulkOCRProcessor.tsx`)

**Updated upload handler:**
```typescript
const handleUploadToArchipelago = async (jobId: string) => {
    // Send request (returns immediately with 202)
    const response = await authenticatedFetch('/api/archipelago/push-bulk-ami', {...});
    
    // Show "Processing in background" message
    setArchipelagoResult({
        success: true,
        message: 'AMI Set creation started. Processing in background...',
        status: 'processing',
    });
    
    // Poll for completion every 5 seconds
    const pollInterval = setInterval(async () => {
        const statusResponse = await authenticatedFetch(`/api/bulk/status/${jobId}`);
        const statusData = await statusResponse.json();
        
        if (statusData.archipelago_result) {
            // Upload complete!
            setArchipelagoResult({...}); // Update with final result
            clearInterval(pollInterval);
        }
    }, 5000); // 5-second poll interval
    
    // Timeout after 30 minutes
    setTimeout(() => clearInterval(pollInterval), 30 * 60 * 1000);
};
```

## Retry Logic

The background task includes robust retry mechanism:

```python
# Retry configuration
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(1, max_retries + 1):
    try:
        result = service.create_bulk_via_ami(...)
        if result and result.get('success'):
            return  # Success
    except Exception as e:
        if attempt < max_retries:
            # Exponential backoff
            time.sleep(retry_delay)
            retry_delay *= 2  # 5s → 10s → 20s
        else:
            raise  # Give up after max retries
```

This handles transient network failures automatically.

## Benefits

1. **No More Timeouts**: Eliminates HTTP timeout errors completely
2. **Better UX**: User sees "processing" message immediately, not stuck waiting
3. **Resilient**: Automatic retry logic for network failures
4. **Scalable**: Background tasks don't block HTTP threads
5. **Transparent**: User can close tab/window, processing continues in background
6. **Pollable**: Status endpoint allows real-time progress updates

## HTTP Status Codes

### Request
```
POST /api/archipelago/push-bulk-ami
Content-Type: application/json

{
  "job_id": "bulk-job-12345",
  "collection_title": "My OCR Collection"
}
```

### Immediate Response (202 Accepted)
```json
{
  "success": true,
  "message": "AMI Set creation started. Processing in background...",
  "job_id": "bulk-job-12345",
  "status": "uploading_to_archipelago"
}
```

### Poll Status (GET /api/bulk/status/{job_id})
**While processing:**
```json
{
  "job_id": "bulk-job-12345",
  "status": "uploading_to_archipelago",
  "updated_at": "2024-01-15T10:30:45.123Z"
}
```

**After completion:**
```json
{
  "job_id": "bulk-job-12345",
  "status": "completed",
  "archipelago_result": {
    "success": true,
    "ami_set_id": 12345,
    "name": "My OCR Collection",
    "message": "Process it at: https://archipelago.example.com/node/12345",
    "csv_fid": 67890,
    "zip_fid": 67891
  }
}
```

## Testing

### Simulate Slow Upload
```bash
# In terminal 1: Start server with longer timeout
UPLOAD_TIMEOUT=300 python -m flask run

# In terminal 2: Trigger bulk OCR job
# Click "Upload to Archipelago" button

# Should see:
# 1. Immediate 202 response
# 2. "Processing in background" message
# 3. Status polling begins
# 4. After 15-30 mins, final result appears
```

### Check Background Task
```bash
# Monitor logs
tail -f logs/app.log

# Should see entries like:
# [Background: Starting AMI Set creation for job xyz]
# [Background: Step 1/10: Validating source files...]
# [Background: Step 9/10: Uploading to Archipelago...]
# [Background: AMI Set created successfully: ami_set_id]
```

## Configuration

No additional configuration needed. The timeout behavior is automatic:

- **Polling interval**: 5 seconds (can be adjusted in frontend)
- **Poll timeout**: 30 minutes (can be extended if needed)
- **Retry attempts**: 3 (configurable in `_push_bulk_ami_background`)
- **Exponential backoff**: 5s → 10s → 20s

## Migration Notes

If upgrading from the old blocking implementation:

1. Existing code calling `/api/archipelago/push-bulk-ami` should continue to work
2. Response will now be 202 instead of 200
3. Code should be updated to handle 202 and poll for results instead of waiting for 200
4. Database queries may need to check `status == 'uploading_to_archipelago'` for in-progress uploads

## Troubleshooting

### "Upload not completing"
- Check server logs for `[Background:` entries
- Verify network connectivity to Archipelago
- Check available disk space for temporary files

### "Polling stuck"
- Check browser console for JavaScript errors
- Verify job_id is correct
- Check network tab for failed requests

### "Archipelago upload still failing"
- Check Archipelago server logs
- Verify file permissions in `/app/uploads`
- Increase retry attempts if network is unstable

## Future Improvements

1. **WebSocket Updates**: Replace polling with real-time WebSocket updates
2. **Job Queue**: Move background tasks to proper job queue (Celery, RQ)
3. **Monitoring**: Add metrics for upload success rates and timing
4. **Notifications**: Email/Slack notification when upload completes
5. **Resume**: Allow resuming interrupted uploads

## Related Files

- `/backend/app/routes/archipelago.py` - API endpoint
- `/backend/app/models/bulk_job.py` - Database model
- `/frontend/src/components/BulkOCR/BulkOCRProcessor.tsx` - UI component
- `/backend/app/services/ami_service.py` - AMI Set creation logic
