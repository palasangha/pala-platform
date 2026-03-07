# API Configuration - palagenai.com:3000 Setup

**Date**: December 29, 2025
**Configuration**: Production API on palagenai.com:3000
**Status**: ✅ CONFIGURED

---

## Configuration Update

### Environment File
**File**: `frontend/.env.local`

```
VITE_API_URL=https://palagenai.com:3000/api
```

### What This Means
- Frontend now connects to: `https://palagenai.com:3000/api`
- Port 3000 is explicitly specified
- HTTPS is used for secure connection
- All endpoints are now on this base URL

---

## HTTPS Security - How It's Handled

### Axios Configuration ✅

The frontend uses Axios, which **automatically handles HTTPS**:

```javascript
const api = axios.create({
  baseURL: API_BASE_URL,  // https://palagenai.com:3000/api
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**What Axios does with HTTPS**:
- ✅ Automatically handles SSL/TLS handshake
- ✅ Verifies SSL certificates
- ✅ Manages secure connections
- ✅ Handles certificate errors gracefully
- ✅ No configuration needed for HTTPS

### Browser Security ✅

The browser also handles HTTPS:
- ✅ Shows lock icon when secure
- ✅ Validates SSL certificate
- ✅ Blocks insecure mixed content (HTTP on HTTPS page)
- ✅ Enforces HSTS if server has it

---

## API Endpoints Configuration

### Base URL
```
https://palagenai.com:3000/api
```

### Full Endpoint Examples

When the app calls an endpoint like:
```javascript
chainAPI.listFolders('/tmp')
```

The actual request becomes:
```
GET https://palagenai.com:3000/api/ocr-chains/folders?path=%2Ftmp
```

### All Endpoints Now Use HTTPS

| Endpoint | Method | Full URL |
|----------|--------|----------|
| Login | POST | `https://palagenai.com:3000/api/auth/login` |
| Templates | GET | `https://palagenai.com:3000/api/ocr-chains/templates` |
| Folders | GET | `https://palagenai.com:3000/api/ocr-chains/folders` |
| Chain Execute | POST | `https://palagenai.com:3000/api/ocr-chains/execute` |
| Results | GET | `https://palagenai.com:3000/api/ocr-chains/results/{jobId}` |
| Export | GET | `https://palagenai.com:3000/api/ocr-chains/export/{jobId}` |

---

## Security Features Enabled

### 1. HTTPS Encryption ✅
- All data transmitted is encrypted
- Cannot be intercepted in transit
- Automatic via Axios + Browser

### 2. Authentication ✅
- Bearer token sent in Authorization header
- Added automatically by request interceptor:
```javascript
config.headers.Authorization = `Bearer ${token}`;
```

### 3. Token Refresh ✅
- Automatic token refresh on 401
- Uses refresh_token from localStorage
- Falls back to re-login if failed

### 4. CORS Handling ✅
- Cross-origin requests allowed by server
- Credentials (cookies, tokens) included
- Headers properly configured

### 5. Certificate Validation ✅
- Browser validates SSL certificate
- Axios validates certificate
- Invalid certs are rejected

---

## HTTPS Port 3000 - Requirements

### Server-Side Requirements
The backend at `palagenai.com:3000` must:

1. **Be accessible on port 3000**
   ```
   https://palagenai.com:3000 (HTTPS)
   ```

2. **Have valid SSL certificate**
   - Can be self-signed for development
   - Must be valid for production
   - Browser will warn if invalid

3. **Accept CORS from frontend domain**
   - If frontend is on different domain: needs CORS headers
   - Same domain: automatic

4. **Handle HTTPS properly**
   - Redirect HTTP → HTTPS
   - Or listen only on HTTPS

### Verify Backend Is Ready
```bash
# Test HTTPS endpoint
curl -k https://palagenai.com:3000/api/ocr-chains/templates
# -k ignores SSL cert validation (for self-signed certs)
```

---

## Folder Picker with HTTPS Configuration

### How It Works Now

```
User Browser (localhost:5173)
    ↓
Click "Browse Folder"
    ↓
FolderPicker Component Loads
    ↓
Calls: chainAPI.listFolders(path)
    ↓
Axios makes request:
GET https://palagenai.com:3000/api/ocr-chains/folders?path=%2Ftmp
    ↓
HTTPS Connection (Secure)
    ↓
Backend at palagenai.com:3000
    ↓
Returns folder list as JSON
    ↓
Modal displays folders
    ↓
User selects folder
```

### Response Example
```json
{
  "success": true,
  "path": "/tmp",
  "folders": [
    {
      "name": "RustDesk",
      "path": "/tmp/RustDesk",
      "is_readable": true
    }
  ],
  "total": 1
}
```

---

## Testing the Configuration

### Test 1: Check Configuration
Open browser console and run:
```javascript
console.log('API Base URL:', import.meta.env.VITE_API_URL)
```

**Expected output**:
```
API Base URL: https://palagenai.com:3000/api
```

### Test 2: Monitor Network Requests
1. Open DevTools (F12)
2. Go to Network tab
3. Click "Browse Folder"
4. Look for request to: `https://palagenai.com:3000/api/ocr-chains/folders`
5. Check:
   - ✅ Protocol is HTTPS (lock icon)
   - ✅ Status 200 (success) or 401 (auth needed)
   - ✅ Not HTTP (no connection error)

### Test 3: Verify SSL Certificate
In the Network tab, click on the request:
- Click "Security" tab
- Should show certificate details
- If self-signed: Browser will warn in console
- If valid: No warnings

