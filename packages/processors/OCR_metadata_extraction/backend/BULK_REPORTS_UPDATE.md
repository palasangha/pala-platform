# Bulk Processing Reports Update

## Summary of Changes

### 1. Individual JSON Files for Each Processed File
Each processed file now gets its own JSON file with the same name as the original file.

### 2. Enhanced CSV Export with All Data
The CSV report now includes ALL available data from each processed file.

### 3. Downloadable Reports from Job History
Reports.zip files are now stored in the database and downloadable from job history.

---

## 1. Individual JSON Files

### What Changed
When bulk processing completes, in addition to the main reports, individual JSON files are created for each processed file.

### File Naming
- **Original file**: `document.jpg`
- **Individual JSON**: `document.json`

### Location in reports.zip
```
reports.zip
├── report.json              # Main report with all files
├── report.csv               # CSV with all data
├── report.txt               # Text report
└── individual_files/        # NEW: Individual JSON files
    ├── document1.json
    ├── document2.json
    ├── image001.json
    └── ...
```

### Individual JSON Structure
Each file contains the complete OCR result for that specific file:

```json
{
  "file": "document.jpg",
  "file_path": "/path/to/document.jpg",
  "status": "success",
  "processed_at": "2025-11-27T10:30:00",
  "provider": "tesseract",
  "languages": ["en"],
  "handwriting": false,
  "text": "Full OCR extracted text here...",
  "confidence": 0.95,
  "detected_language": "en",
  "file_info": {
    "size": 245678,
    "type": "image/jpeg",
    "extension": ".jpg",
    "is_pdf": false,
    "width": 1920,
    "height": 1080
  },
  "metadata": {
    "processing_time": 2.5
  },
  "blocks_count": 15,
  "words_count": 250,
  "pages_processed": 1
}
```

### Use Cases
1. **Import to other systems**: Each file's data is ready to import
2. **Archive with original**: Store JSON alongside the original file
3. **Selective processing**: Use only specific files' OCR results
4. **Easy parsing**: One JSON per file is simpler to process programmatically

