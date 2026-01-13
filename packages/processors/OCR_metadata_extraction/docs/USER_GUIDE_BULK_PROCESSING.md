# User Guide: Bulk Processing Functionality

## 📖 Introduction

The **Bulk Processing** feature allows you to process multiple scanned images or PDF documents at once from a folder. Instead of processing files one by one, you can:
- Process entire folders with hundreds of files
- Choose your preferred OCR provider
- Select languages for text recognition
- Get multiple report formats (JSON, CSV, TXT)
- Track progress in real-time
- Download all results as a single file

## 🎯 Quick Start

### Step 1: Access Bulk Processing
1. Log in to the application
2. Click on the **"Bulk Processing"** menu item in the navigation
3. You'll see the Bulk Processing interface

### Step 2: Prepare Your Folder
Before processing, prepare a folder with:
- **Scanned images** (.jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp)
- **PDF documents** (.pdf)
- **Subfolders** (optional) with images inside

**Example folder structure:**
```
my_documents/
├── scan1.pdf
├── scan2.jpg
├── scan3.png
└── subfolder/
    ├── scan4.pdf
    └── scan5.jpg
```

### Step 3: Configure Processing
1. **Folder Path:** Enter the absolute path to your folder
   - Example: `/app/uploads/my_documents`
   - Or: `/home/username/scans`

2. **Select OCR Provider:**
   - **Tesseract** (Recommended for speed, local processing)
   - **Chrome Lens** (Recommended for PDF accuracy)
   - **Google Vision** (Recommended for high accuracy)
   - **EasyOCR** (Good for multiple languages)

3. **Enable/Disable Options:**
   - **✓ Process Subfolders** - Check to include files from subfolders
   - **✓ Detect Handwriting** - Check if documents have handwritten text

### Step 4: Select Languages
Click on the language buttons to select which languages to detect:
- English (en)
- Hindi (हिन्दी)
- Spanish (Español)
- French (Français)
- German (Deutsch)
- Chinese (中文)
- Japanese (日本語)

You can select multiple languages. By default, **English** is selected.

### Step 5: Choose Export Formats
Select which report formats you want to generate:
- **📄 JSON** - Structured data with full metadata (best for data processing)
- **📊 CSV** - Spreadsheet format (best for Excel/Sheets)
- **📝 TXT** - Human-readable text (best for review)

All selected formats will be included in the final download.

### Step 6: Start Processing
Click the **"Start Processing"** button to begin.

## 📊 Understanding the Progress Display

Once processing starts, you'll see:

```
Processing: scan1.pdf [████████░░░░░░░░░░] 45%
```

- **Progress Bar** - Shows overall progress across all files
- **Current File** - Shows which file is being processed
- **Percentage** - Completion percentage
- **Estimated Time** - Approximately how long processing will take

The progress updates in real-time as each file is processed.

## 📈 Results Dashboard

After processing completes, you'll see a comprehensive results dashboard with:

### 1. **Summary Statistics**
```
Total Files Processed:    5
Successfully Processed:   5 (100%)
Failed:                   0 (0%)
Success Rate:             100%
```

### 2. **Detailed Statistics**
```
Total Characters Extracted:     36,145
Average Confidence:              85.00%
Average Words per File:          100.0
Average Blocks per File:         3.2
Languages Detected:              English (en)
```

### 3. **Sample Results**
Shows details of the first 3 files processed:
- File name
- Number of pages
- Characters extracted
- Confidence score
- Languages detected
- Processing status

### 4. **Error Log** (if any)
If any files failed, you'll see:
- File name
- Error message
- Timestamp
- Suggestion for fixing

### 5. **Download Button**
A single **"Download Reports"** button that packages all reports into a ZIP file.

## 💾 Understanding the Reports

### JSON Report
**Best for:** Data processing, integration with other systems, preserving metadata

**What it contains:**
- Metadata (generation date, file counts)
- Summary statistics (total characters, confidence, languages)
- Complete results for each file with full metadata
- Error logs

**Example structure:**
```json
{
  "metadata": {
    "generated_at": "2025-11-15T10:30:00Z",
    "total_files": 5,
    "successful": 5,
    "failed": 0
  },
  "summary": {
    "total_characters": 36145,
    "average_confidence": 85.0,
    "languages": ["en"]
  },
  "results": [
    {
      "file": "scan1.pdf",
      "status": "success",
      "confidence": 85.0,
      "text": "Extracted text here...",
      "page_count": 7
    }
  ]
}
```

### CSV Report
**Best for:** Opening in Excel, Google Sheets, or other spreadsheet applications