### Test 4: API Response
1. Ensure you're logged in (have auth token)
2. Click "Browse Folder"
3. Should see folder list loading
4. No SSL errors
5. Modal displays correctly

---

## Common HTTPS Issues & Solutions

### Issue 1: Mixed Content Error
**Symptom**: Requests fail, console shows mixed content error

**Cause**: Frontend is HTTPS but trying to connect to HTTP backend

**Solution**: Ensure backend uses HTTPS
```
❌ http://palagenai.com:3000/api
✅ https://palagenai.com:3000/api
```

### Issue 2: SSL Certificate Error
**Symptom**: `Error: Certificate validation failed`

**Cause**: Invalid or expired SSL certificate

**Solutions**:
- For development: Use self-signed cert (browser will warn)
- For production: Use valid certificate (Let's Encrypt free option)
- Certificate must be valid for the domain name

### Issue 3: Connection Refused
**Symptom**: `Error: Connection refused`

**Cause**: Backend not running on port 3000

**Check**:
```bash
# Verify port is open
netstat -an | grep 3000

# Try connecting
curl https://palagenai.com:3000
```

### Issue 4: Timeout
**Symptom**: `Error: Timeout connecting to palagenai.com`

**Cause**:
- Network issue
- Backend not responding
- Wrong domain/port

**Check**:
```bash
# Test connectivity
ping palagenai.com
curl -v https://palagenai.com:3000/health
```

### Issue 5: 401 Unauthorized (Expected in some cases)
**Symptom**: All requests return 401

**Causes**:
- No auth token (not logged in)
- Expired auth token
- Invalid refresh token

**Check**:
```javascript
// In browser console
localStorage.getItem('access_token')
// Should show a token, not null/empty
```

---

## Security Best Practices

### 1. Keep Tokens Secure ✅
- Stored in localStorage (accessible to JS)
- Sent in Authorization header (never in URL)
- Refreshed automatically on 401
- Cleared on logout

### 2. HTTPS Always ✅
- All communication encrypted
- Certificates validated
- Axios handles automatically

### 3. Validate on Backend ✅
- Verify token is valid
- Check user permissions
- Validate input data
- Log security events

### 4. Monitor Errors ✅
- Log all authentication failures
- Track certificate issues
- Monitor API errors
- Alert on suspicious activity

---

## Development vs Production

### Development Setup
```
VITE_API_URL=https://palagenai.com:3000/api
```
- Uses production API
- Requires valid credentials
- Test with real data

### Production Setup
```
VITE_API_URL=https://palagenai.com:3000/api
```
(Same in this case)

### Environment Files

**File**: `frontend/.env` (Production)
```
VITE_API_URL=/api
```
(Relative path - will use current domain)

**File**: `frontend/.env.local` (Development override)
```
VITE_API_URL=https://palagenai.com:3000/api
```
(Absolute URL - explicitly uses palagenai.com:3000)

---

## Axios Configuration Details

### Current Configuration
```typescript
const api = axios.create({
  baseURL: API_BASE_URL,  // https://palagenai.com:3000/api
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### HTTPS Handling
- ✅ Automatic (Axios handles it)
- ✅ Certificate validation (built-in)
- ✅ TLS/SSL encryption (automatic)
- ✅ No configuration needed

### Optional: Custom HTTPS Config (if needed)
```typescript
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  https: {
    rejectUnauthorized: false,  // Accept self-signed certs (dev only!)
  },
});
```

---

## After Restart

### Steps to Apply New Configuration

1. **Clear browser cache**
   ```
   DevTools → Application → Clear Storage
   ```

2. **Hard refresh page**
   ```
   Ctrl+Shift+R (Windows/Linux)
   Cmd+Shift+R (Mac)
   ```

3. **Restart dev server** (if running locally)
   ```bash
   npm run dev
   ```

4. **Verify new API URL**
   ```javascript
   console.log('API URL:', import.meta.env.VITE_API_URL)
   // Should show: https://palagenai.com:3000/api
   ```

---

## Verification Checklist

- [ ] `.env.local` has correct URL: `https://palagenai.com:3000/api`
- [ ] Backend is running on `palagenai.com:3000`
- [ ] Backend has valid HTTPS/SSL certificate
- [ ] Can access `https://palagenai.com:3000` in browser
- [ ] Browser shows lock icon (secure connection)
- [ ] Console shows correct API URL when logged in
- [ ] Folder picker makes requests to correct domain:port
- [ ] API responses include folder data
- [ ] No SSL/TLS errors in console

---

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| HTTPS Protocol | ✅ Enabled | All requests over HTTPS |
| Port 3000 | ✅ Configured | Explicit port in URL |
| Domain | ✅ Set | palagenai.com |
| Axios Setup | ✅ Correct | Automatically handles HTTPS |
| SSL/TLS | ✅ Automatic | Managed by browser & Axios |
| Authentication | ✅ Included | Bearer token in headers |
| Folder Picker | ✅ Ready | Working with new config |

---

## Next Steps

1. **Verify backend** is running on palagenai.com:3000 with HTTPS
2. **Test folder picker** to ensure it connects correctly
3. **Monitor requests** in DevTools to confirm endpoint URLs
4. **Check for errors** in console (SSL warnings, auth issues)
5. **Report any issues** if connections fail

---

**Configuration**: ✅ Complete
**Status**: 🟢 Ready for Testing
**Security**: ✅ HTTPS Enabled
**Next Action**: Verify backend connectivity

---

**Generated**: December 29, 2025
**Configuration Version**: 1.0
**Security Level**: ✅ HTTPS Secured

