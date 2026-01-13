# How Files Get Uploaded to Archipelago and Linked to Metadata

This document explains the complete workflow of how actual PDF files from Bhushanji folder are uploaded to Archipelago and how they're linked to their OCR metadata.

---

## Overview: The Complete Flow

```
Bhushanji Folder
    ↓
OCR Processing (GVPOCR)
    ↓
CSV File (Metadata) + ZIP File (Source Files)
    ↓
Upload to Archipelago
    ↓
AMI Set Creation (Configuration)
    ↓
Processing in Archipelago
    ↓
Digital Objects with Files + Metadata
```

---

## Step 1: Source Files in Bhushanji

Files start here:

```
./Bhushanji/eng-typed/
├── document1.pdf
├── document2.pdf
├── document3.pdf
└── ...
```

Each PDF is processed by OCR to extract text and metadata.

---

## Step 2: OCR Processing Generates Metadata

For each PDF, OCR produces:

```python
{
  "file_info": {
    "filename": "document1.pdf",
    "file_path": "eng-typed/document1.pdf"
  },
  "text": "Full OCR extracted text...",
  "ocr_metadata": {
    "provider": "google_vision",
    "confidence": 0.95,
    "language": "English",
    "word_count": 1250,
    "character_count": 8500
  },
  "label": "Document 1",
  "description": "PDF processed via OCR"
}
```

---

## Step 3: Create CSV File (Metadata Manifest)

The CSV file contains metadata about each document:

### CSV Structure

```csv
node_uuid,type,label,description,documents,images,ocr_text_file,ocr_metadata_file,thumbnail,ismemberof,language,owner,rights,creator,ocr_text_preview,ocr_provider,ocr_confidence,ocr_language,ocr_processing_date
"uuid-1","DigitalDocument","Document 1","PDF processed","document1.pdf","","document1_ocr.txt","document1_metadata.json","document1_thumb.jpg","394","English","VRI","All rights reserved","VRI","Full OCR text preview...","google_vision","0.95","English","2025-12-07"
"uuid-2","DigitalDocument","Document 2","PDF processed","document2.pdf","","document2_ocr.txt","document2_metadata.json","document2_thumb.jpg","394","English","VRI","All rights reserved","VRI","Full OCR text preview...","google_vision","0.95","English","2025-12-07"
```

### Key Columns Explained

| Column | Purpose | Example |
|--------|---------|---------|
| `node_uuid` | Unique ID for the digital object | `550e8400-e29b-41d4-a716-446655440000` |
| `type` | Content type in Archipelago | `DigitalDocument` |
| `label` | Title/name | `Document 1` |
| `description` | Description | `PDF processed via OCR` |
| **`documents`** | **PDF filename in ZIP** | `document1.pdf` |
| `images` | Image filenames in ZIP | (empty for PDFs) |
| `ocr_text_file` | Full OCR text file | `document1_ocr.txt` |
| `ocr_metadata_file` | OCR metadata JSON | `document1_metadata.json` |
| `thumbnail` | Thumbnail image | `document1_thumb.jpg` |
| `ismemberof` | Parent collection ID | `394` |
| `language` | Document language | `English` |
| `owner` | Organization | `Vipassana Research Institute` |
| `rights` | Rights statement | `All rights reserved` |
| `creator` | Creator | `VRI` |
| `ocr_text_preview` | First 500 chars of OCR | `Text preview...` |
| `ocr_provider` | OCR service used | `google_vision` |
| `ocr_confidence` | OCR accuracy score | `0.95` |
| `ocr_language` | Detected language | `English` |
| `ocr_processing_date` | When OCR was done | `2025-12-07` |

---

## Step 4: Create ZIP File (Source Files)

The ZIP contains actual files referenced in CSV:

