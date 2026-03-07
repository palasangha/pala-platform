# Folder Browser Feature - Quick Start

## ✨ What's New

Added a **folder browser button** to the Bulk Processing page that lets you visually browse and select folders from the server machine without typing paths manually.

---

## 🚀 How to Use

### Step 1: Open Bulk Processing
1. Navigate to http://localhost:3000
2. Login if needed
3. Click "Bulk Processing" in the menu

### Step 2: Open Folder Browser
1. Look for the **"Browse"** button next to "Folder Path" input
2. Click the Browse button
3. A modal opens showing server folders

### Step 3: Navigate Folders
- **Click folder name** → Opens that folder
- **Click "Go to parent folder"** → Goes up one level
- **Breadcrumb at top** → Shows current path

### Step 4: Select Folder
- Click **"Select"** button next to the folder you want
- Folder path automatically fills in
- Modal closes automatically

### Step 5: Configure & Process
1. Adjust other settings if needed:
   - OCR Provider
   - Languages
   - Process subfolders
   - Export formats
2. Click "Start Processing"

---

## 📁 Root Folders Available

You can browse:
- `/mnt/sda1/mango1_home` - Home directory with Bhushanji data
- `/home` - System home directories
- `./uploads` - Application uploads folder

---

## 🎯 Example Workflow

**Goal:** Process English typed documents

1. Click "Browse" button
2. Open → `mango1_home`
3. Open → `Bhushanji`
4. Open → `eng-typed`
5. Click "Select" button
6. Path automatically set to: `/mnt/sda1/mango1_home/Bhushanji/eng-typed`
7. Keep defaults (Tesseract, EN language, etc.)
8. Click "Start Processing"

Done! No typing required.

---

## 💡 Tips & Tricks

### Quick Selection
- You can click "Select" on any folder
- Don't need to navigate all the way down
- Useful for parent folders with subfolders

### View Files
- Each folder shows file count
- Files listed at bottom of folder view
- Shows file size for each image
- Helps verify right folder selected

### Supported File Types
The browser shows these image file types:
- JPG / JPEG
- PNG
- BMP
- GIF
- TIFF
- WebP
- PDF (auto-converted to images during processing)

### Navigation Tips
- "Go to parent folder" button appears only when navigating (not at root)
- Breadcrumb shows full path you can copy
- Modal stays open until you select or close

---

## ⚡ Features

✅ **Visual Folder Browsing**
- See folder structure graphically
- No need to type paths
- File previews in each folder

✅ **Quick Selection**
- One click to select folder
- Automatic path filling
- Closes modal after selection

✅ **Safe Navigation**
- Only shows allowed server paths
- Cannot access restricted directories
- Permission errors handled gracefully

✅ **File Previews**
- See how many files in each folder
- View file names and sizes
- Helps verify you're in right location

✅ **Mobile Friendly**
- Works on tablets
- Touch-friendly buttons
- Responsive design

---

## 🔒 Security

The folder browser is secure:
- Requires you to be logged in
- Only shows specified root paths
- Hidden files not shown (files starting with `.`)
- Permission checks prevent access errors
- Backend validates all paths before showing

---

## ❌ Common Issues & Solutions

### Modal Doesn't Open
**Problem:** Click Browse button but modal doesn't appear
**Solution:**
- Refresh page
- Check backend is running: `docker compose ps`
- Check JavaScript console (F12) for errors

### Folders Not Showing
**Problem:** Modal opens but no folders listed
**Solution:**
- You might be at root with no accessible folders
- Try typing path manually in input field
- Check folder permissions on server

### "Permission Denied" Error
**Problem:** Getting permission error when browsing
**Solution:**
- Folder exists but backend can't read it
- Check folder permissions: `ls -la /path`
- May need to adjust file permissions

### Wrong Folder Selected
**Problem:** Selected folder but wrong path filled in
**Solution:**
- Check breadcrumb to see selected path
- Try again - modal will reopen if you click Browse again
- Or manually edit path in input field

---

## 🔧 Customization

### Add More Root Paths
To browse additional folders, contact admin to:
1. Edit `backend/app/routes/bulk.py`
2. Add path to `allowed_roots` list
3. Restart backend

Example: To add `/data` folder
```python
allowed_roots = [
    '/mnt/sda1/mango1_home',
    '/home',
    './uploads',
    '/data',  # Add your path here
]
```

---

## 📊 Behind the Scenes

**How it works:**

1. Click "Browse" → Frontend calls backend API
2. Backend lists folders in allowed paths
3. Modal shows folder structure
4. Click folder → Frontend requests folder contents
5. Backend returns subfolders and files
6. Click "Select" → Frontend fills path and closes
7. Rest of bulk processing works as normal

**API Endpoint:**
- `POST /api/bulk/browse-folders`
- Requires JWT authentication
- Accepts folder path parameter
- Returns folder list, file list, and metadata

---

## 📱 Browser Support

Works on:
- ✅ Chrome / Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers

---

## 🎓 Learning More

For detailed technical information, see:
- `FOLDER_BROWSER_FEATURE.md` - Complete technical documentation
- `backend/app/routes/bulk.py` - Backend API code
- `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx` - Frontend code

---

## ✨ Summary

The folder browser makes it easy to:
1. ✅ Browse folders visually
2. ✅ No need to type paths
3. ✅ See file previews
4. ✅ Quick folder selection
5. ✅ Automatic path filling

**Try it now:** http://localhost:3000 → Bulk Processing → Click "Browse"

Enjoy! 🎉
