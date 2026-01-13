# Archipelago Push Flow - Frontend to Backend

## Quick Answer

**No, `ami_service` is NOT used by the default "Push to Archipelago Commons" button from the frontend.**

There are TWO different push workflows:

1. **Standard Push** (Most Common) - Uses `ArchipelagoService` + `DataMapper`
2. **AMI Sets Push** (Advanced) - Uses `AMIService` exclusively

---

## Push Workflows Comparison

### Workflow 1: Standard Push (Direct JSON:API)

**Frontend Button**: "Push to Archipelago Commons"
**Location**: `/mnt/sda1/mango1_home/gvpocr/frontend/src/components/BulkOCR/BulkJobHistory.tsx:434`

**API Flow**:
```
Frontend
  ↓
[POST] /api/archipelago/push-bulk-job
  ↓
ArchipelagoService (NOT AMIService)
  ├─ Login to Archipelago
  ├─ Create collection node
  └─ For each document:
     ├─ DataMapper.map_ocr_to_archipelago()
     ├─ POST /jsonapi/node/digital_object
     └─ Create Drupal node with metadata
  ↓
✅ Digital objects created immediately
```

**Backend Code**:
```python
# File: /mnt/sda1/mango1_home/gvpocr/backend/app/routes/archipelago.py:130-228

@archipelago_bp.route('/push-bulk-job', methods=['POST'])
def push_bulk_job(current_user_id):
    service = ArchipelagoService()  # NOT AMIService
    result = service.create_bulk_collection(
        collection_title=collection_title,
        document_results=successful_samples,
        collection_metadata=collection_metadata
    )
```

**Services Used**:
- ✅ `ArchipelagoService` (`archipelago_service.py`)
- ✅ `DataMapper` (`data_mapper.py`) - Maps OCR data to Archipelago format
- ❌ `AMIService` - NOT used

---

### Workflow 2: AMI Sets Push (Batch CSV/ZIP)

**Frontend Button**: "Upload to Archipelago (AMI Sets)"
**Location**: `/mnt/sda1/mango1_home/gvpocr/frontend/src/components/BulkOCR/BulkOCRProcessor.tsx:1078`

**API Flow**:
```
Frontend
  ↓
[POST] /api/archipelago/push-bulk-ami
  ↓
AMIService (DIFFERENT SERVICE)
  ├─ Generate CSV from OCR data
  ├─ Create ZIP from source files
  ├─ Upload CSV to Archipelago → Get FID
  ├─ Upload ZIP to Archipelago → Get FID
  └─ Create AMI Set entity
     └─ Provides processing URL
  ↓
⏳ Deferred - User processes in Archipelago UI
  ↓
Archipelago batch processor:
  ├─ Reads CSV
  ├─ Extracts files from ZIP
  ├─ Creates digital objects with proper file entities
  └─ Assigns dr:fid automatically
  ↓
✅ Digital objects created with full file integration
```

**Backend Code**:
```python
# File: /mnt/sda1/mango1_home/gvpocr/backend/app/routes/archipelago.py:332-432

@archipelago_bp.route('/push-bulk-ami', methods=['POST'])
def push_bulk_ami(current_user_id):
    service = AMIService()  # YES - Uses AMIService
    result = service.create_bulk_via_ami(
        ocr_data_list=ocr_data_list,
        collection_name=collection_title,
        collection_id=collection_id
    )
```

**Services Used**:
- ✅ `AMIService` (`ami_service.py`) - Creates AMI Set
- ✅ CSV & ZIP generation
- ❌ `ArchipelagoService` - NOT used
- ❌ `DataMapper` - NOT used

---

## Which Service is Used by Default?

**The default "Push to Archipelago Commons" button uses:**

1. **`ArchipelagoService`** - Main service for pushing
2. **`DataMapper`** - Converts OCR data to Archipelago format
3. **NOT `AMIService`** - This is a separate workflow

---

## Service Routing Table

| Push Button | Endpoint | Handler Function | Service(s) Used |
|-------------|----------|------------------|-----------------|
| "Push to Archipelago Commons" | `/api/archipelago/push-bulk-job` | `push_bulk_job()` | `ArchipelagoService` + `DataMapper` |
| "Upload to Archipelago (AMI Sets)" | `/api/archipelago/push-bulk-ami` | `push_bulk_ami()` | `AMIService` only |
| Single document push | `/api/archipelago/push-document` | `push_document()` | `ArchipelagoService` + `DataMapper` |
| Project push | `/api/archipelago/push-project` | `push_project()` | `ArchipelagoService` + `DataMapper` |

---

## Code Locations

### Frontend Push Buttons