```
files.zip
├── document1.pdf          ← Actual PDF file from Bhushanji
├── document2.pdf          ← Actual PDF file from Bhushanji
├── document3.pdf          ← Actual PDF file from Bhushanji
├── document1_ocr.txt      ← Full OCR text
├── document2_ocr.txt      ← Full OCR text
├── document3_ocr.txt      ← Full OCR text
├── document1_metadata.json ← OCR metadata
├── document2_metadata.json ← OCR metadata
├── document3_metadata.json ← OCR metadata
├── document1_thumb.jpg    ← Generated thumbnail
├── document2_thumb.jpg    ← Generated thumbnail
└── document3_thumb.jpg    ← Generated thumbnail
```

**Important**: Files in ZIP are **flat** (no directory structure). Archipelago looks them up by exact filename in the CSV.

---

## Step 5: Upload Files to Archipelago

### 5a. Upload CSV File

```python
# Backend code:
csv_fid = self.upload_file_to_archipelago(csv_path)

# What happens:
POST http://localhost:8001/jsonapi/file/file
Content-Type: text/csv  ← FIXED: Was application/octet-stream
Content: [CSV data]

# Response:
{
  "data": {
    "attributes": {
      "drupal_internal__fid": 312  ← File entity ID
    }
  }
}
```

**Returns**: File ID `312` (Drupal file entity ID)

### 5b. Upload ZIP File

```python
# Backend code:
zip_fid = self.upload_file_to_archipelago(zip_path)

# What happens:
POST http://localhost:8001/jsonapi/file/file
Content-Type: application/zip  ← FIXED: Was application/octet-stream
Content: [ZIP data with all files]

# Response:
{
  "data": {
    "attributes": {
      "drupal_internal__fid": 313  ← File entity ID
    }
  }
}
```

**Returns**: File ID `313` (Drupal file entity ID)

---

## Step 6: Create AMI Set Configuration

The AMI Set tells Archipelago how to process the files:

```json
{
  "csv": "312",           ← Reference to CSV file (FID)
  "zip": "313",           ← Reference to ZIP file (FID)
  "plugin": "spreadsheet",
  "mapping": {
    "globalmapping": "custom",
    "custommapping_settings": {
      "DigitalDocument": {
        "bundle": "digital_object:field_descriptive_metadata",
        "metadata": "direct",
        "files": {
          "documents": "documents",  ← Maps CSV "documents" column to this field
          "images": "images",
          "videos": "videos",
          "audios": "audios",
          "model": "model"
        }
      }
    }
  },
  "pluginconfig": {
    "op": "create"
  },
  "adomapping": {
    "parents": "394"  ← Parent collection ID
  }
}
```

This configuration is stored in Archipelago as an AMI Set entity.

---

## Step 7: Archipelago Processes the AMI Set

When you click "Process" in Archipelago, it does this:

```
1. Read CSV file (FID 312)
   ↓
2. For each row in CSV:
   a) Create new Digital Object (ADO)
   b) Store metadata in field_descriptive_metadata (Strawberry Field JSON)
   c) Look for "document1.pdf" in ZIP file (FID 313)
   d) Extract "document1.pdf" from ZIP
   e) Create Drupal file entity for it
   f) Assign File ID (dr:fid) automatically
   g) Add to "documents" array
   h) Repeat for all files

3. Result: Digital Object with:
   - Metadata from CSV (title, description, OCR text, etc.)
   - Actual PDF file linked (with dr:fid)
   - Thumbnails generated automatically
   - Search indexes created
   - IIIF manifests generated
```

---

## Step 8: Final Result in Archipelago

After processing, each document becomes a Digital Object:

