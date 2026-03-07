# OCR Chain Results - JSON Structure & Storage Format

**Date**: December 29, 2025
**Document**: Complete guide to how chain results are stored and formatted

---

## Overview

OCR Chain results are stored with **complete step-by-step data**, showing the output of each individual step in the chain. This allows users to see how the OCR text evolved through each processing stage.

---

## Data Storage Architecture

### 1. Real-time Storage (During Processing)

Results are stored in MongoDB as processing completes:

**Collection**: `bulk_jobs`
**Field**: `checkpoint.results[]`

Each result includes:
- File metadata
- Final output text
- Chain steps (all intermediate outputs)
- Metadata and timing

### 2. Export Format (When Downloaded)

Results are exported as a **ZIP file** containing multiple JSON files:

```
chain_results.zip
├── results.json          (Full detailed results)
├── timeline.json         (Timeline visualization data)
├── summary.csv          (CSV summary table)
├── metadata.json        (Job configuration)
├── final_outputs/       (Final text files per image)
│   ├── image1.txt
│   ├── image2.txt
│   └── ...
└── step_outputs/        (Individual step outputs per image)
    ├── step_1/
    │   ├── image1.txt
    │   ├── image2.txt
    │   └── ...
    ├── step_2/
    │   ├── image1.txt
    │   ├── image2.txt
    │   └── ...
    └── step_N/
        └── ...
```

---

## JSON Structure with Examples

### 1. results.json - Complete Results with All Steps

**Purpose**: Full detailed results for all processed images with complete step-by-step data