**File**: `/mnt/sda1/mango1_home/gvpocr/frontend/src/components/BulkOCR/BulkJobHistory.tsx`

Button 1 (Standard Push):
```javascript
// Line 434
<button onClick={() => handlePushToArchipelago(job)}>
  Push to Archipelago Commons
</button>

// Handler (Line 211)
fetch('/api/archipelago/push-bulk-job', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    job_id: job.job_id,
    collection_title: metadata.title,
    collection_description: metadata.description
  })
})
```

### Backend Route Handlers

**File**: `/mnt/sda1/mango1_home/gvpocr/backend/app/routes/archipelago.py`

```python
# Standard Push (Line 130)
@archipelago_bp.route('/push-bulk-job', methods=['POST'])
def push_bulk_job(current_user_id):
    service = ArchipelagoService()  # Uses ArchipelagoService
    result = service.create_bulk_collection(
        collection_title=collection_title,
        document_results=successful_samples,
        collection_metadata=collection_metadata
    )

# AMI Sets Push (Line 332)
@archipelago_bp.route('/push-bulk-ami', methods=['POST'])
def push_bulk_ami(current_user_id):
    service = AMIService()  # Uses AMIService
    result = service.create_bulk_via_ami(
        ocr_data_list=ocr_data_list,
        collection_name=collection_title,
        collection_id=collection_id
    )
```

### Service Implementations

**ArchipelagoService**:
- File: `/mnt/sda1/mango1_home/gvpocr/backend/app/services/archipelago_service.py`
- Main methods:
  - `create_digital_object()` - Line 76
  - `create_bulk_collection()` - Line 654
  - `create_digital_object_from_ocr_data()` - Line 789

**AMIService**:
- File: `/mnt/sda1/mango1_home/gvpocr/backend/app/services/ami_service.py`
- Main method:
  - `create_bulk_via_ami()` - Line 464

**DataMapper**:
- File: `/mnt/sda1/mango1_home/gvpocr/backend/app/services/data_mapper.py`
- Main method:
  - `map_ocr_to_archipelago()` - Line 87

---

## Workflow Comparison

### Standard Push Workflow (Direct JSON:API)

**Pros**:
- ✅ Immediate availability - objects appear in Archipelago right away
- ✅ Direct control - can customize each object's metadata
- ✅ Real-time feedback - know status immediately
- ✅ Simpler setup - no manual processing steps

**Cons**:
- ❌ No proper file entities - files stored as S3/MinIO references
- ❌ Limited file metadata - PDFs may not display correctly (before our fix)
- ❌ No thumbnails/derivatives - Archipelago doesn't process files
- ❌ Slower for large batches - one API call per document

**Use Case**: Quick individual document uploads, testing, small batches

---

### AMI Sets Workflow (Batch CSV/ZIP)

**Pros**:
- ✅ Proper file entities - Creates real Drupal file entities with dr:fid
- ✅ Full Archipelago processing - Generates thumbnails, extracts metadata
- ✅ CSV-based - Easy to review and modify metadata
- ✅ Batch efficient - Single AMI Set handles many documents
- ✅ Deferred processing - Can process on schedule

**Cons**:
- ❌ Manual processing required - Must click "Process" in Archipelago UI
- ❌ Async - Results take time, must monitor progress
- ❌ More complex - Additional CSV/ZIP generation step
- ❌ No immediate feedback - Status not visible in our app

**Use Case**: Large batch imports, production uploads, full file integration

---

## Recommended Use

### Use Standard Push ("Push to Archipelago Commons") When:
- Uploading small number of documents
- Quick testing needed
- Immediate visibility required
- Simple metadata OK
- Willing to upload files to S3/MinIO

### Use AMI Sets Push ("Upload to Archipelago (AMI Sets)") When:
- Uploading large batches (50+ documents)
- Full file integration needed (proper dr:fid)
- PDF metadata important (page count, thumbnails)
- Batch processing acceptable
- Files should be in Archipelago's managed storage

---

## Summary

**Answer to "Is ami_service used when we use push to archipelago from frontend?"**

**For the default button**: NO
- The default "Push to Archipelago Commons" button uses `ArchipelagoService` + `DataMapper`
- It does NOT use `AMIService`

**For the advanced button**: YES
- The "Upload to Archipelago (AMI Sets)" button uses `AMIService` exclusively
- It's a completely different workflow with better file integration

This is why the PDF fixes we made to `ami_service.py` only apply to the AMI Sets workflow, not the standard workflow. If you're having PDF display issues with the standard push, the problem is in `ArchipelagoService` or `DataMapper`, not `AMIService`.