**Columns included:**
| Column | Description | Example |
|--------|-------------|---------|
| File | Filename | scan1.pdf |
| Status | success/failed | success |
| Provider | OCR provider used | Chrome Lens |
| Languages | Detected languages | en |
| Confidence | Recognition confidence | 85.0 |
| Text Length | Number of characters | 1234 |
| Blocks | Number of text blocks | 3 |
| Words | Approximate word count | 100 |
| Pages | Number of pages | 7 |
| Error | Error message if failed | (empty if success) |

**Use case:** You can open this CSV in Excel to:
- Sort by confidence score
- Filter by language
- Create charts of success rates
- Compare results across different OCR providers

### TXT Report
**Best for:** Human review, printing, quick reference

**Format:**
```
================================================================================
                    BULK OCR PROCESSING REPORT
================================================================================
Generated: 2025-11-15 10:30:00

SUMMARY
-------
Total Files:          5
Successfully Processed: 5
Failed:               0
Success Rate:         100%

STATISTICS
----------
Total Characters:     36,145
Average Confidence:   85.00%
Languages:            en

DETAILED RESULTS
----------------
File: scan1.pdf
Status: SUCCESS
Provider: Chrome Lens
Confidence: 85%
Pages: 7
Characters: 1,234

[Full extracted text here...]

---

File: scan2.jpg
Status: SUCCESS
Provider: Chrome Lens
Confidence: 85%
Pages: 1
Characters: 234

[Full extracted text here...]
```

## 🎯 Common Use Cases

### Use Case 1: Digitizing Paper Documents
**Goal:** Convert a stack of scanned PDFs into searchable text

**Steps:**
1. Place all PDF scans in a folder: `/Documents/scans`
2. Select **Chrome Lens** (best for PDFs)
3. Select **English** language
4. Enable **Process Subfolders** if scans are in multiple folders
5. Select all export formats
6. Click **Start Processing**
7. Download reports and search the JSON or TXT file

### Use Case 2: Multi-Language Document Processing
**Goal:** Extract text from documents in multiple languages

**Steps:**
1. Put documents in `/Documents/multilingual`
2. Select appropriate OCR provider (EasyOCR is best for multiple languages)
3. Click **English, Hindi, Spanish, Chinese** buttons
4. Enable **Process Subfolders**
5. Start processing
6. Use JSON report to see which language was detected for each file

### Use Case 3: Quality Assessment
**Goal:** Check OCR accuracy and confidence scores

**Steps:**
1. Process a sample batch of documents
2. Select all export formats
3. Download and open the **CSV report** in Excel
4. Sort by "Confidence" column to see lowest scoring results
5. Review the TXT report to manually check low-confidence results
6. Use JSON report for detailed metadata

### Use Case 4: Batch Processing for Archive
**Goal:** OCR an entire archive of documents

**Steps:**
1. Organize documents in `/Archive` with subfolders by year/category
2. Select **Tesseract** for speed (fastest local option)
3. Enable **Process Subfolders**
4. Select **JSON export** only (smallest file size, easiest to search)
5. Process the entire folder
6. Extract JSON and build a searchable database

## 🔧 Advanced Options

### Provider Selection Guide

**Tesseract OCR**
- Speed: ⚡⚡⚡ Very Fast (2-5 seconds per file)
- Accuracy: ⭐⭐⭐ Good
- Cost: Free (runs locally)
- Best For: Speed-critical applications, batch processing
- Supported Languages: 100+

**Chrome Lens**
- Speed: ⚡ Slow (10-12 seconds per file)
- Accuracy: ⭐⭐⭐⭐ Excellent
- Cost: Free (limited daily quota)
- Best For: High accuracy needed, PDF handling
- Supported Languages: 50+

**Google Vision**
- Speed: ⚡⚡ Fast (2-4 seconds per file)
- Accuracy: ⭐⭐⭐⭐⭐ Very High
- Cost: Paid (per image)
- Best For: Production use, highest accuracy needed
- Supported Languages: 50+

**EasyOCR**
- Speed: ⚡⚡ Medium (8-10 seconds per file)
- Accuracy: ⭐⭐⭐⭐ Good
- Cost: Free (runs locally)
- Best For: Multiple languages, handwriting
- Supported Languages: 80+

### Language Selection Guide

| Language | Use When | Example |
|----------|----------|---------|
| English | English documents | Business letters, bills |
| Hindi | Hindi documents | Indian newspapers, forms |
| Spanish | Spanish documents | Spanish contracts, notices |
| French | French documents | French books, manuals |
| German | German documents | German technical documents |
| Chinese | Chinese documents | Chinese books, contracts |
| Japanese | Japanese documents | Japanese manuals, forms |

