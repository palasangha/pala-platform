# Integration and E2E Test Cases - OCR Provider Chaining

## Overview

This document provides comprehensive test cases for integration and end-to-end testing of the OCR Provider Chaining feature. Each test case includes setup steps, execution flow, expected results, and failure scenarios.

---

## Part 1: Integration Tests

Integration tests verify that multiple components work together correctly.

### IT-001: Template Creation and Persistence

**Objective**: Verify that templates can be created via API and persisted to MongoDB

**Prerequisites**:
- Backend running with MongoDB
- Authenticated user token
- Test data: Valid chain configuration

**Steps**:
```
1. Call POST /api/ocr-chains/templates with valid template data
   {
     "name": "Test Chain",
     "description": "Test template",
     "steps": [
       {
         "step_number": 1,
         "provider": "google_vision",
         "input_source": "original_image",
         "prompt": "",
         "enabled": true
       },
       {
         "step_number": 2,
         "provider": "claude",
         "input_source": "previous_step",
         "prompt": "Extract names",
         "enabled": true
       }
     ],
     "is_public": false
   }

2. Assert HTTP 201 Created response
3. Extract template ID from response
4. Call GET /api/ocr-chains/templates/{id}
5. Assert returned template matches input data
6. Verify created_at and updated_at timestamps
7. Query MongoDB directly to verify persistence
```

**Expected Results**:
- ✅ POST returns 201 with template _id
- ✅ GET returns matching template data
- ✅ MongoDB contains document with all fields
- ✅ User ID matches authenticated user

**Failure Scenarios**:
- ❌ Invalid user_id format → Should return 400 Bad Request
- ❌ Missing required fields (name, steps) → Should return 400
- ❌ Invalid step configuration → Should return 400
- ❌ MongoDB connection fails → Should return 500

**Error Message Tests**:
```
Test: Missing "name" field
Input: { "steps": [...] }
Expected Error: "Template name required"
Actual Error: [Verify message is clear and specific]

Test: Non-sequential steps
Input: steps = [step_1, step_3]
Expected Error: "Step numbers must be sequential (expected 2, got 3)"
Actual Error: [Verify message is clear]

Test: Step 1 with previous_step input
Input: step_number=1, input_source="previous_step"
Expected Error: "Step 1 cannot use 'previous_step' as input"
Actual Error: [Verify message is clear]
```

---

### IT-002: Template Update and Validation

**Objective**: Verify templates can be updated with full validation

**Prerequisites**:
- Template created from IT-001
- Original steps: [Step 1: Google Vision → Step 2: Claude]

**Steps**:
```
1. Update template to new configuration:
   {
     "steps": [
       {"step_number": 1, "provider": "google_vision", "input_source": "original_image"},
       {"step_number": 2, "provider": "ollama", "input_source": "previous_step"},
       {"step_number": 3, "provider": "claude", "input_source": "step_N",
        "input_step_numbers": [2]}
     ]
   }

2. Call PUT /api/ocr-chains/templates/{id} with new data
3. Assert HTTP 200 OK
4. Verify updated_at changed
5. Verify all steps in response

Test invalid update:
6. Attempt to update with forward reference (step 2 → step 4)
7. Assert HTTP 400 Bad Request
8. Verify original template unchanged in MongoDB
```

**Expected Results**:
- ✅ Valid update returns 200 with updated template
- ✅ updated_at timestamp changed
- ✅ Invalid update returns 400 with clear error
- ✅ Original template preserved on validation failure

**Error Message Tests**:
```
Test: Step 2 references step 4 (not yet created)
Attempted Input:
  step 2: input_source="step_N", input_step_numbers=[4]
  step 3: (doesn't exist yet)
Expected Error: "Step 2 cannot reference step 4 (cannot reference self or future steps)"

Test: Circular reference (step 2 → step 1 → step 2)
Note: With current architecture, only forward refs prevented
Expected Error: Should be prevented by validation
```

---

### IT-003: Template Duplication

**Objective**: Verify template duplication preserves all data

**Prerequisites**:
- Template from IT-001

**Steps**:
```
1. Call POST /api/ocr-chains/templates/{id}/duplicate
   Body: { "name": "Test Chain Copy" }

2. Assert HTTP 201 Created
3. Extract new template ID
4. Compare original and duplicate:
   - name: Should be "Test Chain Copy" (different)
   - steps: Should be identical
   - user_id: Should be same
   - is_public: Should be same
5. Verify _id is different
6. Verify both templates exist in MongoDB
```

