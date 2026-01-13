# Frontend Logging Guide for Failed to Fetch Debugging

## Overview

Comprehensive logging has been added to the frontend to help debug "Failed to fetch" errors during Archipelago uploads.

## Log Categories

### 1. **[FETCH]** - General HTTP Request Logging
Logs all authenticated fetch requests and network-level issues.

**What it logs:**
- Request URL and method
- Token availability
- Request headers
- Response status codes
- Response metadata (content-type, content-length)
- Network errors (TypeError, etc.)
- SSL/CORS errors

**Example output:**
```
[FETCH] Starting request to: /api/archipelago/push-bulk-ami
[FETCH] Method: POST
[FETCH] Has token: true
[FETCH] Sending request with headers: ['Authorization', 'Content-Type']
[FETCH] Response status: 202
[FETCH] Response ok: true
[FETCH] Response headers: {content-type: "application/json", content-length: "156"}
```

### 2. **[UPLOAD]** - Archipelago Upload Flow
High-level logging of the entire upload process.

**What it logs:**
- Job ID
- Number of successful samples
- Collection title
- Request initiation
- Response status
- Parsing of response data
- Polling interval start
- Timeout warnings
- Errors at any stage

**Example output:**
```
[UPLOAD] Starting Archipelago upload for job: abc123
[UPLOAD] Successful samples: 150
[UPLOAD] Collection title: Documents - 12/21/2024
[UPLOAD] Sending POST request to /api/archipelago/push-bulk-ami
[UPLOAD] Response received: 202
[UPLOAD] Response ok: true
[UPLOAD] Upload request accepted (202)
[UPLOAD] Starting polling interval for job abc123
```

### 3. **[POLL]** - Status Polling Loop
Detailed logging of the polling mechanism checking for completion.

**What it logs:**
- Each poll attempt
- Response status code
- Status data received
- Detection of completion
- Processing still ongoing
- Polling errors
- Response parsing failures

**Example output:**
```
[POLL] Checking status for job abc123
[POLL] Status response code: 200
[POLL] Status data received: {status: "uploading_to_archipelago", ...}
[POLL] Still uploading... status: uploading_to_archipelago
```

After upload completes:
```
[POLL] Checking status for job abc123
[POLL] Status response code: 200
[POLL] ✅ Upload complete! {ami_set_id: 12345, ...}
```

## How to Access Logs

### Step 1: Open Browser Developer Tools
```
Windows/Linux: F12 or Ctrl+Shift+I
Mac: Cmd+Option+I
```

### Step 2: Go to Console Tab
Click on the "Console" tab to see all logs.

### Step 3: Filter by Log Category
Type in the console filter box to see specific logs:
- `[FETCH]` - Network requests
- `[UPLOAD]` - Upload process
- `[POLL]` - Status polling
- `❌` - Errors only

## Common Error Scenarios

### Scenario 1: "Failed to fetch" on Initial Upload Request

**Log pattern:**
```
[UPLOAD] Starting Archipelago upload for job: xyz
[UPLOAD] Sending POST request to /api/archipelago/push-bulk-ami
[FETCH] Network error for /api/archipelago/push-bulk-ami: TypeError: Failed to fetch
[FETCH] Error type: TypeError
[FETCH] Error message: Failed to fetch
[FETCH] This is likely a network/CORS/SSL error
[UPLOAD] ❌ CRITICAL ERROR: TypeError: Failed to fetch
```

**Possible causes:**
1. **SSL/Certificate Issue** - See [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md)
2. **Network/Firewall** - Backend unreachable
3. **CORS Issue** - Check backend CORS configuration
4. **Backend not running** - Verify backend is started

**Solution:**
- Check `ARCHIPELAGO_VERIFY_SSL` environment variable
- Verify backend server is running and accessible
- Check network connectivity
- Review browser console for additional errors

### Scenario 2: 401 Unauthorized

**Log pattern:**
```
[FETCH] Response status: 401
[FETCH] Response ok: false
[FETCH] Got 401 - attempting token refresh
[FETCH] Token refreshed, retrying request
[FETCH] Retry response status: 202
```

**This is normal** - System automatically refreshes token and retries.

### Scenario 3: 500 Server Error

**Log pattern:**
```
[UPLOAD] Response received: 500
[UPLOAD] Response ok: false
[UPLOAD] ❌ Error from server: Internal Server Error
```

**Solution:**
- Check backend logs for error details
- Verify Archipelago server is reachable
- Check database connectivity

### Scenario 4: Polling Fails

**Log pattern:**
```
[POLL] Checking status for job xyz
[FETCH] Network error for /api/bulk/status/xyz: TypeError: Failed to fetch
[POLL] ❌ Error polling for result: TypeError: Failed to fetch
[POLL] Error details: Failed to fetch
```

