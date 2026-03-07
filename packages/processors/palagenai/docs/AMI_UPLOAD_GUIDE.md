# AMI Sets Upload Guide - Upload Bhushanji to Archipelago

This guide shows you how to use the provided Python script to upload files from the `./Bhushanji` folder to Archipelago Commons using AMI Sets.

---

## Quick Start (2 Minutes)

### Prerequisites
- Backend running: `docker-compose up backend` or `python3 app.py`
- Archipelago running: `docker-compose up`
- Python 3 installed with `requests` library: `pip install requests`
- Files in `./Bhushanji/eng-typed/` (or similar folder)

### Run the Script

```bash
python3 ami_upload_bhushanji.py \
  --email test@example.com \
  --password your_password \
  --folder eng-typed \
  --provider google_vision
```

That's it! The script will:
1. ✅ Authenticate
2. ✅ Start OCR processing
3. ✅ Wait for completion
4. ✅ Upload to Archipelago
5. ✅ Show you the processing URL

---

## Available Options

### Required Arguments
```
--email           Your GVPOCR email address
--password        Your GVPOCR password
```

### Optional Arguments
```
--folder          Folder within Bhushanji (default: eng-typed)
--provider        OCR provider to use (default: google_vision)
                  Options: google_vision, ollama, tesseract
--backend         Backend URL (default: http://localhost:5000)
--limit           Max number of files to process (default: all)
--collection-title Custom collection title in Archipelago
```

---

## Examples

### Example 1: Process English Typed Documents
```bash
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder eng-typed \
  --provider google_vision
```

### Example 2: Process Hindi Typed Documents (Limit to 10 files)
```bash
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder hin-typed \
  --provider google_vision \
  --limit 10
```

### Example 3: Process Hindi Written Documents
```bash
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder hin-written \
  --provider ollama
```

### Example 4: Custom Backend and Collection Title
```bash
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --backend http://192.168.1.100:5000 \
  --folder eng-typed \
  --collection-title "My Special Collection - December 2025"
```

---

## What the Script Does (Step by Step)

### Step 1: Verify Bhushanji Folder
- Checks if `./Bhushanji/eng-typed/` (or your chosen folder) exists
- Counts available files
- Shows warning if folder not found (but continues anyway)

### Step 2: Authenticate
- Logs in with your email and password
- Gets JWT authentication token
- Stores token for subsequent API calls

### Step 3: Start OCR Processing
- Makes API request to backend: `/api/bulk/process`
- Backend starts processing files from your folder
- Returns a job ID to track progress

### Step 4: Wait for Completion
- Polls job status every 5 seconds
- Shows progress bar: `[████████░░░░] 42/50 (84%)`
- Waits until all files are processed
- Handles errors if processing fails

### Step 5: Upload to Archipelago
- Calls backend endpoint: `/api/archipelago/push-bulk-ami`
- Backend creates AMI Set with:
  - CSV file with document metadata
  - ZIP file with source documents
- Returns AMI Set ID and processing URL

### Step 6: Show Results
- Displays the Archipelago processing URL
- Shows next steps to process documents
- Provides link to view results

---

## Output Example

```
============================================================
         Upload Bhushanji to Archipelago via AMI Sets
============================================================

Verifying Bhushanji folder...
✅ Found folder: ./Bhushanji/eng-typed
✅ Files found: 42

[1/5] Authenticating...
✅ Authenticated (token: eyJhbGciOiJIUzI1NiIs...)

[2/5] Starting OCR on folder: eng-typed
     Provider: google_vision
✅ OCR job started (ID: job_1234567890)

[3/5] Processing files...
     [████████████████████] 42/42 (100%)
✅ OCR completed (42/42 files)

[4/5] Creating AMI Set in Archipelago...
     Collection: Bhushanji eng-typed - 2025-12-07
✅ AMI Set created successfully!
     AMI Set ID: 5
     Documents: 42
     CSV File ID: 312
     ZIP File ID: 313

[5/5] Summary
============================================================
✅ SUCCESS! Your files are ready in Archipelago
============================================================

Processing URL: http://localhost:8001/amiset/5/process

Next steps:
1. Open the URL above in your browser
2. Review the AMI Set configuration
3. Click the 'Process' tab
4. Choose 'Process via Queue' (recommended)
5. Monitor progress in Archipelago

View your documents at:
  http://localhost:8001/admin/content
```

---

## Folder Structure

The script expects files in this structure:

```
./Bhushanji/
├── eng-typed/          ← English typed documents (PDFs)
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
├── hin-typed/          ← Hindi typed documents
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
└── hin-written/        ← Hindi handwritten documents
    ├── document1.pdf
    ├── document2.pdf
    └── ...
```

If your folder is elsewhere, you can use absolute path:
```bash
# From the root of the repository
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder /mnt/sda1/mango1_home/Bhushanji/eng-typed
```

---

## Troubleshooting

### Error: "Authentication failed"
```bash
# Check your credentials
# Make sure email and password are correct
python3 ami_upload_bhushanji.py \
  --email your-actual-email@example.com \
  --password your-actual-password
```

### Error: "Could not find eng-typed folder in Bhushanji"
```bash
# Check where your files are located
find . -name "*.pdf" -type f | head -5

# Use the correct path
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder /full/path/to/your/folder
```