**Tip:** Select multiple languages if documents are multilingual. OCR will detect the actual language used in each document.

### Handwriting Detection

Enable **"Detect Handwriting"** if your documents contain:
- Hand-written notes
- Signatures
- Hand-drawn diagrams with text
- Historical handwritten documents

**Note:** Handwriting detection is slower and may be less accurate than printed text.

## ⚠️ Troubleshooting

### Problem: "No supported image files found"
**Cause:** The folder doesn't contain supported file types
**Solution:**
1. Check folder path is correct
2. Verify files are: .pdf, .jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp
3. Check file permissions (folder must be readable)
4. If using relative path, try absolute path

### Problem: Processing is very slow
**Cause:** Large files or slow provider selected
**Solution:**
1. Try **Tesseract** instead (much faster)
2. Process smaller batches first
3. Check system resources (CPU, memory)
4. Close other applications

### Problem: Confidence scores are low (< 70%)
**Cause:** Poor quality scans or small text
**Solution:**
1. Try **Google Vision** or **Chrome Lens** (more accurate)
2. Increase image quality/resolution if possible
3. Check if documents are rotated correctly
4. Enable "Detect Handwriting" if applicable

### Problem: Wrong language detected
**Cause:** Didn't select the right language
**Solution:**
1. Select the correct language from buttons
2. Try selecting multiple languages for mixed documents
3. Use EasyOCR which handles multilingual better

### Problem: Download button not working
**Cause:** Browser issue or network timeout
**Solution:**
1. Refresh the page and try again
2. Clear browser cache
3. Try different browser
4. Check internet connection

### Problem: Backend error or processing failed
**Cause:** Server issue or folder access problem
**Solution:**
1. Check if folder path exists and is readable
2. Try processing smaller folder first
3. Contact system administrator

## 📋 Report Format Comparison

| Feature | JSON | CSV | TXT |
|---------|------|-----|-----|
| **Size** | Medium (44 KB for 5 files) | Small (0.7 KB for 5 files) | Large (37 KB for 5 files) |
| **Readable** | For programmers | For spreadsheets | For humans |
| **Contains full text** | Yes | No | Yes |
| **Contains metadata** | Yes | Yes (some) | Yes |
| **Importable to Excel** | Via plugin | Native | No |
| **Searchable** | Yes (with tools) | Yes | Yes |
| **Best for** | Data processing | Statistics | Review |

## 💡 Pro Tips

1. **Start small:** Process 5-10 files first to verify settings
2. **Use JSON for archival:** Most complete format, easiest to search
3. **Use CSV for analysis:** Open in Excel to analyze confidence/accuracy
4. **Compare providers:** Process same files with different providers to find best results
5. **Save report links:** Copy download link before closing page
6. **Check errors first:** Review error log before assuming all files processed correctly
7. **Batch by language:** Process same-language documents together
8. **Archive results:** Keep JSON reports for long-term archival and searching

## 🎓 Example Workflow

### Scenario: Processing 100 Insurance Forms

**Step 1: Preparation**
- Collected 100 scanned insurance forms in `/Documents/insurance_forms`
- Forms are organized by year in subfolders
- All forms are in English

**Step 2: Configuration**
1. Open Bulk Processing
2. Enter folder path: `/Documents/insurance_forms`
3. Select provider: **Chrome Lens** (good accuracy for forms)
4. Select language: **English**
5. Check **Process Subfolders** ✓
6. Select formats: **JSON** (for archival), **CSV** (for analysis)

**Step 3: Processing**
1. Click **Start Processing**
2. Watch progress bar: ████████░░░░░░░░░░ 45%
3. Wait for completion (~20-30 minutes for 100 files)

**Step 4: Review Results**
1. Check summary: 100 files, 95 successful, 5 failed
2. Open CSV in Excel to analyze confidence scores
3. Review error log for the 5 failed files
4. Manually process the 5 failed files

**Step 5: Archive**
1. Save JSON report to database
2. Create searchable index from extracted text
3. Link original PDFs with extracted text
4. Implement full-text search capability

## 📞 Getting Help

If you encounter issues:
1. Check the **Troubleshooting** section above
2. Review the technical documentation in **BULK_PROCESSING_FEATURE.md**
3. Contact your system administrator with:
   - Folder path you tried
   - OCR provider selected
   - Error message (if any)
   - Number of files in the folder

---

**Version:** 1.0  
**Last Updated:** November 15, 2025  
**For Questions:** Contact Support Team
