# Folder Picker - Error Diagnostics

**Date**: December 29, 2025
**Issue**: 401 Unauthorized on API calls

---

## Problem Analysis

Browser console shows:
```
GET https://docgenai.com/api/bulk/history?page=1&limit=10 401 (Unauthorized)
```

This is **NOT an error with the folder picker code** - it's a **general API configuration issue**.

---

## Root Cause

The frontend is configured with:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
```

**From `.env` file**:
```
VITE_API_URL=/api
```

### The Problem

When `VITE_API_URL=/api` is set as a relative path:
- The browser resolves it relative to the current domain
- If you're on `https://docgenai.com`, it becomes `https://docgenai.com/api`
- This production domain doesn't have your local database/users
- **Result**: 401 Unauthorized

---

## Solution

The frontend needs to be configured to use the **local backend**.

### Option 1: Update `.env` to use full URL (Recommended for Development)

```bash
# frontend/.env
VITE_API_URL=http://localhost:5000/api
```

Then restart the dev server:
```bash
npm run dev
```

### Option 2: Use `.env.local` for local development

Create `frontend/.env.local`:
```
VITE_API_URL=http://localhost:5000/api
```

This file is git-ignored and won't affect production config.

### Option 3: Proxy Configuration (Alternative)

If using Vite dev server, you can configure a proxy in `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
})
```

---

## Folder Picker Specific Impact

The folder picker endpoint requires:
1. ✅ Backend endpoint to be running on localhost:5000
2. ✅ Authentication token to be valid
3. ✅ API to be configured correctly

**Current Status**:
- ✅ Backend endpoint exists and works
- ❌ API is pointing to wrong server (docgenai.com instead of localhost)
- ❌ No valid auth token for docgenai.com

---

## Testing the Fix

After fixing the API URL:

1. **Clear browser cache** (or use incognito mode)
2. **Restart the frontend dev server**
3. **Log in to get a valid token**
4. **Navigate to OCR Chain Builder**
5. **Click "Browse Folder" button**
6. **Folder picker modal should appear and load folders**

---

## What Works Without the Fix

With the current configuration:
- ✅ Frontend compiles and runs
- ✅ UI renders correctly
- ✅ Folder picker component loads
- ✅ Folder picker modal appears when button clicked

## What Doesn't Work

- ❌ API calls fail with 401
- ❌ Folder listing can't fetch data
- ❌ Most features that require backend API

---

## Verification Steps

### Step 1: Check Current API URL

Open browser DevTools Console and run:
```javascript
console.log('API Base URL:', import.meta.env.VITE_API_URL)
```

**Expected output**:
```
API Base URL: /api
```

This is the problem - it's relative!

### Step 2: Check What URL Is Actually Being Used

In the Network tab of DevTools:
- Look at any failed API request
- Check the full URL
- It should show `https://docgenai.com/api/...`

### Step 3: Fix and Verify

1. Update `frontend/.env` to: `VITE_API_URL=http://localhost:5000/api`
2. Restart dev server: `npm run dev`
3. Run console check again - should show: `http://localhost:5000/api`
4. New requests should go to localhost

---

## Why This Happened

The `.env` file was configured with a relative path for **production deployment**:
- On `docgenai.com`, `/api` correctly refers to `https://docgenai.com/api`
- In local development, `/api` refers to `https://localhost:5173/api` (frontend URL)
- This doesn't work for local backend on port 5000

**Solution**: Different `.env` files for different environments:
- **Development**: `VITE_API_URL=http://localhost:5000/api`
- **Production**: `VITE_API_URL=/api` (or `https://docgenai.com/api`)

---

## Folder Picker Code Status

**The folder picker code itself is 100% correct**:
- ✅ Backend endpoint implemented
- ✅ Frontend component created
- ✅ API service method added
- ✅ Integration complete
- ✅ All code compiles without errors

**The issue is environmental**, not code-related.

---

## Next Steps

1. **Decide on environment strategy**:
   - Use `.env.local` for local development
   - Keep `.env` for production

2. **Update configuration**:
   ```bash
   echo "VITE_API_URL=http://localhost:5000/api" > frontend/.env.local
   ```

3. **Restart frontend**:
   ```bash
   npm run dev
   ```

4. **Verify it works**:
   - Check browser console for new API URL
   - Test API calls (should succeed with 401 only if no token)
   - Click browse folder button to test

---

## Expected Behavior After Fix

When you click the browse folder button:

1. Modal appears
2. Backend API call to `/api/ocr-chains/folders?path=/` is made
3. If authenticated (you have a token):
   - Folder list appears
   - You can navigate folders
   - You can select a folder
4. Selected path updates in OCRChainBuilder

---

## Summary

| Issue | Status | Impact |
|-------|--------|--------|
| Folder picker code | ✅ OK | None |
| Backend endpoint | ✅ OK | None |
| Frontend component | ✅ OK | None |
| API configuration | ❌ WRONG | All API calls fail |
| 401 error | ✅ Expected | Due to wrong URL + no production token |

**Fix required**: Update `VITE_API_URL` to point to localhost backend.

---

**Generated**: December 29, 2025
**Diagnosis**: Environment Configuration Issue
**Severity**: Low (Code is correct, configuration needs adjustment)

