# Fixed: "Failed to fetch" Error in Archipelago Upload Polling

## Problem
The frontend was trying to poll `/api/bulk/status/{job_id}` but this endpoint didn't exist, causing "Failed to fetch" errors.

## Root Cause
1. Frontend polling code referenced non-existent GET endpoint
2. Old `/api/bulk/status` endpoint was POST and only a placeholder
3. No way for frontend to check Archipelago upload status

## Solution Implemented

### Backend Changes
**Added new GET endpoint:** `/api/bulk/status/<job_id>`

```python
@bulk_bp.route('/status/<job_id>', methods=['GET'])
@token_required
def get_job_status(current_user_id, job_id):
    """Get status of a bulk processing job including Archipelago upload results"""
    # Returns:
    # - job_id
    # - status (processing, completed, uploading_to_archipelago, error)
    # - archipelago_result (populated after upload completes)
    # - archipelago_uploaded_at
    # - progress metrics
    # - errors if any
```

### Frontend Changes
1. Fixed polling code to use correct endpoint path
2. Removed duplicate Authorization header (authenticatedFetch already adds it)
3. Updated state type definitions to support new fields

## How It Works Now

```typescript
// 1. User clicks "Upload to Archipelago"
POST /api/archipelago/push-bulk-ami
↓ Returns 202 Accepted immediately

// 2. Frontend shows "Processing in background..."
// 3. Frontend polls every 5 seconds
GET /api/bulk/status/{job_id}

// While uploading:
{
  "status": "uploading_to_archipelago",
  "progress": { ... }
}

// After upload completes:
{
  "status": "completed",
  "archipelago_result": {
    "ami_set_id": 12345,
    "name": "My Collection",
    "message": "Process it at: https://archipelago.example.com/node/12345"
  }
}
```

## Files Changed
- `backend/app/routes/bulk.py` - Added GET /api/bulk/status/<job_id> endpoint
- `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx` - Fixed polling logic

## What Works Now
✅ Polling endpoint exists  
✅ Returns Archipelago upload status  
✅ Frontend can track progress  
✅ No more "Failed to fetch" errors  
✅ User sees real-time status updates  

## Testing
```bash
1. Start bulk OCR job
2. Click "Upload to Archipelago"
3. Check browser console - should see polling requests
4. Should see "Processing in background..." message
5. Status should update every 5 seconds
6. After upload completes, should show success
```
