# Folder Selection Note Added

## Date: November 15, 2025

---

## Summary

Added an informative note to the folder selection UI explaining that folder paths are from the server machine/Docker container.

---

## Change Made

### File: `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`

**Location:** Folder Path input section (after the Browse button)

**Note Added:**
```tsx
<p className="text-xs text-gray-500 mt-2">
  💡 <strong>Note:</strong> Paths are from the server machine/Docker container. Use the "Browse" button to select folders, or enter paths like <code className="bg-gray-100 px-1 rounded">/data/Bhushanji/eng-typed</code>
</p>
```

---

## Visual Display

The note appears as:
- **Color:** Gray text (text-gray-500)
- **Size:** Extra small (text-xs)
- **Spacing:** Margin top for separation
- **Format:** 
  - 💡 Icon for clarity
  - Bold "Note:" label
  - Clear explanation of path source
  - Example path in code-style box

---

## What Users Will See

```
Folder Path
[text input field] [Browse button]

💡 Note: Paths are from the server machine/Docker container. Use the "Browse" button to 
select folders, or enter paths like /data/Bhushanji/eng-typed
```

---

## Benefits

✅ **Clarity** - Users understand that paths are server-side, not local
✅ **Guidance** - Example helps users understand correct path format
✅ **Discovery** - Mentions the Browse button for folder selection
✅ **Visual** - Icon and formatting make it stand out without being intrusive
✅ **Contextual** - Appears right where users need the information

---

## Related Features

This note complements:
1. **Browse Button** - Allows visual folder selection from server
2. **Server Paths** - Folders like `/data/Bhushanji/eng-typed`
3. **Docker Volumes** - Mounted from host machine to container

---

## Backend Paths Available

Users can use paths like:
- `/data/Bhushanji/eng-typed` - English typed documents
- `/data/Bhushanji/hin-typed` - Hindi typed documents
- `/data/Bhushanji/hin-written` - Hindi handwritten documents
- `/app/uploads` - Application uploads folder

---

## Frontend Status

✅ **Code Change:** Applied successfully
✅ **Error Checking:** No TypeScript errors
✅ **Container Restarted:** Frontend restarted to apply changes
✅ **Live:** Available at http://localhost:3000

---

## Testing

To see the change:
1. Open http://localhost:3000
2. Navigate to "Bulk Processing"
3. Look at the "Folder Path" input section
4. You'll see the informative note below the input field

---

## Verification

```bash
# View the change in the file
grep -A 5 "Paths are from the server machine" \
  frontend/src/components/BulkOCR/BulkOCRProcessor.tsx

# Verify frontend is running
docker compose ps | grep frontend
```

---

## Next Steps

1. ✅ Note added to UI
2. ✅ Frontend restarted
3. 👉 Open http://localhost:3000 to see the change
4. Use the Bulk Processing feature with the clarification

---

## Related Documentation

- `BULK_PROCESSING_FIXES.md` - Comprehensive bulk processing guide
- `VOLUME_MOUNT_RESTORED.md` - Volume mount configuration
- `COMPLETE_CHANGES_SUMMARY.md` - All changes summary

---

**Status:** ✅ Complete and Live

**Frontend:** http://localhost:3000
**Note Visible:** In Bulk Processing → Folder Path section
