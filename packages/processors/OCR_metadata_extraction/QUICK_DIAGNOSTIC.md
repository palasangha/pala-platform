# Quick Diagnostic: Failed to Fetch Troubleshooting

## TL;DR - Quick Fixes

1. **Open browser console** (F12 → Console tab)
2. **Look for [FETCH] or [UPLOAD] logs with ❌**
3. **Check error type:**

| Error Message | Fix |
|---------------|-----|
| `Failed to fetch` | Check SSL/CORS → See [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md) |
| `net::ERR_NETWORK_CHANGED` | SSL issue → Add `ARCHIPELAGO_VERIFY_SSL=false` to .env |
| `401 Unauthorized` | Token expired → Refresh page and try again |
| `500 Internal Server Error` | Backend problem → Check backend logs |
| `404 Not Found` | Wrong API endpoint → Backend not running |

## Step-by-Step Diagnosis

### Step 1: Start a Bulk OCR Job
1. Go to Bulk OCR section
2. Select folder with images
3. Click "Process"
4. Wait for completion

### Step 2: Open Browser Console
```
F12 (Windows/Linux) or Cmd+Option+I (Mac)
→ Click "Console" tab
```

### Step 3: Click "Upload to Archipelago"
Watch the console for logs starting with:
- `[UPLOAD]` - Upload initialization
- `[FETCH]` - Network requests
- `[POLL]` - Status checking

### Step 4: Check for Error Logs
Look for lines with:
- `❌` (red X) - Errors
- `⏱️` (clock) - Timeouts
- `⚠️` (warning) - Issues

### Step 5: Identify Problem

**If you see:**
```
[FETCH] Network error for /api/archipelago/push-bulk-ami: TypeError: Failed to fetch
[FETCH] This is likely a network/CORS/SSL error
```
→ **Solution:** SSL/HTTPS problem - Follow [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md)

**If you see:**
```
[UPLOAD] Response received: 500
[UPLOAD] ❌ Error from server: Internal Server Error
```
→ **Solution:** Backend error - Check server logs: `docker logs gvpocr-backend`

**If you see:**
```
[POLL] Status response code: 404
```
→ **Solution:** Endpoint not found - Backend API might be down

**If you see multiple:**
```
[POLL] Checking status for job xyz
[POLL] Still uploading... status: uploading_to_archipelago
```
→ **Normal** - Just waiting for Archipelago upload to complete (5-30 mins)

## Common Issues & Quick Fixes

### Issue 1: SSL Certificate Error
**Signs:**
- `Failed to fetch` immediately
- `net::ERR_NETWORK_CHANGED`
- No [UPLOAD] logs, just [FETCH] error

**Quick Fix:**
```bash
# Add to .env file
ARCHIPELAGO_VERIFY_SSL=false

# Restart backend
docker-compose restart backend
```

### Issue 2: Backend Not Reachable
**Signs:**
- `Failed to fetch`
- Backend container not running
- No response to any API call

**Quick Fix:**
```bash
# Check backend status
docker ps | grep backend

# Restart backend
docker-compose restart backend

# Check logs
docker logs -f gvpocr-backend
```

### Issue 3: Token Expired
**Signs:**
- `[FETCH] Response status: 401`
- Then `[FETCH] Token refreshed, retrying request`

**Quick Fix:**
- This is automatic, should retry
- If keeps happening, refresh page and login again

### Issue 4: Long Upload Time (Still Processing)
**Signs:**
- `[POLL] Still uploading... status: uploading_to_archipelago`
- Repeats every 5 seconds for 5-30+ minutes

**This is normal!**
- Large files take time to upload
- Archipelago takes time to process
- Wait and check back later

### Issue 5: Archipelago Server Down
**Signs:**
- `[UPLOAD] Response received: 500` or `503`
- Error from Archipelago, not from your app

**Quick Fix:**
- Verify Archipelago server is running
- Check Archipelago server logs
- Wait for Archipelago to recover

## Information to Provide When Reporting Issues

**For GitHub issue or support:**

1. **Your error logs** (Copy from console):
   ```
   [UPLOAD] Starting Archipelago upload for job: xyz
   [FETCH] Network error: ...
   ... (all [FETCH], [UPLOAD], [POLL] logs)
   ```

2. **Environment info:**
   ```
   ARCHIPELAGO_BASE_URL=?
   ARCHIPELAGO_VERIFY_SSL=?
   Backend running? (docker ps | grep backend)
   ```

3. **Network info:**
   ```
   Can access backend API? (curl http://localhost:5000/api/health)
   Can access Archipelago? (curl https://your-archipelago.com)
   ```

4. **Backend logs:**
   ```
   docker logs -f gvpocr-backend | grep -i "error\|archipelago"
   ```

## Advanced: Network Tab Analysis

1. Open DevTools (F12)
2. Go to "Network" tab
3. Trigger upload
4. Look for requests:

**Expected:**
```
POST /api/archipelago/push-bulk-ami      → 202 Accepted ✓
GET  /api/bulk/status/{id}               → 200 OK ✓ (repeats)
```

**Problems:**
```
POST /api/archipelago/push-bulk-ami      → (no response) ❌ Network error
GET  /api/bulk/status/{id}               → 404 Not Found ❌ Endpoint missing
GET  /api/bulk/status/{id}               → 401 Unauthorized ❌ Token issue
```

## When to Check Logs

| Action | Log to Check |
|--------|--------------|
| Click "Upload to Archipelago" | `[UPLOAD] Starting...` |
| Request sent | `[FETCH] Response status:` |
| Upload accepted | `[UPLOAD] Upload request accepted (202)` |
| Waiting for completion | `[POLL] Still uploading...` |
| Upload complete | `[POLL] ✅ Upload complete!` |
| Error occurs | Look for `❌` in logs |

## Quick Log Search

In browser console, type:
```javascript
// Find errors
console.log("Search console for: ❌")

// Count polling attempts
console.log("Type in filter box: [POLL]")

// Find SSL issues
console.log("Type in filter box: Failed to fetch")
```

## Need More Help?

1. **See full guide:** [FRONTEND_LOGGING_GUIDE.md](./FRONTEND_LOGGING_GUIDE.md)
2. **SSL issues:** [HTTPS_SSL_TROUBLESHOOTING.md](./HTTPS_SSL_TROUBLESHOOTING.md)
3. **Timeout issues:** [ARCHIPELAGO_API_TIMEOUT_FIX.md](./ARCHIPELAGO_API_TIMEOUT_FIX.md)
4. **Polling issues:** [ARCHIPELAGO_POLLING_FIX.md](./ARCHIPELAGO_POLLING_FIX.md)

---

**Key Point:** The console logs now tell you exactly what happened, where it failed, and why. Check them first before anything else!