```json
{
  "nid": 123,
  "title": "Document 1",
  "type": "digital_object",
  
  "field_descriptive_metadata": {
    "label": "Document 1",
    "description": "PDF processed via OCR",
    "language": ["English"],
    "owner": "Vipassana Research Institute",
    "rights": "All rights reserved",
    "creator": "VRI",
    
    "note": "Full OCR text (first 5000 chars)...",
    
    "as:document": {
      "urn:uuid:550e8400-e29b-41d4-a716-446655440000": {
        "url": "s3://archipelago/document1.pdf",
        "name": "document1.pdf",
        "dr:fid": 1001,           ← ⭐ ACTUAL FILE ENTITY ID
        "dr:filesize": 563750,
        "dr:mimetype": "application/pdf",
        "flv:exif": {
          "MIMEType": "application/pdf",
          "PageCount": 7,
          "FileSize": "550.5 kB"
        }
      }
    },
    
    "ocr_text_preview": "Full OCR text...",
    "ocr_provider": "google_vision",
    "ocr_confidence": 0.95,
    "ocr_language": "English"
  },
  
  "field_file_drop": {
    "1001": {                     ← Links to actual file by dr:fid
      "filepath": "public://...",
      "filesize": 563750,
      "filemime": "application/pdf"
    }
  },
  
  "ismemberof": ["394"]          ← Linked to collection
}
```

---

## How File and Metadata Are Linked

### The Linking Chain

```
CSV Row
  ↓
documents: "document1.pdf"
  ↓
Archipelago looks in ZIP for "document1.pdf"
  ↓
Extracts file from ZIP
  ↓
Creates Drupal file entity
  ↓
Assigns dr:fid (e.g., 1001)
  ↓
Stores in "as:document" object
  ↓
Links via field_file_drop[1001]
  ↓
⭐ Metadata (title, description, OCR text) linked to file via node
```

### Key Fields in Metadata

The actual PDF file is referenced through:

1. **CSV Column `documents`**: `document1.pdf` → tells where file is in ZIP

2. **as:document Structure**: 
   - Contains file metadata (MIME type, size, page count)
   - Contains `dr:fid: 1001` → reference to Drupal file entity

3. **field_file_drop**:
   - Key: `1001` (the dr:fid)
   - Value: File storage path and properties

4. **Metadata Array**:
   - `ocr_text_preview`, `ocr_provider`, `ocr_confidence`, etc.
   - All stored together with file reference

---

## Complete Example: One Document

### Input (from Bhushanji)
```
./Bhushanji/eng-typed/myfile.pdf  (100 KB PDF)
```

### OCR Results
```json
{
  "file_info": {
    "filename": "myfile.pdf",
    "file_path": "eng-typed/myfile.pdf"
  },
  "text": "Page 1: Lorem ipsum...\nPage 2: ...",
  "ocr_metadata": {
    "provider": "google_vision",
    "confidence": 0.97,
    "language": "English"
  },
  "label": "My File"
}
```

### CSV Row
```csv
"abc-123","DigitalDocument","My File","Processed PDF","myfile.pdf","","myfile_ocr.txt","myfile_metadata.json","myfile_thumb.jpg","394","English","VRI","All rights","VRI","Lorem ipsum...","google_vision","0.97","English","2025-12-07"
```

### ZIP Contents
```
myfile.pdf              ← Actual file from Bhushanji (100 KB)
myfile_ocr.txt          ← Full OCR text
myfile_metadata.json    ← OCR metadata
myfile_thumb.jpg        ← Generated thumbnail
```

### After Archipelago Processes

**Digital Object Created:**
- **Title**: "My File"
- **Description**: "Processed PDF"
- **Metadata**: Language, Creator, Rights, OCR details
- **File**: myfile.pdf (now in Archipelago storage)
  - **dr:fid**: 1001 (Drupal file entity ID)
  - **MIME type**: application/pdf
  - **Size**: 100 KB
  - **Searchable OCR**: "Lorem ipsum..." indexed
- **Parent**: Collection 394
- **Thumbnail**: Generated and stored

---

## Data Flow Diagram

