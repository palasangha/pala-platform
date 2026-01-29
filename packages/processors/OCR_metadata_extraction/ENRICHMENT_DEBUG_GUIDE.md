# Enrichment Data Flow - Debugging Guide

## Detailed Logging Added ✅

The result-aggregator has been updated with **step-by-step detailed logging** to trace the entire enrichment and ZIP creation process.

## Logging Steps

### Phase 1: Enrichment Initialization
```
[ENRICHMENT] Step 1: Starting inline enrichment for OCR job {job_id}
[ENRICHMENT] Step 1: Total OCR results to enrich: N
[ENRICHMENT] Step 1: ENRICHMENT_AVAILABLE=True, ENRICHMENT_ENABLED=true
```

### Phase 2: Service Initialization
```
[ENRICHMENT] Step 2: Initializing enrichment service
[ENRICHMENT] Step 2: Service initialized: <InlineEnrichmentService object>
```

### Phase 3: Enrichment Processing
```
[ENRICHMENT] Step 3: Calling enrich_ocr_results with timeout=900s
[ENRICHMENT] Step 3: Enrichment completed, output keys: ['enriched_results', 'statistics']
```

### Phase 4: Results Extraction
```
[ENRICHMENT] Step 4: Extracted enriched_results count: N
[ENRICHMENT] Step 4: Enrichment stats: {...}
```

### Phase 5: Completion Summary
```
[ENRICHMENT] Step 5: Enrichment completed for job {job_id}: N successful, 0 failed
```

### Phase 6: MongoDB Save
```
[ENRICHMENT] Step 6: Saving N enriched documents to MongoDB
[ENRICHMENT] Step 6: Enriched documents saved successfully

[ENRICHMENT-DB] Step 6a: Starting to save enriched results, count=N
[ENRICHMENT-DB] Step 6a: OCR Job ID: {job_id}
[ENRICHMENT-DB] Step 6a: Enrichment Stats: {...}
[ENRICHMENT-DB] Step 6b: Processing file: {filename}
[ENRICHMENT-DB] Step 6b: Enriched data keys: [...]
[ENRICHMENT-DB] Step 6c: Document to insert: ['ocr_job_id', 'filename', 'enriched_data', ...]
[ENRICHMENT-DB] Step 6d: Saved document with ID: {id}, filename: {filename}
[ENRICHMENT-DB] Step 6e: All saved! Total documents inserted: N/N
[ENRICHMENT-DB] Step 7: Verifying MongoDB save by querying collection
[ENRICHMENT-DB] Step 7: Verification query returned N documents
[ENRICHMENT-DB] Step 7: Found doc - filename: {filename}, id: {id}
```

### Phase 7: ZIP Creation
```
[ZIP] Step 8: Starting ZIP creation for job {job_id}
[ZIP] Step 8: ZIP file path: /app/uploads/bulk_results/{job_id}/{job_id}_bulk_ocr_results.zip
[ZIP] Step 9: Opening ZipFile for writing
[ZIP] Step 9a: Adding main report files
[ZIP] Step 9b: Added N report files to ZIP
[ZIP] Step 9c: Adding N individual JSON files
[ZIP] Step 9d: Added N individual JSON files to ZIP
[ZIP] Step 9e: Now calling _add_enrichment_results_to_zip
```

### Phase 8: Enrichment ZIP Inclusion
```
[ZIP-ENRICHMENT] Step 10: Starting to add enrichment results for job {job_id}
[ZIP-ENRICHMENT] Step 10a: Querying enrichment_jobs collection
[ZIP-ENRICHMENT] Step 10a: Found 0 enrichment jobs
[ZIP-ENRICHMENT] Step 10b: No enrichment jobs found, trying direct enriched_documents query
[ZIP-ENRICHMENT] Step 10b: Direct query for enriched_documents returned N documents
[ZIP-ENRICHMENT] Step 10c: Processing N enriched documents for ZIP
[ZIP-ENRICHMENT] Step 10d: Adding enriched doc - filename: {filename}, base_name: {base_name}
[ZIP-ENRICHMENT] Step 10e: Added to ZIP: enriched_results/{filename}_enriched.json
[ZIP-ENRICHMENT] Step 10f: Successfully added N enriched documents to ZIP
```

## How to Debug

### 1. Start a New Bulk Job
Use the UI or API to start a bulk OCR job:
```bash
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Content-Type: application/json" \
  -d '{"folder": "./data"}' \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Monitor Logs in Real-Time
```bash
cd /path/to/ocr_metadata_extraction
docker compose logs result-aggregator -f | grep -E "\[ENRICHMENT\]|\[ZIP\]"
```

### 3. Follow the Step Numbers
- **Steps 1-5**: Enrichment processing
- **Step 6**: Saving to MongoDB
- **Steps 8-9**: ZIP creation
- **Step 10**: Adding enrichment data to ZIP

### 4. Check for Issues
```bash
# See all enrichment logs
docker compose logs result-aggregator | grep "\[ENRICHMENT\]"

# See all ZIP logs
docker compose logs result-aggregator | grep "\[ZIP"

# See errors
docker compose logs result-aggregator | grep "ERROR"
```

## Key Verification Points

### Does enrichment service initialize?
Look for:
```
[ENRICHMENT] Step 2: Service initialized: <InlineEnrichmentService...>
```

### Does enrichment process documents?
Look for:
```
[ENRICHMENT] Step 4: Extracted enriched_results count: N  (N > 0?)
```

### Are documents saved to MongoDB?
Look for:
```
[ENRICHMENT-DB] Step 7: Verification query returned N documents
```

### Are enriched documents added to ZIP?
Look for:
```
[ZIP-ENRICHMENT] Step 10b: Direct query for enriched_documents returned N documents
[ZIP-ENRICHMENT] Step 10f: Successfully added N enriched documents to ZIP
```

## Expected Timeline

```
Start Job
  ↓ (30-60s)
[ENRICHMENT] Step 1 - Enrichment starts
  ↓ (5-15 min)
[ENRICHMENT] Step 5 - Enrichment completes
[ENRICHMENT-DB] Steps 6-7 - Save to MongoDB
[ZIP] Step 8 - ZIP creation starts
[ZIP-ENRICHMENT] Step 10 - Add enrichment to ZIP
  ↓
✓ Job complete with enrichment in ZIP
```

## Troubleshooting

### No enrichment logs appear?
- Check if ENRICHMENT_AVAILABLE is true
- Check if ENRICHMENT_ENABLED=true in environment
- Verify get_inline_enrichment_service() is imported

### Enrichment has 0 results?
- Check MCP server is running
- Check if OCR results have text content
- Monitor inline_enrichment_service.py logs

### MongoDB save fails?
- Verify MongoDB connection
- Check enriched_documents collection exists
- Look for [ENRICHMENT-DB] ERROR logs

### Enrichment not in ZIP?
- Verify Step 10b shows N > 0 documents
- Check arcname is created correctly
- Verify zipf.writestr() succeeded

## Log File Locations

```bash
# View logs
docker compose logs result-aggregator --since 10m | tee /tmp/enrichment_debug.log

# Extract just enrichment logs
grep "\[ENRICHMENT\]" /tmp/enrichment_debug.log > /tmp/enrichment_only.log

# Extract just ZIP logs
grep "\[ZIP" /tmp/enrichment_debug.log > /tmp/zip_only.log
```

---

**Status**: ✅ Detailed logging enabled  
**Ready**: Start a test job and monitor logs  
**Expected**: Full enrichment workflow visible in logs