**Structure**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-12-29T10:00:00Z",
  "completed_at": "2025-12-29T10:05:30Z",
  "total_processing_time_ms": 330000,
  "total_images": 2,
  "images": [
    {
      "filename": "document1.png",
      "file_path": "/documents/document1.png",
      "status": "success",
      "processing_mode": "chain",
      "final_output": "Final extracted and processed text after all steps",
      "final_output_length": 2543,
      "processing_time_ms": 150000,
      "total_chain_time_ms": 150000,
      "steps": [
        {
          "step_number": 1,
          "provider": "google_vision",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "Raw OCR output from Google Vision...",
            "full_text": "Raw OCR output from Google Vision...",
            "confidence": 0.95
          },
          "metadata": {
            "processing_time_ms": 2000,
            "timestamp": "2025-12-29T10:00:05Z",
            "input_length": 150000,
            "output_length": 1200
          }
        },
        {
          "step_number": 2,
          "provider": "tesseract",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "OCR output from Tesseract for comparison...",
            "full_text": "OCR output from Tesseract for comparison...",
            "confidence": 0.87
          },
          "metadata": {
            "processing_time_ms": 3000,
            "timestamp": "2025-12-29T10:00:08Z",
            "input_length": 150000,
            "output_length": 1100
          }
        },
        {
          "step_number": 3,
          "provider": "claude",
          "input_source": "combined",
          "prompt": "Combine and reconcile the two OCR outputs to create the most accurate text",
          "output": {
            "text": "Final extracted and processed text after all steps",
            "full_text": "Final extracted and processed text after all steps",
            "confidence": 0.92
          },
          "metadata": {
            "processing_time_ms": 5000,
            "timestamp": "2025-12-29T10:00:13Z",
            "input_length": 2300,
            "output_length": 2543
          }
        }
      ]
    },
    {
      "filename": "document2.png",
      "file_path": "/documents/document2.png",
      "status": "success",
      "processing_mode": "chain",
      "final_output": "Another document's processed text...",
      "final_output_length": 1890,
      "processing_time_ms": 180000,
      "total_chain_time_ms": 180000,
      "steps": [
        {
          "step_number": 1,
          "provider": "google_vision",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "Raw OCR for document 2...",
            "full_text": "Raw OCR for document 2...",
            "confidence": 0.93
          },
          "metadata": {
            "processing_time_ms": 2500,
            "timestamp": "2025-12-29T10:02:00Z",
            "input_length": 200000,
            "output_length": 1400
          }
        },
        {
          "step_number": 2,
          "provider": "tesseract",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "Tesseract output for document 2...",
            "full_text": "Tesseract output for document 2...",
            "confidence": 0.85
          },
          "metadata": {
            "processing_time_ms": 3500,
            "timestamp": "2025-12-29T10:02:06Z",
            "input_length": 200000,
            "output_length": 1300
          }
        },
        {
          "step_number": 3,
          "provider": "claude",
          "input_source": "combined",
          "prompt": "Combine and reconcile the two OCR outputs to create the most accurate text",
          "output": {
            "text": "Another document's processed text...",
            "full_text": "Another document's processed text...",
            "confidence": 0.91
          },
          "metadata": {
            "processing_time_ms": 4500,
            "timestamp": "2025-12-29T10:02:10Z",
            "input_length": 2700,
            "output_length": 1890
          }
        }
      ]
    }
  ]
}
```

### Key Features in results.json

✅ **Complete step data** - Every step's output is included
✅ **Confidence scores** - Each step shows confidence
✅ **Timing information** - Processing time per step
✅ **All intermediate outputs** - Not just final result
✅ **Input/output lengths** - Track text evolution
✅ **Metadata** - Timestamps and detailed info
✅ **Error handling** - Step errors are logged

---

### 2. timeline.json - Timeline Visualization Data

**Purpose**: Simplified data for visualizing step progression

**Structure**:
```json
{
  "total_images": 2,
  "total_time_ms": 330000,
  "success_count": 2,
  "error_count": 0,
  "images": [
    {
      "filename": "document1.png",
      "steps": [
        {
          "step_number": 1,
          "provider": "google_vision",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "Raw OCR output from Google Vision...",
            "full_text": "Raw OCR output from Google Vision...",
            "confidence": 0.95
          },
          "metadata": {
            "processing_time_ms": 2000,
            "timestamp": "2025-12-29T10:00:05Z",
            "input_length": 150000,
            "output_length": 1200
          }
        },
        {
          "step_number": 2,
          "provider": "tesseract",
          "input_source": "original_image",
          "prompt": "",
          "output": {
            "text": "OCR output from Tesseract for comparison...",
            "full_text": "OCR output from Tesseract for comparison...",
            "confidence": 0.87
          },
          "metadata": {
            "processing_time_ms": 3000,
            "timestamp": "2025-12-29T10:00:08Z",
            "input_length": 150000,
            "output_length": 1100
          }
        },
        {
          "step_number": 3,
          "provider": "claude",
          "input_source": "combined",
          "prompt": "Combine and reconcile...",
          "output": {
            "text": "Final extracted and processed text...",
            "full_text": "Final extracted and processed text...",
            "confidence": 0.92
          },
          "metadata": {
            "processing_time_ms": 5000,
            "timestamp": "2025-12-29T10:00:13Z",
            "input_length": 2300,
            "output_length": 2543
          }
        }
      ]
    }
  ]
}
```

---

### 3. summary.csv - Quick Overview Table

**Purpose**: Spreadsheet-friendly summary of all results

**Structure**:
```csv
Filename,Status,Output Length,Processing Time (ms),Chain Steps
document1.png,success,2543,150000,3
document2.png,success,1890,180000,3
```

**Use Cases**:
- Quick filtering and sorting
- Import to Excel/Google Sheets
- Email reports
- Statistics compilation

---

### 4. metadata.json - Job Configuration & Settings

**Purpose**: Job metadata and processing configuration

**Structure**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "processing_mode": "chain",
  "chain_config": {
    "template_id": "template-123",
    "steps": [
      {
        "step_number": 1,
        "provider": "google_vision",
        "input_source": "original_image",
        "prompt": ""
      },
      {
        "step_number": 2,
        "provider": "tesseract",
        "input_source": "original_image",
        "prompt": ""
      },
      {
        "step_number": 3,
        "provider": "claude",
        "input_source": "combined",
        "input_step_numbers": [1, 2],
        "prompt": "Combine and reconcile the two OCR outputs to create the most accurate text"
      }
    ]
  },
  "total_files": 2,
  "processed_files": 2,
  "created_at": "2025-12-29T10:00:00Z",
  "completed_at": "2025-12-29T10:05:30Z",
  "export_date": "2025-12-29T10:10:00Z"
}
```

