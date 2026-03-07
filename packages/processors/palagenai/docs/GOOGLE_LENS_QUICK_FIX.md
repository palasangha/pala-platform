# Google Lens Provider - Quick Fix Guide

## 🔧 Issue Fixed

**Problem**: `Unknown field for AnnotateImageResponse: text_detection` error when using Google Lens

**Solution**: Updated API calls to use correct Google Cloud Vision methods

---

## ✅ What Was Fixed

1. **API Method** - Changed from `annotate_image()` to `batch_annotate_images()`
2. **Response Field** - Changed from `text_detection` to `text_annotations`
3. **Response Handling** - Properly extract response from batch

---

## 🚀 How to Apply the Fix

### Option 1: Restart Docker (Recommended)
```bash
cd /mnt/sda1/mango1_home/gvpocr
docker-compose down
docker-compose up --build -d
```

### Option 2: Restart Backend Only
```bash
docker-compose restart backend
```

### Option 3: Restart Local Server
If running locally:
```bash
# Kill current process and restart
python run.py
```

---

## 🧪 Verify the Fix Works

### Test via REST API
```bash
curl -X POST http://localhost:5000/ocr/process/IMAGE_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google_lens",
    "languages": ["en"]
  }'
```

### Expected Success Response
```json
{
  "message": "OCR processing completed",
  "image_id": "IMAGE_ID",
  "text": "Full extracted text...",
  "confidence": 0.95,
  "provider": "google_lens",
  "metadata": {
    "sender": {
      "name": "John Smith",
      "email": "john@example.com"
    },
    "document_type": "letter",
    "date": "November 14, 2025"
  }
}
```

### Test via UI
1. Open the OCR application in browser
2. Select an image to process
3. Choose "Google Lens (Advanced)" as provider
4. Click "Process"
5. Should complete without "Unknown field" error

---

## ✨ What's Different Now

### Before (Broken)
```
Provider: google_lens
Status: ❌ Error
Message: Unknown field for AnnotateImageResponse: text_detection
```

### After (Fixed)
```
Provider: google_lens
Status: ✅ Success
Text: [Full document text]
Metadata: [Sender, recipient, date, etc.]
```

---

## 📋 Files Changed

**Single file modified**:
- `backend/app/services/ocr_providers/google_lens_provider.py`

**Changes**:
- Lines 39-91: Fixed API call method
- Lines 290-297: Fixed language detection field

---

## 🔍 If Issues Persist

### Check 1: Verify Backend Restarted
```bash
docker-compose logs backend | grep "Lens\|Google"
```

### Check 2: Verify Credentials
```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
# Should show path to your credentials file
```

### Check 3: Check Vision API Status
```bash
python -c "from google.cloud import vision; print('✓ Vision API OK')"
```

### Check 4: Review Logs
```bash
docker-compose logs backend --tail=50
# Look for any error messages
```

---

## 🎯 Expected Behavior After Fix

✅ Google Lens provider appears in available providers list  
✅ No "Unknown field" errors  
✅ Text extraction works correctly  
✅ Metadata is properly extracted  
✅ Sender, recipient, date information detected  
✅ Document type classification working  

---

## 📞 Support

**Document**: See `GOOGLE_LENS_API_FIX.md` for technical details

**Troubleshooting**: See `GOOGLE_LENS_SETUP.md` → Troubleshooting section

---

## ✅ Confirmation Checklist

After restarting, verify:
- [ ] Backend service is running
- [ ] No "Unknown field" errors in logs
- [ ] Google Lens provider available in UI
- [ ] Can process image without errors
- [ ] Metadata is extracted correctly

**Status**: ✅ Ready to Use

---

**Last Updated**: November 14, 2025
