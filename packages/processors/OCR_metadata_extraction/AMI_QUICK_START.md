# Quick Start - Upload Bhushanji to Archipelago (60 seconds)

## One Command to Rule Them All

```bash
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password your_password \
  --folder eng-typed
```

That's it! The script will handle everything.

---

## What Happens Next (Automatic)

1. ✅ Authenticates with GVPOCR
2. ✅ Starts OCR processing on `./Bhushanji/eng-typed/`
3. ✅ Waits for all files to be processed (shows progress bar)
4. ✅ Creates AMI Set in Archipelago
5. ✅ Shows you the processing URL

---

## After the Script Finishes

You'll see output like:

```
Processing URL: http://localhost:8001/amiset/5/process

Next steps:
1. Open the URL above in your browser
2. Review the AMI Set configuration
3. Click the 'Process' tab
4. Choose 'Process via Queue' (recommended)
5. Monitor progress in Archipelago
```

Just follow those steps!

---

## Available Folders in Bhushanji

```bash
# English Typed
python3 ami_upload_bhushanji.py --email user@example.com --password password --folder eng-typed

# Hindi Typed
python3 ami_upload_bhushanji.py --email user@example.com --password password --folder hin-typed

# Hindi Written
python3 ami_upload_bhushanji.py --email user@example.com --password password --folder hin-written
```

---

## Limit Files (Test with Small Batch)

```bash
# Process only 5 files to test
python3 ami_upload_bhushanji.py \
  --email user@example.com \
  --password password \
  --folder eng-typed \
  --limit 5
```

---

## Troubleshooting (Quick)

| Problem | Solution |
|---------|----------|
| "Authentication failed" | Check email/password |
| "Could not find folder" | Make sure files exist in `./Bhushanji/eng-typed/` |
| "Connection refused" | Start backend: `docker-compose up` |
| "Timeout" | Files are still processing (check manually with job ID) |

---

## What Gets Uploaded

- 📄 PDF files from your folder
- 📊 CSV with document metadata
- 📦 ZIP with all source files
- ✅ Everything ready for Archipelago

---

## Check Your Results

After processing in Archipelago:
- Go to: http://localhost:8001/admin/content
- Filter by recently created
- Your documents are there! 🎉

---

## Need More Help?

See detailed guide: `AMI_UPLOAD_GUIDE.md`

---

## One More Thing...

Make sure you have `requests` library:

```bash
pip install requests
```

That's all you need!
