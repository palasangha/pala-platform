# Phase 1 Implementation Guide: Unified Metadata Storage

**Estimated Time:** 2-3 hours  
**Difficulty:** Easy  
**Risk Level:** Very Low  
**Value:** Transformational (stops data loss)

---

## Overview

This phase adds a unified database layer so all processor results persist. No more data disappearing on page refresh!

### What Changes:
1. ✅ Add `metadata_store.py` to `packages/shared/`
2. ✅ Update OCR agent to save results
3. ✅ Add `get_job` tool to MCP for polling
4. ✅ Update frontend to poll instead of wait
5. ✅ Test end-to-end

### What Stays the Same:
- MCP protocol (no changes)
- Agent communication (no changes)
- Existing APIs (no breaking changes)

---

## Step 1: Create Unified Metadata Store

**File:** `packages/shared/metadata_store.py`

```python
"""
Unified metadata storage for all processors.

Every processor (OCR, Transcription, Translation, Metadata Extraction, etc.)
writes to this same store with consistent schema.

This enables:
- Persistent results (no data loss on refresh)
- Multi-stage pipelines (OCR → Metadata → Translation)
- Audit trails (full history)
- ChatGPT-style tool synthesis (combine results to answer questions)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum

# These would normally come from MongoDB connection
# For now, we'll use a basic class


class ProcessorType(Enum):
    """Types of processors"""
    OCR = "ocr"
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    METADATA_EXTRACTION = "metadata_extraction"
    VERIFICATION = "verification"
    CUSTOM = "custom"


class ProcessingStatus(Enum):
    """Status of a processing job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ProcessingJob:
    """
    Represents a single document being processed through pipeline.
    
    Example:
    {
        "job_id": "job_abc123",
        "content_id": "doc_invoice_001",
        "filename": "invoice.pdf",
        "status": "completed",
        "pipeline": ["ocr", "metadata_extraction", "translation"],
        "stages": {
            "ocr": {
                "status": "completed",
                "result": {
                    "text": "extracted text here...",
                    "confidence": 0.92
                },
                "metadata": {
                    "model": "minicpm-v",
                    "provider": "ollama",
                    "duration_seconds": 120,
                    "cost_usd": 0.00,
                    "error": null
                },
                "completed_at": "2026-03-03T10:30:00Z"
            },
            "metadata_extraction": {
                "status": "completed",
                "result": {
                    "invoice_number": "INV-2025-001",
                    "total_amount": 1500.00,
                    "date": "2025-03-01"
                },
                "metadata": {
                    "model": "claude-opus",
                    "provider": "anthropic",
                    "duration_seconds": 5,
                    "cost_usd": 0.15,
                    "error": null
                },
                "completed_at": "2026-03-03T10:31:00Z"
            },
            "translation": {
                "status": "pending",
                "result": null,
                "metadata": {...},
                "completed_at": null
            }
        },
        "created_at": "2026-03-03T10:00:00Z",
        "updated_at": "2026-03-03T10:31:00Z"
    }
    """

    def __init__(
        self,
        content_id: str,
        filename: str,
        pipeline: List[str],
        input_data: Optional[Dict[str, Any]] = None
    ):
        self.job_id = f"job_{uuid.uuid4().hex[:12]}"
        self.content_id = content_id
        self.filename = filename
        self.pipeline = pipeline  # e.g., ["ocr", "metadata_extraction", "translation"]
        self.status = ProcessingStatus.PENDING
        self.stages = {
            stage: {
                "status": ProcessingStatus.PENDING.value,
                "result": None,
                "metadata": {},
                "completed_at": None
            }
            for stage in pipeline
        }
        self.input_data = input_data or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "job_id": self.job_id,
            "content_id": self.content_id,
            "filename": self.filename,
            "pipeline": self.pipeline,
            "status": self.status.value,
            "stages": self.stages,
            "input_data": self.input_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class MetadataStore:
    """
    Unified storage interface for all processor results.
    
    In production, this would use MongoDB. For now, uses in-memory dict.
    """

    def __init__(self, mongo_client=None):
        """
        Initialize metadata store.
        
        Args:
            mongo_client: MongoDB connection (optional for testing)
        """
        self.mongo = mongo_client
        # In-memory fallback for testing
        self._in_memory_store = {}

    def create_job(
        self,
        content_id: str,
        filename: str,
        pipeline: List[str],
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new processing job.
        
        Args:
            content_id: Unique document identifier
            filename: Original filename
            pipeline: List of stages to process (e.g., ["ocr", "metadata", "translation"])
            input_data: Optional input data (file size, format, etc.)
        
        Returns:
            job_id for status tracking
        
        Example:
            job_id = store.create_job(
                content_id="doc_invoice_001",
                filename="invoice.pdf",
                pipeline=["ocr", "metadata_extraction"],
                input_data={"file_size": 128000}
            )
        """
        job = ProcessingJob(content_id, filename, pipeline, input_data)
        
        if self.mongo:
            # Store in MongoDB
            self.mongo.db.processing_jobs.insert_one(job.to_dict())
        else:
            # Store in memory
            self._in_memory_store[job.job_id] = job.to_dict()
        
        return job.job_id

    def update_stage(
        self,
        job_id: str,
        stage: str,
        status: ProcessingStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a processing stage.
        
        Args:
            job_id: Job ID to update
            stage: Stage name (e.g., "ocr", "metadata_extraction")
            status: ProcessingStatus enum
            result: Processing result
            error: Error message if failed
            metadata: Stage metadata (model, provider, cost, duration)
        
        Returns:
            True if successful
        
        Example:
            store.update_stage(
                job_id="job_abc123",
                stage="ocr",
                status=ProcessingStatus.COMPLETED,
                result={"text": "extracted text...", "confidence": 0.92},
                metadata={
                    "model": "minicpm-v",
                    "provider": "ollama",
                    "duration_seconds": 120,
                    "cost_usd": 0.00
                }
            )
        """
        if self.mongo:
            # Update in MongoDB
            update_data = {
                f"stages.{stage}.status": status.value,
                f"stages.{stage}.completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            if result is not None:
                update_data[f"stages.{stage}.result"] = result
            
            if error:
                update_data[f"stages.{stage}.error"] = error
            
            if metadata:
                update_data[f"stages.{stage}.metadata"] = metadata
            
            # Update job overall status
            all_stages = self.get_job(job_id)
            if all_stages:
                stages_dict = all_stages.get("stages", {})
                all_completed = all(
                    s.get("status") in [ProcessingStatus.COMPLETED.value, ProcessingStatus.FAILED.value]
                    for s in stages_dict.values()
                )
                if all_completed:
                    update_data["status"] = ProcessingStatus.COMPLETED.value
            
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = self.mongo.db.processing_jobs.update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        else:
            # Update in memory
            if job_id not in self._in_memory_store:
                return False
            
            job = self._in_memory_store[job_id]
            job["stages"][stage]["status"] = status.value
            job["stages"][stage]["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            if result is not None:
                job["stages"][stage]["result"] = result
            
            if error:
                job["stages"][stage]["error"] = error
            
            if metadata:
                job["stages"][stage]["metadata"] = metadata
            
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return True

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details.
        
        Args:
            job_id: Job ID to retrieve
        
        Returns:
            Job data or None if not found
        """
        if self.mongo:
            return self.mongo.db.processing_jobs.find_one(
                {"job_id": job_id},
                {"_id": 0}
            )
        else:
            return self._in_memory_store.get(job_id)

    def list_jobs_by_content(
        self,
        content_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all jobs for a document.
        
        Useful for seeing processing history.
        
        Args:
            content_id: Document ID
        
        Returns:
            List of all jobs for this document
        """
        if self.mongo:
            return list(self.mongo.db.processing_jobs.find(
                {"content_id": content_id},
                {"_id": 0}
            ).sort("created_at", -1))
        else:
            return [
                job for job in self._in_memory_store.values()
                if job.get("content_id") == content_id
            ]

    def get_stage_result(
        self,
        job_id: str,
        stage: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get result from specific stage.
        
        Useful for OCR agent reading metadata extraction results before translation.
        
        Args:
            job_id: Job ID
            stage: Stage name
        
        Returns:
            Stage result or None
        """
        job = self.get_job(job_id)
        if not job:
            return None
        
        stage_data = job.get("stages", {}).get(stage, {})
        return stage_data.get("result")

    def list_pending_jobs(self, stage: str, limit: int = 10) -> List[str]:
        """
        Get pending jobs for a stage.
        
        Used by agents polling for work.
        
        Args:
            stage: Stage name (e.g., "ocr", "metadata_extraction")
            limit: Max jobs to return
        
        Returns:
            List of job IDs
        
        Example:
            # OCR Agent polls for work
            pending_jobs = store.list_pending_jobs("ocr", limit=1)
            if pending_jobs:
                job_id = pending_jobs[0]
                # Process job_id
                store.update_stage(job_id, "ocr", ProcessingStatus.PROCESSING)
        """
        if self.mongo:
            jobs = self.mongo.db.processing_jobs.find(
                {f"stages.{stage}.status": ProcessingStatus.PENDING.value},
                {"job_id": 1}
            ).limit(limit)
            return [job["job_id"] for job in jobs]
        else:
            pending = [
                job_id for job_id, job in self._in_memory_store.items()
                if job.get("stages", {}).get(stage, {}).get("status") == ProcessingStatus.PENDING.value
            ]
            return pending[:limit]

    def add_event(
        self,
        job_id: str,
        event_type: str,
        stage: str,
        details: Dict[str, Any]
    ):
        """
        Add event to audit log.
        
        Creates immutable record of all processing events.
        
        Args:
            job_id: Job ID
            event_type: "stage_started", "stage_completed", "stage_failed", etc.
            stage: Stage name
            details: Event details
        
        Example:
            store.add_event(
                job_id="job_abc123",
                event_type="stage_completed",
                stage="ocr",
                details={"confidence": 0.92, "text_length": 1234}
            )
        """
        event = {
            "job_id": job_id,
            "event_type": event_type,
            "stage": stage,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.mongo:
            self.mongo.db.processing_events.insert_one(event)
        # Note: We don't track events in memory for testing


# Singleton instance for easy access
_metadata_store = None


def get_metadata_store(mongo_client=None) -> MetadataStore:
    """Get or create singleton metadata store"""
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = MetadataStore(mongo_client)
    return _metadata_store


# Type hints for agent code
JobID = str
StageResult = Dict[str, Any]
```

