# Bulk Processing Pause/Resume Feature

## Overview

The bulk processing system now supports pausing and resuming jobs, with automatic error recovery and retry logic. This feature allows:

- **Pause/Resume Jobs**: Manually pause and resume bulk processing at any time
- **Automatic Error Handling**: Auto-pause on network failures or consecutive errors
- **Retry Logic**: Automatic retry with exponential backoff for failed files
- **State Persistence**: Job state is maintained across pauses
- **Graceful Recovery**: Network disconnections are handled gracefully

---

## Features

### 1. **Manual Pause/Resume**

Users can pause a running job and resume it later:
- Pause processing at any point
- Resume from where it left off
- No data loss or duplication

### 2. **Auto-Pause on Errors**

Automatically pauses after **5 consecutive errors**:
- Prevents runaway error loops
- Gives time to fix issues (network, provider, etc.)
- Manual resume required after auto-pause

### 3. **Retry Logic**

Each file is retried up to **3 times** with exponential backoff:
- 1st retry: 2 seconds delay
- 2nd retry: 4 seconds delay
- 3rd retry: 8 seconds delay
- Network errors trigger immediate retry
- Other errors retry on next attempt

### 4. **Network Disconnect Handling**

Detects and handles network errors:
- Connection timeout
- Connection refused
- Network unreachable
- Connection reset

Auto-retries network errors with backoff, then auto-pauses if persistent.

### 5. **State Checkpointing**

Job state is tracked and can be saved:
- Processed file count
- Successful results
- Error log with retry counts
- Current state (running/paused/stopped)

---

## API Endpoints

### Pause a Job

```bash
POST /api/bulk/pause/<job_id>
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Job paused successfully",
  "job_id": "abc-123",
  "state": "paused"
}
```

### Resume a Job

```bash
POST /api/bulk/resume/<job_id>
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Job resumed successfully",
  "job_id": "abc-123",
  "state": "running"
}
```

### Stop/Cancel a Job

```bash
POST /api/bulk/stop/<job_id>
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled successfully",
  "job_id": "abc-123",
  "state": "stopped"
}
```

### Get Job State

```bash
GET /api/bulk/state/<job_id>
Authorization: Bearer <token>
```

**Response:**
```json
{
  "job_id": "abc-123",
  "state": "paused",
  "is_paused": true,
  "is_stopped": false,
  "checkpoint": {
    "processed_count": 50,
    "results_count": 48,
    "errors_count": 2,
    "consecutive_errors": 0,
    "retry_count": {
      "/path/to/file1.jpg": 1,
      "/path/to/file2.jpg": 2
    }
  }
}
```

---

## Usage Examples

### Example 1: Pause and Resume a Job

```bash
# Start bulk processing
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/images",
    "provider": "google_vision",
    "parallel": true,
    "max_workers": 4
  }'

# Response
{
  "job_id": "abc-123",
  "progress_url": "/api/bulk/progress/abc-123"
}

# Check progress
curl http://localhost:5000/api/bulk/progress/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Pause the job
curl -X POST http://localhost:5000/api/bulk/pause/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Job is now paused - do maintenance, fix network, etc.

# Resume the job
curl -X POST http://localhost:5000/api/bulk/resume/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Job continues from where it left off
```

### Example 2: Handle Network Disconnection

**Scenario**: Processing 100 files when network disconnects

**What Happens**:
1. File 45 fails with "Connection timeout"
2. System retries after 2s → Still fails
3. System retries after 4s → Still fails
4. System retries after 8s → Still fails
5. File 46 fails (consecutive error count: 2)
6. File 47 fails (consecutive error count: 3)
7. File 48 fails (consecutive error count: 4)
8. File 49 fails (consecutive error count: 5)
9. **Auto-pause triggered** ⏸️