### Code Location
[app/routes/bulk.py:313-352](app/routes/bulk.py#L313-L352)

```python
# Create individual JSON files for each processed file
individual_json_folder = os.path.join(output_folder, 'individual_files')
os.makedirs(individual_json_folder, exist_ok=True)

for result in results['results']:
    # Get original filename without extension
    original_filename = result.get('file', 'unknown')
    base_name = os.path.splitext(original_filename)[0]

    # Create JSON filename: document.jpg -> document.json
    json_filename = f"{base_name}.json"
    json_filepath = os.path.join(individual_json_folder, json_filename)

    # Write individual JSON file
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
```

---

## 2. Enhanced CSV Export

### What Changed
The CSV export now includes **ALL available data** from each processed file, not just a summary.

### New CSV Columns

#### Basic Information
- `File` - Filename
- `File Path` - Full path to file
- `Status` - Success or Error

#### OCR Configuration
- `Provider` - OCR provider used (tesseract, google_vision, etc.)
- `Languages` - Languages specified for OCR
- `Detected Language` - Language detected by OCR
- `Handwriting` - Whether handwriting detection was enabled

#### OCR Results
- `Confidence` - OCR confidence score (0-1)
- `Text Length` - Length of extracted text
- `Character Count` - Number of characters
- `Blocks Count` - Number of text blocks detected
- `Words Count` - Number of words extracted
- `Pages Processed` - Number of pages (for PDFs)
- `OCR Text` - **Full extracted text** (NEW!)

#### File Information
- `File Size` - Size in bytes
- `File Type` - MIME type (image/jpeg, application/pdf, etc.)
- `File Extension` - File extension (.jpg, .pdf, etc.)
- `Is PDF` - Boolean indicating if file is a PDF
- `Image Width` - Image width in pixels
- `Image Height` - Image height in pixels

#### Processing Information
- `Processed At` - ISO timestamp of processing
- `Processing Time` - Time taken to process (seconds)
- `Error` - Error message (if failed)

### Example CSV Output

```csv
File,File Path,Status,Provider,Languages,Confidence,Detected Language,Handwriting,Text Length,Character Count,Blocks Count,Words Count,Pages Processed,Processed At,File Size,File Type,File Extension,Is PDF,Image Width,Image Height,Processing Time,OCR Text,Error
document1.jpg,/path/to/document1.jpg,Success,tesseract,en,0.95,en,False,1234,1234,15,250,1,2025-11-27T10:30:00,245678,image/jpeg,.jpg,False,1920,1080,2.5,"Full OCR text from document1...",
document2.pdf,/path/to/document2.pdf,Success,google_vision,en,0.98,en,False,5678,5678,45,890,3,2025-11-27T10:31:30,987654,application/pdf,.pdf,True,2480,3508,8.7,"Full OCR text from document2...",
failed.jpg,/path/to/failed.jpg,Error,,,,,,,,,,2025-11-27T10:32:00,,,,,,,,"","File not found"
```

### Code Location
[app/services/bulk_processor.py:242-333](app/services/bulk_processor.py#L242-L333)

### Benefits
1. **Complete data in one file**: All information accessible in Excel/Google Sheets
2. **Full text searchable**: OCR text included in CSV for searching
3. **Easy analysis**: All metrics in columns for statistical analysis
4. **Import ready**: Can import to databases or other systems
5. **Audit trail**: Complete record of what was processed and how

---

## 3. Downloadable Reports from Job History

### What Changed
- Reports.zip path is now stored in the database
- Downloads work from job history (not just in-memory)
- Download endpoint checks both memory and database

### Database Storage
When a job completes, the response data now includes:

```python
response_data = {
    'job_id': job_id,
    'download_url': f'/api/bulk/download/{job_id}',
    'zip_path': zip_path,  # Full path to reports.zip
    'output_folder': output_folder,
    'individual_json_folder': individual_json_folder,
    'report_files': {
        'zip': 'reports.zip',
        'individual_json_count': 150  # Number of individual JSON files
    }
}
```

This data is saved to MongoDB in the `bulk_jobs` collection.

### Download Endpoint Enhancement

**Endpoint**: `GET /api/bulk/download/{job_id}`

**Authentication**: Required (JWT token)

**Process**:
1. Check in-memory storage first (for recent jobs)
2. If not found, check database (for older jobs)
3. Verify user owns the job
4. Return the reports.zip file

**Code Location**: [app/routes/bulk.py:632-671](app/routes/bulk.py#L632-L671)

```python
@bulk_bp.route('/download/<job_id>', methods=['GET'])
@token_required
def download_reports(current_user_id, job_id):
    """Download processed reports as ZIP"""
    zip_path = None

    # First check in-memory storage
    if job_id in current_app.bulk_processing_outputs:
        output_info = current_app.bulk_processing_outputs[job_id]
        zip_path = output_info['zip']
    else:
        # Check database for completed jobs
        job = BulkJob.find_by_job_id(mongo, job_id, user_id=current_user_id)

        if job and job.get('results'):
            zip_path = job['results'].get('zip_path')

    # Verify file exists and return it
    if zip_path and os.path.exists(zip_path):
        return send_file(zip_path, ...)
```

### Job History Response
Job history now includes download information:

```json
{
  "jobs": [
    {
      "id": "...",
      "job_id": "abc123-def456",
      "status": "completed",
      "folder_path": "/path/to/folder",
      "created_at": "2025-11-27T10:00:00",
      "completed_at": "2025-11-27T10:15:00",
      "results": {
        "success": true,
        "job_id": "abc123-def456",
        "summary": {
          "total_files": 150,
          "successful": 148,
          "failed": 2
        },
        "download_url": "/api/bulk/download/abc123-def456",
        "zip_path": "/tmp/ocr_bulk_xyz/reports.zip",
        "report_files": {
          "zip": "reports.zip",
          "individual_json_count": 148
        }
      }
    }
  ]
}
```

### Frontend Integration

```javascript
// Get job history
const response = await fetch('/api/bulk/history?page=1&limit=10', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();

// Download reports for a specific job
data.jobs.forEach(job => {
  if (job.status === 'completed' && job.results.download_url) {
    // Show download button
    const downloadUrl = job.results.download_url;

    // Download on click
    fetch(downloadUrl, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    .then(response => response.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ocr_reports_${job.job_id}.zip`;
      a.click();
    });
  }
});
```

---

## File Structure Comparison

### Before
```
reports.zip
├── report.json    # Main report
├── report.csv     # Basic CSV
└── report.txt     # Text report
```

### After
```
reports.zip
├── report.json              # Main report (all files)
├── report.csv               # Enhanced CSV with ALL data including full OCR text
├── report.txt               # Text report
└── individual_files/        # NEW: Individual JSON files
    ├── document001.json     # Complete OCR result for document001.jpg
    ├── document002.json     # Complete OCR result for document002.jpg
    ├── image_001.json       # Complete OCR result for image_001.png
    ├── scan_page1.json      # Complete OCR result for scan_page1.pdf
    └── ...                  # One JSON per processed file
