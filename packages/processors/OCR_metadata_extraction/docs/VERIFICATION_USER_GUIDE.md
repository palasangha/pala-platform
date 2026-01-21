# Verification Workflow User Guide

## Overview

The Verification Workflow allows administrators (Sevak) to review and validate OCR-extracted metadata before it's published. This ensures data quality and accuracy through human review with inline editing capabilities and complete audit trails.

## Getting Started

### Accessing the Verification Dashboard

1. Log in to the application
2. Navigate to `/verification` in your browser
3. You'll see the Verification Dashboard with three tabs:
   - **Pending**: Items waiting for review
   - **Verified**: Items that have been approved
   - **Rejected**: Items that were rejected

## Verification Dashboard

### Queue Tabs

**Pending Tab**
- Shows all images awaiting verification
- Default view when you first open the dashboard
- Badge shows count of pending items

**Verified Tab**
- Shows all approved images
- Badge shows count of verified items

**Rejected Tab**
- Shows all rejected images
- Badge shows count of rejected items

### Queue Features

**Search**
- Search by filename or OCR text content
- Real-time filtering as you type

**Batch Selection**
- Select multiple items using checkboxes
- Batch verify or reject selected items
- Selection count displayed

**Refresh**
- Manual refresh button to reload the queue
- Useful when working in a team

## Reviewing Individual Items

### Opening an Item

1. Click "Review" on any item in the queue
2. This opens the Verification Detail page

### Verification Detail Page

The detail page shows:

**Left Panel: Document Preview**
- Visual preview of the original document
- File information (type, status, processing date)

**Right Panel: OCR Text Editor**
- Editable text area with OCR results
- Notes field for adding comments
- Save button (enabled when changes are made)

**Audit Trail**
- Complete history of all changes
- Shows who made each change and when
- Accessible via "Audit Trail" button

### Editing OCR Text

1. Click into the OCR text area
2. Make your corrections
3. Add optional notes explaining the changes
4. Click "Save Changes"

**Important Notes:**
- Save before verifying or rejecting
- Unsaved changes warning is displayed
- Version conflict detection prevents overwriting others' work

### Verifying an Item

Once you've reviewed and corrected the OCR text:

1. Ensure all changes are saved
2. Click the green "Verify" button
3. The item moves to the "Verified" queue
4. An audit entry is created

### Rejecting an Item

If the OCR quality is too poor or needs reprocessing:

1. Click the red "Reject" button
2. Enter a reason for rejection (required)
3. The item moves to the "Rejected" queue
4. An audit entry is created with your reason

## Batch Operations

### Batch Verification

For multiple items that don't need editing:

1. Select items using checkboxes
2. Click "Verify Selected"
3. All selected items are verified at once
4. Success count is displayed

### Batch Rejection

For multiple items that all need rejection:

1. Select items using checkboxes
2. Click "Reject Selected"
3. Enter a reason (applies to all)
4. All selected items are rejected
5. Success count is displayed

## Audit Trail

### Viewing Audit History

1. Open an item for review
2. Click "Audit Trail" button
3. See chronological list of all changes

### Audit Entry Information

Each entry shows:
- **Action**: edit, verify, or reject
- **Field**: Which field was changed (for edits)
- **User**: Who made the change
- **Timestamp**: When it occurred
- **Notes**: Any comments added

### Audit Actions

- **Edit**: Field value was changed
- **Verify**: Item was approved
- **Reject**: Item was rejected

## Version Control & Conflicts

### Optimistic Locking

The system uses version control to prevent conflicts:

1. Each image has a version number
2. Version increments with each change
3. Your changes include the current version
4. If someone else edited first, you get a conflict error

### Handling Conflicts

If you see "Version conflict" error:

1. Click "Refresh" to reload the latest version
2. Review the new changes
3. Re-apply your edits if still needed
4. Save again

## Best Practices

### Review Guidelines

1. **Check Original Document**: Always compare OCR text with the preview
2. **Fix Obvious Errors**: Correct clear mistakes in OCR extraction
3. **Add Context in Notes**: Explain non-obvious corrections
4. **Batch Similar Items**: Group similar quality items for efficiency
5. **Regular Breaks**: Take breaks during long review sessions

### When to Verify

✓ OCR text is accurate
✓ All corrections have been made
✓ Text matches the original document
✓ No obvious quality issues

### When to Reject

✗ OCR quality is extremely poor
✗ Document is unreadable/damaged
✗ Wrong language detected
✗ Needs different OCR provider
✗ Technical processing error

### Note-Taking Tips

Good notes examples:
- "Fixed date format from MM/DD/YYYY to DD/MM/YYYY"
- "Corrected misspelled Sanskrit terms"
- "Added missing punctuation"

Poor quality - reject notes:
- "Handwritten text not recognized"
- "Low image quality, needs better scan"
- "Wrong script/language detected"

## Keyboard Shortcuts

*(Future Feature)*

- `Ctrl/Cmd + S`: Save changes
- `Ctrl/Cmd + Enter`: Verify item
- `Esc`: Cancel/Go back
- `→`: Next item
- `←`: Previous item

## Status Flow

```
New Image
    ↓
OCR Processing
    ↓
pending_verification  ←→  (Can edit multiple times)
    ↓
verified or rejected
    ↓
Published or Reprocessed
```

## Troubleshooting

### "Failed to load verification queue"

**Solution:**
- Check your internet connection
- Click Refresh
- Log out and log back in
- Contact support if persists

### "Version conflict" on every save

**Solution:**
- Someone else is editing the same item
- Coordinate with team
- Use "Refresh" to get latest version
- Consider batch operations instead

### Changes not saving

**Solution:**
- Check for error messages
- Verify you're logged in
- Check network connection
- Try refreshing the page

### Can't verify item

**Possible causes:**
- Unsaved changes exist (save first)
- Version conflict (refresh and retry)
- Not authorized (check permissions)

## FAQ

**Q: Can I undo a verification?**
A: Not currently. Once verified, items would need admin intervention to change status. (Undo/redo is planned for future releases)

**Q: What happens to rejected items?**
A: They remain in the system for analysis. Admins can decide whether to reprocess or delete them.

**Q: Can multiple people review the same item?**
A: Yes, but version control prevents conflicts. The first person to save wins; others get a conflict error.

**Q: How long is the audit trail kept?**
A: Indefinitely. All changes are permanently logged for compliance and quality tracking.

**Q: Can I export verified items?**
A: Yes, use the export functionality in the main project view (separate from verification workflow).

## Support

For technical issues or questions:
- Check the API documentation: `docs/VERIFICATION_API.md`
- Contact your system administrator
- File an issue in the project repository

## Feedback

Help us improve the verification workflow:
- Report bugs or issues
- Suggest new features
- Share best practices with the team
