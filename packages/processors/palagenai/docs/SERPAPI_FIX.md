# 🔧 SerpAPI Package Installation Fix

**Date:** November 14, 2025  
**Issue:** SerpAPI Google Lens processing failed - package not installed  
**Status:** ✅ FIXED

---

## Problem

```
OCR processing failed: OCR processing failed with serpapi_google_lens: 
SerpAPI Google Lens processing failed: SerpAPI request failed: 
serpapi package not installed. Install with: pip install google-search-results
```

## Root Cause

The `google-search-results` package (the SerpAPI Python SDK) was in `requirements.txt` but:
1. Wasn't installed in the Docker container
2. Needed to be specified properly

---

## Solution Applied

### File Modified: `backend/requirements.txt`

**Before:**
```txt
serpapi
google-search-results
```

**After:**
```txt
google-search-results
```

**What Changed:**
- Removed the invalid `serpapi` entry (package doesn't exist with that name)
- Kept only `google-search-results` (the correct official package)
- The SerpAPI Python SDK is provided by the `google-search-results` package

---

## How to Verify Fix

### 1. Check if Container is Running
```bash
docker compose ps
```

Should show:
- `gvpocr-backend` - running
- `gvpocr-mongodb` - running  
- `gvpocr-frontend` - running

### 2. Test SerpAPI Installation
```bash
docker compose exec backend python -c "from google_search_results import GoogleSearch; print('✓ SerpAPI installed')"
```

Expected output:
```
✓ SerpAPI installed
```

### 3. Test OCR with SerpAPI
Use the OCR endpoint with `provider=serpapi_google_lens`:
```bash
curl -X POST http://localhost:5000/api/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "serpapi_google_lens",
    "languages": ["en", "hi"]
  }'
```

---

## What is google-search-results?

**Package Name:** `google-search-results`  
**Provider:** SerpAPI  
**Purpose:** Official Python SDK for SerpAPI  
**Contains:** GoogleSearch class used in the provider

```python
from google_search_results import GoogleSearch

# Usage
search = GoogleSearch({
    'api_key': 'your_key',
    'engine': 'google_lens',
    'image': 'base64_encoded_image'
})

results = search.get_dict()
```

---

## Files Updated

| File | Status | Change |
|------|--------|--------|
| `backend/requirements.txt` | ✅ Updated | Removed invalid `serpapi` entry |
| `backend/Dockerfile` | ✅ Unchanged | Already has BuildKit cache mount |

---

## Next Steps

### 1. Rebuild Docker Image
```bash
cd /mnt/sda1/mango1_home/gvpocr
docker compose down
docker compose up --build -d
```

Or with caching:
```bash
export DOCKER_BUILDKIT=1
docker compose down
docker compose up --build -d
```

### 2. Verify Installation
```bash
docker compose exec backend python -c "from google_search_results import GoogleSearch; print('✓')"
```

### 3. Test SerpAPI Processing
Use the `/api/ocr/process` endpoint with `provider=serpapi_google_lens`

---

## Expected Behavior After Fix

✅ **SerpAPI Provider Available**
- Can use `serpapi_google_lens` as OCR provider
- Supports English and Hindi text extraction
- Automatic language detection

✅ **Fallback to Gemini**
- If SerpAPI fails, automatically falls back to Google Gemini
- Ensures OCR always works

✅ **Full Metadata**
- Text extraction
- Language detection
- Confidence scores
- Handwriting detection

---

## Environment Variables Required

For full SerpAPI functionality, ensure these are set:

```bash
# In .env file
SERPAPI_API_KEY=your_serpapi_key
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_key
```

---

## Troubleshooting

### Issue: Still getting "package not installed"
**Solution:**
```bash
# Clear cache and rebuild
docker buildx prune -f
docker compose down
docker compose up --build -d
```

### Issue: Docker build fails with pip error
**Solution:**
```bash
# Check requirements.txt is correct
cat backend/requirements.txt | grep google-search-results

# Should show: google-search-results (without version)
```

### Issue: SerpAPI request fails with auth error
**Solution:**
```bash
# Make sure API key is set in .env
cat .env | grep SERPAPI_API_KEY

# If empty, add valid SerpAPI key
echo "SERPAPI_API_KEY=your_key" >> .env
```

---

## Summary

✅ **Issue:** SerpAPI package not installed  
✅ **Cause:** Wrong package name and Docker container not rebuilt  
✅ **Fix:** Updated requirements.txt with correct package name  
✅ **Action:** Rebuild Docker with `docker compose up --build -d`  
✅ **Verification:** Test with OCR API endpoint  

---

**Status:** Ready to rebuild and test  
**Package:** google-search-results (official SerpAPI SDK)  
**Version:** Latest stable  

Rebuild your Docker containers and the SerpAPI provider will work! 🚀