---

## Step 2: Update OCR Agent

**File:** `packages/agents/ocr-agent/main.py`

Add these imports and changes:

```python
# At top of file, add:
import sys
from pathlib import Path

# Add to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from metadata_store import (
    get_metadata_store,
    ProcessingStatus,
    ProcessingJob
)

# In handle_extract_text function, AFTER extraction, add:

async def handle_extract_text(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text from image"""
    
    image_path = params.get("image_path")
    image_data = params.get("image_data")
    file_name = params.get("file_name", "document")
    provider_name = params.get("provider", "tesseract")
    language = params.get("language", "eng")
    
    # NEW: Get job_id for persistence
    job_id = params.get("job_id")
    
    logger.info(f"[TRACE] handle_extract_text called with params keys: {list(params.keys())}")
    
    # ... existing code for decoding base64 ...
    
    try:
        logger.info(f"[TRACE] Getting provider instance for: {provider_name}")
        provider = _get_provider(provider_name)
        
        # NEW: Mark job as processing
        if job_id:
            metadata_store = get_metadata_store()
            metadata_store.update_stage(
                job_id=job_id,
                stage="ocr",
                status=ProcessingStatus.PROCESSING
            )
        
        logger.info(f"[TRACE] Starting extraction from file: {image_path}")
        result = await _progress_wrapper(
            _extract_text_for_file(provider, image_path, language),
            f"OCR extraction using {provider_name}"
        )
        
        logger.info(f"[TRACE] Extraction successful, extracted text length: {len(result.get('text', ''))}")
        
        # NEW: Store result in database
        if job_id:
            metadata_store = get_metadata_store()
            metadata_store.update_stage(
                job_id=job_id,
                stage="ocr",
                status=ProcessingStatus.COMPLETED,
                result={
                    "text": result.get("text"),
                    "confidence": result.get("confidence")
                },
                metadata={
                    "model": result.get("metadata", {}).get("model"),
                    "provider": result.get("metadata", {}).get("provider"),
                    "duration_seconds": 120,  # TODO: actual timing
                    "cost_usd": 0.00
                }
            )
            logger.info(f"[TRACE] Job {job_id} stored in database")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRACE] Error in extract_text: {e}", exc_info=True)
        
        # NEW: Mark job as failed
        if job_id:
            metadata_store = get_metadata_store()
            metadata_store.update_stage(
                job_id=job_id,
                stage="ocr",
                status=ProcessingStatus.FAILED,
                error=str(e)
            )
        
        raise
```

