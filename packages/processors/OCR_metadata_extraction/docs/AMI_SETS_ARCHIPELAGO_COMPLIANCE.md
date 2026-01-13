# AMI Sets - Archipelago Compliance Documentation

**Status**: ✅ Updated to match Archipelago official specifications

**Reference**: [Archipelago Commons AMI Documentation](https://docs.archipelago.nyc/1.4.0/ami_index/)

---

## Overview

This document describes the AMI Set implementation in GVPOCR and how it aligns with Archipelago's official documentation and best practices.

---

## What is an AMI Set?

Per [Archipelago Documentation](https://docs.archipelago.nyc/1.4.0/ami_index/):

> An AMI Set is "a special custom entity that hold an Ingest Strategy generated via the previous Setup steps (as JSON with all its settings), a CSV with data imported from the original source (with UUIDs prepopulated if they were not provided by the user)."

**Key Characteristics**:
- All data lives in a CSV file
- Can be corrected and re-uploaded at any time
- Follows a multi-step setup and configuration process
- Supports batch processing with parent/child validation

---

## AMI Set Structure (Per Archipelago Specs)

### 1. **CSV File Format**

**Required Columns** (per Archipelago documentation):
- `node_uuid` - Unique identifier for the ADO (auto-generated if not provided)
- `type` - Content type (e.g., `DigitalDocument`)
- `label` - Title/label (required field)

**Optional Columns**:
- File references: `documents`, `images`, `videos`, `audios`, `model`
- Metadata: Any Strawberry Field metadata fields
- Custom fields: Application-specific fields

**GVPOCR CSV Implementation** (16 columns):

| Column | Type | Purpose |
|--------|------|---------|
| `node_uuid` | String | Required - unique ADO identifier |
| `type` | String | Required - content type (DigitalDocument) |
| `label` | String | Required - title/label |
| `description` | String | Optional - description text |
| `documents` | String | File column - PDF/document filename from ZIP |
| `images` | String | File column - image filename from ZIP |
| `ismemberof` | String | Collection link (node ID) |
| `language` | String | Language code |
| `owner` | String | Owner organization |
| `rights` | String | Rights statement |
| `creator` | String | Creator name |
| `ocr_text` | Text | OCR extracted text (first 5000 chars) |
| `ocr_provider` | String | OCR provider used |
| `ocr_confidence` | Float | OCR confidence score |
| `ocr_language` | String | Detected language from OCR |
| `ocr_processing_date` | DateTime | OCR processing timestamp |

### 2. **ZIP File Format**

- Contains the actual source files to be ingested
- Files must match filenames referenced in CSV's `documents`, `images`, columns
- Filenames are case-sensitive and must match exactly
- No directory structure inside ZIP (flat structure)

### 3. **AMI Set Configuration (JSON)**

Per Archipelago's mapping specification:

```json
{
  "csv": "file_id_of_csv",
  "zip": "file_id_of_zip",
  "plugin": "spreadsheet",
  "mapping": {
    "globalmapping": "custom",
    "custommapping_settings": {
      "DigitalDocument": {
        "bundle": "digital_object:field_descriptive_metadata",
        "metadata": "direct",
        "files": {
          "documents": "documents",
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
    "parents": "collection_node_id"
  }
}
```

**Configuration Breakdown**:

| Field | Value | Explanation |
|-------|-------|-------------|
| `csv` | FID | Drupal file ID of uploaded CSV |
| `zip` | FID | Drupal file ID of uploaded ZIP |
| `plugin` | spreadsheet | CSV-based import plugin |
| `globalmapping` | custom | Use per-type configuration |
| `bundle` | digital_object:field_descriptive_metadata | Strawberry Field storage location |
| `metadata` | direct | Direct CSV-to-JSON mapping (no Twig template) |
| `files` | {...} | File field mappings per content type |
| `op` | create | Operation type (create new ADOs) |
| `parents` | collection_id | Collection node ID for parent link |

---

## How Archipelago Processes AMI Sets

1. **User creates AMI Set** via API or UI
   - Uploads CSV file → Gets FID
   - Uploads ZIP file → Gets FID
   - Creates AMI Set entity with configuration JSON

2. **User navigates to processing URL** in Archipelago
   - URL format: `{archipelago_url}/amiset/{ami_set_id}/process`

3. **Archipelago processes the AMI Set** (Queue or Batch)
   - Reads CSV file
   - Extracts filenames from `documents`/`images` columns
   - Extracts actual files from ZIP by filename
   - For each file:
     - **Uploads to Drupal file system** → Gets real `dr:fid`
     - **Creates Digital Object (ADO)** with metadata
     - **Auto-populates `documents` array** with `dr:fid`
     - **Auto-generates `as:document` structure** with file metadata
     - **Extracts metadata** (PDF page count, thumbnails, etc.)

4. **Result**: Digital objects with proper file integration
   - Single `as:document` entry per file
   - Real Drupal file entity ID (`dr:fid`)
   - Automatic PDF metadata extraction
   - Generated thumbnails and derivatives

---

## GVPOCR AMI Implementation

### CSV Generation (`create_csv_from_ocr_data`)

**Key Features**:
- ✅ Generates `node_uuid` automatically (unique per record)
- ✅ Sets `type` to `DigitalDocument`
- ✅ Requires valid `label` (skips records without it)
- ✅ Auto-detects file type (documents, images, videos, audios)
- ✅ Matches filenames exactly with ZIP contents
- ✅ Validates required fields before writing CSV
- ✅ Limits OCR text to 5000 chars for CSV compatibility
- ✅ Includes OCR metadata for searchability

**Validation**:
```python
# Skips records with missing filename or label
if not filename or not label:
    logger.warning(f"Skipping record: missing required field")
    continue
```

### ZIP Creation (`create_zip_from_files`)

**Key Features**:
- ✅ Creates flat ZIP structure (no directories)
- ✅ Uses original filenames (matches CSV references)
- ✅ Logs skipped files (missing or inaccessible)
- ✅ Handles relative and absolute paths

### File Upload (`upload_file_to_archipelago`)

**Key Features**:
- ✅ Uploads to Archipelago's managed file system
- ✅ Uses JSON:API for uploads
- ✅ Returns `drupal_internal__fid` (Drupal file entity ID)
- ✅ Logs upload status and FIDs

### AMI Set Creation (`create_ami_set`)

**Key Features**:
- ✅ Creates proper JSON:API request format
- ✅ References CSV FID via `source_data` relationship
- ✅ References ZIP FID via `zip_file` relationship
- ✅ Encodes AMI config as JSON in `set.value`
- ✅ Supports collection mapping via `adomapping.parents`
- ✅ Uses correct content type: `ami_set_entity--ami_set_entity`

---

## Data Transformation Mode

GVPOCR uses **"direct" metadata mode**:

**Per Archipelago docs**:
> "Columns from your spreadsheet source will be cast directly to ADO metadata (JSON), without transformation - best for simple ingestion"

**What This Means**:
- CSV columns are directly cast to metadata fields
- `label` column → ADO title
- `description` column → ADO description
- `language` column → ADO language
- Custom fields like `ocr_text`, `ocr_provider` → Stored in Strawberry Field JSON

**Alternative (Not Used)**:
- **Template mode** - Uses Twig templates for complex transformations
- **Custom (Expert) mode** - Granular per-type control

---

## File Entity Assignment (The Key Difference)

### ❌ Old Direct Mapper Approach
```
You manually set dr:fid = 1, 2, 3
        ↓
Archipelago sees these FIDs
        ↓
Archipelago fetches those file entities (wrong files!)
        ↓
Result: Duplicate/wrong documents displayed
```

### ✅ AMI Sets Approach (Current)
```
Archipelago extracts files from ZIP
        ↓
Archipelago uploads each file to Drupal
        ↓
Drupal assigns real dr:fid automatically
        ↓
Archipelago creates ADO with correct dr:fid
        ↓
Result: Proper file integration + thumbnails
```

---

## Workflow Example

### Step 1: Bulk OCR Processing
```
Files in Bhushanji/eng-typed/
        ↓
Process with OCR provider
        ↓
Get OCR results with text, confidence, language
```

### Step 2: Create AMI Set via API
```
POST /api/archipelago/push-bulk-ami
{
  "job_id": "bulk_abc123",
  "collection_title": "Bhushanji Collection"
}
```

### Step 3: Backend Processing
```
1. Generate CSV from OCR results
   ├─ node_uuid: auto-generated
   ├─ label: filename
   ├─ documents: filename (for ZIP reference)
   └─ ocr_text: extracted text

2. Create ZIP with source files
   └─ Filenames match CSV references exactly

3. Upload CSV to Archipelago → Get FID
4. Upload ZIP to Archipelago → Get FID
5. Create AMI Set entity with configuration
   └─ References both FIDs
```

### Step 4: Manual Processing in Archipelago
```
1. Navigate to /amiset/{ami_set_id}/process
2. Review configuration (should match our setup)
3. Click "Process" → Queue or Batch
4. Archipelago processes:
   ├─ Reads CSV
   ├─ Extracts files from ZIP
   ├─ Uploads each file → Gets dr:fid
   ├─ Creates ADOs with proper metadata
   └─ Generates thumbnails & derivatives
```

### Result
✅ Digital objects with:
- Single `as:document` entry (no duplicates)
- Real Drupal file entity ID (`dr:fid`)
- Proper file integration
- Automatic PDF metadata
- Generated thumbnails

---

## Key Compliance Points

| Requirement | Status | Implementation |
|-------------|--------|-----------------|
| CSV format | ✅ | 16 columns per spec |
| Required fields | ✅ | node_uuid, type, label |
| File field mapping | ✅ | documents, images, videos, audios |
| ZIP structure | ✅ | Flat, matching CSV filenames |
| JSON:API format | ✅ | Correct content type & relationships |
| AMI config structure | ✅ | Per Archipelago specs |
| Data transformation | ✅ | Direct mode (no Twig templates) |
| Metadata storage | ✅ | Strawberry Field JSON |
| File entity creation | ✅ | Archipelago handles automatically |

---

## Troubleshooting

### "Files not displaying"

**Checklist**:
1. ✅ CSV filenames match ZIP filenames exactly (case-sensitive)
2. ✅ AMI Set was processed (not just created)
3. ✅ Check Archipelago logs: `/admin/reports/dblog`
4. ✅ Verify ZIP upload succeeded (check file entity)
5. ✅ Verify CSV upload succeeded (check file entity)

### "CSV upload fails"

- Check file permissions
- Verify GVPOCR_PATH environment variable is set
- Check source files exist at specified paths
- Review backend logs: `docker-compose logs backend`

### "ZIP upload fails"

- Check file size (verify upload limit in Archipelago)
- Verify all source files are accessible
- Check ZIP file is valid (test extraction locally)

### "AMI Set creation fails"

- Verify Archipelago credentials are correct
- Check JSON:API is enabled in Archipelago
- Verify Drupal file entities exist (CSV and ZIP uploaded successfully)
- Review Archipelago logs for JSON:API errors

---

## API Endpoint

**Endpoint**: `POST /api/archipelago/push-bulk-ami`

**Request**:
```json
{
  "job_id": "bulk_job_12345",
  "collection_title": "My Collection",
  "collection_id": 123
}
```

**Response**:
```json
{
  "success": true,
  "ami_set_id": 5,
  "ami_set_name": "OCR Bulk Upload 2025-12-06_14-30-00",
  "csv_fid": 310,
  "zip_fid": 311,
  "message": "AMI Set created successfully. Process it at: http://esmero-web:80/amiset/5/process",
  "total_documents": 25
}
```

---

## References

- **Official Archipelago Documentation**: https://docs.archipelago.nyc/1.4.0/ami_index/
- **AMI Update Operations**: https://docs.archipelago.nyc/1.4.0/ami_update/
- **AMI Spreadsheet Overview**: https://docs.archipelago.nyc/1.0.0-RC3/ami_spreadsheet_overview/
- **Archipelago Commons**: https://archipelago.nyc/

---

## Implementation Files

- **Service**: `/mnt/sda1/mango1_home/gvpocr/backend/app/services/ami_service.py`
- **Routes**: `/mnt/sda1/mango1_home/gvpocr/backend/app/routes/archipelago.py`
- **Tests**: `/mnt/sda1/mango1_home/gvpocr/test_ami_endpoint.sh`

---

**Last Updated**: 2025-12-06
**Status**: ✅ Compliant with Archipelago 1.4.0 specifications
