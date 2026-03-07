# Worker Path Resolution Fix

## Problem
When processing files from `./data` folder, workers were looking for files at `/app/Bhushanji/data/t1/...` instead of `/app/data/t1/...`

### Error Message
```
Exception: Image file not found: /app/Bhushanji/data/t1/From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf
```

## Root Cause
In `backend/app/workers/ocr_worker.py`, the path resolution logic had a hardcoded fallback:

**Before (Lines 90-93)**:
```python
# Default: prepend GVPOCR_PATH
else:
    gvpocr_path = os.getenv('GVPOCR_PATH', '/data/Bhushanji')
    file_path = os.path.join(gvpocr_path, file_path)
```

This meant:
- Input: `data/t1/file.pdf`
- Resolved to: `/data/Bhushanji/data/t1/file.pdf` ❌

## Solution
Changed the default path resolution to use `/app/` prefix:

**After (Lines 90-92)**:
```python
# Default: prepend /app/ for generic paths
else:
    file_path = os.path.join('/app', file_path)
```

Now:
- Input: `data/t1/file.pdf`
- Resolved to: `/app/data/t1/file.pdf` ✅

## Path Resolution Logic

The worker now handles 3 cases:

### 1. Bhushanji-prefixed paths
```python
if file_path.startswith('Bhushanji/'):
    gvpocr_path = os.getenv('GVPOCR_PATH', '/app/Bhushanji')
    relative_part = file_path.replace('Bhushanji/', '', 1)
    file_path = os.path.join(gvpocr_path, relative_part)
```
- Input: `Bhushanji/eng-typed/file.pdf`
- Output: `/app/Bhushanji/eng-typed/file.pdf`

### 2. Newsletters-prefixed paths
```python
elif file_path.startswith('newsletters/'):
    newsletters_path = os.getenv('NEWSLETTERS_PATH', '/data/newsletters')
    relative_part = file_path.replace('newsletters/', '', 1)
    file_path = os.path.join(newsletters_path, relative_part)
```
- Input: `newsletters/2024/file.pdf`
- Output: `/data/newsletters/2024/file.pdf`

### 3. Generic paths (NEW - Fixed)
```python
else:
    file_path = os.path.join('/app', file_path)
```
- Input: `data/t1/file.pdf`
- Output: `/app/data/t1/file.pdf` ✅

## Testing

### Verification
All workers can now access the file:
```bash
docker exec ocr_metadata_extraction-ocr-worker-1 ls -la /app/data/t1/
docker exec ocr_metadata_extraction-ocr-worker-2 ls -la /app/data/t1/
docker exec ocr_metadata_extraction-ocr-worker-3 ls -la /app/data/t1/

# All show:
# -rw-rw-r-- 1 1004 1004 563750 Dec 16 10:28 From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf
```

### NSQ Status
```bash
curl -s http://localhost:4151/stats?format=json | python3 -m json.tool | grep client_count

# Output: "client_count": 3  ✅
```

## Next Steps

**User Action Required**: Restart the bulk job from the UI:
1. Go to Bulk Processing page
2. Enter path: `./data` (or any generic folder)
3. Click "Start Processing"
4. Workers will now correctly resolve paths to `/app/data/...`

## Changes Summary

**File Modified**: `backend/app/workers/ocr_worker.py`
- **Lines changed**: 90-93
- **Change type**: Path resolution logic fix
- **Impact**: Workers can now process files from any folder, not just Bhushanji

**Workers restarted**: ✅ All 3 workers running with fix

---
**Date**: 2026-01-26  
**Issue**: Hardcoded Bhushanji path in worker  
**Status**: FIXED ✅
