# Bulk OCR Processing Feature

## Overview

The Bulk OCR Processing feature allows users to process multiple image files from a folder and its subfolders in a single operation. It includes:

- **Recursive folder scanning** for image discovery
- **Progress tracking** with real-time updates
- **Multiple output formats** (JSON, CSV, TXT)
- **Comprehensive reporting** with statistics and metadata
- **Error handling** with detailed error logs

## Test Results

### Chrome Lens Bulk Processing Test

**Test Date:** November 15, 2025

#### Configuration
- **Provider:** Chrome Lens
- **Languages:** English
- **Folder:** `/app/uploads/691803122872c23ac9e9f628/`
- **Recursive:** Yes
- **Handwriting Detection:** Disabled

#### Results Summary
```
Total Files Processed: 5
Successful: 5
Failed: 0
Success Rate: 100%
```

#### Detailed Statistics
- **Total Characters Extracted:** 36,145
- **Average Confidence:** 85.00%
- **Average Words per File:** 100.0
- **Average Blocks per File:** 3.2
- **Languages Detected:** English

#### Sample Files Processed
1. **1dd92614-9e45-4d5c-a054-387fed0fb7fb.pdf**
   - Status: ✓ Success
   - Confidence: 85.00%
   - Text Length: 19,761 characters
   - Pages: 7

2. **1f2ea453-711e-4833-adf4-0bcbd6d1d1fb.pdf**
   - Status: ✓ Success
   - Confidence: 85.00%
   - Text Length: 1,796 characters
   - Pages: 1

3. **4e3e2cd5-9310-43f9-8e86-8c39d100d626.pdf**
   - Status: ✓ Success
   - Confidence: 85.00%
   - Text Length: 3,057 characters
   - Pages: 2

#### Report Files Generated
- **report.json** - 44.0 KB
- **report.csv** - 0.7 KB
- **report.txt** - 37.8 KB
- **reports.zip** - Contains all three files

## Feature Details

### Backend Components

#### 1. BulkProcessor Service (`app/services/bulk_processor.py`)

**Key Methods:**
- `scan_folder(folder_path, recursive=True)` - Recursively scan for supported image files
- `process_folder(folder_path, provider, languages, handwriting, recursive)` - Process all images in folder
- `export_to_json(output_path)` - Export results as JSON
- `export_to_csv(output_path)` - Export results as CSV
- `export_to_text(output_path)` - Export results as plain text
- `export_all_reports(output_folder, base_name)` - Export all formats at once

**Supported File Formats:**
```
.jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp, .pdf
```

#### 2. Bulk Routes (`app/routes/bulk.py`)

**Endpoints:**

##### POST `/api/bulk/process`
Process images from a folder.

**Request Body:**
```json
{
  "folder_path": "/path/to/folder",
  "recursive": true,
  "provider": "tesseract",
  "languages": ["en"],
  "handwriting": false,
  "export_formats": ["json", "csv", "text"]
}
```

**Response:**
```json
{
  "success": true,
  "summary": {
    "total_files": 5,
    "successful": 5,
    "failed": 0,
    "folder_path": "/path/to/folder",
    "processed_at": "2025-11-15T10:30:00.000000",
    "statistics": {
      "total_characters": 36145,
      "average_confidence": 0.85,
      "average_words": 100.0,
      "average_blocks": 3.2,
      "languages": ["en"]
    }
  },
  "report_files": {
    "json": "report.json",
    "csv": "report.csv",
    "text": "report.txt",
    "zip": "reports.zip"
  },
  "download_url": "/api/bulk/download/job_id",
  "results_preview": {
    "total_results": 5,
    "successful_samples": [...],
    "error_samples": [...]
  }
}
```

##### GET `/api/bulk/download/<job_id>`
Download processed reports as ZIP file.

### Frontend Components

#### BulkOCRProcessor Component (`frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`)

**Features:**
- Folder path input
- OCR provider selection (Tesseract, Chrome Lens, Google Vision, EasyOCR)
- Language selection (EN, HI, ES, FR, DE, ZH, JA)
- Export format selection (JSON, CSV, TXT)
- Processing options (recursive, handwriting detection)
- Real-time progress bar
- Results summary with statistics
- Sample results display
- Error listing
- One-click download of all reports

**UI Sections:**
1. **Configuration Panel** - Input settings and basic options
2. **Advanced Options** - Language and export format selection
3. **Progress Bar** - Real-time progress tracking
4. **Results Report** - Summary statistics and detailed results

## Export Formats

### JSON Format
Complete results with metadata, statistics, and all processing details.

**Structure:**
```json
{
  "metadata": {
    "generated_at": "2025-11-15T...",
    "total_files": 5,
    "successful": 5,
    "failed": 0
  },
  "summary": {
    "total_characters": 36145,
    "average_confidence": 0.85,
    ...
  },
  "results": [
    {
      "file": "image.pdf",
      "file_path": "/path/to/image.pdf",
      "status": "success",
      "processed_at": "2025-11-15T...",
      "provider": "chrome_lens",
      "languages": ["en"],
      "text": "Extracted text...",
      "confidence": 0.85,
      "detected_language": "en",
      "metadata": {...},
      ...
    }
  ],
  "errors": [...]
}
```