---

## File Organization in ZIP

### Final Outputs Directory
```
final_outputs/
├── document1.txt    (Final output from last step)
├── document2.txt    (Final output from last step)
└── ...
```

**Content Example** (`document1.txt`):
```
Final extracted and processed text after all steps
This is the output from the last step in the chain (Step 3 - Claude)
Contains the reconciled and most accurate text
```

### Step Outputs Directories
```
step_outputs/
├── step_1/
│   ├── document1.txt    (Google Vision output)
│   ├── document2.txt    (Google Vision output)
│   └── ...
├── step_2/
│   ├── document1.txt    (Tesseract output)
│   ├── document2.txt    (Tesseract output)
│   └── ...
└── step_3/
    ├── document1.txt    (Claude output)
    ├── document2.txt    (Claude output)
    └── ...
```

**Content Example** (`step_outputs/step_1/document1.txt`):
```
Raw OCR output from Google Vision...
This is the initial OCR extraction without processing
```

**Content Example** (`step_outputs/step_2/document1.txt`):
```
OCR output from Tesseract for comparison...
This is the Tesseract OCR extraction for comparison
```

**Content Example** (`step_outputs/step_3/document1.txt`):
```
Final extracted and processed text after all steps...
This is the Claude-processed reconciliation of both OCR outputs
```

---

## How Individual Steps Are Tracked

### Step Result Structure

Each step in the chain stores:

```python
{
    'step_number': 1,              # Sequential step number
    'provider': 'google_vision',   # OCR provider used
    'input_source': 'original_image',  # Where input came from
    'prompt': '',                  # Custom prompt if any
    'output': {
        'text': '...',            # Extracted/processed text
        'full_text': '...',       # Full text with all details
        'confidence': 0.95        # Confidence score
    },
    'metadata': {
        'processing_time_ms': 2000,    # How long it took
        'timestamp': '2025-12-29T10:00:05Z',  # When it ran
        'input_length': 150000,        # Input size
        'output_length': 1200          # Output size
    }
}
```

### Error Handling in Steps

If a step fails:

```python
{
    'step_number': 2,
    'provider': 'tesseract',
    'input_source': 'original_image',
    'prompt': '',
    'error': 'Connection timeout to Tesseract server',
    'metadata': {
        'processing_time_ms': 5000,
        'timestamp': '2025-12-29T10:00:10Z'
    }
    # Note: No 'output' field if error occurred
}
```

---

## Data Flow Example

### Example: 3-Step Chain Processing

**Input**: `document.png` (150KB image)

**Step 1 - Google Vision**
```
Input: document.png (150KB)
↓
Processing: OCR extraction
↓
Output: Raw OCR text (1200 chars)
Confidence: 0.95
Time: 2000ms
```

**Step 2 - Tesseract**
```
Input: Same document.png (150KB)
↓
Processing: Alternative OCR extraction
↓
Output: Tesseract's OCR text (1100 chars)
Confidence: 0.87
Time: 3000ms
```

**Step 3 - Claude (Text Processing)**
```
Input: Combined text from Step 1 + Step 2 (2300 chars)
↓
Processing: Reconcile both OCR outputs with prompt
↓
Output: Final processed text (2543 chars)
Confidence: 0.92
Time: 5000ms
```

**Final Result**:
- All 3 step outputs saved
- Combined processing time: 10,000ms
- Final text is from Step 3 (2543 chars)
- All intermediate outputs available for comparison

---

## Accessing Results from Database

### Before Export (During Processing)

