# AMI Sets Upload Test Guide

This guide will walk you through testing the AMI Sets upload workflow from the frontend.

## Prerequisites

1. ✅ Backend is running with AMI service
2. ✅ Archipelago is accessible
3. ✅ You have authentication token (JWT)
4. ✅ Files in Bhushanji folder are accessible

## Step 1: Create a Bulk OCR Job

First, you need to process some files from the Bhushanji folder using the bulk OCR feature.

### Via Frontend UI:

1. Navigate to the Bulk Processing page
2. Select folder: `eng-typed` (or `hin-typed`, `hin-written`)
3. Choose OCR provider (e.g., Google Vision)
4. Start the bulk processing job
5. Wait for completion
6. **Note the Job ID** from the results page

### Via API (Alternative):

```bash
# Start bulk processing
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "eng-typed",
    "provider": "google_vision",
    "output_format": "json"
  }'

# Response will include job_id
# Monitor progress at: GET /api/bulk/status/{job_id}
```

## Step 2: Upload to Archipelago via AMI Sets

Once the bulk job is complete, use the new AMI Sets endpoint.

### Via Frontend (Recommended):

Add this to your bulk processing results page:

**New Button**: "Upload to Archipelago (AMI Sets)"

**Click Handler**:
```javascript
async function uploadViaAMI(jobId) {
  try {
    const response = await fetch('/api/archipelago/push-bulk-ami', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        job_id: jobId,
        collection_title: 'Bhushanji Documents Collection',
        // collection_id: 123  // Optional: use existing collection
      })
    });

    const result = await response.json();

    if (result.success) {
      alert(`AMI Set Created Successfully!

AMI Set ID: ${result.ami_set_id}
Name: ${result.ami_set_name}
Documents: ${result.total_documents}

Next: Visit ${result.message}`);

      // Open processing URL in new tab
      window.open(result.message.split('Process it at: ')[1], '_blank');
    } else {
      alert('Error: ' + result.error);
    }
  } catch (error) {
    console.error('Upload error:', error);
    alert('Failed to upload: ' + error.message);
  }
}
```

### Via API (Testing):

```bash
curl -X POST http://localhost:5000/api/archipelago/push-bulk-ami \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "REPLACE_WITH_YOUR_JOB_ID",
    "collection_title": "Bhushanji Test Collection"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "ami_set_id": 5,
  "ami_set_name": "Bhushanji Test Collection",
  "csv_fid": 312,
  "zip_fid": 313,
  "message": "AMI Set created successfully. Process it at: http://esmero-web:80/amiset/5/process",
  "total_documents": 15
}
```

## Step 3: Process AMI Set in Archipelago

After creating the AMI Set, you need to process it in Archipelago's UI:

1. **Navigate to the processing URL** from the response message:
   ```
   http://localhost:8001/amiset/5/process
   ```
   (Replace `5` with your actual AMI Set ID)

2. **Review Configuration**:
   - Check CSV file is uploaded
   - Check ZIP file is uploaded
   - Verify mapping settings

3. **Process the Set**:
   - Click the **"Process"** tab
   - Choose processing method:
     - **"Process via Queue"** (Recommended for large batches)
     - **"Process via Batch"** (For immediate processing)
   - Click **"Process"** button

4. **Monitor Progress**:
   - For Queue: Check Hydroponics service queue
   - For Batch: Watch the progress bar
   - View processing logs in real-time

5. **Check Results**:
   - Go to `/admin/content` in Archipelago
   - Filter by recent digital objects
   - Verify files display correctly
   - Check that each has:
     - ✅ Single document in `as:document` (no duplicates)
     - ✅ Real Drupal file entity ID (`dr:fid`)
     - ✅ Proper thumbnails
     - ✅ PDF metadata (page count, etc.)

## Step 4: Verify Upload Success

### Check in Archipelago UI:

1. Navigate to latest digital objects: `http://localhost:8001/admin/content`
2. Click on one of the newly created objects
3. Check the "Manage" → "Display" tabs
4. Verify PDF viewer works correctly
5. Check metadata is complete

### Check via API:

```bash
# Get latest digital objects
curl -X GET "http://localhost:8001/jsonapi/node/digital_object?sort=-drupal_internal__nid&page[limit]=5" \
  -H "Accept: application/vnd.api+json" \
  --cookie "your_archipelago_session_cookie"

# Check specific node metadata
curl -X GET "http://localhost:8001/jsonapi/node/digital_object/{node_id}" \
  -H "Accept: application/vnd.api+json" \
  --cookie "your_archipelago_session_cookie"
```

## Troubleshooting

### Error: "job_id is required"
- Make sure you're passing the job_id in the request body
- Check the job_id format is correct

### Error: "Bulk job not found"
- Verify the job_id exists
- Ensure it belongs to your user account
- Check if the job completed successfully

### Error: "No successful results to push"
- The bulk OCR job had no successful files
- Check the bulk job results for errors
- Verify files exist in the specified folder

### Error: "Failed to upload CSV file"
- Check file permissions on the backend
- Verify GVPOCR_PATH is set correctly
- Check backend logs for detailed error

### Error: "Failed to create AMI Set"
- Check Archipelago credentials
- Verify Archipelago is accessible
- Check backend logs for JSON:API errors
- Ensure JSON:API module is enabled in Archipelago

### AMI Set Created but Processing Fails
- Check CSV format is correct
- Verify ZIP file contains all referenced files
- Check file names match between CSV and ZIP
- Review Archipelago logs: `/admin/reports/dblog`

### Files Not Displaying
- Check that files were uploaded to Archipelago
- Verify file entity IDs are correct
- Check MinIO/S3 storage is accessible
- Review file permissions

## Expected Results

After successful AMI Sets upload and processing:

✅ **No Duplicate Documents**
- Each node has exactly 1 entry in `as:document`
- No random PDFs from previous uploads

✅ **Real File Entities**
- Each file has a valid `dr:fid` (Drupal file ID)
- Files are tracked in Archipelago's file system

✅ **Complete Metadata**
- `flv:exif` with page count, file size
- `flv:pdfinfo` with page dimensions
- `flv:pronom` with file format info
- OCR text in metadata

✅ **Proper Display**
- PDF viewer works correctly
- Shows correct number of pages
- Thumbnails generated
- Files match their titles

✅ **Better Integration**
- Files appear in Archipelago's file management
- IIIF manifests generated
- Search indexing works
- All Archipelago features available

## Comparison: Old vs New

### Old Direct API Upload (Before AMI)
```
Result: Node with S3 URL, no thumbnails, no file entity
Display: Works but limited features
File Tracking: Not in Archipelago's file system
```

### New AMI Sets Upload
```
Result: Node with file entity, thumbnails, full metadata
Display: Full PDF viewer with all pages
File Tracking: Complete Archipelago integration
```

## Next Steps

After successful test:

1. **Add UI Button** to bulk processing results page
2. **Show Progress** indicator during AMI Set creation
3. **Auto-redirect** to processing URL
4. **Save AMI Set ID** in bulk job record for tracking
5. **Add Status Polling** to check when processing completes

## Support

If you encounter issues:

1. Check backend logs: `docker-compose logs backend`
2. Check Archipelago logs: `/admin/reports/dblog`
3. Review [AMI_SETS_IMPLEMENTATION.md](AMI_SETS_IMPLEMENTATION.md)
4. Test with small batch first (2-3 files)
5. Verify individual file uploads work

---

**Ready to Test!** Follow the steps above to upload your first batch via AMI Sets.