**Possible causes:**
- Backend restarted or crashed
- Network interruption
- SSL/certificate issue

**Solution:**
- Check backend status
- Verify network connectivity
- Review [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md)

### Scenario 5: Polling Timeout

**Log pattern:**
```
[UPLOAD] Polling started, will timeout in 30 minutes
... (5+ minutes of polling) ...
[UPLOAD] ⏱️ Polling timeout - 30 minutes elapsed
```

**Possible causes:**
- Archipelago upload taking very long
- Stuck in background processing
- Backend task not completing

**Solution:**
- Check backend logs for background task status
- Verify Archipelago server status
- Check available disk space on Archipelago server

## Complete Upload Flow Logs

### Successful Upload (Summary)
```
[UPLOAD] Starting Archipelago upload for job: abc123
[UPLOAD] Successful samples: 150
[UPLOAD] Sending POST request to /api/archipelago/push-bulk-ami
[FETCH] Starting request to: /api/archipelago/push-bulk-ami
[FETCH] Response status: 202
[UPLOAD] Response received: 202
[UPLOAD] Upload request accepted (202)
[UPLOAD] Starting polling interval for job abc123
[POLL] Checking status for job abc123
[POLL] Status response code: 200
[POLL] Still uploading... status: uploading_to_archipelago
... (repeats every 5 seconds) ...
[POLL] ✅ Upload complete! {ami_set_id: 12345, ...}
```

### Failed Upload (Network Error)
```
[UPLOAD] Starting Archipelago upload for job: xyz
[UPLOAD] Sending POST request to /api/archipelago/push-bulk-ami
[FETCH] Starting request to: /api/archipelago/push-bulk-ami
[FETCH] Network error for /api/archipelago/push-bulk-ami: TypeError: Failed to fetch
[FETCH] Error type: TypeError
[FETCH] This is likely a network/CORS/SSL error
[UPLOAD] ❌ CRITICAL ERROR: TypeError: Failed to fetch
```

## Capturing Logs for Support

### Option 1: Screenshot Console
Press F12, switch to Console tab, and take a screenshot of the logs.

### Option 2: Export Console Logs
Run this in the console to get all logs as text:
```javascript
// Copy this to browser console and run:
copy(
  Array.from(document.querySelectorAll('.console-log-item, .console-message'))
    .map(el => el.textContent)
    .join('\n')
)
// Then paste with Ctrl+V / Cmd+V
```

### Option 3: Use Browser DevTools Features
1. Right-click on console
2. Select "Save as" to save console output
3. Or use browser's built-in Console history

## Log Levels

### Info Level (Default)
```
[FETCH] Starting request...
[UPLOAD] Starting Archipelago upload...
[POLL] Checking status...
```

### Warning Level
```
⚠️ Network proxy warning
⏱️ Polling timeout warning
```

### Error Level
```
❌ CRITICAL ERROR
[POLL] ❌ Bad response status
[FETCH] Network error
```

## Advanced Debugging

### Check Token in Console
```javascript
localStorage.getItem('access_token')
```

### Test API Endpoint Directly
```javascript
// Test upload endpoint
fetch('/api/archipelago/push-bulk-ami', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    job_id: 'test-job-id',
    collection_title: 'Test'
  })
})
  .then(r => {
    console.log('Status:', r.status);
    return r.json();
  })
  .then(d => console.log('Response:', d))
  .catch(e => console.error('Error:', e));
```

### Check Network Tab
1. Open DevTools (F12)
2. Go to "Network" tab
3. Trigger upload
4. Look for requests to:
   - `/api/archipelago/push-bulk-ami` (should be 202)
   - `/api/bulk/status/{job_id}` (should be 200, repeating)
5. Click each request to see:
   - Request headers (especially Authorization)
   - Response status
   - Response body (JSON)
   - Request timing

## Related Documentation

- [ARCHIPELAGO_API_TIMEOUT_FIX.md](./ARCHIPELAGO_API_TIMEOUT_FIX.md) - Async implementation
- [ARCHIPELAGO_POLLING_FIX.md](./ARCHIPELAGO_POLLING_FIX.md) - Polling endpoint
- [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md) - SSL/HTTPS issues
- [ARCHIPELAGO_TIMEOUT_QUICK_FIX.md](./ARCHIPELAGO_TIMEOUT_QUICK_FIX.md) - Quick reference

## Summary

The logging system provides detailed information about:
1. **Network layer** - [FETCH] logs
2. **Business logic** - [UPLOAD] logs
3. **Polling mechanism** - [POLL] logs
4. **Error details** - Full error context and stack traces

Use these logs to:
- Understand where the upload process fails
- Identify network vs. application issues
- Provide detailed bug reports
- Debug SSL/HTTPS problems
- Monitor polling progress