```

---

## Storage Locations

### In-Memory (Current Session)
```python
current_app.bulk_processing_outputs[job_id] = {
    'folder': output_folder,
    'files': exported_files,
    'zip': zip_path,
    'job_id': job_id
}
```

### Database (MongoDB - Persistent)
Collection: `bulk_jobs`

Document structure:
```json
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "job_id": "abc123-def456",
  "status": "completed",
  "results": {
    "zip_path": "/tmp/ocr_bulk_xyz/reports.zip",
    "output_folder": "/tmp/ocr_bulk_xyz",
    "individual_json_folder": "/tmp/ocr_bulk_xyz/individual_files",
    "download_url": "/api/bulk/download/abc123-def456",
    "report_files": {
      "individual_json_count": 150
    }
  }
}
```

### Filesystem
```
/tmp/ocr_bulk_{timestamp}/
├── reports.zip                    # ZIP with all reports
├── report.json                    # Main JSON report
├── report.csv                     # Enhanced CSV with all data
├── report.txt                     # Text report
├── result.json                    # Alias for report.json
└── individual_files/              # Individual JSON files
    ├── file001.json
    ├── file002.json
    └── ...
```

---

## API Endpoints

### Get Job History
```
GET /api/bulk/history?page=1&limit=10
Authorization: Bearer {token}
```

Response includes `download_url` and `zip_path` for each completed job.

### Download Reports
```
GET /api/bulk/download/{job_id}
Authorization: Bearer {token}
```

Returns `reports.zip` file with all reports and individual JSON files.

---

## Benefits Summary

### Individual JSON Files
✅ Easy to archive with original files
✅ One-to-one mapping with source files
✅ Simple to import to other systems
✅ Can process files individually
✅ Clean naming: `document.jpg` → `document.json`

### Enhanced CSV
✅ Complete data in Excel/Sheets
✅ Full OCR text searchable
✅ All metadata in columns
✅ Easy statistical analysis
✅ Database import ready

### Downloadable from History
✅ Access old jobs anytime
✅ No need to keep page open
✅ Works across sessions
✅ Survives server restart (if files preserved)
✅ User-specific access control

---

## Migration Notes

### Existing Jobs
- Old jobs in database won't have `zip_path`
- Downloads will fail for old jobs (no zip stored)
- Only new jobs (processed after this update) will be downloadable from history

### Temporary Files
- Reports are in `/tmp` by default (may be cleaned by system)
- Consider moving to persistent storage for long-term access
- Can configure via `UPLOAD_FOLDER` in config

### Recommended: Persistent Storage
Update `docker-compose.yml` to mount persistent volume:

```yaml
backend:
  volumes:
    - ./backend/uploads:/app/uploads
    - ./backend/reports:/tmp/ocr_bulk  # Persist reports
```

---

## Related Files

- [app/routes/bulk.py](app/routes/bulk.py) - Bulk processing routes (individual JSON creation)
- [app/services/bulk_processor.py](app/services/bulk_processor.py) - Enhanced CSV export
- [app/models/bulk_job.py](app/models/bulk_job.py) - Job history model
- [JOB_HISTORY_FIX.md](JOB_HISTORY_FIX.md) - Job history authentication fix

---

## Testing

### Test Individual JSON Files
```bash
# Process a folder
# Download reports.zip
unzip reports.zip
cd individual_files
ls -la  # Should see one .json per processed file
cat document001.json  # View individual OCR result
```

### Test Enhanced CSV
```bash
# Open report.csv in Excel/LibreOffice
# Should see columns: File, File Path, Status, Provider, ..., OCR Text
# OCR Text column should contain full extracted text
```

### Test Download from History
```bash
# Get job history
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/bulk/history?page=1&limit=10

# Download from job_id
curl -H "Authorization: Bearer $TOKEN" \
     -o reports.zip \
     http://localhost:5000/api/bulk/download/{job_id}

# Verify zip contents
unzip -l reports.zip
```