**User Actions**:
```bash
# Check job state
curl http://localhost:5000/api/bulk/state/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response shows auto-paused
{
  "state": "paused",
  "is_paused": true,
  "checkpoint": {
    "processed_count": 49,
    "results_count": 44,
    "errors_count": 5,
    "consecutive_errors": 5
  }
}

# Fix network issue

# Resume processing
curl -X POST http://localhost:5000/api/bulk/resume/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Processing continues from file 50
# Previously failed files (45-49) are retried
```

### Example 3: Stop a Running Job

```bash
# User decides to cancel the job
curl -X POST http://localhost:5000/api/bulk/stop/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "success": true,
  "message": "Job cancelled successfully",
  "state": "stopped"
}

# Job stops immediately
# Partial results are still available
curl http://localhost:5000/api/bulk/progress/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Configuration

### Retry Settings

Located in [app/services/bulk_processor.py](app/services/bulk_processor.py):

```python
# Maximum retries per file
self._max_retries = 3

# Auto-pause threshold
self._max_consecutive_errors = 5
```

**To change defaults**, edit the `BulkProcessor.__init__` method:

```python
def __init__(self, ..., max_retries=3, auto_pause_threshold=5):
    self._max_retries = max_retries
    self._max_consecutive_errors = auto_pause_threshold
```

### Retry Delay

Exponential backoff formula:
```python
retry_delay = min(2 ** attempt, 30)  # Max 30 seconds
```

**Examples**:
- Attempt 1: 2^0 = 1s
- Attempt 2: 2^1 = 2s
- Attempt 3: 2^2 = 4s
- Attempt 4: 2^3 = 8s
- Attempt 5: 2^4 = 16s
- Attempt 6+: 30s (capped)

---

## State Machine

```
[START]
   ↓
[RUNNING] ←---→ [PAUSED]
   ↓               ↓
   ↓           [RESUMED]
   ↓               ↓
   └──→ [COMPLETED] ←──┘
   │
   └──→ [STOPPED/CANCELLED]
   │
   └──→ [ERROR]
```

**State Transitions**:

| From | To | Trigger |
|------|-------|---------|
| RUNNING | PAUSED | Manual pause or auto-pause |
| PAUSED | RUNNING | Manual resume |
| RUNNING | STOPPED | Manual stop |
| RUNNING | COMPLETED | All files processed |
| RUNNING | ERROR | Unrecoverable error |
| PAUSED | STOPPED | Manual stop while paused |

---

## Error Handling

### Network Error Detection

Automatically detected errors:
- `connection`
- `timeout`
- `network`
- `unreachable`
- `refused`
- `reset`

**Behavior**:
- Immediate retry with exponential backoff
- Up to max_retries attempts
- If all attempts fail → marked as error

### Consecutive Error Tracking

Tracks errors across different files:
- **Success** → Reset consecutive error count
- **Error** → Increment count
- **Count ≥ 5** → Auto-pause

**Reset on**:
- Manual resume
- Successful file processing

### Retry Tracking

Per-file retry count stored:
```python
{
  "/path/to/file1.jpg": 2,  # Failed twice
  "/path/to/file2.png": 1   # Failed once
}
```

**Cleared on**:
- Successful processing
- Job completion

---

## Implementation Details

### BulkProcessor Class

**Key Methods**:

```python
# Control methods
processor.pause()          # Pause processing
processor.resume()         # Resume processing
processor.stop()           # Stop/cancel processing

# State queries
processor.is_paused()      # Returns bool
processor.is_stopped()     # Returns bool
processor.get_state()      # Returns 'running'|'paused'|'stopped'

# Checkpoint
processor.get_checkpoint_data()        # Get current state
processor.restore_from_checkpoint(data) # Restore from state
```

**Thread Safety**:
- Uses `threading.Lock` for shared data
- Uses `threading.Event` for pause/resume signals
- Safe for parallel processing

### File Processing Flow

```python
for each file:
    1. Check if stopped → Exit
    2. Wait if paused → Block until resumed
    3. Try processing (up to max_retries):
        a. Process file
        b. On success → Reset error count
        c. On error:
            - Check if network error
            - Increment consecutive errors
            - If consecutive_errors >= threshold → Auto-pause
            - Apply retry delay with exponential backoff
            - Retry or fail
    4. Record result/error
    5. Update progress
