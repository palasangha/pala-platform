# Folder Browser Feature - Documentation

## Overview

Added a folder browser UI component to the bulk processing page that allows users to browse and select folders from the server machine.

---

## Features

### 1. **Browse Server Folders**
- Click "Browse" button next to the folder path input
- Opens a modal dialog showing server folders
- Navigate through folder hierarchy
- View files in each folder

### 2. **Folder Navigation**
- Click folder name to navigate into it
- Click "Go to parent folder" to go back up
- Breadcrumb shows current path
- Shows file count for each folder

### 3. **File Preview**
- Lists image files in current folder
- Shows file size for each file
- Supports: JPG, JPEG, PNG, BMP, GIF, TIFF, WebP, PDF

### 4. **Quick Selection**
- "Select" button next to each folder
- Automatically fills path and closes browser
- No need to navigate to leaf folder

---

## Files Modified

### Backend
**File:** `backend/app/routes/bulk.py`

**New Endpoint:** `POST /api/bulk/browse-folders`

**Request:**
```json
{
  "path": "/path/to/browse" or "" for root
}
```

**Response:**
```json
{
  "success": true,
  "current_path": "/path/to/browse",
  "folders": [
    {
      "name": "folder_name",
      "path": "/full/path/to/folder",
      "file_count": 5,
      "is_dir": true
    }
  ],
  "files": [
    {
      "name": "image.jpg",
      "path": "/full/path/to/image.jpg",
      "size": 512000,
      "is_dir": false
    }
  ],
  "parent_path": "/parent/path" or null,
  "folder_count": 2,
  "file_count": 1
}
```

### Frontend
**File:** `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`

**Changes:**
1. Added `FolderBrowserState` interface
2. Added `browserState` state management
3. Added handler functions:
   - `handleOpenBrowser()` - Opens the modal
   - `handleNavigateFolder()` - Navigates to a folder
   - `handleSelectFolder()` - Selects a folder
   - `handleCloseBrowser()` - Closes the modal
4. Added folder browser modal UI
5. Added "Browse" button next to folder path input

---

## How to Use

### Step 1: Open Browser
1. Go to "Bulk Processing" page
2. Click "Browse" button next to "Folder Path" field
3. Modal opens showing root folders

### Step 2: Navigate Folders
1. Click on folder name to navigate into it
2. Or click "Go to parent folder" to go back
3. Breadcrumb shows current path

### Step 3: Select Folder
1. Click "Select" button next to desired folder
2. Folder path automatically fills in
3. Modal closes

### Step 4: Configure & Process
1. Adjust other settings (provider, languages, etc.)
2. Click "Start Processing"

---

## Allowed Root Paths

The browser can browse:
- `/mnt/sda1/mango1_home`
- `/home`
- `./uploads` (relative to app)

Users cannot browse outside these paths for security.

---

## Security Considerations

✅ **Path Validation**
- All paths validated before access
- Permission checks with `os.access()`
- Hidden files (starting with `.`) excluded

✅ **Authentication**
- Requires valid JWT token
- Protected with `@token_required` decorator
- Only logged-in users can browse

✅ **Restricted Roots**
- Only specific root paths allowed
- Cannot browse arbitrary system directories
- Prevents information disclosure

✅ **File Filtering**
- Only shows image files and folders
- Excludes hidden files
- No sensitive file types listed

---

## Error Handling

**"Path not found"**
- User tried to access non-existent folder
- Check breadcrumb path

**"Permission denied"**
- Backend process doesn't have read permission
- Check folder permissions on server

**"Failed to load folders"**
- Network issue or backend error
- Check backend logs

---

## Backend Implementation Details

### Browse Folders Endpoint

```python
@bulk_bp.route('/browse-folders', methods=['POST'])
@token_required
def browse_folders(current_user_id):
    """Browse folders on the server"""
```

**Features:**
- Returns root folders if path is empty
- Recursively lists subfolders
- Counts files in each folder
- Shows file previews
- Calculates file sizes
- Handles permission errors gracefully

**Allowed Roots:**
```python
allowed_roots = [
    '/mnt/sda1/mango1_home',
    '/home',
    './uploads',
]
```

**File Types Shown:**
```python
('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.pdf')
```

---

## Frontend Implementation Details

### State Management

```typescript
interface FolderBrowserState {
  isOpen: boolean;              // Modal visibility
  currentPath: string;          // Current directory
  folders: Array<...>;          // Subfolder list
  files: Array<...>;            // File list
  parentPath: string | null;    // Parent directory
  isLoading: boolean;           // Loading state
  error: string | null;         // Error message
}
```