---

## Step 3: Add MCP Tools for Job Management

**File:** `packages/mcp-server/src/registry/job-tools.ts`

```typescript
/**
 * Job management tools for polling and querying results
 */

export const JOB_TOOLS = [
  {
    name: "get_job",
    description: "Get status and results of a processing job",
    inputSchema: {
      type: "object",
      properties: {
        job_id: {
          type: "string",
          description: "Job ID returned from extraction tool"
        }
      },
      required: ["job_id"]
    }
  },
  {
    name: "list_jobs",
    description: "List all jobs for a document",
    inputSchema: {
      type: "object",
      properties: {
        content_id: {
          type: "string",
          description: "Document/content ID"
        }
      },
      required: ["content_id"]
    }
  }
];

// Handler implementations would go in server.ts
```

---

## Step 4: Update Frontend to Utilize New Storage

**File:** `apps/web/components/Dashboard.tsx`

```typescript
// Add state for job tracking
const [jobId, setJobId] = useState<string | null>(null);
const [jobStatus, setJobStatus] = useState<string>("idle");
const [pollingInterval, setPollingInterval] = useState<number | null>(null);

// Poll job status
useEffect(() => {
  if (!jobId) return;

  const pollJob = async () => {
    try {
      const result = await send("tools/invoke", {
        toolName: "get_job",
        arguments: { job_id: jobId }
      });

      const job = result as any;
      setJobStatus(job.status);

      if (job.status === "completed" || job.status === "failed") {
        // Job complete, show results
        const ocrStage = job.stages?.ocr;
        if (ocrStage?.result) {
          setOCRResult(ocrStage.result.text);
          setExtractedText(ocrStage.result.text);
        }

        // Stop polling
        setPollingInterval(null);
      }
    } catch (err) {
      console.error("Error polling job:", err);
    }
  };

  // Poll every 2 seconds
  const interval = window.setInterval(pollJob, 2000);
  setPollingInterval(interval as any);

  return () => clearInterval(interval);
}, [jobId, send]);

// When user uploads file, now create job FIRST
const handleRunOCR = async () => {
  if (!documentFile) {
    alert("Please select a document");
    return;
  }

  try {
    setLoading(true);
    setOCRResult("");

    // NEW: Create job first
    const createJobResult = await send("tools/invoke", {
      toolName: "create_job",
      arguments: {
        content_id: `doc_${Date.now()}`,
        filename: documentFile.name,
        pipeline: ["ocr"]
      }
    });

    const newJobId = createJobResult.job_id;
    setJobId(newJobId);

    // Convert file to base64
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const arrayBuffer = reader.result as ArrayBuffer;
        const bytes = new Uint8Array(arrayBuffer);
        const binary = String.fromCharCode.apply(null, Array.from(bytes));
        const base64Data = btoa(binary);

        // NEW: Pass job_id to extraction tool
        await send("tools/invoke", {
          toolName: "extract_text",
          arguments: {
            image_data: base64Data,
            file_name: documentFile.name,
            provider: selectedOCRProvider,
            language: "eng",
            job_id: newJobId  // NEW!
          }
        });

        // Job queued, now start polling
        setJobStatus("processing");
      } catch (err) {
        console.error("Error queuing OCR:", err);
        setOCRResult("Error: Failed to queue OCR job");
      }
    };

    reader.readAsArrayBuffer(documentFile);
  } catch (err) {
    console.error("Error creating job:", err);
    setOCRResult("Error: Failed to create job");
  } finally {
    setLoading(false);
  }
};
```