```

---

## Database Schema

Jobs now include additional fields:

```javascript
{
  job_id: "abc-123",
  user_id: "user-456",
  status: "paused",  // "processing", "paused", "completed", "cancelled", "error"
  created_at: ISODate("2025-11-28T..."),
  updated_at: ISODate("2025-11-28T..."),
  folder_path: "/path/to/images",
  provider: "google_vision",
  parallel: true,
  max_workers: 4,

  // Pause/resume fields
  checkpoint: {
    processed_count: 50,
    results_count: 48,
    errors_count: 2,
    consecutive_errors: 0,
    retry_count: {
      "/path/file.jpg": 1
    },
    state: "paused"
  },

  results: {
    // Partial or complete results
  }
}
```

---

## Frontend Integration

### UI Components Needed

**1. Job Control Buttons**
```jsx
{job.status === 'processing' && (
  <button onClick={() => pauseJob(job.id)}>
    ⏸️ Pause
  </button>
)}

{job.status === 'paused' && (
  <button onClick={() => resumeJob(job.id)}>
    ▶️ Resume
  </button>
)}

{(job.status === 'processing' || job.status === 'paused') && (
  <button onClick={() => stopJob(job.id)}>
    ⏹️ Stop
  </button>
)}
```

**2. Status Badge**
```jsx
const statusColors = {
  processing: 'blue',
  paused: 'yellow',
  completed: 'green',
  cancelled: 'gray',
  error: 'red'
};

<Badge color={statusColors[job.status]}>
  {job.status.toUpperCase()}
