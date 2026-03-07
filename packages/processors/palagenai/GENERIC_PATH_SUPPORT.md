# Generic Path Support - Removed Hardcoded References

## Issue
The UI and backend had hardcoded references to "Bhushanji" paths in comments and help text, which could confuse users into thinking the system only works with that specific folder structure.

## Changes Made

### 1. Backend - Updated Comment (bulk.py)
**File**: `backend/app/routes/bulk.py` (line 902)

**Before**:
```python
# Resolve relative paths (e.g., ./Bhushanji/eng-typed -> /app/Bhushanji/eng-typed)
```

**After**:
```python
# Resolve relative paths (e.g., ./data/documents -> /app/data/documents)
```

### 2. Frontend - Updated Help Text (BulkOCRProcessor.tsx)
**File**: `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx` (line 1077)

**Before**:
```tsx
<p className="text-xs text-gray-500 mt-2">
  💡 <strong>Note:</strong> Paths are from the server machine/Docker container. 
  Use the "Browse" button to select folders, or enter paths like 
  <code className="bg-gray-100 px-1 rounded">/data/Bhushanji/eng-typed</code>
</p>
```

**After**:
```tsx
<p className="text-xs text-gray-500 mt-2">
  💡 <strong>Note:</strong> Paths are from the server machine/Docker container. 
  Use the "Browse" button to select folders, or enter paths like 
  <code className="bg-gray-100 px-1 rounded">/data/documents</code> or 
  <code className="bg-gray-100 px-1 rounded">./data</code>
</p>
```

## How It Works

The system **already supported** processing from any folder - these were just cosmetic/documentation changes.

### Supported Path Formats

1. **Absolute paths**:
   - `/data/my-documents`
   - `/app/files/scanned-pdfs`
   - `/mnt/storage/archive`

2. **Relative paths** (converted to `/app/` prefix):
   - `./data` → `/app/data`
   - `./documents/2024` → `/app/documents/2024`
   - `./my-folder` → `/app/my-folder`

### Path Resolution Logic

The backend automatically resolves relative paths:
```python
if folder_path.startswith('./'):
    folder_path = '/app/' + folder_path[2:]
```

This means:
- **Input**: `./data/t1` 
- **Resolved to**: `/app/data/t1`
- **Container sees**: Whatever is mounted at `/app/data/t1`

## Examples

### Example 1: Processing ./data folder
```
1. Enter path: ./data
2. Backend resolves to: /app/data
3. Scans all files recursively
4. Processes PDFs, images, etc.
```

### Example 2: Processing absolute path
```
1. Enter path: /mnt/archive/documents
2. Backend uses as-is: /mnt/archive/documents
3. Requires volume mount in docker-compose.yml
```

### Example 3: Using folder browser
```
1. Click "Browse" button
2. Navigate to desired folder
3. Click "Select"
4. Path automatically filled
5. Click "Start Processing"
```

## Docker Volume Mapping

For paths to work, they must be mapped in `docker-compose.yml`:

```yaml
backend:
  volumes:
    - ./data:/app/data:ro              # ./data paths
    - /mnt/storage:/mnt/storage:ro     # absolute paths
```

## No Hardcoded Dependencies

The application is **completely generic** and works with ANY folder structure:
- ✅ Works with `./data`
- ✅ Works with `./documents`
- ✅ Works with `./scans/2024`
- ✅ Works with `/custom/path/anywhere`

The only requirement is that the path must be accessible from within the Docker container.

## Testing

Test with your specific folder:
```bash
# 1. Ensure folder is mounted
docker exec gvpocr-backend ls -la ./data

# 2. Use bulk processing UI
#    - Enter: ./data (or your folder)
#    - Click "Start Processing"

# 3. Monitor progress
#    - Progress bar shows current file
#    - Can download samples during processing
#    - Can cancel if needed
```

## Summary

✅ **No hardcoded "Bhushanji" dependencies**  
✅ **Works with any folder path**  
✅ **Relative and absolute paths supported**  
✅ **Browse button for easy navigation**  
✅ **Generic help text and examples**

---
**Date**: 2026-01-26  
**Status**: COMPLETED ✅