---

## Step 5: Database Schema (MongoDB)

**File:** `packages/shared/mongodb_schema.js`

```javascript
// Create indexes for performance
db.processing_jobs.createIndex({ "job_id": 1 }, { unique: true })
db.processing_jobs.createIndex({ "content_id": 1 })
db.processing_jobs.createIndex({ "status": 1 })
db.processing_jobs.createIndex({ "created_at": -1 })
db.processing_jobs.createIndex({ "stages.ocr.status": 1 })
db.processing_jobs.createIndex({ "stages.metadata_extraction.status": 1 })
db.processing_jobs.createIndex({ "stages.translation.status": 1 })

db.processing_events.createIndex({ "job_id": 1 })
db.processing_events.createIndex({ "timestamp": -1 })
db.processing_events.createIndex({ "event_type": 1 })

// Sample document
db.processing_jobs.insertOne({
  "job_id": "job_abc123def456",
  "content_id": "doc_invoice_001",
  "filename": "invoice.pdf",
  "pipeline": ["ocr", "metadata_extraction", "translation"],
  "status": "completed",
  "stages": {
    "ocr": {
      "status": "completed",
      "result": {
        "text": "Invoice Number: INV-2025-001...",
        "confidence": 0.92
      },
      "metadata": {
        "model": "minicpm-v",
        "provider": "ollama",
        "duration_seconds": 120,
        "cost_usd": 0.00
      },
      "error": null,
      "completed_at": "2026-03-03T10:30:00Z"
    },
    "metadata_extraction": {
      "status": "pending",
      "result": null,
      "metadata": {},
      "error": null,
      "completed_at": null
    },
    "translation": {
      "status": "pending",
      "result": null,
      "metadata": {},
      "error": null,
      "completed_at": null
    }
  },
  "input_data": {},
  "created_at": "2026-03-03T10:00:00Z",
  "updated_at": "2026-03-03T10:30:00Z"
})
```