</Badge>
```

**3. Error Information**
```jsx
{job.checkpoint?.consecutive_errors > 0 && (
  <Alert type="warning">
    {job.checkpoint.consecutive_errors} consecutive errors detected.
    {job.checkpoint.consecutive_errors >= 5 && " Job auto-paused."}
  </Alert>
)}
```

### API Integration

```typescript
// Pause job
async function pauseJob(jobId: string) {
  const response = await fetch(`/api/bulk/pause/${jobId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// Resume job
async function resumeJob(jobId: string) {
  const response = await fetch(`/api/bulk/resume/${jobId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// Stop job
async function stopJob(jobId: string) {
  const response = await fetch(`/api/bulk/stop/${jobId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// Get job state
async function getJobState(jobId: string) {
  const response = await fetch(`/api/bulk/state/${jobId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

---

## Testing

### Test Scenario 1: Manual Pause/Resume

```bash
# 1. Start job
JOB_ID=$(curl -X POST http://localhost:5000/api/bulk/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"folder_path":"/path/to/100images","provider":"tesseract"}' \
  | jq -r '.job_id')

# 2. Wait a bit
sleep 5

# 3. Pause
curl -X POST http://localhost:5000/api/bulk/pause/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# 4. Check state
curl http://localhost:5000/api/bulk/state/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# 5. Resume
curl -X POST http://localhost:5000/api/bulk/resume/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# 6. Wait for completion
while true; do
  STATUS=$(curl -s http://localhost:5000/api/bulk/progress/$JOB_ID \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  sleep 2
done
```

### Test Scenario 2: Auto-Pause on Network Error

```bash
# 1. Start job with provider that will fail
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"folder_path":"/path/to/images","provider":"offline_provider"}'

# 2. Simulate network disconnect (stop provider service)
docker-compose stop some-provider-service

# 3. Monitor for auto-pause
watch -n 1 'curl -s http://localhost:5000/api/bulk/state/$JOB_ID \
  -H "Authorization: Bearer $TOKEN" | jq ".state"'

# 4. When paused, restore network
docker-compose start some-provider-service

# 5. Resume
curl -X POST http://localhost:5000/api/bulk/resume/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Logging

### Log Messages

```
INFO: Starting background processing for job abc-123
INFO: Using parallel processing with 4 workers
INFO: Processing 1/100: image001.jpg (attempt 1/4)
ERROR: Error processing image001.jpg (attempt 1/4): Connection timeout
INFO: Retrying image001.jpg in 2s...
INFO: Processing 1/100: image001.jpg (attempt 2/4)
WARNING: Too many consecutive errors (5), auto-pausing job abc-123
INFO: Job abc-123 paused, waiting for resume...
INFO: Pause requested for job abc-123
INFO: Resume requested for job abc-123
INFO: Job abc-123 resumed
INFO: Job abc-123 completed successfully
INFO: Cleaned up processor for job abc-123
```

### Monitoring Logs

```bash
# Follow bulk processor logs
docker-compose logs -f backend | grep -E "Processing|paused|resumed|error"

# Count errors
docker-compose logs backend | grep "Error processing" | wc -l

# Check auto-pause events
docker-compose logs backend | grep "auto-pausing"
```

---

## Troubleshooting

### Issue 1: Job won't resume

**Symptoms**:
- Resume API returns success
- Job stays paused

**Diagnosis**:
```bash
# Check if processor is still active
curl http://localhost:5000/api/bulk/state/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# Check logs
docker-compose logs backend | grep $JOB_ID
```

**Solution**:
- Job may have completed or crashed
- Check database: `db.bulk_jobs.findOne({job_id: "abc-123"})`
- Restart processing if needed

### Issue 2: Too many auto-pauses

**Symptoms**:
- Job keeps auto-pausing
- Many consecutive errors

**Diagnosis**:
```bash
# Check error patterns
docker-compose logs backend | grep -A 5 "Error processing"
```

**Solutions**:
1. **Provider Issues**: Switch provider or fix credentials
2. **Network Issues**: Check connectivity to API endpoints
3. **File Issues**: Check file permissions and formats
4. **Rate Limiting**: Reduce `max_workers` or add delays

### Issue 3: Retries not working

**Symptoms**:
- Files fail immediately without retries

**Diagnosis**:
Check if error is network-related:
```python
is_network_error = any(keyword in error_msg.lower() for keyword in [
    'connection', 'timeout', 'network', 'unreachable', 'refused', 'reset'
])
```

**Solution**:
- Add more keywords to network error detection
- Or force retries for specific error types

---

## Best Practices

### 1. **Set Appropriate Worker Count**

```bash
# For stable network - higher parallelism
"max_workers": 8

# For unstable network - lower parallelism
"max_workers": 2
```

### 2. **Monitor Job Progress**

```javascript
// Poll every 2 seconds
const interval = setInterval(async () => {
  const progress = await getProgress(jobId);

  if (progress.status === 'paused') {
    // Show resume button
    showResumeButton();
  }

  if (progress.status === 'completed') {
    clearInterval(interval);
  }
}, 2000);
```

### 3. **Handle Auto-Pause**

```javascript
if (progress.status === 'paused' &&
    progress.checkpoint?.consecutive_errors >= 5) {
  // Show alert
  alert('Job auto-paused due to errors. Please check and resume.');
}
```

### 4. **Save Partial Results**

Even if job is paused/stopped, partial results are available:
```bash
curl http://localhost:5000/api/bulk/download/$JOB_ID \
  -H "Authorization: Bearer $TOKEN" \
  -o partial_results.zip
```

---

## Summary

✅ **Implemented Features**:
- Manual pause/resume controls
- Auto-pause on consecutive errors
- Retry logic with exponential backoff
- Network error detection
- State management and checkpointing
- Job cancellation
- Thread-safe parallel processing

✅ **API Endpoints**:
- `POST /api/bulk/pause/<job_id>` - Pause job
- `POST /api/bulk/resume/<job_id>` - Resume job
- `POST /api/bulk/stop/<job_id>` - Stop job
- `GET /api/bulk/state/<job_id>` - Get job state

✅ **Error Handling**:
- Up to 3 retries per file
- Exponential backoff (2s, 4s, 8s)
- Auto-pause after 5 consecutive errors
- Network error detection
- Graceful recovery

The bulk processing system is now resilient to network failures and provides full control over long-running jobs!