### Modal Features

**Header:**
- Title "Browse Server Folders"
- Close button (X)

**Content:**
- Loading spinner
- Error message display
- Breadcrumb path
- Parent folder button
- Folder list with "Select" buttons
- File list with sizes

**Footer:**
- Close button

---

## Testing

### Test Case 1: Open Browser
1. Open bulk processing page
2. Click "Browse" button
3. ✅ Modal should open with root folders

### Test Case 2: Navigate Folders
1. Click folder name
2. ✅ Should navigate into folder
3. ✅ Breadcrumb should update
4. ✅ "Go to parent folder" button should appear

### Test Case 3: Select Folder
1. Click "Select" button
2. ✅ Modal should close
3. ✅ Folder path should fill in
4. ✅ Path should be correct

### Test Case 4: File Preview
1. Navigate to folder with files
2. ✅ Files should be listed
3. ✅ File sizes should show
4. ✅ Only image files should appear

### Test Case 5: Error Handling
1. Enter invalid path in input
2. Browse to restricted path (if possible)
3. ✅ Error message should display
4. ✅ Modal should stay open for retry

---

## Customization

### Add More Root Paths

Edit `backend/app/routes/bulk.py`:

```python
allowed_roots = [
    '/mnt/sda1/mango1_home',
    '/home',
    './uploads',
    '/your/new/path',  # Add here
]
```

### Change Supported File Types

Edit `backend/app/routes/bulk.py`:

```python
if item.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
    # Add more extensions here
```

### Customize Modal Appearance

Edit `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`:
- Modal colors: Change `bg-blue-600` classes
- Modal size: Adjust `max-w-2xl` in modal div
- Button styles: Update Tailwind classes

---

## Limitations

⚠️ **Current Limitations:**

1. **No Sorting Options**
   - Folders/files sorted alphabetically
   - Cannot change sort order

2. **No Favorites/Bookmarks**
   - Can't save frequently used paths
   - Must navigate each time

3. **No Search**
   - Cannot search for folders
   - Must navigate folder hierarchy

4. **No Multi-Select**
   - Can only select one folder at a time
   - Cannot process multiple folders at once

5. **Performance with Large Folders**
   - Very large folders may be slow
   - File listing not paginated

**Future Enhancements:**
- Add folder search
- Add bookmarks for common paths
- Add pagination for large folders
- Add multi-folder selection

---

## Troubleshooting

### Browser Modal Doesn't Open
- Check backend is running
- Check JavaScript console for errors
- Verify authentication token is valid

### Folders Not Showing
- Check allowed_roots in backend
- Verify folder permissions
- Check backend logs for errors

### "Permission Denied" Error
- Check folder permissions: `ls -la /path`
- Ensure Docker backend process can read folder
- May need to adjust folder permissions

### Wrong Paths Showing
- Verify allowed_roots configuration
- Check path is in allowed list
- Restart backend if changed

---

## API Reference

### Browse Folders Endpoint

**URL:** `POST /api/bulk/browse-folders`

**Authentication:** Required (JWT token)

**Request Body:**
```json
{
  "path": "/path/to/browse" or ""
}
```

**Success Response (200):**
```json
{
  "success": true,
  "current_path": "/path/to/browse",
  "folders": [...],
  "files": [...],
  "parent_path": "/parent/path",
  "folder_count": 2,
  "file_count": 1
}
```

**Error Response (400/403/500):**
```json
{
  "error": "Error message"
}
```

**Status Codes:**
- 200: Success
- 400: Path not found
- 403: Permission denied
- 401: Not authenticated
- 500: Server error

---

## Performance Notes

✅ **Optimizations:**
- File listing limited to 10 root items initially
- Large folder listings not paginated (future improvement)
- Requests use POST for consistency with auth

⚠️ **Considerations:**
- Very large folders (10,000+ items) may be slow
- Network latency affects modal responsiveness
- File size calculation adds minimal overhead

---

## Browser Compatibility

✅ Tested on:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Related Files

- `backend/app/routes/bulk.py` - Backend implementation
- `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx` - Frontend implementation
- `backend/app/utils/decorators.py` - Authentication decorator
- `frontend/src/stores/authStore.ts` - Token management

---

## Summary

The folder browser adds a user-friendly way to select folders without typing paths. Users can:
✅ Browse server folders
✅ Navigate folder hierarchy
✅ View files in folders
✅ Quickly select folders
✅ Automatic path filling

This improves UX and reduces errors from manual path entry.