---

## Step 6: Testing

**File:** `tests/phase1_integration_test.py`

```python
import pytest
from packages.shared.metadata_store import (
    MetadataStore,
    ProcessingStatus
)


def test_create_job():
    """Test job creation"""
    store = MetadataStore()
    
    job_id = store.create_job(
        content_id="doc_test_001",
        filename="test.pdf",
        pipeline=["ocr", "metadata_extraction"]
    )
    
    assert job_id.startswith("job_")
    assert store.get_job(job_id) is not None


def test_update_stage():
    """Test stage update"""
    store = MetadataStore()
    
    job_id = store.create_job(
        content_id="doc_test_002",
        filename="test.pdf",
        pipeline=["ocr"]
    )
    
    # Update OCR stage
    success = store.update_stage(
        job_id=job_id,
        stage="ocr",
        status=ProcessingStatus.COMPLETED,
        result={"text": "sample text", "confidence": 0.95},
        metadata={"provider": "ollama", "duration_seconds": 120}
    )
    
    assert success
    job = store.get_job(job_id)
    assert job["stages"]["ocr"]["status"] == "completed"
    assert job["stages"]["ocr"]["result"]["confidence"] == 0.95


def test_list_pending_jobs():
    """Test finding pending jobs"""
    store = MetadataStore()
    
    job_id = store.create_job(
        content_id="doc_test_003",
        filename="test.pdf",
        pipeline=["ocr"]
    )
    
    pending = store.list_pending_jobs("ocr")
    assert job_id in pending


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Rollout Checklist

- [ ] **Step 1:** Create `packages/shared/metadata_store.py`
- [ ] **Step 2:** Update `ocr-agent/main.py` with storage calls
- [ ] **Step 3:** Add job tools to MCP server
- [ ] **Step 4:** Update frontend dashboard for polling
- [ ] **Step 5:** Create MongoDB indexes and collections
- [ ] **Step 6:** Run integration tests
- [ ] **Step 7:** Test end-to-end:
  - [ ] Upload document
  - [ ] Get job_id back
  - [ ] Poll job status
  - [ ] See results persist on refresh
  - [ ] Check database directly
- [ ] **Step 8:** Document changes for team

---

## Verification

After implementation, verify:

✅ **User uploads PDF**
- ✓ Job is created with job_id
- ✓ Job status shows "processing"

✅ **OCR processes**
- ✓ Results stored in database
- ✓ Job status updates to "completed"

✅ **Frontend polls**
- ✓ Frontend gets job status updates every 2 seconds
- ✓ When complete, shows results

✅ **Data persistence**
- ✓ Refresh page → results still visible
- ✓ Query MongoDB directly → data is there
- ✓ Can see full history of what was processed

✅ **Ready for Phase 2**
- ✓ Now can chain jobs (OCR → Metadata → Translation)
- ✓ Foundation set for async processing

---

## Troubleshooting

**Q: Job status stuck at "processing"?**
A: Check agent logs for errors. Make sure `metadata_store.update_stage()` is being called.

**Q: Frontend not polling?**
A: Check browser console. Make sure `get_job` tool is registered in MCP.

**Q: Results not in database?**
A: Verify MongoDB connection. Check agent is calling `metadata_store.update_stage()`.

**Q: Tests failing?**
A: Make sure `ProcessingStatus` enum values match what's stored.

---

## Next: Phase 2

Once this is working, you'll have foundation for:
- Job queues (agents poll for work)
- Multi-stage pipelines (OCR → Metadata → Translation auto-chaining)
- Error recovery (failed jobs can retry)
- ChatGPT-style tools (combine results to answer questions)

**Estimated Phase 2 time:** 1 week of development

