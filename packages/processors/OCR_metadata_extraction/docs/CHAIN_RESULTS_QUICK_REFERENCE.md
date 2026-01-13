# Chain Results - Quick Reference

**Question**: How is the result for chain stored in JSON? Does it show the result of individual steps?

**Answer**: ✅ **YES - Complete individual step results are stored**

---

## The Short Answer

Every step's output is saved with:
- ✅ Text result
- ✅ Confidence score
- ✅ Processing time
- ✅ Timestamps
- ✅ Error messages (if failed)

All in detailed JSON files.

---

## JSON Files Generated

When you export chain results, you get:

1. **results.json** - COMPLETE with all steps
   ```json
   {
     "images": [
       {
         "filename": "doc.png",
         "steps": [
           { "step_number": 1, "provider": "google_vision", "output": { "text": "..." } },
           { "step_number": 2, "provider": "tesseract", "output": { "text": "..." } },
           { "step_number": 3, "provider": "claude", "output": { "text": "..." } }
         ]
       }
     ]
   }
   ```

2. **step_outputs/** - Individual step outputs
   ```
   step_1/document.txt    (Google Vision output)
   step_2/document.txt    (Tesseract output)
   step_3/document.txt    (Claude output)
   ```

3. **final_outputs/** - Just the final result
   ```
   final_outputs/document.txt    (Step 3 output)
   ```

4. **timeline.json** - Visualization data with all steps

5. **summary.csv** - Quick table summary

---

## Per-Step Data Stored

For EACH step, you get:

```json
{
  "step_number": 1,
  "provider": "google_vision",
  "input_source": "original_image",
  "prompt": "",
  "output": {
    "text": "Raw OCR output...",
    "full_text": "Raw OCR output...",
    "confidence": 0.95
  },
  "metadata": {
    "processing_time_ms": 2000,
    "timestamp": "2025-12-29T10:00:05Z",
    "input_length": 150000,
    "output_length": 1200
  }
}
```

---

## Example: 3-Step Chain

**Input**: `document.png`

**Step 1** (Google Vision)
- Input: document.png (image)
- Output: "Raw OCR text..." (1200 chars)
- Confidence: 0.95
- Time: 2000ms

**Step 2** (Tesseract)
- Input: document.png (image)
- Output: "Tesseract OCR text..." (1100 chars)
- Confidence: 0.87
- Time: 3000ms

**Step 3** (Claude)
- Input: Combined text from Step 1 + Step 2
- Output: "Final processed text..." (2543 chars)
- Confidence: 0.92
- Time: 5000ms

**Result**:
- ✅ All 3 step outputs saved in results.json
- ✅ Each step has separate output file (step_1/, step_2/, step_3/)
- ✅ Final output in final_outputs/
- ✅ Can compare all intermediate results

---

## Key Files to Check

**For complete results**: `results.json`
```
Each image → steps array → Each step has full output data
```

**For visualization**: `timeline.json`
```
Same structure as results.json, optimized for UI display
```

**For individual step outputs**: `step_outputs/step_N/filename.txt`
```
Each step gets its own directory with outputs
```

**For final results**: `final_outputs/filename.txt`
```
Just the output from the last step
```

---

## How to Access Results

### Option 1: Use results.json
```python
import json
import zipfile

with zipfile.ZipFile('chain_results.zip') as z:
    results = json.loads(z.read('results.json'))

    for image in results['images']:
        print(f"Image: {image['filename']}")
        for step in image['steps']:
            print(f"  Step {step['step_number']}: {step['output']['text'][:50]}...")
```

### Option 2: Compare step outputs
```python
with zipfile.ZipFile('chain_results.zip') as z:
    # Compare outputs from different steps
    google_result = z.read('step_outputs/step_1/document.txt').decode()
    tesseract_result = z.read('step_outputs/step_2/document.txt').decode()
    final_result = z.read('step_outputs/step_3/document.txt').decode()

    print("Google Vision:", len(google_result), "chars")
    print("Tesseract:", len(tesseract_result), "chars")
    print("Final (Claude):", len(final_result), "chars")
```

### Option 3: Quick CSV summary
```python
import csv
import zipfile

with zipfile.ZipFile('chain_results.zip') as z:
    reader = csv.reader(z.read('summary.csv').decode().splitlines())
    for row in reader:
        print(row)  # [filename, status, output_length, processing_time, chain_steps]
```

---

## Data Storage Location

### During Processing
MongoDB `bulk_jobs` collection:
```
job.checkpoint.results[i].chain_steps[j]
```

### After Export
ZIP file structure:
```
results.json              ← All detailed results
timeline.json            ← Timeline visualization
summary.csv              ← CSV table
metadata.json            ← Job config
final_outputs/           ← Final results only
step_outputs/step_1/     ← Step 1 outputs
step_outputs/step_2/     ← Step 2 outputs
step_outputs/step_3/     ← Step 3 outputs
```

---

## Complete Example: results.json Structure

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_images": 1,
  "total_processing_time_ms": 10000,
  "images": [
    {
      "filename": "document.png",
      "final_output": "Final text after all processing",
      "processing_mode": "chain",
      "steps": [
        {
          "step_number": 1,
          "provider": "google_vision",
          "output": { "text": "Google's OCR...", "confidence": 0.95 },
          "metadata": { "processing_time_ms": 2000 }
        },
        {
          "step_number": 2,
          "provider": "tesseract",
          "output": { "text": "Tesseract OCR...", "confidence": 0.87 },
          "metadata": { "processing_time_ms": 3000 }
        },
        {
          "step_number": 3,
          "provider": "claude",
          "output": { "text": "Final text after all processing", "confidence": 0.92 },
          "metadata": { "processing_time_ms": 5000 }
        }
      ]
    }
  ]
}
```

---

## Summary Table

| Aspect | Status | Location |
|--------|--------|----------|
| Individual step results | ✅ YES | results.json `steps[]` |
| Step output text | ✅ YES | `output.text` |
| Step confidence | ✅ YES | `output.confidence` |
| Step timing | ✅ YES | `metadata.processing_time_ms` |
| Separate step files | ✅ YES | `step_outputs/step_N/` |
| Final result | ✅ YES | `final_outputs/` |
| Error tracking | ✅ YES | Step `error` field |
| Complete history | ✅ YES | All steps in array |

---

## Answer to Your Question

**Q: How is the result for chain stored in JSON?**
A: In `results.json` with complete structure including all image data

**Q: Does it show the result of individual steps?**
A: ✅ YES - Each step shows:
- Output text
- Confidence score
- Processing time
- Input/output metadata
- Timestamps
- Errors (if any)

**Q: Can I see how text evolved through steps?**
A: ✅ YES - Compare outputs:
- `step_1/document.txt` - First step result
- `step_2/document.txt` - Second step result
- `step_3/document.txt` - Third step result
- Or use results.json and iterate through `steps[]` array

---

**For Detailed Info**: See `CHAIN_RESULTS_JSON_STRUCTURE.md`

**Generated**: December 29, 2025