**Expected Results**:
- ✅ Duplicate created with new _id
- ✅ All steps copied exactly
- ✅ New name applied
- ✅ Both templates queryable

**Edge Cases**:
```
Test: Duplicate non-existent template
Input: POST /api/ocr-chains/templates/invalid_id/duplicate
Expected: 404 Not Found

Test: Duplicate template of another user
Setup: User A creates template
Input: User B attempts to duplicate
Expected: 404 Not Found (authorization check)

Test: Duplicate with empty name
Input: { "name": "" }
Expected: Should use default name or error
```

---

### IT-004: Chain Execution Workflow

**Objective**: Verify complete chain execution from job creation to result retrieval

**Prerequisites**:
- Test images in `/tmp/test_images/`
- 3 images: test1.jpg, test2.jpg, test3.jpg
- NSQ running and workers connected
- All OCR providers available

**Steps**:
```
1. Create test folder with sample images
   mkdir -p /tmp/test_images
   cp test_image.jpg /tmp/test_images/test1.jpg
   cp test_image.jpg /tmp/test_images/test2.jpg
   cp test_image.jpg /tmp/test_images/test3.jpg

2. Create chain template (from IT-001)

3. Start chain job:
   POST /api/ocr-chains/execute
   Body: {
     "folder_path": "/tmp/test_images",
     "chain_config": {
       "template_id": "...",
       "steps": [...]
     },
     "languages": ["en"],
     "handwriting": false,
     "recursive": false
   }

4. Assert HTTP 201 with job_id
5. Store job_id for polling

6. Poll job status:
   GET /api/ocr-chains/results/{job_id}
   Repeat every 2 seconds for 5 minutes

7. Assert status changes:
   - Initially: "processing"
   - Progress updates with each file
   - Finally: "completed" or "error"

8. When completed, verify results:
   - All 3 files processed
   - Each has checkpoint.results entry
   - Each result has chain_steps array
   - Each step has output and metadata
```

**Expected Results**:
- ✅ Job created with proper ID
- ✅ NSQ tasks published for 3 files
- ✅ Status transitions: processing → completed
- ✅ Progress updates: 0% → 100%
- ✅ All files appear in results
- ✅ Each file has 2 steps in chain_steps

**Failure Scenarios**:
```
Test: Invalid folder path
Input: folder_path="/nonexistent/path"
Expected: HTTP 400 with message "Folder not found"

Test: Empty folder
Input: folder_path="/empty/folder"
Expected: Job created but no files processed, status="completed"

Test: Folder with unsupported file types
Input: folder_path="/folder/with/txt/files"
Expected: Files skipped, status="completed" with 0 processed

Test: NSQ not running
Expected: HTTP 500 with message "NSQ not enabled" or connection error

Test: Provider becomes unavailable mid-job
Expected: Step fails, error captured in result, job continues
```

**Error Message Tests**:
```
Test: Invalid chain config
Input: chain_config with forward reference
Expected Error: "Invalid chain configuration: Step 2 cannot reference step 3"

Test: Invalid folder path format
Input: folder_path="relative/path" (not absolute)
Expected Error: Should validate or accept relative paths consistently

Test: Permission denied on folder
Input: folder_path="/root/private"
Expected Error: "Permission denied: /root/private"
```

---

### IT-005: Export Functionality

**Objective**: Verify ZIP export generation and download

**Prerequisites**:
- Completed job from IT-004
- Job has results for 3 images with 2-step chain

