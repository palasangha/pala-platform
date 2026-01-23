# OCR RBAC System - API Quick Reference

**Base URL**: `http://localhost:5000/api`

**Authentication**: JWT token in `Authorization: Bearer <token>` header

---

## Authentication Endpoints

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@ocr.com",
  "password": "password123"
}

Response 200:
{
  "status": "success",
  "user_id": "507f1f77bcf86cd799439011",
  "email": "admin@ocr.com",
  "name": "Administrator",
  "roles": ["admin"],
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "newuser@ocr.com",
  "password": "password123",
  "name": "New User"
}

Response 201: User created
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response 200:
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>

Response 200:
{
  "status": "success",
  "user": {
    "user_id": "507f1f77bcf86cd799439011",
    "email": "admin@ocr.com",
    "roles": ["admin"]
  }
}
```

### Logout
```http
POST /auth/logout
Authorization: Bearer <access_token>

Response 200:
{
  "status": "success",
  "message": "Logged out successfully"
}
```

---

## Document Classification Endpoints

### Classify Document (Admin Only)
```http
POST /documents/<doc_id>/classify
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "classification": "PUBLIC",
  "reason": "Community review document"
}

Response 200:
{
  "status": "success",
  "document_id": "507f1f77bcf86cd799439012",
  "classification": "PUBLIC",
  "new_status": "CLASSIFIED_PUBLIC",
  "message": "Document classified as PUBLIC"
}

Errors:
- 403: Only Admin can classify
- 404: Document not found
- 409: Cannot change classification after OCR
```

---

## OCR Processing Endpoints

### Start Batch OCR (Admin Only)
```http
POST /ocr/batch/process
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "document_ids": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"],
  "provider": "google_vision",
  "settings": {
    "languages": ["en", "es"],
    "handwriting": false
  }
}

Response 201:
{
  "status": "success",
  "job_id": "job_abc123def456",
  "document_count": 2,
  "status": "PROCESSING",
  "progress": {
    "current": 0,
    "total": 2,
    "percentage": 0
  },
  "message": "OCR batch job started"
}

Errors:
- 403: Only Admin can run OCR
- 400: Invalid provider
- 409: Document not classified
```

### Get OCR Job Status
```http
GET /ocr/jobs/<job_id>/status
Authorization: Bearer <token>

Response 200:
{
  "status": "success",
  "job_id": "job_abc123def456",
  "batch_status": "PROCESSING",
  "progress": {
    "current": 1,
    "total": 2,
    "percentage": 50
  },
  "created_at": "2026-01-22T10:00:00Z",
  "updated_at": "2026-01-22T10:05:00Z"
}
```

### Configure OCR Provider (Admin Only)
```http
POST /ocr/configure-provider
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "provider_name": "google_vision",
  "api_key": "your-api-key",
  "settings": {
    "max_requests_per_minute": 60
  }
}

Response 200:
{
  "status": "success",
  "provider": "google_vision",
  "message": "Provider configured successfully"
}
```

---

## Review Queue Endpoints

### Get Review Queue (Reviewer/Teacher)
```http
GET /review-queue
Authorization: Bearer <reviewer_token>
Query Parameters:
  - page=1 (default 1)
  - per_page=10 (default 10)

