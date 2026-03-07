# AMI Sets vs Direct JSON:API Upload Analysis

## Current Situation

### Working Node (Node 114)
- **Method**: Uploaded via AMI Sets or Webform
- **as:document count**: 1 (correct)
- **dr:fid**: 49 (valid Drupal file entity)
- **Has PDF metadata**: Yes (flv:exif, flv:pdfinfo)
- **Result**: Displays correctly

### Broken Nodes (265-267)
- **Method**: Our direct JSON:API upload with buggy code
- **as:document count**: 2 (duplicates!)
- **dr:fid**: 14, 15, 16 (wrong file entities from previous uploads)
- **Has PDF metadata**: Only on first document (wrong one)
- **Result**: Displays wrong file

## Key Differences

### AMI Sets Approach
1. **Uploads files to Archipelago** → Creates Drupal file entities with proper FIDs
2. **Processes files through Archipelago's pipeline** → Extracts metadata automatically
3. **Creates proper file references** → Single `as:document` entry with valid `dr:fid`
4. **Handles file processing** → PDF metadata extraction, thumbnails, etc.

### Our Current Direct API Approach (FIXED)
1. **Uploads files to MinIO** → Gets S3 URLs (no Drupal file entities)
2. **Manually extracts PDF metadata** → Using PyPDF2 in our code
3. **Creates metadata-only references** → `as:document` with S3 URL but no `dr:fid`
4. **Bypasses Archipelago processing** → No thumbnails, no automatic processing

## The Problem with Our Old Code

**Before Fix:**
- Passed fake `file_id=1,2,3...` (loop indexes)
- Data mapper added `dr:fid: 1,2,3...` to metadata
- Archipelago saw these FIDs and fetched wrong file entities
- Result: Duplicate documents (wrong file + our S3 file)

**After Fix:**
- Passes `file_id=None`
- Data mapper doesn't add `dr:fid` to metadata
- Only our S3 file is in `as:document`
- Result: Single document, but no Drupal file entity integration

## Should We Use AMI Sets?

### Pros of Using AMI Sets
✅ **Proper Drupal file entity creation** - Gets real FIDs
✅ **Automatic metadata extraction** - Archipelago handles PDF processing
✅ **Proper file processing pipeline** - Thumbnails, derivatives, etc.
✅ **Better integration** - Works with all Archipelago features
✅ **Batch processing** - Can handle large uploads efficiently
✅ **CSV-based** - Easy to prepare metadata in spreadsheets

### Cons of Using AMI Sets
❌ **More complex workflow** - Requires CSV preparation + ZIP file
❌ **Less programmatic control** - Goes through UI or requires AMI API calls
❌ **Async processing** - Need to monitor queue status
❌ **Harder to integrate** - Would require significant refactoring

## Recommendation

### Option 1: Continue with Direct API (Current Approach - FIXED)
**Best for**: Programmatic, automated uploads where you control the entire flow

**Pros**:
- Already working after fix
- Direct integration with OCR pipeline
- Full control over metadata
- No duplicate files anymore

**Cons**:
- No Drupal file entities (files only in MinIO)
- No automatic thumbnail generation
- Missing some Archipelago processing features

**Action**: Test new uploads after fix to confirm no duplicates

### Option 2: Switch to AMI Sets
**Best for**: Manual batch uploads, better Archipelago integration

**Pros**:
- Proper file entity creation with real FIDs
- Full Archipelago processing pipeline
- Better long-term maintainability

**Cons**:
- Requires CSV generation from OCR results
- ZIP file creation from source files
- More complex API integration
- Async processing complexity

**Action**: Would require refactoring the bulk upload workflow

### Option 3: Hybrid Approach (RECOMMENDED)
**Use the `_upload_file_to_node` method** that already exists in `archipelago_service.py`

**How it works**:
1. Create node with metadata (current approach)
2. Upload file to node using `_upload_file_to_node()` method
3. Archipelago creates file entity and processes it
4. Update node metadata with returned `dr:fid`

**Benefits**:
- ✅ Get real Drupal file entities
- ✅ Keep programmatic control
- ✅ Minimal refactoring needed
- ✅ Archipelago handles file processing

**Implementation**:
```python
# After creating node
if file_path:
    file_result = self._upload_file_to_node(
        file_path=file_path,
        node_uuid=node_uuid,
        csrf_token=csrf_token
    )
    if file_result:
        # Update node with real dr:fid
        # Archipelago will add to as:document automatically
```

## Conclusion

The current fix (file_id=None) **solves the duplicate document problem** for S3-only uploads. However, for full Archipelago integration with thumbnails and proper file entities, we should use the **Hybrid Approach** with `_upload_file_to_node()`.