**Steps**:
```
1. Call GET /api/ocr-chains/export/{job_id}

2. Assert response headers:
   - Content-Type: application/zip
   - Content-Disposition: attachment; filename="chain_results_*.zip"

3. Assert response is binary blob

4. Download and extract ZIP file:
   unzip -l chain_results_*.zip

5. Verify ZIP structure:
   - results.json (root level)
   - timeline.json (root level)
   - summary.csv (root level)
   - metadata.json (root level)
   - final_outputs/ directory
   - final_outputs/test1.txt
   - final_outputs/test2.txt
   - final_outputs/test3.txt
   - step_outputs/ directory
   - step_outputs/step_1/ directory
   - step_outputs/step_1/test1.txt
   - step_outputs/step_1/test2.txt
   - step_outputs/step_2/test1.txt

6. Verify results.json content:
   ```json
   {
     "job_id": "...",
     "status": "completed",
     "total_images": 3,
     "total_processing_time_ms": 5000,
     "images": [
       {
         "filename": "test1.jpg",
         "status": "success",
         "final_output": "...",
         "steps": [
           {
             "step_number": 1,
             "provider": "google_vision",
             "output": { "text": "...", "confidence": 0.95 },
             "metadata": { "processing_time_ms": 2000 }
           },
           {
             "step_number": 2,
             "provider": "claude",
             "output": { "text": "...", "confidence": 0.90 },
             "metadata": { "processing_time_ms": 1000 }
           }
         ]
       }
     ]
   }
   ```

7. Verify summary.csv:
   Filename, Status, Output Length, Processing Time (ms), Chain Steps
   test1.jpg, success, 150, 3000, 2
   test2.jpg, success, 145, 3100, 2
   test3.jpg, success, 155, 2900, 2

8. Verify metadata.json includes chain_config

9. Verify file contents:
   - final_outputs/test1.txt contains step 2 output (final result)
   - step_outputs/step_1/test1.txt contains step 1 output
```

**Expected Results**:
- ✅ ZIP file generated successfully
- ✅ All required files present
- ✅ JSON files valid and complete
- ✅ CSV properly formatted
- ✅ All output files contain correct text
- ✅ File size reasonable (< 50MB for 3 images)

**Failure Scenarios**:
```
Test: Export non-completed job
Input: job_id with status="processing"
Expected: HTTP 400 with message "Job must be completed before export"

Test: Export non-existent job
Input: job_id="invalid"
Expected: HTTP 404 with message "Job not found"

Test: Export very large results (100,000 images)
Expected: ZIP generation succeeds without OOM
```

**Error Handling Tests**:
```
Test: MongoDB connection fails during export
Expected: HTTP 500 with clear error message
Verify: Temp directory cleaned up

Test: Disk space exhausted
Expected: HTTP 500 with message about disk space
Verify: Temp directory cleaned up

Test: Invalid characters in filenames
Input: Image with name "test[1].jpg"
Expected: ZIP entry created with safe filename
```

---

## Part 2: End-to-End (E2E) Tests

E2E tests verify the complete workflow from user perspective.

### E2E-001: Create Chain, Execute, View Results, Export

**Objective**: Complete workflow from chain creation to export

**Prerequisites**:
- Frontend running on localhost:5173
- Backend running on localhost:5000
- User authenticated
- Test images prepared

**Steps**:
```
1. Navigate to /ocr-chains
   Assert: OCRChainBuilder page loads

2. Create chain template:
   a. Click "Add Step" button
   b. Select provider: "Google Vision"
   c. Verify input_source defaults to "original_image"
   d. Click "Add Step" button again
   e. Select provider: "Claude"
   f. Change input_source to "previous_step"
   g. Enter prompt: "Extract the names mentioned in this text"
   h. Enter template name: "E2E Test Chain"
   i. Enter description: "Chain for testing"
   j. Click "Save Template" button

3. Assert success message appears
4. Assert template appears in template list
5. Enter folder path: "/tmp/test_images"
6. Click "Start Chain Processing"
7. Assert redirect to /ocr-chains/results/{jobId}

8. On OCRChainResults page:
   a. Assert progress bar appears
   b. Wait for processing (poll every 2 seconds)
   c. Observe progress increasing: 0% → 33% → 66% → 100%
   d. Assert each file appears in "Processed Files" list

9. When processing completes:
   a. Click first file in list (test1.jpg)
   b. Assert ChainTimeline appears showing 2 steps
   c. Assert step 1 shows Google Vision output
   d. Assert step 2 shows Claude output
   e. View step metadata (processing time, confidence)

10. Verify final output:
    a. Assert "Final Output" section populated
    b. Assert output is readable text
    c. Click "Copy" button
    d. Verify text copied to clipboard

11. Export results:
    a. Click "Export Results" button
    b. Assert download starts
    c. Verify file: chain_results_<jobId>.zip
    d. Extract and verify contents

12. Verify exported data:
    a. results.json contains all 3 files
    b. final_outputs/ contains 3 .txt files
    c. step_outputs/step_1/ contains 3 files
    d. step_outputs/step_2/ contains 3 files
    e. summary.csv has 3 rows (plus header)
```

**Expected Results**:
- ✅ Template created and saved
- ✅ Chain job started successfully
- ✅ Progress bar updates smoothly
- ✅ All 3 files processed
- ✅ Results display correctly
- ✅ Export generates valid ZIP
- ✅ All files in ZIP accessible and readable