Results stored in MongoDB:

```javascript
// MongoDB Query
db.bulk_jobs.findOne({ job_id: '550e8400...' })

// Result structure in 'checkpoint' field
{
  checkpoint: {
    results: [
      {
        file: 'document1.png',
        file_path: '/documents/document1.png',
        status: 'success',
        text: 'Final output...',
        processing_mode: 'chain',
        chain_steps: [
          { step_number: 1, provider: 'google_vision', output: { text: '...', confidence: 0.95 }, ... },
          { step_number: 2, provider: 'tesseract', output: { text: '...', confidence: 0.87 }, ... },
          { step_number: 3, provider: 'claude', output: { text: '...', confidence: 0.92 }, ... }
        ],
        metadata: { processing_time: 10, total_chain_time_ms: 10000 }
      }
    ]
  }
}
```

### After Export (ZIP File)

Access JSON files:

```python
import zipfile
import json

# Open ZIP
with zipfile.ZipFile('chain_results.zip', 'r') as z:
    # Read results.json
    with z.open('results.json') as f:
        results = json.load(f)

    # Read timeline.json
    with z.open('timeline.json') as f:
        timeline = json.load(f)

    # Access individual step outputs
    for image in results['images']:
        for step in image['steps']:
            print(f"Step {step['step_number']}: {step['output']['text'][:100]}")
```

---

## Step-by-Step Data Available

For each step, you get:

| Field | Example | Use |
|-------|---------|-----|
| `step_number` | 1, 2, 3 | Identify step |
| `provider` | google_vision, tesseract, claude | Show which OCR was used |
| `input_source` | original_image, combined | Understand input routing |
| `prompt` | "Reconcile..." | See custom instructions |
| `output.text` | Full extracted text | Get the result |
| `output.confidence` | 0.95, 0.87, 0.92 | Quality indicator |
| `metadata.processing_time_ms` | 2000, 3000, 5000 | Performance analysis |
| `metadata.timestamp` | ISO datetime | Track when each step ran |
| `metadata.input_length` | 150000, 2300 | Input size tracking |
| `metadata.output_length` | 1200, 2543 | Output size tracking |

---

## Comparison Analysis Across Steps

The JSON format enables easy comparison:

```python
import json

results = json.load(open('results.json'))

# Compare outputs across steps for first image
image = results['images'][0]
steps = image['steps']

print("Step Comparison:")
for step in steps:
    print(f"Step {step['step_number']} ({step['provider']}):")
    print(f"  Text length: {step['metadata']['output_length']} chars")
    print(f"  Confidence: {step['output']['confidence']}")
    print(f"  Time: {step['metadata']['processing_time_ms']}ms")
    print()
```

Output:
```
Step Comparison:
Step 1 (google_vision):
  Text length: 1200 chars
  Confidence: 0.95
  Time: 2000ms

Step 2 (tesseract):
  Text length: 1100 chars
  Confidence: 0.87
  Time: 3000ms

Step 3 (claude):
  Text length: 2543 chars
  Confidence: 0.92
  Time: 5000ms
```

---

## Summary

**Yes - Individual Step Results Are Fully Stored** ✅

Each chain processing includes:
- ✅ Every step's output text
- ✅ Confidence scores per step
- ✅ Processing time per step
- ✅ Metadata for each step
- ✅ Error messages if step fails
- ✅ Separate files for each step's outputs
- ✅ Complete step history in results.json
- ✅ Timeline visualization data
- ✅ CSV summary for quick review

**Available Formats**:
- `results.json` - Complete detailed results with all steps
- `timeline.json` - Visualization-ready timeline
- `summary.csv` - Quick reference table
- `metadata.json` - Job configuration
- `final_outputs/` - Just the final results
- `step_outputs/step_N/` - Individual step outputs

Users can see exactly how the text evolved through each step of the chain!

---

**Generated**: December 29, 2025
**Status**: Complete Documentation
**Confidence**: Very High