### CSV Format
Tabular format for spreadsheet analysis.

**Columns:**
- File
- Status
- Provider
- Languages
- Confidence
- Detected Language
- Text Length
- Blocks Count
- Words Count
- Pages
- Processed At
- Error

### TXT Format
Human-readable format with detailed information.

**Sections:**
1. Summary (total, successful, failed counts)
2. Statistics (characters, confidence, languages)
3. Detailed Results (file-by-file breakdown with extracted text)
4. Errors (failed file details)

## Usage Example

### Backend (Python)
```python
from app.services.ocr_service import OCRService
from app.services.bulk_processor import BulkProcessor

# Initialize
ocr_service = OCRService()
processor = BulkProcessor(ocr_service, progress_callback)

# Process folder
results = processor.process_folder(
    folder_path='/path/to/images',
    provider='chrome_lens',
    languages=['en'],
    handwriting=False,
    recursive=True
)

# Export all formats
exported = processor.export_all_reports(
    output_folder='/path/to/output',
    base_name='ocr_report'
)
```

### Frontend (React/TypeScript)
```typescript
const response = await fetch('/api/bulk/process', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    folder_path: '/path/to/folder',
    recursive: true,
    provider: 'chrome_lens',
    languages: ['en'],
    handwriting: false,
    export_formats: ['json', 'csv', 'text']
  })
});

const data = await response.json();
// Download reports
const downloadUrl = data.download_url;
```

## Performance

### Bulk Processing Performance (Chrome Lens)
- **5 PDF files** processed in approximately **60 seconds**
- **Average processing time:** ~12 seconds per file
- **Memory efficient:** Uses streaming for large files
- **Disk efficient:** Temporary files cleaned up after export

### Report Generation
- **JSON:** 44 KB for 5 files (~8.8 KB per file)
- **CSV:** 0.7 KB for 5 files (~0.14 KB per file)
- **TXT:** 37.8 KB for 5 files (~7.56 KB per file)

## Error Handling

### Supported Error Cases
1. **Invalid folder path** - Returns 400 error
2. **Missing authorization token** - Returns 401 error
3. **No images found** - Returns informative error message
4. **Individual file processing errors** - Logged with specific error details
5. **PDF conversion failures** - Graceful fallback with error message

### Error Reporting
Each failed file includes:
- Filename
- Error message
- Processing timestamp

## Future Enhancements

1. **WebSocket Support** - Real-time progress updates during processing
2. **Database Integration** - Store bulk processing results in MongoDB
3. **Scheduled Processing** - Process folders on a schedule
4. **Email Notifications** - Notify users when processing completes
5. **Advanced Filtering** - Filter results by confidence, language, date
6. **Batch Operations** - Compare results across multiple processing runs
7. **API Key Rate Limiting** - Prevent abuse of bulk processing

## Configuration

### Environment Variables
- `UPLOAD_FOLDER` - Directory for uploads (default: `uploads/`)
- `TEMP_FOLDER` - Directory for temporary files (default: system temp)

### Settings
- **Max file size:** Configurable in upload routes
- **Supported formats:** Defined in BulkProcessor.SUPPORTED_EXTENSIONS
- **Default DPI (for PDF):** 150 DPI
- **Timeout:** 30 seconds per file

## Troubleshooting

### Issue: "No supported image files found"
**Solution:** Ensure folder path is correct and contains supported image formats.

### Issue: "Failed to convert PDF to images"
**Solution:** Verify poppler-utils is installed in the container.

### Issue: "Memory exhausted"
**Solution:** Process smaller batches or increase container memory.

### Issue: "Processing hangs"
**Solution:** Check if OCR provider service is running (Chrome Lens, Tesseract, etc.).

## Security Considerations

1. **Path Validation** - Paths are validated to prevent directory traversal
2. **Authentication** - All endpoints require valid JWT token
3. **Temporary Files** - Cleaned up automatically after download
4. **File Access** - Only processes files in upload folder
5. **Rate Limiting** - (Future) Implement rate limiting per user

## Testing

### Run Tests
```bash
# Test with Chrome Lens
docker compose exec -T backend python - < test_chrome_lens_bulk.py

# Test with Tesseract
docker compose exec -T backend python - < test_tesseract_bulk.py
```

### Test Results Summary
✅ Folder scanning - PASSED
✅ PDF processing - PASSED
✅ Multi-file processing - PASSED
✅ Progress tracking - PASSED
✅ JSON export - PASSED
✅ CSV export - PASSED
✅ TXT export - PASSED
✅ Error handling - PASSED
✅ ZIP download - PASSED