**Failure Scenarios**:
```
Scenario 1: User tries to export during processing
Input: Click "Export Results" while status="processing"
Expected: Button disabled, tooltip says "Job must be completed"

Scenario 2: Browser back button during export
Input: Start export, click back button
Expected: Export continues in background, no error

Scenario 3: User closes browser during export
Input: Close browser after export button clicked
Expected: No partial files left on disk

Scenario 4: Provider becomes unavailable
Input: Google Vision goes offline during processing
Expected: Step 1 shows error, Step 2 continues with empty input
         Export includes error message in step results
```

**Error Message Validation**:
```
Test: Invalid folder path on form submit
Input: folder_path=""
Expected: Error shown: "Folder path is required"

Test: Network error while loading templates
Expected: Error toast shown, user can retry

Test: JSON parsing error in response
Expected: Graceful error handling, no console errors

Test: Very long final output (1MB)
Expected: Page remains responsive, text scrollable
```

---

### E2E-002: Load Existing Template and Execute

**Objective**: Verify users can reuse saved templates

**Prerequisites**:
- Template "E2E Test Chain" from E2E-001 exists
- User authenticated

**Steps**:
```
1. Navigate to /ocr-chains
2. Assert template appears in "Select Template" dropdown
3. Click dropdown, select "E2E Test Chain"
4. Assert steps populate from template:
   - Step 1: Google Vision, original_image
   - Step 2: Claude, previous_step, prompt="Extract the names..."
5. Change folder path to "/tmp/test_images"
6. Click "Start Chain Processing"
7. Assert job created and results page loaded
8. Verify execution proceeds as E2E-001 steps 8-12
```

**Expected Results**:
- ✅ Template loads correctly
- ✅ All step data preserved
- ✅ Execution proceeds normally
- ✅ Results identical to original

**Error Scenarios**:
```
Test: Delete template while editing
Setup: Load template, template gets deleted elsewhere
Input: Try to save changes
Expected: Clear error about template deletion

Test: Template becomes inaccessible (permissions change)
Input: Load template, user access revoked
Expected: Cannot load template, error message shown
```

---

### E2E-003: Error Recovery

**Objective**: Verify system gracefully handles errors

**Prerequisites**:
- Backend and frontend running

**Steps**:
```
Test Case 1: Network Error During Job Execution
1. Start chain job
2. Stop backend server while processing
3. Wait for polling to detect error
4. Assert error message displayed
5. Restart backend
6. Click refresh or retry button
7. Verify job status retrieved successfully

Test Case 2: Provider Failure Mid-Chain
1. Start chain with 2 steps
2. First provider completes successfully
3. Second provider unavailable
4. Assert job completes with one failed step
5. Export results
6. Verify error captured in step result

Test Case 3: Browser Tab Switched
1. Start chain execution
2. Switch browser tabs
3. Switch back after 30 seconds
4. Assert polling resumed, progress updated

Test Case 4: Memory Issues (Large Results)
1. Process 1000 large images
2. Assert export still succeeds
3. Assert no browser crashes or slowdowns
```

**Expected Results**:
- ✅ Errors handled gracefully
- ✅ Clear error messages shown
- ✅ Recovery possible after errors
- ✅ Large result sets handled

---

## Part 3: Performance Tests

### PT-001: Single Step Execution Speed

**Objective**: Measure execution time for simple OCR

**Test Setup**:
```
- Single image: 2400x3200px JPG
- Chain: 1 step (Google Vision)
- Provider: Available and responsive
```

**Execution**:
```
1. Start job
2. Measure time to completion
3. Expected: < 5 seconds for typical image
```

**Acceptance Criteria**:
- ✅ Single step: < 5 seconds
- ✅ Memory usage: < 500MB
- ✅ CPU usage: < 80%

### PT-002: Multi-Step Chain Speed

**Test Setup**:
```
- Single image: 2400x3200px JPG
- Chain: 3 steps (Google Vision → Claude → Ollama)
- Providers: All available
```

**Execution**:
```
1. Start job
2. Measure total time
3. Expected: < 15 seconds
```

**Acceptance Criteria**:
- ✅ 3 steps: < 15 seconds total
- ✅ Step 1: < 5 seconds
- ✅ Step 2: < 6 seconds
- ✅ Step 3: < 6 seconds

