# Verification API Documentation

## Overview

The Verification API provides endpoints for managing the human review workflow for OCR metadata. It enables administrators (Sevak) to review, edit, verify, or reject OCR extracted text with full audit trail tracking and optimistic locking for concurrent edits.

## Base URL

All verification endpoints are prefixed with `/api/verification`

## Authentication

All endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### Get Verification Queue

Get a paginated list of images filtered by verification status.

**Endpoint:** `GET /api/verification/queue`

**Query Parameters:**
- `status` (optional): Filter by verification status
  - Values: `pending_verification`, `verified`, `rejected`
  - Default: `pending_verification`
- `skip` (optional): Number of items to skip for pagination
  - Default: 0
- `limit` (optional): Maximum items to return
  - Default: 50
  - Max: 100

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "id": "image_id",
      "project_id": "project_id",
      "filename": "stored_filename.jpg",
      "original_filename": "original.jpg",
      "file_type": "image",
      "ocr_text": "Extracted text...",
      "ocr_status": "completed",
      "verification_status": "pending_verification",
      "verified_by": null,
      "verified_at": null,
      "version": 1,
      "created_at": "2024-01-20T10:30:00Z",
      "updated_at": "2024-01-20T10:30:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

### Get Queue Counts

Get counts for each verification status.

**Endpoint:** `GET /api/verification/queue/counts`

**Response:**
```json
{
  "success": true,
  "counts": {
    "pending_verification": 150,
    "verified": 500,
    "rejected": 25
  }
}
```

### Get Image for Verification

Get detailed image information including audit trail.

**Endpoint:** `GET /api/verification/image/{image_id}`

**Response:**
```json
{
  "success": true,
  "image": {
    "id": "image_id",
    "ocr_text": "Extracted text...",
    "verification_status": "pending_verification",
    "version": 1,
    ...
  },
  "audit_trail": [
    {
      "id": "audit_id",
      "image_id": "image_id",
      "user_id": "user_id",
      "action": "edit",
      "field_name": "ocr_text",
      "old_value": "old text",
      "new_value": "new text",
      "notes": "Fixed typo",
      "created_at": "2024-01-20T10:30:00Z"
    }
  ]
}
```

### Edit Image Metadata

Edit OCR text with optimistic locking.

**Endpoint:** `PUT /api/verification/image/{image_id}/edit`

**Request Body:**
```json
{
  "ocr_text": "Corrected text...",
  "version": 1,
  "notes": "Fixed spelling errors"
}
```

**Response:**
```json
{
  "success": true,
  "image": {
    "id": "image_id",
    "ocr_text": "Corrected text...",
    "version": 2,
    ...
  }
}
```

**Error Response (Version Conflict):**
```json
{
  "success": false,
  "error": "Version conflict - image was updated by another user"
}
```
Status Code: 409

### Verify Image

Mark an image as verified.

**Endpoint:** `POST /api/verification/image/{image_id}/verify`

**Request Body:**
```json
{
  "version": 2,
  "notes": "Looks good"
}
```

**Response:**
```json
{
  "success": true,
  "image": {
    "id": "image_id",
    "verification_status": "verified",
    "verified_by": "user_id",
    "verified_at": "2024-01-20T10:35:00Z",
    "version": 3,
    ...
  }
}
```

### Reject Image

Mark an image as rejected.

**Endpoint:** `POST /api/verification/image/{image_id}/reject`

**Request Body:**
```json
{
  "version": 2,
  "notes": "Poor quality OCR, needs reprocessing"
}
```

**Response:**
```json
{
  "success": true,
  "image": {
    "id": "image_id",
    "verification_status": "rejected",
    "verified_by": "user_id",
    "verified_at": "2024-01-20T10:35:00Z",
    "version": 3,
    ...
  }
}
```

**Note:** Rejection notes are required.

### Batch Verify

Verify multiple images at once.

**Endpoint:** `POST /api/verification/batch/verify`

**Request Body:**
```json
{
  "image_ids": ["id1", "id2", "id3"],
  "notes": "Batch verification of reviewed items"
}
```