Response 200 (Reviewer sees only PUBLIC):
{
  "status": "success",
  "queue": [
    {
      "_id": "507f1f77bcf86cd799439014",
      "filename": "document_001.pdf",
      "classification": "PUBLIC",
      "status": "IN_REVIEW",
      "queued_at": "2026-01-22T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_count": 50,
    "total_pages": 5
  }
}

Notes: Teacher sees both PUBLIC and PRIVATE
```

### Claim Document (Reviewer/Teacher)
```http
POST /review/<doc_id>/claim
Authorization: Bearer <reviewer_token>

Response 200:
{
  "status": "success",
  "message": "Document claimed successfully",
  "document_id": "507f1f77bcf86cd799439014",
  "claimed_at": "2026-01-22T10:30:00Z"
}

Errors:
- 403: Cannot access PRIVATE (reviewer only)
- 409: Document already claimed
```

### Approve Document (Reviewer/Teacher)
```http
POST /review/<doc_id>/approve
Authorization: Bearer <reviewer_token>
Content-Type: application/json

{
  "edit_fields": {
    "author_name": "John Doe (corrected)",
    "date": "2026-01-22"
  },
  "notes": "Fixed author name, verified date"
}

Response 200:
{
  "status": "success",
  "message": "Document approved successfully",
  "document_id": "507f1f77bcf86cd799439014",
  "new_status": "REVIEWED_APPROVED",
  "edits_count": 2
}

Errors:
- 409: Document not in IN_REVIEW status
- 403: Not claimed by current user
```

### Reject Document (Reviewer/Teacher)
```http
POST /review/<doc_id>/reject
Authorization: Bearer <reviewer_token>
Content-Type: application/json

{
  "reason": "OCR quality too low"
}

Response 200:
{
  "status": "success",
  "message": "Document rejected",
  "document_id": "507f1f77bcf86cd799439014",
  "new_status": "IN_REVIEW",
  "reason": "OCR quality too low"
}
```

---

## Admin Dashboard Endpoints

### Get Dashboard Overview (Admin Only)
```http
GET /dashboard/overview
Authorization: Bearer <admin_token>
Query Parameters:
  - project_id (optional)
  - date_from (optional)
  - date_to (optional)

Response 200:
{
  "status": "success",
  "overview": {
    "total_documents": 1000,
    "in_process": 200,
    "approved": 500,
    "exported": 300,
    "progress_percentage": 30
  },
  "bottleneck_stage": "IN_REVIEW",
  "bottleneck_count": 150
}
```

### Get User Metrics (Admin Only)
```http
GET /dashboard/user-metrics
Authorization: Bearer <admin_token>
Query Parameters:
  - user_id (optional)
  - role (optional)
  - date_from (optional)
  - date_to (optional)

Response 200:
{
  "status": "success",
  "metrics": [
    {
      "user_id": "507f1f77bcf86cd799439011",
      "name": "Public Reviewer",
      "role": "reviewer",
      "documents_processed": 250,
      "approval_rate": 0.92,
      "manual_edit_count": 25,
      "avg_time_per_doc": 600  // seconds
    }
  ]
}
```

### Get Quality Metrics (Admin Only)
```http
GET /dashboard/quality-metrics
Authorization: Bearer <admin_token>

Response 200:
{
  "status": "success",
  "ocr_metrics": {
    "avg_confidence": 0.94,
    "failed_rate": 0.02,
    "retry_count": 45
  },
  "enrichment_metrics": {
    "avg_confidence": 0.91,
    "incomplete_count": 50
  },
  "by_provider": {
    "tesseract": { "confidence": 0.92 },
    "google_vision": { "confidence": 0.96 }
  }
}
```

### Get SLA Metrics (Admin Only)
```http
GET /dashboard/sla-metrics
Authorization: Bearer <admin_token>

Response 200:
{
  "status": "success",
  "sla_metrics": {
    "on_time_compliance": 0.98,
    "violations_count": 20,
    "avg_time_per_stage": {
      "classification": 120,
      "ocr_processing": 600,
      "review": 3600,
      "approval": 300
    }
  }
}
```

---

## Export Endpoints

### Export Documents (Admin Only)
```http
POST /export
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "document_ids": ["507f1f77bcf86cd799439014", ...],
  "destination": "mongodb"
}

Response 201:
{
  "status": "success",
  "export_job_id": "export_job_001",
  "document_count": 100,
  "destination": "mongodb",
  "status": "PROCESSING",
  "message": "Export job started"
}

Destinations: "mongodb" | "archipelago"
```

### Get Export Status (Admin Only)
```http
GET /export/<export_job_id>/status
Authorization: Bearer <admin_token>

Response 200:
{
  "status": "success",
  "export_job_id": "export_job_001",
  "status": "COMPLETED",
  "records_exported": 100,
  "errors": [],
  "completed_at": "2026-01-22T12:00:00Z"
}
```

---

## Audit Log Endpoints

### Get Audit Logs (Admin Only)
```http
GET /audit-logs
Authorization: Bearer <admin_token>
Query Parameters:
  - document_id (optional)
  - action_type (optional)
  - actor_id (optional)
  - date_from (optional)
  - date_to (optional)
  - page=1 (optional)
  - per_page=10 (optional)