### PT-003: Bulk Processing

**Test Setup**:
```
- 100 images in folder
- Chain: 2 steps
- Workers: 4 concurrent
```

**Execution**:
```
1. Start job
2. Monitor progress
3. Expected: 100 files in ~5 minutes with 4 workers
```

**Acceptance Criteria**:
- ✅ 100 files processed
- ✅ No memory leaks over time
- ✅ CPU usage manageable (< 90%)
- ✅ Throughput: > 1 file/sec per worker

### PT-004: Export Generation

**Test Setup**:
```
- 100 completed images
- 2-step chain results
- Total output: ~5MB of text
```

**Execution**:
```
1. Request export
2. Measure ZIP generation time
3. Measure ZIP file size
4. Expected: < 10 seconds generation
```

**Acceptance Criteria**:
- ✅ ZIP generated in < 10 seconds
- ✅ ZIP file size reasonable (< 50MB for 100 images)
- ✅ No memory spikes during export

---

## Test Execution Guide

### Running Backend Unit Tests

```bash
# Navigate to backend
cd backend

# Run template tests
python -m pytest tests/test_ocr_chain_template.py -v

# Run service tests
python -m pytest tests/test_ocr_chain_service.py -v

# Run all chain tests
python -m pytest tests/ -k "chain" -v

# Show coverage
python -m pytest tests/test_ocr_chain_*.py --cov=app.models --cov=app.services
```

### Running Frontend Unit Tests

```bash
# Navigate to frontend
cd frontend

# Run component tests
npm test -- test_ocr_chain_results.test.ts

# Run with coverage
npm test -- --coverage

# Run specific test
npm test -- test_ocr_chain_results.test.ts --testNamePattern="Component Initialization"
```

### Running Integration Tests

```bash
# Start all services
docker-compose up -d mongodb nsq redis

# Start backend
python -m app

# In another terminal, run integration tests
pytest tests/integration/ -v --tb=short

# Specify integration test file
pytest tests/integration/test_chain_workflow.py -v
```

### Running E2E Tests

```bash
# Install test runner (Cypress or Playwright)
npm install --save-dev cypress

# Start all services and applications
docker-compose up
npm run dev

# Open Cypress dashboard
npx cypress open

# Run headless
npx cypress run

# Or with Playwright
npm install --save-dev @playwright/test
npx playwright test
```

---

## Test Reporting

### Report Format

For each test, document:

```markdown
## Test: [Test Name]

**Status**: [PASS | FAIL | SKIP]

**Execution Time**: [Duration]

**Details**:
- Expected: [What should happen]
- Actual: [What happened]
- Error (if any): [Error message]

**Issues Found** (if any):
- Issue #1: [Description]
- Issue #2: [Description]

**Notes**: [Any additional observations]
```

### Example Report

```markdown
## Test: IT-001 - Template Creation and Persistence

**Status**: PASS

**Execution Time**: 2.3 seconds

**Details**:
- Expected: POST /api/ocr-chains/templates returns 201 with template _id
- Actual: Returned 201 with valid _id and all fields present
- Error: None

**Issues Found**: None

**Notes**: All assertions passed, template correctly persisted to MongoDB
```

---

## Automated Test Runner Script

```bash
#!/bin/bash
# run_all_tests.sh

echo "====== OCR CHAIN FEATURE - COMPLETE TEST SUITE ======"

echo ""
echo "📋 Running Backend Unit Tests..."
cd backend
python -m pytest tests/test_ocr_chain_template.py -v --tb=short
python -m pytest tests/test_ocr_chain_service.py -v --tb=short

echo ""
echo "📋 Running Frontend Unit Tests..."
cd ../frontend
npm test -- --coverage --watchAll=false

echo ""
echo "📋 Running Integration Tests..."
cd ..
pytest tests/integration/ -v --tb=short

echo ""
echo "📋 Running E2E Tests..."
npx cypress run

echo ""
echo "====== TEST EXECUTION COMPLETE ======"
```

---

## Conclusion

This comprehensive test suite covers:
- ✅ Unit tests for models and services
- ✅ Integration tests for component interactions
- ✅ E2E tests for complete workflows
- ✅ Performance benchmarks
- ✅ Error scenarios and edge cases
- ✅ Detailed error message validation

**Total Test Coverage**: 80+ test cases
**Estimated Execution Time**: 30-45 minutes
**Success Criteria**: All tests passing with < 5% failures due to external dependencies