```
┌─────────────────────────────────┐
│  ./Bhushanji/eng-typed/         │
│  myfile.pdf (100 KB)            │
└────────────────┬────────────────┘
                 │ OCR Processing
                 ↓
    ┌────────────────────────────┐
    │ OCR Results                │
    │ - text: "Full OCR..."      │
    │ - confidence: 0.97         │
    │ - provider: google_vision  │
    └────────────┬───────────────┘
                 │
        ┌────────┴──────────┐
        ↓                   ↓
   ┌─────────────┐   ┌──────────────┐
   │ CSV File    │   │ ZIP File     │
   │ (metadata)  │   │ (documents)  │
   │ - label     │   │ - myfile.pdf │
   │ - ocr_text  │   │ - ocr.txt    │
   │ - provider  │   │ - metadata   │
   │ - confidence│   │ - thumbnail  │
   └──────┬──────┘   └──────┬───────┘
          │                 │
          └────────┬────────┘
                   │ Upload to Archipelago
                   ↓
          ┌────────────────────┐
          │ Archipelago        │
          │ FID-312 (CSV)      │
          │ FID-313 (ZIP)      │
          └────────┬───────────┘
                   │ Create AMI Set
                   ↓
          ┌────────────────────┐
          │ AMI Set            │
          │ config + mapping   │
          └────────┬───────────┘
                   │ Process
                   ↓
    ┌──────────────────────────────┐
    │ Digital Object               │
    │ ├─ nid: 456                  │
    │ ├─ title: "My File"          │
    │ ├─ description               │
    │ ├─ ocr_text: "Full OCR..."   │
    │ ├─ provider: google_vision    │
    │ ├─ confidence: 0.97           │
    │ ├─ as:document               │
    │ │  └─ dr:fid: 1001           │
    │ ├─ field_file_drop[1001]     │
    │ │  └─ myfile.pdf file entity │
    │ └─ ismemberof: [394]         │
    └──────────────────────────────┘
```

---

## Key Technical Points

### 1. File IDs (FID)

There are **two types** of file IDs:

| Type | Purpose | Example | When Created |
|------|---------|---------|--------------|
| **csv_fid** | References CSV metadata file | 312 | When CSV uploaded |
| **zip_fid** | References ZIP with documents | 313 | When ZIP uploaded |
| **dr:fid** (internal) | References individual file in ADO | 1001 | When Archipelago extracts from ZIP |

### 2. Content-Type Fix

**Critical Bug (now fixed)**:

```
BEFORE (HTTP 415 error):
POST /jsonapi/file/file
Content-Type: application/octet-stream
[CSV data] → ❌ REJECTED

AFTER (Fixed):
POST /jsonapi/file/file
Content-Type: text/csv
[CSV data] → ✅ ACCEPTED

Same for ZIP:
Content-Type: application/zip ✅
```

### 3. Metadata Storage

All OCR metadata is stored in Strawberry Field JSON:

```json
field_descriptive_metadata: {
  "note": "Full OCR text (5000 chars)",
  "ocr_text_preview": "Text preview",
  "ocr_provider": "google_vision",
  "ocr_confidence": 0.95,
  "ocr_language": "English",
  "ocr_processing_date": "2025-12-07",
  "as:document": {
    "urn:uuid:...": {
      "dr:fid": 1001,
      "dr:filesize": 100000,
      "dr:mimetype": "application/pdf"
    }
  }
}
```

---

## Summary

**How it works:**

1. PDF files from Bhushanji are OCR'd → **Metadata extracted**
2. CSV created → **Contains metadata references + filename pointers**
3. ZIP created → **Contains actual PDF + OCR artifacts**
4. CSV uploaded → **Gets FID 312**
5. ZIP uploaded → **Gets FID 313**
6. AMI Set created → **Links FID 312 + FID 313 with mapping rules**
7. Archipelago processes → **Extracts files from ZIP, creates entities, assigns dr:fids**
8. Result → **Digital Object with PDF file + all metadata linked**

**The file and metadata are linked through:**
- CSV column names (e.g., `documents: "myfile.pdf"`)
- Archipelago's file extraction from ZIP by filename
- Drupal file entity ID (dr:fid) in the `as:document` structure
- All metadata stored in Strawberry Field JSON in same node

---

## See Also

- `AMI_UPLOAD_GUIDE.md` - How to run the upload script
- `ARCHIPELAGO_PUSH_FIX.md` - Details of the Content-Type bug fix
- `AMI_QUICK_START.md` - Quick reference guide
