# Enrichment ZIP Integration - Debug Summary

## Issue Found & Fixed

### Root Cause
**Missing dependency**: The `websockets` Python library was not installed in the Docker image, causing the inline enrichment service import to fail silently.

```
ModuleNotFoundError: No module named 'websockets'
```

This caused the result-aggregator to log:
```
Inline enrichment service not available
```

And it would fall back to the OLD NSQ-based enrichment method instead of using the NEW inline enrichment.

### Solution Applied

1. **Added websockets to requirements.txt**:
   ```bash
   echo "websockets>=11.0" >> backend/requirements.txt
   ```

2. **Installed websockets in running container** (as temporary fix):
   ```bash
   docker exec gvpocr-result-aggregator pip install websockets
   ```

3. **Fixed docker-compose.yml mount issue**:
   Changed from:
   ```yaml
   - ./backend/google-credentials.json:/app/google-credentials.json:ro
   ```
   To:
   ```yaml
   - ./backend/google-credentials.json:/app/google-credentials/:ro
   ```
   (Because it's a directory, not a file)

## Current Status

✅ **Inline enrichment service is NOW AVAILABLE**
- `websockets` module installed in container
- Import working: `from app.services.inline_enrichment_service import get_inline_enrichment_service`
- All services running and connected

## How Inline Enrichment Works (NOW FIXED)

### Processing Order

```
1. OCR Completes
   ↓
2. Result Aggregator Starts
   ├─ Deduplicates results
   ├─ Generates reports (JSON/CSV/TXT)  
   ├─ Creates individual JSON files
   ├─ [NEW] Runs inline enrichment BEFORE ZIP
   │  ├─ Connects to MCP server
   │  ├─ Processes all 4 enrichment phases
   │  └─ Saves to MongoDB
   └─ Creates ZIP with enrichment data included
   ↓
3. ZIP Contains
   ├─ results.json
   ├─ results.csv
   ├─ results.txt
   ├─ individual_files/
   ├─ enriched_results/ ✨ NEW
   │  ├─ filename_enriched.json
   │  └─ enrichment_job_summary.json
   └─ raw_model_outputs/ ✨ NEW
```

## What Still Needs to Be Done

### Permanent Fix
Update Dockerfile to ensure websockets is installed during build:
```dockerfile
RUN pip install -r requirements.txt  # Will now include websockets
```

Then rebuild:
```bash
docker compose build backend
docker compose up -d
```

### Testing
Start a new bulk OCR job and verify:
1. Check logs for "Starting inline enrichment"
2. Verify ZIP contains enriched_results/ folder
3. Check enriched_results/enrichment_job_summary.json

## Code Files Modified

1. **`backend/requirements.txt`**
   - Added: `websockets>=11.0`

2. **`backend/app/services/inline_enrichment_service.py`** (NEW)
   - `MCPEnrichmentClient` - Direct WebSocket client
   - `InlineEnrichmentService` - Orchestrates enrichment
   - Processes 4 phases with proper timeouts

3. **`backend/app/workers/result_aggregator.py`** (MODIFIED)
   - Moved enrichment call BEFORE ZIP creation
   - Added `_save_enriched_results_to_db()` method
   - Now calls inline enrichment when ENRICHMENT_ENABLED=true

4. **`docker-compose.yml`** (FIXED)
   - Fixed google-credentials mount path (directory not file)

## Verification Checklist

- [x] Websockets module installed
- [x] Inline enrichment service import successful
- [x] All services running
- [x] Database accessible
- [x] MCP server running (5 min timeout fixed)
- [ ] New bulk job started
- [ ] Enrichment processes inline
- [ ] ZIP contains enriched_results folder
- [ ] Enrichment job summary in ZIP

## Notes for Next Test Run

When you start a new bulk job:
1. OCR will complete in ~30-60 seconds
2. Enrichment will run inline (5-15 minutes)
3. ZIP will be created with enrichment data
4. Total time: ~5-16 minutes

The logs should show:
```
Starting inline enrichment for OCR job XXX
Phase 1: Extracting metadata...
Phase 2: Extracting entities and structure...
Phase 3: Analyzing content...
Phase 4: Analyzing context...
Saved N enriched documents to MongoDB
Added N enriched documents to ZIP
✓ ZIP archive created successfully
```

---

**Status**: ✅ READY FOR TESTING  
**Next Step**: Start a new bulk job and verify enrichment is in ZIP