**Response:**
```json
{
  "success": true,
  "verified_count": 3,
  "total_count": 3,
  "errors": []
}
```

**Note:** Version checking is skipped for batch operations.

### Batch Reject

Reject multiple images at once.

**Endpoint:** `POST /api/verification/batch/reject`

**Request Body:**
```json
{
  "image_ids": ["id1", "id2"],
  "notes": "Low quality OCR results"
}
```

**Response:**
```json
{
  "success": true,
  "rejected_count": 2,
  "total_count": 2,
  "errors": []
}
```

**Note:** Rejection notes are required for batch operations.

### Get Audit Trail

Get complete audit trail for an image.

**Endpoint:** `GET /api/verification/audit/{image_id}`

**Response:**
```json
{
  "success": true,
  "audit_trail": [
    {
      "id": "audit_id",
      "action": "edit",
      "field_name": "ocr_text",
      "old_value": "old",
      "new_value": "new",
      "notes": "Fixed typo",
      "created_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": "audit_id_2",
      "action": "verify",
      "notes": "Looks good",
      "created_at": "2024-01-20T10:35:00Z"
    }
  ],
  "count": 2
}
```

## Audit Actions

The following actions are tracked in the audit trail:

- `edit`: Metadata field was edited
- `verify`: Image was verified
- `reject`: Image was rejected
- `undo`: Change was undone (future feature)
- `redo`: Change was redone (future feature)

## Optimistic Locking

The verification system uses optimistic locking to prevent concurrent edit conflicts:

1. Each image has a `version` field that starts at 1
2. When updating an image, include the current `version` in the request
3. The system increments the version on each update
4. If the version doesn't match, a 409 Conflict error is returned
5. The client should reload the image and retry the operation

## Verification Status Flow

```
pending_verification → verified
                    ↓
                  rejected
```

Once an image is verified or rejected, it can be edited again which will create new audit entries, but the verification status remains unless explicitly changed again.

## Error Responses

All endpoints may return the following error responses:

**400 Bad Request:**
```json
{
  "success": false,
  "error": "Error message"
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Authentication required"
}
```

**404 Not Found:**
```json
{
  "success": false,
  "error": "Image not found"
}
```

**409 Conflict:**
```json
{
  "success": false,
  "error": "Version conflict - image was updated by another user"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "error": "Error message"
}
```

## Usage Examples

### Example 1: Review and verify an image

```javascript
// 1. Get image details
const { image, audit_trail } = await fetch('/api/verification/image/IMAGE_ID')
  .then(r => r.json());

// 2. Edit OCR text if needed
if (needsCorrection) {
  await fetch('/api/verification/image/IMAGE_ID/edit', {
    method: 'PUT',
    body: JSON.stringify({
      ocr_text: 'Corrected text',
      version: image.version,
      notes: 'Fixed typos'
    })
  });
}

// 3. Verify the image
await fetch('/api/verification/image/IMAGE_ID/verify', {
  method: 'POST',
  body: JSON.stringify({
    version: image.version + 1, // Increment if edited
    notes: 'Looks good'
  })
});
```

### Example 2: Batch verify multiple images

```javascript
const selectedIds = ['id1', 'id2', 'id3'];

const result = await fetch('/api/verification/batch/verify', {
  method: 'POST',
  body: JSON.stringify({
    image_ids: selectedIds,
    notes: 'Batch verification'
  })
}).then(r => r.json());

console.log(`Verified ${result.verified_count} of ${result.total_count} images`);
```

### Example 3: Handle version conflicts

```javascript
try {
  await fetch('/api/verification/image/IMAGE_ID/edit', {
    method: 'PUT',
    body: JSON.stringify({
      ocr_text: 'Updated text',
      version: currentVersion
    })
  });
} catch (error) {
  if (error.status === 409) {
    // Reload image and retry
    const { image } = await fetch('/api/verification/image/IMAGE_ID')
      .then(r => r.json());
    // Retry with new version
  }
}
```