### Error: "Backend is not accessible"
```bash
# Make sure backend is running
docker-compose ps
# or
python3 backend/app.py

# Check backend URL
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --backend http://localhost:5000  # or your actual URL
```

### Error: "Connection refused"
```bash
# Check if Archipelago is running
curl http://localhost:8001/

# If not, start it
docker-compose up
```

### "Job timeout after 3600 seconds"
- Files are still being processed but took too long
- You can check status manually:
```bash
# Use the job_id from the output
curl http://localhost:5000/api/bulk/status/job_1234567890 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### "No files processed" or "Job failed"
- Check if files exist in the folder
- Verify file permissions
- Check backend logs: `docker-compose logs backend`

---

## Advanced Usage

### Process Multiple Folders in Sequence
```bash
#!/bin/bash
# upload_all_folders.sh

EMAIL="user@example.com"
PASSWORD="password123"

for folder in eng-typed hin-typed hin-written; do
  echo "Processing $folder..."
  python3 ami_upload_bhushanji.py \
    --email $EMAIL \
    --password $PASSWORD \
    --folder $folder \
    --provider google_vision
  
  echo "Waiting 10 seconds before next folder..."
  sleep 10
done

echo "All folders processed!"
```

Run it:
```bash
chmod +x upload_all_folders.sh
./upload_all_folders.sh
```

### Process in Parallel (with limit)
```bash
#!/bin/bash
# upload_parallel.sh

EMAIL="user@example.com"
PASSWORD="password123"

# Start all in background
python3 ami_upload_bhushanji.py --email $EMAIL --password $PASSWORD --folder eng-typed &
python3 ami_upload_bhushanji.py --email $EMAIL --password $PASSWORD --folder hin-typed &
python3 ami_upload_bhushanji.py --email $EMAIL --password $PASSWORD --folder hin-written &

# Wait for all to complete
wait

echo "All uploads complete!"
```

### Get Job ID Without Waiting
```bash
# Just start the job, don't wait for completion
JOB_ID=$(python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password123 \
  --folder eng-typed \
  --skip-wait 2>&1 | grep "Job started" | grep -o "job_[0-9]*")

echo "Job ID: $JOB_ID"

# Check status later
curl http://localhost:5000/api/bulk/status/$JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## What Gets Uploaded to Archipelago?

When you run the script, it uploads:

1. **CSV File** (Metadata)
   - Document titles
   - OCR text (first 5000 characters)
   - OCR provider, confidence, language
   - File references
   - Archipelago metadata

2. **ZIP File** (Source Documents)
   - All PDF files from your folder
   - Named according to the CSV references
   - In flat structure (no subdirectories)

3. **AMI Set** (Configuration)
   - Mapping rules for how to import
   - File entity assignments
   - Collection membership
   - Processing instructions

Example CSV structure:
```
node_uuid,type,label,description,documents,ismemberof,ocr_text,...
,DigitalDocument,document1.pdf,OCR processed,document1.pdf,394,"Full OCR text...",...
,DigitalDocument,document2.pdf,OCR processed,document2.pdf,394,"Full OCR text...",...
```

---

## Next Steps After Upload

1. **Open Processing URL** (shown at the end)
   - Go to: `http://localhost:8001/amiset/5/process`
   - (Replace `5` with your AMI Set ID)

2. **Review Configuration**
   - Check CSV is uploaded
   - Check ZIP is uploaded
   - Verify file mappings

3. **Process the Set**
   - Click "Process" tab
   - Choose "Process via Queue"
   - Click "Process" button

4. **Monitor Progress**
   - Wait for processing to complete
   - Documents will appear in Archipelago

5. **View Your Documents**
   - Go to: `http://localhost:8001/admin/content`
   - Filter by recently created
   - Click on any document to view

---

## Files in This Package

- **ami_upload_bhushanji.py** - Main script (this is what you run)
- **AMI_UPLOAD_GUIDE.md** - This guide
- **AMI_SETS_USAGE_EXAMPLE.md** - More detailed examples
- **ARCHIPELAGO_PUSH_FIX.md** - Technical details about the fix

---

## Requirements

```bash
# Install Python dependencies
pip install requests

# Make sure you have:
# - Backend running
# - Archipelago running
# - Files in ./Bhushanji/
# - Valid credentials
```

---

## Support & Troubleshooting

### Check Backend Logs
```bash
docker-compose logs backend | tail -50
```

### Check Archipelago Logs
```bash
docker-compose logs -f
# or
# http://localhost:8001/admin/reports/dblog (in Archipelago UI)
```

### Test Backend Connectivity
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

### Test Archipelago Connectivity
```bash
curl http://localhost:8001/
```

---

## Success Criteria

✅ **You've successfully uploaded when you see:**
- "✅ Authenticated" message
- "✅ OCR job started" with a job ID
- Progress bar reaching 100%
- "✅ AMI Set created successfully!" message
- A processing URL displayed

Then:
- Open the URL in browser
- Click "Process" tab
- Monitor progress in Archipelago
- Documents appear in `/admin/content`

---

Good luck! 🚀 If you have questions, check the logs or reach out for support.