Response 200:
{
  "status": "success",
  "audit_logs": [
    {
      "_id": "507f1f77bcf86cd799439015",
      "action_type": "ADMIN_CLASSIFY_DOC",
      "actor_id": "507f1f77bcf86cd799439011",
      "actor_role": "admin",
      "document_id": "507f1f77bcf86cd799439014",
      "previous_state": { "status": "CLASSIFICATION_PENDING" },
      "new_state": { "status": "CLASSIFIED_PUBLIC" },
      "reason": "Community review document",
      "created_at": "2026-01-22T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "total_count": 500,
    "total_pages": 50
  }
}
```

### Get Document Audit Trail (Admin Only)
```http
GET /audit-logs/document/<doc_id>
Authorization: Bearer <admin_token>

Response 200:
{
  "status": "success",
  "document_id": "507f1f77bcf86cd799439014",
  "audit_trail": [
    {
      "timestamp": "2026-01-22T09:00:00Z",
      "action": "UPLOADED",
      "actor": "system"
    },
    {
      "timestamp": "2026-01-22T10:00:00Z",
      "action": "ADMIN_CLASSIFY_DOC",
      "actor_id": "507f1f77bcf86cd799439011",
      "details": "Classified as PUBLIC"
    },
    ...
  ]
}
```

---

## Common Error Codes

| Code | Error | Meaning |
|------|-------|---------|
| 400 | Bad Request | Invalid input, missing fields |
| 401 | Unauthorized | Invalid/expired token, no token |
| 403 | Forbidden | Permission denied, role mismatch |
| 404 | Not Found | Resource not found |
| 409 | Conflict | State violation, already exists |
| 429 | Too Many Requests | Rate limit exceeded |
| 503 | Service Unavailable | Database/API down |
| 500 | Internal Server Error | Server error |

---

## HTTP Headers

### Request Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

### Response Headers
```
Content-Type: application/json
X-Request-ID: <unique-request-id>
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1234567890
```

---

## Rate Limiting

- **Per User**: 100 requests/minute
- **Per IP**: 1000 requests/minute
- **Burst**: 200 requests/second

Response headers include:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

---

## Pagination

All list endpoints support pagination:

```
GET /api/resource?page=1&per_page=20

Response:
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_count": 500,
    "total_pages": 25
  }
}
```

---

## Sorting

Some endpoints support sorting:

```
GET /api/documents?sort=-created_at,status

Formats:
  - Ascending: field_name
  - Descending: -field_name
```

---

## Filtering

Common query parameters:

```
GET /api/documents?status=IN_REVIEW&classification=PUBLIC&date_from=2026-01-01

Supported filters vary by endpoint
```

---

## Response Format

### Success Response
```json
{
  "status": "success",
  "data": {},
  "message": "Operation completed"
}
```

### Error Response
```json
{
  "status": "error",
  "code": 403,
  "error": "Forbidden",
  "message": "Permission denied",
  "details": "Only Admin can perform this action"
}
```

---

## Example cURL Commands

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ocr.com",
    "password": "password123"
  }'
```

### Classify Document
```bash
curl -X POST http://localhost:5000/api/documents/<doc_id>/classify \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "classification": "PUBLIC",
    "reason": "Community review"
  }'
```

### Get Review Queue
```bash
curl -X GET "http://localhost:5000/api/review-queue?page=1&per_page=10" \
  -H "Authorization: Bearer <token>"
```

### Claim Document
```bash
curl -X POST http://localhost:5000/api/review/<doc_id>/claim \
  -H "Authorization: Bearer <token>"
```

### Approve Document
```bash
curl -X POST http://localhost:5000/api/review/<doc_id>/approve \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "edit_fields": {
      "author": "John Doe"
    },
    "notes": "Corrected author name"
  }'
```

---

## SDK Examples

### Python Requests
```python
import requests

BASE_URL = "http://localhost:5000/api"

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "admin@ocr.com",
    "password": "password123"
})
data = response.json()
token = data['access_token']

# Get review queue
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/review-queue", headers=headers)
documents = response.json()['queue']
```

### JavaScript Fetch
```javascript
const BASE_URL = "http://localhost:5000/api";

// Login
const loginResponse = await fetch(`${BASE_URL}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "admin@ocr.com",
    password: "password123"
  })
});
const { access_token } = await loginResponse.json();

// Get review queue
const queueResponse = await fetch(`${BASE_URL}/review-queue`, {
  headers: { "Authorization": `Bearer ${access_token}` }
});
const { queue } = await queueResponse.json();
```

