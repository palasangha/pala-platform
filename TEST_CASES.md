# OCR RBAC System - Comprehensive Test Cases & Login Scenarios

**Document Version**: 1.0
**Date**: 2026-01-22
**Status**: Testing Phase Ready

---

## Table of Contents

1. [Login Test Cases](#login-test-cases)
2. [Admin Workflow Test Cases](#admin-workflow-test-cases)
3. [OCR Reviewer Workflow Test Cases](#ocr-reviewer-workflow-test-cases)
4. [Teacher Workflow Test Cases](#teacher-workflow-test-cases)
5. [Cross-Role Security Test Cases](#cross-role-security-test-cases)
6. [Error Handling Test Cases](#error-handling-test-cases)
7. [Edge Cases & Boundary Tests](#edge-cases--boundary-tests)
8. [Performance Test Cases](#performance-test-cases)
9. [Audit Trail Test Cases](#audit-trail-test-cases)
10. [Test Execution Report Template](#test-execution-report-template)

---

# 1. LOGIN TEST CASES

## Test Case 1.1: Admin Login with Email/Password

**Test ID**: `TC-LOGIN-001`

**Objective**: Verify Admin user can login with valid email and password

**Preconditions**:
- Admin user account exists in database
- Email: `admin@ocr-platform.com`
- Password: `SecureAdminPass123!`
- User is not logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login form is displayed |
| 2 | Enter email: `admin@ocr-platform.com` | Email field populated |
| 3 | Enter password: `SecureAdminPass123!` | Password field populated (masked) |
| 4 | Click "Login" button | Request sent to `/api/auth/login` |
| 5 | System validates credentials | Database lookup returns user with admin role |
| 6 | JWT tokens generated | `access_token` (1h expiry) and `refresh_token` (30d expiry) returned |
| 7 | Tokens stored in localStorage | User can access protected routes |
| 8 | Redirect to dashboard | Admin dashboard loads with "Welcome, Admin" message |

**Expected Output**:
```json
{
  "status": "success",
  "user_id": "507f1f77bcf86cd799439011",
  "email": "admin@ocr-platform.com",
  "name": "Administrator",
  "roles": ["admin"],
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Pass Criteria**: ✅ Login successful, tokens received, dashboard loads

**Fail Criteria**: ❌ Login fails, error message displayed

**Error Cases**:
- Invalid password → `401 Unauthorized: Invalid credentials`
- User doesn't exist → `401 Unauthorized: Invalid credentials`
- Account locked (5+ failed attempts) → `403 Forbidden: Account locked. Try again in 15 minutes`

---

## Test Case 1.2: Reviewer Login with Email/Password

**Test ID**: `TC-LOGIN-002`

**Objective**: Verify Reviewer user can login with valid credentials

**Preconditions**:
- Reviewer user account exists
- Email: `reviewer@ocr-platform.com`
- Password: `ReviewerPass456!`
- User not already logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login form displayed |
| 2 | Enter email: `reviewer@ocr-platform.com` | Email field populated |
| 3 | Enter password: `ReviewerPass456!` | Password field populated (masked) |
| 4 | Click "Login" button | POST `/api/auth/login` with credentials |
| 5 | Validate credentials in database | User found with reviewer role |
| 6 | Generate JWT tokens | Access token and refresh token created |
| 7 | Store tokens | Tokens saved to localStorage |
| 8 | Redirect to review queue | Review queue page loads |

**Expected Output**:
```json
{
  "status": "success",
  "user_id": "507f1f77bcf86cd799439012",
  "email": "reviewer@ocr-platform.com",
  "name": "Public Reviewer",
  "roles": ["reviewer"],
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600
}
```

**Pass Criteria**: ✅ Login successful, redirected to review queue

**Fail Criteria**: ❌ Login fails, error displayed

**Error Cases**:
- Invalid password → `401 Unauthorized`
- User not found → `401 Unauthorized`
- Role not found in system → `500 Internal Server Error: Invalid role configuration`

---

## Test Case 1.3: Teacher Login with Email/Password

**Test ID**: `TC-LOGIN-003`

**Objective**: Verify Teacher user can login successfully

**Preconditions**:
- Teacher user exists in database
- Email: `teacher@ocr-platform.com`
- Password: `TeacherPass789!`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Go to login page | Form displays |
| 2 | Enter email: `teacher@ocr-platform.com` | Email field has value |
| 3 | Enter password: `TeacherPass789!` | Password masked |
| 4 | Click login | POST to `/api/auth/login` |
| 5 | Credentials validated | Database returns teacher record |
| 6 | Tokens generated | JWT tokens created |
| 7 | Stored in browser | localStorage updated |
| 8 | Redirect to review queue | Can see both Public and Private docs in queue |

**Expected Output**:
```json
{
  "status": "success",
  "user_id": "507f1f77bcf86cd799439013",
  "name": "Senior Teacher",
  "roles": ["teacher"],
  "access_token": "...",
  "refresh_token": "..."
}
```

**Pass Criteria**: ✅ Logged in, can access full review queue

**Fail Criteria**: ❌ Login fails

---

## Test Case 1.4: Google OAuth Login

**Test ID**: `TC-LOGIN-004`

**Objective**: Verify user can login via Google OAuth

**Preconditions**:
- Google OAuth client configured
- User has Google account: `user@gmail.com`
- First-time user (new account)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login form displays |
| 2 | Click "Login with Google" button | Redirects to Google OAuth consent page |
| 3 | User enters Google credentials | Google validates user |
| 4 | User grants permission | Authorization code returned to callback |
| 5 | GET `/api/auth/google/callback?code=...` | Backend exchanges code for tokens |
| 6 | User created/updated in DB | Record created with google_id field |
| 7 | JWT tokens generated | Access and refresh tokens created |
| 8 | Redirect to dashboard | User logged in with default role |

**Expected Output**:
```json
{
  "status": "success",
  "user_id": "507f1f77bcf86cd799439014",
  "email": "user@gmail.com",
  "google_id": "118412345678901234567",
  "roles": ["reviewer"],
  "access_token": "..."
}
```

**Pass Criteria**: ✅ OAuth flow successful, user created/logged in

**Fail Criteria**: ❌ OAuth fails, error shown

**Error Cases**:
- User denies permission → Redirected back to login with error
- Invalid OAuth code → `400 Bad Request: Invalid authorization code`
- OAuth service down → `503 Service Unavailable`

---

## Test Case 1.5: Invalid Email Format

**Test ID**: `TC-LOGIN-005`

**Objective**: Verify system rejects invalid email format

**Preconditions**:
- Login page open
- User attempts invalid email

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enter email: `notanemail` | Email field populated |
| 2 | Enter any password | Password field populated |
| 3 | Click login | Frontend validation triggers |
| 4 | Error message displayed | "Please enter a valid email address" |

**Expected Output**:
```
Frontend validation error: Email format invalid
No API request sent
```

**Pass Criteria**: ✅ Invalid email rejected before API call

**Fail Criteria**: ❌ Invalid email sent to backend

---

## Test Case 1.6: Token Refresh

**Test ID**: `TC-LOGIN-006`

**Objective**: Verify user can refresh expired access token

**Preconditions**:
- User logged in
- Access token expired (1 hour passed)
- Refresh token still valid (< 30 days)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | User clicks any protected endpoint | System detects expired token |
| 2 | POST `/api/auth/refresh` with refresh_token | Backend validates refresh token |
| 3 | Refresh token is valid | New access token generated |
| 4 | New token returned to frontend | `access_token` field updated |
| 5 | Original request retried | Request succeeds with new token |
| 6 | Session continues | User remains logged in |

**Expected Output**:
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Pass Criteria**: ✅ Token refreshed, session continues

**Fail Criteria**: ❌ Refresh fails, user logged out

**Error Cases**:
- Invalid refresh token → `401 Unauthorized: Invalid refresh token`
- Refresh token expired → `401 Unauthorized: Refresh token expired. Please login again`

---

## Test Case 1.7: Logout

**Test ID**: `TC-LOGIN-007`

**Objective**: Verify user can logout and token is invalidated

**Preconditions**:
- User logged in
- Access token valid

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | User clicks "Logout" button | POST `/api/auth/logout` with token |
| 2 | Backend blacklists token | Token added to blacklist in Redis |
| 3 | Response received | `200 OK: Logged out successfully` |
| 4 | localStorage cleared | Tokens removed from browser |
| 5 | Redirect to login page | User back at login form |
| 6 | User attempts to access dashboard | Redirected to login (no valid token) |

**Expected Output**:
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

**Pass Criteria**: ✅ User logged out, cannot access protected routes

**Fail Criteria**: ❌ User can still access protected routes

---

## Test Case 1.8: Session Timeout (Inactive)

**Test ID**: `TC-LOGIN-008`

**Objective**: Verify user is logged out after inactivity timeout

**Preconditions**:
- User logged in
- No activity for 1 hour
- Session timeout configured to 1 hour

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | User inactive for 1 hour | Session timeout clock runs |
| 2 | User attempts any action | Access token expired |
| 3 | Refresh token request sent | Refresh token also expired (no recent activity) |
| 4 | Backend returns 401 | `401 Unauthorized: Session expired` |
| 5 | Frontend logs user out | localStorage cleared |
| 6 | Redirect to login | User sees login form with timeout message |

**Expected Output**:
```json
{
  "status": "error",
  "message": "Session expired. Please login again.",
  "code": 401
}
```

**Pass Criteria**: ✅ User logged out after inactivity

**Fail Criteria**: ❌ User can still access dashboard

---

# 2. ADMIN WORKFLOW TEST CASES

## Test Case 2.1: Admin Classify Document (Public)

**Test ID**: `TC-ADMIN-001`

**Objective**: Verify Admin can classify a document as Public

**Preconditions**:
- Admin logged in
- Project exists with ID: `proj_123`
- Document uploaded with ID: `doc_001`
- Document status: `CLASSIFICATION_PENDING`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to documents list | All documents shown |
| 2 | Click on document `doc_001` | Document detail page opens |
| 3 | Click "Classify" button | Classification modal appears |
| 4 | Select "Public" from dropdown | Classification type selected |
| 5 | (Optional) Add reason: "Community review" | Reason field populated |
| 6 | Click "Confirm Classification" | POST `/api/documents/doc_001/classify` with `{classification: "PUBLIC", reason: "Community review"}` |
| 7 | Backend validates authorization | User role is admin ✓ |
| 8 | Status updated to CLASSIFIED_PUBLIC | Document status changed in database |
| 9 | Audit log created | Entry: `ADMIN_CLASSIFY_DOC` |
| 10 | Success message shown | "Document classified as Public" |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "_id": "doc_001",
    "classification": "PUBLIC",
    "status": "CLASSIFIED_PUBLIC",
    "classified_by": "admin_user_id",
    "classified_at": "2026-01-22T10:30:00Z"
  },
  "message": "Document successfully classified as Public"
}
```

**Pass Criteria**: ✅ Document status changed, audit log created

**Fail Criteria**: ❌ Classification fails, error shown

**Error Cases**:
- Non-admin user attempts → `403 Forbidden: Only Admin can classify`
- Document already OCR'd → `409 Conflict: Cannot change classification after OCR`
- Invalid classification value → `400 Bad Request: Invalid classification type`

---

## Test Case 2.2: Admin Classify Document (Private)

**Test ID**: `TC-ADMIN-002`

**Objective**: Verify Admin can classify document as Private

**Preconditions**:
- Admin logged in
- Document ID: `doc_002`
- Status: `CLASSIFICATION_PENDING`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open document `doc_002` | Document detail loads |
| 2 | Click "Classify" | Modal opens |
| 3 | Select "Private" | Classification type selected |
| 4 | Add reason: "Sensitive content" | Reason recorded |
| 5 | Click "Confirm" | POST request sent |
| 6 | Backend validates | Admin role confirmed |
| 7 | Status → CLASSIFIED_PRIVATE | Database updated |
| 8 | Audit logged | `ADMIN_CLASSIFY_DOC` event created |
| 9 | Success message | "Classified as Private" displayed |
| 10 | Document appears in Private queue only | Teachers can see, Reviewers cannot |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "_id": "doc_002",
    "classification": "PRIVATE",
    "status": "CLASSIFIED_PRIVATE",
    "classified_by": "admin_id",
    "classified_at": "2026-01-22T10:35:00Z"
  }
}
```

**Pass Criteria**: ✅ Document Private, audit logged

**Fail Criteria**: ❌ Classification fails

---

## Test Case 2.3: Admin Run OCR on Document

**Test ID**: `TC-ADMIN-003`

**Objective**: Verify Admin can run OCR on classified document

**Preconditions**:
- Admin logged in
- Document ID: `doc_003`
- Status: `CLASSIFIED_PUBLIC`
- Classification: `PUBLIC`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to documents list | Classified documents shown |
| 2 | Select document `doc_003` | Detail page opens |
| 3 | Click "Run OCR" button | OCR configuration modal opens |
| 4 | Select provider: "Google Vision" | Provider selected |
| 5 | (Optional) Select languages: ["English", "Spanish"] | Languages selected |
| 6 | (Optional) Enable handwriting detection | Checkbox checked |
| 7 | Click "Start OCR" | POST `/api/ocr/batch/process` with document_ids and provider |
| 8 | Backend validates authorization | Admin role confirmed ✓ |
| 9 | Status → OCR_PROCESSING | Document status updated |
| 10 | Background job queued | NSQ job published or async task started |
| 11 | Job ID returned | User sees progress tracker |
| 12 | OCR processing begins | Google Vision API called |
| 13 | OCR completes (2-5 min) | `ocr_text` and `ocr_confidence` populated |
| 14 | Status → OCR_PROCESSED | Document ready for review |
| 15 | Audit logged | `ADMIN_RUN_OCR` event recorded |

**Expected Output**:
```json
{
  "status": "success",
  "job_id": "job_20260122_001",
  "document_id": "doc_003",
  "status": "OCR_PROCESSING",
  "message": "OCR processing started",
  "progress": {
    "current": 0,
    "total": 1,
    "percentage": 0
  }
}
```

**Pass Criteria**: ✅ OCR job created, status updated, audit logged

**Fail Criteria**: ❌ OCR fails, error shown

**Error Cases**:
- Non-admin user attempts → `403 Forbidden: Only Admin can run OCR`
- Document not classified → `409 Conflict: Document must be classified first`
- Invalid provider → `400 Bad Request: Invalid OCR provider`
- OCR provider API error → `503 Service Unavailable: OCR provider error. Retry?`
- API quota exceeded → `429 Too Many Requests: OCR provider quota exceeded`

---

## Test Case 2.4: Admin Batch Run OCR

**Test ID**: `TC-ADMIN-004`

**Objective**: Verify Admin can run OCR on batch of documents

**Preconditions**:
- Admin logged in
- 100 documents classified
- Status: `CLASSIFIED_PUBLIC` or `CLASSIFIED_PRIVATE`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Go to documents list | All classified docs visible |
| 2 | Select "Batch Actions" | Batch menu appears |
| 3 | Select 100 documents (checkbox) | All documents highlighted |
| 4 | Click "Run OCR Batch" | Batch OCR configuration modal |
| 5 | Select provider: "Tesseract" | Provider chosen |
| 6 | Set batch size: 10 | Documents batched (10 per group) |
| 7 | Click "Start Batch OCR" | POST `/api/ocr/batch/process` with 100 doc IDs |
| 8 | Backend validates | Admin role ✓, all docs classified ✓ |
| 9 | Status → OCR_PROCESSING for all | Batch update to database |
| 10 | Jobs queued | NSQ jobs published for each batch |
| 11 | Batch ID returned | `batch_job_20260122_001` |
| 12 | Progress tracker shows | "Processing 100 documents (0% complete)" |
| 13 | Jobs process in parallel | 10 docs at a time |
| 14 | Progress updates | Real-time: 20/100 (20%), 50/100 (50%), etc. |
| 15 | All completed | 100/100 (100% complete) |
| 16 | Status → OCR_PROCESSED for all | Batch status updated |

**Expected Output**:
```json
{
  "status": "success",
  "batch_job_id": "batch_job_20260122_001",
  "document_count": 100,
  "status": "PROCESSING",
  "message": "Batch OCR started for 100 documents",
  "progress": {
    "current": 0,
    "total": 100,
    "percentage": 0,
    "estimated_time": "15 minutes"
  }
}
```

**Pass Criteria**: ✅ Batch job created, progress tracked, all docs processed

**Fail Criteria**: ❌ Batch job fails, documents not processed

**Error Cases**:
- Some documents failed → `206 Partial Success: 95/100 documents processed. 5 failed.`
- Batch size too large (>1000) → `400 Bad Request: Batch size limited to 1000`
- Provider quota exceeded → `429 Too Many Requests: Retrying in 5 minutes`

---

## Test Case 2.5: Admin Assign Documents to Reviewer

**Test ID**: `TC-ADMIN-005`

**Objective**: Verify Admin can assign OCR'd documents to Reviewers for review

**Preconditions**:
- Admin logged in
- 50 documents in `OCR_PROCESSED` status
- Reviewer account exists: `reviewer@ocr.com`
- All docs are PUBLIC classification

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to OCR'd documents | Documents with status `OCR_PROCESSED` shown |
| 2 | Select 50 documents | Checkbox all selected |
| 3 | Click "Assign for Review" | Assignment modal opens |
| 4 | Select role: "Reviewer" | Role chosen |
| 5 | Assign to: `reviewer@ocr.com` | Reviewer selected |
| 6 | Set due date: 2 days | Due date configured |
| 7 | Add note: "Public documents batch" | Assignment notes added |
| 8 | Click "Assign Batch" | POST `/api/review-queue/bulk-assign` |
| 9 | Backend validates | Admin role ✓, all PUBLIC ✓ |
| 10 | Status → IN_REVIEW | 50 docs status updated |
| 11 | Review queue entries created | 50 records in review_queues collection |
| 12 | Assignment tracking created | assignment_ids recorded |
| 13 | Audit logged | `ADMIN_ASSIGN_BATCH` event |
| 14 | Reviewer notified | Email sent with assignment details |
| 15 | Reviewer sees in queue | Review queue shows 50 new documents |

**Expected Output**:
```json
{
  "status": "success",
  "assignment_id": "assign_20260122_001",
  "assigned_count": 50,
  "assignee": {
    "user_id": "reviewer_id",
    "email": "reviewer@ocr.com",
    "role": "reviewer"
  },
  "documents": {
    "status": "IN_REVIEW",
    "classification": "PUBLIC"
  },
  "due_at": "2026-01-24",
  "message": "50 documents assigned to reviewer"
}
```

**Pass Criteria**: ✅ Documents assigned, queue populated, audit logged

**Fail Criteria**: ❌ Assignment fails

**Error Cases**:
- Non-admin user attempts → `403 Forbidden`
- Reviewer doesn't exist → `404 Not Found: Reviewer not found`
- Cannot assign Private docs to Reviewer → `409 Conflict: Cannot assign Private docs to Reviewer`
- Invalid due date (past) → `400 Bad Request: Due date must be in future`

---

## Test Case 2.6: Admin Assign Documents to Teacher

**Test ID**: `TC-ADMIN-006`

**Objective**: Verify Admin can assign Public AND Private documents to Teacher

**Preconditions**:
- Admin logged in
- 30 PUBLIC + 20 PRIVATE documents in `OCR_PROCESSED`
- Teacher account exists: `teacher@ocr.com`

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Filter: Status = OCR_PROCESSED | 50 docs shown (30 PUBLIC, 20 PRIVATE) |
| 2 | Select all 50 documents | All highlighted |
| 3 | Click "Assign for Review" | Modal opens |
| 4 | Select role: "Teacher" | Teacher role selected |
| 5 | Select teacher: `teacher@ocr.com` | Teacher chosen |
| 6 | Set due date: 3 days | Deadline set |
| 7 | Add priority: "High" | Priority configured |
| 8 | Click "Assign" | POST `/api/review-queue/bulk-assign` |
| 9 | Backend validates | Admin ✓, Teacher ✓, can see Private ✓ |
| 10 | Status → IN_REVIEW for all | 50 docs updated |
| 11 | Review queue populated | 50 entries with mixed classification |
| 12 | Audit logged | Assignment tracked |
| 13 | Teacher can see all 50 | 30 PUBLIC + 20 PRIVATE in queue |
| 14 | Reviewer would see only PUBLIC | Reviewer's query filters to 30 only |

**Expected Output**:
```json
{
  "status": "success",
  "assignment_id": "assign_20260122_002",
  "assigned_count": 50,
  "classification_breakdown": {
    "PUBLIC": 30,
    "PRIVATE": 20
  },
  "assignee": {
    "email": "teacher@ocr.com",
    "role": "teacher"
  }
}
```

**Pass Criteria**: ✅ Teacher gets both PUBLIC and PRIVATE, Reviewer would only get PUBLIC

**Fail Criteria**: ❌ Assignment fails or security boundary broken

---

## Test Case 2.7: Admin Final Approval

**Test ID**: `TC-ADMIN-007`

**Objective**: Verify Admin can approve documents for export

**Preconditions**:
- Admin logged in
- 100 documents in `REVIEWED_APPROVED` status
- All have been reviewed and approved by Reviewers/Teachers

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Go to "Final Approval Queue" | All `REVIEWED_APPROVED` docs shown |
| 2 | Review approval status | All show as "Approved by Reviewer" |
| 3 | Select 100 documents | All checked |
| 4 | Click "Final Approve Batch" | Approval modal opens |
| 5 | Add final notes: "Batch 1 approved for export" | Notes recorded |
| 6 | Click "Approve for Export" | POST `/api/final-approval/batch` |
| 7 | Backend validates | Admin role ✓, all reviewed ✓ |
| 8 | Status → FINAL_APPROVED | 100 docs updated |
| 9 | Ready for export | Documents queued for export |
| 10 | Audit logged | `ADMIN_FINAL_APPROVE` event |
| 11 | Success shown | "100 documents approved and ready for export" |

**Expected Output**:
```json
{
  "status": "success",
  "approval_batch_id": "approval_20260122_001",
  "approved_count": 100,
  "status": "FINAL_APPROVED",
  "ready_for_export": true,
  "approved_by": "admin_id",
  "approved_at": "2026-01-22T12:00:00Z"
}
```

**Pass Criteria**: ✅ Documents marked for export, audit logged

**Fail Criteria**: ❌ Approval fails

**Error Cases**:
- Non-admin attempts → `403 Forbidden`
- Document not reviewed → `409 Conflict: Document must be reviewed before final approval`
- Invalid status → `409 Conflict: Document not in REVIEWED_APPROVED status`

---

## Test Case 2.8: Admin Export to MongoDB

**Test ID**: `TC-ADMIN-008`

**Objective**: Verify Admin can export approved documents to MongoDB

**Preconditions**:
- Admin logged in
- 100 documents in `FINAL_APPROVED` status
- MongoDB connection configured

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to "Ready for Export" | 100 approved docs shown |
| 2 | Select all | All highlighted |
| 3 | Click "Export" | Export modal opens |
| 4 | Select destination: "MongoDB" | Destination chosen |
| 5 | Confirm collection: "ocr_results" | Collection name shown |
| 6 | Click "Export Now" | POST `/api/export` |
| 7 | Backend validates | Admin ✓, all FINAL_APPROVED ✓ |
| 8 | Export job created | `export_job_20260122_001` |
| 9 | Status → EXPORTING | Docs marked as exporting |
| 10 | Data transformed | OCR data formatted for MongoDB |
| 11 | MongoDB write | 100 documents inserted |
| 12 | Status → EXPORTED | All docs marked as exported |
| 13 | Audit logged | `ADMIN_EXPORT_TO_DOWNSTREAM` |
| 14 | Success message | "Successfully exported 100 documents" |
| 15 | Export timestamp recorded | `exported_at` populated |

**Expected Output**:
```json
{
  "status": "success",
  "export_job_id": "export_job_20260122_001",
  "document_count": 100,
  "destination": "mongodb",
  "status": "EXPORTED",
  "message": "Export completed successfully",
  "exported_at": "2026-01-22T12:15:00Z",
  "mongodb_details": {
    "collection": "ocr_results",
    "inserted_count": 100
  }
}
```

**Pass Criteria**: ✅ Documents exported, MongoDB contains data, audit logged

**Fail Criteria**: ❌ Export fails, MongoDB empty

**Error Cases**:
- MongoDB connection error → `503 Service Unavailable: MongoDB connection failed`
- Non-admin attempts → `403 Forbidden`
- Document not FINAL_APPROVED → `409 Conflict`
- Invalid destination → `400 Bad Request: Invalid export destination`

---

## Test Case 2.9: Admin Export to Archipelago

**Test ID**: `TC-ADMIN-009`

**Objective**: Verify Admin can export documents to Archipelago Commons

**Preconditions**:
- Admin logged in
- 50 documents FINAL_APPROVED
- Archipelago Commons configured
- API credentials valid

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select 50 approved documents | Docs highlighted |
| 2 | Click "Export" | Export modal |
| 3 | Select destination: "Archipelago" | Archipelago chosen |
| 4 | Provide collection metadata | Title, description entered |
| 5 | Click "Export" | POST `/api/export` with destination |
| 6 | Backend validates | Admin ✓, all FINAL_APPROVED ✓ |
| 7 | Archipelago API called | Metadata uploaded |
| 8 | Collection created | Archipelago receives documents |
| 9 | Status → EXPORTED | Docs marked exported |
| 10 | Audit logged | `ADMIN_EXPORT_TO_DOWNSTREAM` |
| 11 | Success shown | "Exported to Archipelago collection ID: arch_123" |

**Expected Output**:
```json
{
  "status": "success",
  "export_job_id": "export_job_20260122_002",
  "document_count": 50,
  "destination": "archipelago",
  "status": "EXPORTED",
  "archipelago_collection_id": "arch_20260122_001",
  "collection_url": "https://archipelago.commons/collection/arch_001"
}
```

**Pass Criteria**: ✅ Documents in Archipelago, collection created

**Fail Criteria**: ❌ Export fails, Archipelago empty

---

## Test Case 2.10: Admin View Dashboard

**Test ID**: `TC-ADMIN-010`

**Objective**: Verify Admin can view comprehensive dashboard

**Preconditions**:
- Admin logged in
- System has 1000 documents in various states

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to Dashboard | GET `/api/dashboard/overview` |
| 2 | Page loads | Admin dashboard displays |
| 3 | Summary cards shown | Total docs: 1000, In process: 200, Approved: 500, Exported: 300 |
| 4 | Status breakdown shown | Pipeline progress bar: 30% complete |
| 5 | Per-user metrics shown | User productivity cards |
| 6 | Quality metrics shown | Avg OCR confidence: 94% |
| 7 | SLA metrics shown | On-time compliance: 98% |
| 8 | Apply filter: "Project 1" | GET `/api/dashboard/overview?project_id=proj_1` |
| 9 | Dashboard updates | Only Project 1 data shown |
| 10 | Drill down into stage | Click "In Review (200)" → List of 200 docs |
| 11 | Sort/filter | Sort by date, filter by reviewer |
| 12 | Export dashboard | Download as PDF |

**Expected Output**:
```json
{
  "status": "success",
  "overview": {
    "total_documents": 1000,
    "in_process": 200,
    "approved": 500,
    "exported": 300,
    "progress_percentage": 30
  },
  "user_metrics": [
    {
      "user_id": "reviewer_1",
      "name": "Public Reviewer",
      "documents_processed": 250,
      "approval_rate": 92
    }
  ],
  "quality_metrics": {
    "avg_ocr_confidence": 0.94,
    "failed_ocr_rate": 0.02
  },
  "sla_metrics": {
    "on_time_compliance": 0.98
  }
}
```

**Pass Criteria**: ✅ Dashboard loads, all metrics display, filters work

**Fail Criteria**: ❌ Dashboard fails to load, metrics missing

---

# 3. OCR REVIEWER WORKFLOW TEST CASES

## Test Case 3.1: Reviewer Login and See Queue

**Test ID**: `TC-REVIEWER-001`

**Objective**: Verify Reviewer can login and see PUBLIC documents only in review queue

**Preconditions**:
- Reviewer account exists
- 100 documents assigned (50 PUBLIC, 50 PRIVATE)
- Documents in IN_REVIEW status

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer logs in | Authenticated with reviewer role |
| 2 | Navigate to review queue | GET `/api/review-queue` |
| 3 | Query includes filter | WHERE classification = 'PUBLIC' AND status = 'IN_REVIEW' |
| 4 | Queue displays | Exactly 50 PUBLIC documents shown |
| 5 | PRIVATE documents hidden | 50 PRIVATE docs NOT in list |
| 6 | Document count shown | "50 documents waiting for review" |
| 7 | Sort by date | Oldest first |
| 8 | Pagination works | 10 per page, 5 pages total |

**Expected Output**:
```json
{
  "status": "success",
  "queue": [
    {
      "document_id": "doc_001",
      "filename": "image_001.jpg",
      "classification": "PUBLIC",
      "status": "IN_REVIEW",
      "queued_at": "2026-01-22T10:00:00Z"
    }
  ],
  "total_count": 50,
  "page": 1,
  "per_page": 10,
  "total_pages": 5
}
```

**Pass Criteria**: ✅ Reviewer sees only PUBLIC (50 docs), PRIVATE hidden (0 docs)

**Fail Criteria**: ❌ Reviewer can see PRIVATE docs (security breach)

---

## Test Case 3.2: Reviewer Claim Document

**Test ID**: `TC-REVIEWER-002`

**Objective**: Verify Reviewer can claim document from queue

**Preconditions**:
- Reviewer logged in
- Document ID: `doc_review_001`
- Status: IN_REVIEW
- Classification: PUBLIC
- Claimed_by: null (unclaimed)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer clicks "Claim" on document | POST `/api/review/doc_review_001/claim` |
| 2 | Backend validates | Reviewer role ✓, PUBLIC doc ✓ |
| 3 | Race condition check | MongoDB: claimed_by null? |
| 4 | Update document | claimed_by = reviewer_id, claimed_at = now |
| 5 | Document removed from queue | Other reviewers won't see it |
| 6 | Reviewer redirected | Document detail page opens |
| 7 | Side-by-side view | Original + OCR output shown |
| 8 | Audit logged | `REVIEWER_CLAIM_DOC` |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_review_001",
    "claimed_by": "reviewer_id",
    "claimed_at": "2026-01-22T11:00:00Z"
  },
  "message": "Document claimed successfully"
}
```

**Pass Criteria**: ✅ Document claimed, appears in "My Documents"

**Fail Criteria**: ❌ Claim fails, document still in queue

**Error Cases**:
- Document already claimed by another reviewer → `409 Conflict: Document already claimed`
- Document is PRIVATE → `403 Forbidden: Cannot access PRIVATE document`
- Concurrent claim (race condition) → `409 Conflict: Claimed by another reviewer`

---

## Test Case 3.3: Reviewer Approve Document (No Edits)

**Test ID**: `TC-REVIEWER-003`

**Objective**: Verify Reviewer can approve document as-is

**Preconditions**:
- Reviewer claimed document: `doc_review_001`
- Review page open with OCR output
- All fields look correct

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer reviews OCR output | Side-by-side comparison shown |
| 2 | Compares with original | All fields match |
| 3 | Clicks "Approve As-Is" | Approval button clicked |
| 4 | Optional notes field shown | "Any comments?" input |
| 5 | Reviewer adds note: "OCR looks good" | Notes recorded |
| 6 | Clicks "Submit" | POST `/api/review/doc_review_001/approve` |
| 7 | Backend validates | Reviewer ✓, claimed_by = reviewer_id ✓ |
| 8 | Status → REVIEWED_APPROVED | Document status changed |
| 9 | Review metadata saved | reviewed_by, reviewed_at, review_notes populated |
| 10 | No manual_edits | manual_edits array remains empty |
| 11 | Audit logged | `REVIEWER_APPROVE_DOC_ASIC` |
| 12 | Document removed from "My Documents" | Document complete for reviewer |
| 13 | Success message | "Document approved" |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_review_001",
    "status": "REVIEWED_APPROVED",
    "reviewed_by": "reviewer_id",
    "reviewed_at": "2026-01-22T11:15:00Z",
    "review_notes": "OCR looks good",
    "manual_edits": []
  },
  "message": "Document approved successfully"
}
```

**Pass Criteria**: ✅ Document approved, status changed, audit logged

**Fail Criteria**: ❌ Approval fails, status not changed

---

## Test Case 3.4: Reviewer Approve with Edits

**Test ID**: `TC-REVIEWER-004`

**Objective**: Verify Reviewer can edit and approve document

**Preconditions**:
- Reviewer claimed document: `doc_review_002`
- OCR has errors (typo in author name)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer views OCR output | Side-by-side shown |
| 2 | Finds error: Author "Jon" should be "John" | Typo identified |
| 3 | Clicks "Edit" on author field | Field becomes editable |
| 4 | Changes value from "Jon" to "John" | Field updated in UI |
| 5 | System tracks edit | Before: "Jon", After: "John" |
| 6 | Clicks "Approve" | POST `/api/review/doc_review_002/approve` with manual_edits |
| 7 | Backend receives | `{manual_edits: [{field_name: "author", old_value: "Jon", new_value: "John"}]}` |
| 8 | Validates edit | field_name exists ✓, edited_by = reviewer_id ✓ |
| 9 | Status → REVIEWED_APPROVED | Document approved with edits |
| 10 | Manual edits saved | Edit history maintained |
| 11 | Audit logged | `REVIEWER_EDIT_AND_APPROVE` with edit details |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_review_002",
    "status": "REVIEWED_APPROVED",
    "reviewed_by": "reviewer_id",
    "manual_edits": [
      {
        "field_name": "author",
        "original_value": "Jon",
        "edited_value": "John",
        "edited_by": "reviewer_id",
        "edited_at": "2026-01-22T11:30:00Z"
      }
    ]
  },
  "message": "Document approved with edits"
}
```

**Pass Criteria**: ✅ Edits saved, audit logged with before/after values

**Fail Criteria**: ❌ Edits lost, audit missing

---

## Test Case 3.5: Reviewer Reject Document

**Test ID**: `TC-REVIEWER-005`

**Objective**: Verify Reviewer can reject document for re-processing

**Preconditions**:
- Reviewer claimed document: `doc_review_003`
- OCR quality very poor (confidence < 70%)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer views OCR output | Quality assessment shown |
| 2 | Identifies poor quality | OCR confidence: 65% |
| 3 | Clicks "Reject" button | Rejection modal appears |
| 4 | Select reason: "OCR quality poor" | Reason chosen from dropdown |
| 5 | Add details: "Many character errors" | Detailed reason recorded |
| 6 | Click "Submit Rejection" | POST `/api/review/doc_review_003/reject` |
| 7 | Backend validates | Reviewer ✓, claimed_by = reviewer_id ✓ |
| 8 | Status → IN_REVIEW (requeue) | Document stays in review queue |
| 9 | Reset claimed_by | claimed_by = null, so other reviewers can see |
| 10 | Rejection reason saved | rejection_reason and details stored |
| 11 | Audit logged | `REVIEWER_REJECT_DOC` |
| 12 | Admin notified | Rejection appears in Admin dashboard |
| 13 | Reviewer can claim different doc | Review queue refreshes |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_review_003",
    "status": "IN_REVIEW",
    "claimed_by": null,
    "rejection_reason": "OCR quality poor",
    "rejection_details": "Many character errors",
    "rejected_by": "reviewer_id",
    "rejected_at": "2026-01-22T11:45:00Z"
  },
  "message": "Document rejected. Admin will re-process."
}
```

**Pass Criteria**: ✅ Rejection recorded, doc re-queued, audit logged

**Fail Criteria**: ❌ Rejection not recorded

**Error Cases**:
- Invalid rejection reason → `400 Bad Request: Invalid rejection reason`
- Document already processed → `409 Conflict: Cannot reject completed document`

---

## Test Case 3.6: Reviewer Cannot See PRIVATE Documents

**Test ID**: `TC-REVIEWER-006`

**Objective**: Verify security - Reviewer cannot access PRIVATE documents

**Preconditions**:
- Reviewer logged in
- PRIVATE document: `doc_private_001` exists in system
- Admin assigned this to Teacher (not Reviewer)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer navigates to `/api/review-queue` | Query with reviewer token |
| 2 | Backend queries documents | WHERE classification = 'PUBLIC' only |
| 3 | PRIVATE docs filtered out | 0 PRIVATE docs returned |
| 4 | Reviewer attempts direct URL | `/api/documents/doc_private_001` |
| 5 | Backend validates authorization | classification = PRIVATE, role = reviewer |
| 6 | Access denied | `403 Forbidden: No access to PRIVATE document` |
| 7 | Error message shown | "You don't have permission to view this document" |
| 8 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Expected Output**:
```json
{
  "status": "error",
  "code": 403,
  "message": "Forbidden: You do not have permission to access this document",
  "audit_event": "AUTH_PERMISSION_DENIED"
}
```

**Pass Criteria**: ✅ Reviewer blocked from PRIVATE, audit logged

**Fail Criteria**: ❌ Reviewer can see PRIVATE (critical security breach)

---

## Test Case 3.7: Reviewer Cannot Run OCR

**Test ID**: `TC-REVIEWER-007`

**Objective**: Verify Reviewer cannot execute OCR

**Preconditions**:
- Reviewer logged in
- Document in OCR_PROCESSED status

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts POST to `/api/ocr/batch/process` | With reviewer token |
| 2 | Backend checks permission | `run_ocr` permission check |
| 3 | Reviewer role lacks permission | run_ocr not in reviewer permissions |
| 4 | Request rejected | `403 Forbidden: Permission denied` |
| 5 | Error message shown | "Only Admins can run OCR" |
| 6 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Expected Output**:
```json
{
  "status": "error",
  "code": 403,
  "message": "Permission denied: Only Admins can run OCR processing"
}
```

**Pass Criteria**: ✅ Reviewer blocked from OCR

**Fail Criteria**: ❌ Reviewer can run OCR (permission bypass)

---

## Test Case 3.8: Reviewer Cannot Classify

**Test ID**: `TC-REVIEWER-008`

**Objective**: Verify Reviewer cannot classify documents

**Preconditions**:
- Reviewer logged in
- Document status: CLASSIFICATION_PENDING

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts POST to `/api/documents/doc_id/classify` | With reviewer token |
| 2 | Backend checks authorization | classify_document permission |
| 3 | Reviewer lacks permission | Not in reviewer permissions |
| 4 | Request rejected | `403 Forbidden` |
| 5 | Error shown | "Only Admins can classify documents" |
| 6 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Expected Output**:
```json
{
  "status": "error",
  "code": 403,
  "message": "Forbidden: Only Admin can classify documents"
}
```

**Pass Criteria**: ✅ Reviewer blocked from classification

**Fail Criteria**: ❌ Reviewer can classify

---

# 4. TEACHER WORKFLOW TEST CASES

## Test Case 4.1: Teacher Login and See Full Queue

**Test ID**: `TC-TEACHER-001`

**Objective**: Verify Teacher can login and see both PUBLIC and PRIVATE documents

**Preconditions**:
- Teacher account exists
- 100 documents assigned (50 PUBLIC, 50 PRIVATE)
- All status: IN_REVIEW

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher logs in | Authenticated with teacher role |
| 2 | Navigate to review queue | GET `/api/review-queue` with teacher token |
| 3 | Query includes both classifications | WHERE classification IN ('PUBLIC', 'PRIVATE') |
| 4 | Queue displays | ALL 100 documents shown |
| 5 | 50 PUBLIC docs visible | Public documents listed |
| 6 | 50 PRIVATE docs visible | Private documents listed |
| 7 | Classification badges shown | [PUBLIC] and [PRIVATE] tags visible |
| 8 | Teacher count: 100 | Total queue count correct |

**Expected Output**:
```json
{
  "status": "success",
  "queue": [
    {
      "document_id": "doc_public_001",
      "classification": "PUBLIC"
    },
    {
      "document_id": "doc_private_001",
      "classification": "PRIVATE"
    }
  ],
  "total_count": 100,
  "breakdown": {
    "PUBLIC": 50,
    "PRIVATE": 50
  }
}
```

**Pass Criteria**: ✅ Teacher sees 100 docs (50 PUBLIC + 50 PRIVATE)

**Fail Criteria**: ❌ Teacher sees < 100 or cannot see PRIVATE

---

## Test Case 4.2: Teacher Claim PRIVATE Document

**Test ID**: `TC-TEACHER-002`

**Objective**: Verify Teacher can claim and review PRIVATE documents

**Preconditions**:
- Teacher logged in
- PRIVATE document: `doc_private_review_001`
- Status: IN_REVIEW
- Classification: PRIVATE

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher clicks "Claim" on PRIVATE doc | POST `/api/review/doc_private_review_001/claim` |
| 2 | Backend validates | Teacher role ✓, PRIVATE doc ✓ |
| 3 | Authorization passes | Teacher CAN view PRIVATE ✓ |
| 4 | Document claimed | claimed_by = teacher_id |
| 5 | Document detail page opens | Side-by-side view with PRIVATE content |
| 6 | Sensitive data visible | PII/sensitive info shown to teacher |
| 7 | Teacher can edit | Edit fields accessible |
| 8 | Audit logged | `TEACHER_CLAIM_DOC` with classification:PRIVATE |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_private_review_001",
    "classification": "PRIVATE",
    "claimed_by": "teacher_id",
    "claimed_at": "2026-01-22T12:00:00Z"
  }
}
```

**Pass Criteria**: ✅ Teacher can access PRIVATE document

**Fail Criteria**: ❌ Teacher blocked from PRIVATE (authorization error)

---

## Test Case 4.3: Teacher Approve PRIVATE Document with Edits

**Test ID**: `TC-TEACHER-003`

**Objective**: Verify Teacher can approve PRIVATE documents with edits

**Preconditions**:
- Teacher claimed PRIVATE document
- Document contains sensitive personal data
- Needs correction

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher reviews PRIVATE content | Sensitive data visible |
| 2 | Identifies error in phone number | Field value incorrect |
| 3 | Edits phone field | Before: "555-1234", After: "555-5678" |
| 4 | System tracks edit | Edit history recorded |
| 5 | Teacher adds note: "Corrected personal contact" | Reason documented |
| 6 | Clicks "Approve" | POST `/api/review/doc_private_review_001/approve` |
| 7 | Backend validates | Teacher ✓, PRIVATE ✓, claimed ✓ |
| 8 | Status → REVIEWED_APPROVED | PRIVATE doc approved |
| 9 | Edits recorded with before/after | Sensitive data change logged |
| 10 | Audit logged | `TEACHER_EDIT_AND_APPROVE` with classification:PRIVATE |

**Expected Output**:
```json
{
  "status": "success",
  "document": {
    "document_id": "doc_private_review_001",
    "classification": "PRIVATE",
    "status": "REVIEWED_APPROVED",
    "reviewed_by": "teacher_id",
    "manual_edits": [
      {
        "field_name": "phone_number",
        "original_value": "555-1234",
        "edited_value": "555-5678",
        "edited_by": "teacher_id",
        "edited_at": "2026-01-22T12:15:00Z"
      }
    ]
  }
}
```

**Pass Criteria**: ✅ PRIVATE doc approved, edits tracked

**Fail Criteria**: ❌ Cannot edit/approve PRIVATE

---

## Test Case 4.4: Teacher Cannot Run OCR

**Test ID**: `TC-TEACHER-004`

**Objective**: Verify Teacher cannot execute OCR

**Preconditions**:
- Teacher logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher attempts POST `/api/ocr/batch/process` | With teacher token |
| 2 | Backend checks permission | run_ocr not in teacher permissions |
| 3 | Request rejected | `403 Forbidden` |
| 4 | Error shown | "Only Admins can run OCR" |
| 5 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Expected Output**:
```json
{
  "status": "error",
  "code": 403,
  "message": "Forbidden: Only Admins can run OCR"
}
```

**Pass Criteria**: ✅ Teacher blocked

**Fail Criteria**: ❌ Teacher can run OCR

---

## Test Case 4.5: Teacher Cannot Classify

**Test ID**: `TC-TEACHER-005`

**Objective**: Verify Teacher cannot classify documents

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher attempts `/api/documents/doc_id/classify` | With teacher token |
| 2 | Backend checks permission | classify_document not in teacher permissions |
| 3 | Request rejected | `403 Forbidden` |
| 4 | Error shown | "Only Admins can classify" |
| 5 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Pass Criteria**: ✅ Teacher blocked from classification

---

## Test Case 4.6: Teacher Cannot Perform Final Approval

**Test ID**: `TC-TEACHER-006`

**Objective**: Verify Teacher cannot approve for export (Admin-only)

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher attempts POST `/api/final-approval/batch` | With teacher token |
| 2 | Backend checks permission | approve_final not in teacher permissions |
| 3 | Request rejected | `403 Forbidden` |
| 4 | Error shown | "Only Admin can perform final approval" |

**Pass Criteria**: ✅ Teacher blocked from final approval

---

# 5. CROSS-ROLE SECURITY TEST CASES

## Test Case 5.1: Reviewer Cannot Access Admin Panel

**Test ID**: `TC-SECURITY-001`

**Objective**: Verify Reviewer has no access to Admin dashboard

**Preconditions**:
- Reviewer logged in
- Admin token exists for comparison

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts GET `/api/dashboard/overview` | With reviewer token |
| 2 | Backend checks authorization | view_dashboards not in reviewer permissions |
| 3 | Request rejected | `403 Forbidden: Access Denied` |
| 4 | Error message shown | "Admin access required" |
| 5 | Audit logged | `AUTH_PERMISSION_DENIED` with route attempted |

**Expected Output**:
```json
{
  "status": "error",
  "code": 403,
  "message": "Forbidden: Admin access required"
}
```

**Pass Criteria**: ✅ Reviewer blocked from dashboard

**Fail Criteria**: ❌ Reviewer can access dashboard (privilege escalation)

---

## Test Case 5.2: Reviewer Cannot See Audit Logs

**Test ID**: `TC-SECURITY-002`

**Objective**: Verify Reviewer cannot access audit logs

**Preconditions**:
- Reviewer logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts GET `/api/audit-logs` | With reviewer token |
| 2 | Backend checks permission | view_audit_logs not in reviewer permissions |
| 3 | Request rejected | `403 Forbidden` |
| 4 | Audit logged | `AUTH_PERMISSION_DENIED` |

**Pass Criteria**: ✅ Reviewer blocked from audit logs

---

## Test Case 5.3: Token Tampering Detection

**Test ID**: `TC-SECURITY-003`

**Objective**: Verify system detects tampered JWT tokens

**Preconditions**:
- Valid JWT token obtained from login
- Token stored in browser

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Attacker modifies token payload | Changes role from "reviewer" to "admin" |
| 2 | Attacker resends modified token | In Authorization header |
| 3 | Backend verifies signature | JWT signature validation fails |
| 4 | Request rejected | `401 Unauthorized: Invalid token signature` |
| 5 | Audit logged | `AUTH_UNAUTHORIZED_ACCESS_ATTEMPT` |
| 6 | User logged out | Token blacklisted if suspicious pattern detected |

**Expected Output**:
```json
{
  "status": "error",
  "code": 401,
  "message": "Unauthorized: Invalid or tampered token"
}
```

**Pass Criteria**: ✅ Tampered token rejected, audit logged

**Fail Criteria**: ❌ Tampered token accepted (critical security flaw)

---

## Test Case 5.4: SQL Injection Prevention

**Test ID**: `TC-SECURITY-004`

**Objective**: Verify system prevents SQL injection via document queries

**Preconditions**:
- Reviewer logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts query with injection | `?doc_id='; DROP TABLE documents; --` |
| 2 | Backend uses parameterized queries | MongoDB uses proper query syntax |
| 3 | Injection attempt neutralized | Treated as literal string |
| 4 | No documents returned | Safe behavior |
| 5 | Audit logged | Suspicious query pattern logged |

**Pass Criteria**: ✅ Injection blocked, no database affected

**Fail Criteria**: ❌ Database tables dropped (critical)

---

## Test Case 5.5: Cross-Role Document Swap Attempt

**Test ID**: `TC-SECURITY-005`

**Objective**: Verify Reviewer cannot view document assigned to Reviewer role that's actually PRIVATE

**Preconditions**:
- PRIVATE document in queue
- Mistakenly assigned to Reviewer queue (bug scenario)
- Reviewer logged in

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer's queue somehow has PRIVATE doc | Query includes PRIVATE by mistake |
| 2 | Reviewer attempts to view PRIVATE doc | GET `/api/documents/doc_private_001` |
| 3 | Backend checks classification | classification = 'PRIVATE' |
| 4 | Backend checks reviewer role | role = 'reviewer' |
| 5 | Authorization fails | reviewer CANNOT see PRIVATE |
| 6 | Request rejected | `403 Forbidden: No access to PRIVATE` |
| 7 | Audit logged | `AUTH_PERMISSION_DENIED` with attempted access to PRIVATE |

**Pass Criteria**: ✅ Access denied despite being in queue

**Fail Criteria**: ❌ Reviewer can view PRIVATE (severe breach)

---

# 6. ERROR HANDLING TEST CASES

## Test Case 6.1: Database Connection Error

**Test ID**: `TC-ERROR-001`

**Objective**: Verify system handles database connection failures gracefully

**Preconditions**:
- MongoDB service down
- User attempts login

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | User clicks login | POST `/api/auth/login` |
| 2 | Backend attempts database query | Connection times out |
| 3 | Retry logic triggered | 3 retries with backoff |
| 4 | All retries fail | Error returned |
| 5 | User shown error message | "Service temporarily unavailable. Please try again in a few moments." |
| 6 | No credentials leaked | Error message generic |
| 7 | Error logged | Server-side logging with full stack trace |

**Expected Output**:
```json
{
  "status": "error",
  "code": 503,
  "message": "Service temporarily unavailable",
  "retry_after": 5
}
```

**Pass Criteria**: ✅ Error handled, user-friendly message, no info leak

**Fail Criteria**: ❌ Stack trace shown, credentials exposed

---

## Test Case 6.2: OCR Provider API Failure

**Test ID**: `TC-ERROR-002`

**Objective**: Verify system handles OCR provider API errors

**Preconditions**:
- Admin running OCR
- Google Vision API experiencing outage

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin starts OCR batch | 10 documents |
| 2 | Google Vision API returns 503 | Service unavailable |
| 3 | Retry logic triggered | Exponential backoff (1s, 2s, 4s, ...) |
| 4 | Max retries reached | 3 attempts failed |
| 5 | Job marked as FAILED | Status updated in database |
| 6 | User notified | "OCR processing failed. Google Vision service unavailable." |
| 7 | Admin shown retry option | "Retry with different provider?" |
| 8 | Audit logged | `PROCESSOR_OCR_FAILED` with error details |
| 9 | Documents remain in OCR_PROCESSING | Not lost |

**Expected Output**:
```json
{
  "status": "error",
  "job_id": "job_ocr_001",
  "message": "OCR processing failed",
  "reason": "Google Vision API returned 503 Service Unavailable",
  "retry_available": true,
  "recommended_actions": ["Retry with same provider", "Switch to Tesseract"]
}
```

**Pass Criteria**: ✅ Error handled, data preserved, options provided

**Fail Criteria**: ❌ Data lost, no recovery option

---

## Test Case 6.3: Concurrent Update Conflict

**Test ID**: `TC-ERROR-003`

**Objective**: Verify system handles race conditions (two reviewers claiming same doc)

**Preconditions**:
- Document: `doc_race_001` in IN_REVIEW
- Two reviewers simultaneously claim

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer A clicks claim | Request 1 starts |
| 2 | Reviewer B clicks claim | Request 2 starts (same time) |
| 3 | Request 1 reaches backend | claimed_by = null? YES → Proceed |
| 4 | Request 2 reaches backend | claimed_by = null? (checking at same time) YES → Proceed |
| 5 | Request 1 updates document | claimed_by = reviewer_A |
| 6 | Request 2 attempts update | claimed_by = null (but it's not!) |
| 7 | Optimistic lock check fails | Version mismatch detected |
| 8 | Request 2 rejected | `409 Conflict: Document already claimed` |
| 9 | Reviewer B shown error | "This document was just claimed by another reviewer" |
| 10 | Reviewer A gets document | Document belongs to Reviewer A |

**Expected Output**:
```json
{
  "status": "error",
  "code": 409,
  "message": "Conflict: Document already claimed by another reviewer",
  "claimed_by": "reviewer_A_id"
}
```

**Pass Criteria**: ✅ Race condition handled, document not duplicated

**Fail Criteria**: ❌ Document claimed by both, data corruption

---

## Test Case 6.4: Invalid JWT Token

**Test ID**: `TC-ERROR-004`

**Objective**: Verify system rejects invalid JWT tokens

**Preconditions**:
- Invalid token in Authorization header

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Request sent with invalid token | `Authorization: Bearer invalid.token.here` |
| 2 | Backend parses token | Parsing fails (malformed JSON) |
| 3 | Request rejected | `401 Unauthorized: Invalid token format` |
| 4 | No user data leaked | Generic error message |
| 5 | Audit logged | `AUTH_UNAUTHORIZED_ACCESS_ATTEMPT` |

**Pass Criteria**: ✅ Invalid token rejected

**Fail Criteria**: ❌ Invalid token accepted

---

## Test Case 6.5: Missing Required Fields

**Test ID**: `TC-ERROR-005`

**Objective**: Verify system validates required fields in requests

**Preconditions**:
- Admin attempting to classify document
- Classification field omitted

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin sends classification request | classification field missing |
| 2 | Backend validates request | Required field check |
| 3 | Request rejected | `400 Bad Request: Missing required field 'classification'` |
| 4 | Error message shown | "Please provide a classification (Public or Private)" |
| 5 | No action taken | Document remains unclassified |

**Expected Output**:
```json
{
  "status": "error",
  "code": 400,
  "message": "Bad Request: Missing required field",
  "field": "classification",
  "expected_values": ["PUBLIC", "PRIVATE"]
}
```

**Pass Criteria**: ✅ Missing field caught, validation works

**Fail Criteria**: ❌ Missing field causes server error

---

# 7. EDGE CASES & BOUNDARY TESTS

## Test Case 7.1: Classify Document After OCR Started

**Test ID**: `TC-EDGE-001`

**Objective**: Verify system prevents classification change after OCR starts

**Preconditions**:
- Document status: OCR_PROCESSING
- Admin attempts to re-classify

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin attempts POST `/api/documents/doc_id/classify` | Request sent |
| 2 | Backend checks status | status != CLASSIFICATION_PENDING |
| 3 | Request rejected | `409 Conflict: Cannot change classification after OCR starts` |
| 4 | Error shown | "Document classification is immutable once processing begins" |

**Pass Criteria**: ✅ Re-classification blocked after OCR

**Fail Criteria**: ❌ Classification changed (workflow violation)

---

## Test Case 7.2: Approve Document from Wrong Status

**Test ID**: `TC-EDGE-002`

**Objective**: Verify system prevents approval from invalid status

**Preconditions**:
- Document status: OCR_PROCESSING
- Reviewer attempts to approve

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer attempts approval on OCR_PROCESSING doc | POST `/api/review/doc_id/approve` |
| 2 | Backend checks status | status != IN_REVIEW |
| 3 | Request rejected | `409 Conflict: Document not in review status` |
| 4 | Error shown | "Can only review documents in IN_REVIEW status" |

**Pass Criteria**: ✅ Invalid approval blocked

**Fail Criteria**: ❌ Document approved from wrong status

---

## Test Case 7.3: Massive Batch Assignment

**Test ID**: `TC-EDGE-003`

**Objective**: Verify system handles large batch assignment (10,000 docs)

**Preconditions**:
- 10,000 documents classified
- Admin attempts batch assignment

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin selects 10,000 documents | Batch action triggered |
| 2 | POST `/api/review-queue/bulk-assign` with 10,000 IDs | Large request |
| 3 | Backend processes batch | Bulk MongoDB operation |
| 4 | Memory usage monitored | Should not exceed limits |
| 5 | All 10,000 records updated | Database transaction completes |
| 6 | Progress tracker shows | Real-time update |
| 7 | Timeout handling | If > 30s, return job ID for async processing |
| 8 | Success message | "10,000 documents assigned" |

**Pass Criteria**: ✅ Large batch handled, no timeout

**Fail Criteria**: ❌ System crashes, documents lost

---

## Test Case 7.4: Empty Search Results

**Test ID**: `TC-EDGE-004`

**Objective**: Verify system handles empty search results gracefully

**Preconditions**:
- Reviewer queue is empty

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer navigates to review queue | GET `/api/review-queue` |
| 2 | No documents in review status | Query returns empty array |
| 3 | User shown message | "No documents to review. Great job!" |
| 4 | No errors in console | UI handles empty state |
| 5 | Refresh button available | Option to reload |

**Expected Output**:
```json
{
  "status": "success",
  "queue": [],
  "total_count": 0,
  "message": "No documents waiting for review"
}
```

**Pass Criteria**: ✅ Empty state handled gracefully

**Fail Criteria**: ❌ Page crashes, error shown

---

## Test Case 7.5: Document with Extremely Long Text

**Test ID**: `TC-EDGE-005`

**Objective**: Verify system handles very long OCR text (500KB)

**Preconditions**:
- Document with 500KB of OCR text
- Admin attempts to export

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Document with massive OCR text loaded | 500KB text field |
| 2 | Admin attempts review | UI should not freeze |
| 3 | Text displayed with pagination | Or truncated preview |
| 4 | Export still works | Large document exported |
| 5 | Database can store | MongoDB field size limits respected |
| 6 | No performance impact | Other operations unaffected |

**Pass Criteria**: ✅ Large text handled efficiently

**Fail Criteria**: ❌ UI freezes, export fails

---

# 8. PERFORMANCE TEST CASES

## Test Case 8.1: Dashboard Load Time

**Test ID**: `TC-PERF-001`

**Objective**: Verify admin dashboard loads within 3 seconds

**Preconditions**:
- Admin logged in
- 10,000 documents in system
- Dashboard requests metrics

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin navigates to dashboard | GET `/api/dashboard/overview` |
| 2 | Request timer starts | Time measured |
| 3 | Backend aggregates metrics | 10,000 documents processed |
| 4 | Dashboard loads | UI renders |
| 5 | Response time < 3000ms | Performance acceptable |
| 6 | Database query optimized | Indexed fields used |
| 7 | Metrics cached (optional) | Redis cache may help |

**Expected Output**:
- Response time: 1,500ms (acceptable)
- All metrics loaded
- No missing data

**Pass Criteria**: ✅ Dashboard loads < 3 seconds

**Fail Criteria**: ❌ Dashboard loads > 5 seconds (timeout)

---

## Test Case 8.2: Review Queue Load Time

**Test ID**: `TC-PERF-002`

**Objective**: Verify review queue loads quickly even with 1000 documents

**Preconditions**:
- Reviewer logged in
- 1,000 PUBLIC documents in queue

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Reviewer navigates to queue | GET `/api/review-queue` |
| 2 | 1,000 documents queried | Pagination applied (10 per page) |
| 3 | First page loads | 10 docs displayed |
| 4 | Response time < 1000ms | Quick load |
| 5 | Pagination works | Page 2 loads quickly |
| 6 | Scroll performance smooth | No lag on UI |

**Pass Criteria**: ✅ Queue loads < 1 second

**Fail Criteria**: ❌ Queue loads > 3 seconds

---

## Test Case 8.3: Batch OCR Throughput

**Test ID**: `TC-PERF-003`

**Objective**: Verify system can process 1000 documents per batch without degradation

**Preconditions**:
- 1,000 documents ready for OCR
- OCR provider configured
- Admin running batch

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin starts batch OCR of 1000 docs | 10 in parallel |
| 2 | Job queued | NSQ jobs distributed |
| 3 | Processing begins | Parallel workers start |
| 4 | CPU usage monitored | Should not exceed 80% |
| 5 | Memory usage monitored | Should not exceed limits |
| 6 | All 1000 complete | ~15-20 minutes |
| 7 | No documents lost | All 1000 successfully processed |
| 8 | Success rate tracked | 98%+ success |

**Pass Criteria**: ✅ 1000 docs processed, system stable

**Fail Criteria**: ❌ System crashes, documents lost

---

# 9. AUDIT TRAIL TEST CASES

## Test Case 9.1: Document Lifecycle Audit Trail

**Test ID**: `TC-AUDIT-001`

**Objective**: Verify complete audit trail for document from upload to export

**Preconditions**:
- Document uploaded
- Full workflow completed

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Document uploaded | UPLOADED event logged |
| 2 | Admin classifies as PUBLIC | ADMIN_CLASSIFY_DOC logged |
| 3 | Admin runs OCR | ADMIN_RUN_OCR logged |
| 4 | OCR completes | OCR_PROCESSED event logged |
| 5 | Assigned to Reviewer | ADMIN_ASSIGN_BATCH logged |
| 6 | Reviewer approves | REVIEWER_APPROVE_DOC_ASIC logged |
| 7 | Admin final approves | ADMIN_FINAL_APPROVE logged |
| 8 | Document exported | ADMIN_EXPORT_TO_DOWNSTREAM logged |
| 9 | Audit query requested | GET `/api/audit-logs?document_id=doc_id` |
| 10 | All events returned | 8+ events in chronological order |

**Expected Output**:
```json
{
  "status": "success",
  "audit_trail": [
    {
      "action_type": "UPLOADED",
      "timestamp": "2026-01-22T10:00:00Z",
      "actor_id": "system"
    },
    {
      "action_type": "ADMIN_CLASSIFY_DOC",
      "timestamp": "2026-01-22T10:05:00Z",
      "actor_id": "admin_id",
      "actor_role": "admin",
      "changes": [{ "field": "classification", "new_value": "PUBLIC" }]
    },
    ...
  ],
  "total_events": 8
}
```

**Pass Criteria**: ✅ Complete audit trail maintained

**Fail Criteria**: ❌ Events missing, order incorrect

---

## Test Case 9.2: Admin Override Audit

**Test ID**: `TC-AUDIT-002`

**Objective**: Verify override actions are fully audited

**Preconditions**:
- Document in REVIEWED_APPROVED status
- Admin overrides for re-OCR

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Admin initiates override | POST `/api/documents/doc_id/override` |
| 2 | Admin selects: re-run OCR | Action chosen |
| 3 | Admin adds reason: "OCR quality needs improvement" | Justification required |
| 4 | Backend processes override | Status → OCR_PROCESSING |
| 5 | Audit event logged | `ADMIN_OVERRIDE_STATE` |
| 6 | Override details recorded | Previous state, new state, reason |
| 7 | Admin who made override logged | User ID and email |
| 8 | Timestamp recorded | When override made |
| 9 | Query audit log | GET `/api/audit-logs?action_type=ADMIN_OVERRIDE_STATE` |
| 10 | Override reason visible | Justification shown |

**Expected Output**:
```json
{
  "action_type": "ADMIN_OVERRIDE_STATE",
  "actor_id": "admin_id",
  "actor_email": "admin@ocr.com",
  "previous_state": "REVIEWED_APPROVED",
  "new_state": "OCR_PROCESSING",
  "reason": "OCR quality needs improvement",
  "timestamp": "2026-01-22T13:00:00Z"
}
```

**Pass Criteria**: ✅ Override fully documented with reason

**Fail Criteria**: ❌ Reason missing, actor not logged

---

## Test Case 9.3: Sensitive Data Access Audit

**Test ID**: `TC-AUDIT-003`

**Objective**: Verify PRIVATE document access is audited

**Preconditions**:
- PRIVATE document exists
- Teacher accesses it

**Steps**:

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Teacher claims PRIVATE document | `TEACHER_VIEW_DOC` event triggered |
| 2 | Event logged with classification | classification: PRIVATE noted |
| 3 | Event logged with timestamp | Exact time recorded |
| 4 | Actor ID recorded | Teacher ID logged |
| 5 | Query sensitive access logs | GET `/api/audit-logs?is_sensitive=true` |
| 6 | Sensitive access shown | Only admin and compliance can see |
| 7 | Count of PRIVATE accesses | Report available |

**Expected Output**:
```json
{
  "sensitive_events": [
    {
      "action_type": "TEACHER_VIEW_DOC",
      "document_classification": "PRIVATE",
      "actor_id": "teacher_id",
      "timestamp": "2026-01-22T12:30:00Z",
      "is_sensitive": true
    }
  ],
  "total_sensitive_events": 1
}
```

**Pass Criteria**: ✅ Sensitive access logged and queryable

**Fail Criteria**: ❌ PRIVATE access not logged (compliance failure)

---

# 10. TEST EXECUTION REPORT TEMPLATE

## Test Execution Report

**Test Suite**: OCR RBAC System - Full Workflow
**Test Date**: ___________
**Executed By**: ___________
**Environment**: [Development / Staging / Production]
**Duration**: ___________

### Summary

| Category | Total | Passed | Failed | Blocked | Pass Rate |
|----------|-------|--------|--------|---------|-----------|
| Login Tests | 8 | ___ | ___ | ___ | __% |
| Admin Tests | 10 | ___ | ___ | ___ | __% |
| Reviewer Tests | 8 | ___ | ___ | ___ | __% |
| Teacher Tests | 6 | ___ | ___ | ___ | __% |
| Security Tests | 5 | ___ | ___ | ___ | __% |
| Error Handling | 5 | ___ | ___ | ___ | __% |
| Edge Cases | 5 | ___ | ___ | ___ | __% |
| Performance | 3 | ___ | ___ | ___ | __% |
| Audit Trail | 3 | ___ | ___ | ___ | __% |
| **TOTAL** | **53** | **___** | **___** | **___** | **__% **|

### Detailed Results

#### Login Tests

| Test ID | Test Case | Status | Remarks |
|---------|-----------|--------|---------|
| TC-LOGIN-001 | Admin Email/Password | [ ] Pass [ ] Fail | |
| TC-LOGIN-002 | Reviewer Email/Password | [ ] Pass [ ] Fail | |
| TC-LOGIN-003 | Teacher Email/Password | [ ] Pass [ ] Fail | |
| TC-LOGIN-004 | Google OAuth | [ ] Pass [ ] Fail | |
| TC-LOGIN-005 | Invalid Email Format | [ ] Pass [ ] Fail | |
| TC-LOGIN-006 | Token Refresh | [ ] Pass [ ] Fail | |
| TC-LOGIN-007 | Logout | [ ] Pass [ ] Fail | |
| TC-LOGIN-008 | Session Timeout | [ ] Pass [ ] Fail | |

#### Admin Tests

| Test ID | Test Case | Status | Remarks |
|---------|-----------|--------|---------|
| TC-ADMIN-001 | Classify PUBLIC | [ ] Pass [ ] Fail | |
| TC-ADMIN-002 | Classify PRIVATE | [ ] Pass [ ] Fail | |
| TC-ADMIN-003 | Run OCR Single | [ ] Pass [ ] Fail | |
| TC-ADMIN-004 | Batch OCR | [ ] Pass [ ] Fail | |
| TC-ADMIN-005 | Assign to Reviewer | [ ] Pass [ ] Fail | |
| TC-ADMIN-006 | Assign to Teacher | [ ] Pass [ ] Fail | |
| TC-ADMIN-007 | Final Approval | [ ] Pass [ ] Fail | |
| TC-ADMIN-008 | Export MongoDB | [ ] Pass [ ] Fail | |
| TC-ADMIN-009 | Export Archipelago | [ ] Pass [ ] Fail | |
| TC-ADMIN-010 | View Dashboard | [ ] Pass [ ] Fail | |

#### Security Tests

| Test ID | Test Case | Status | Error Details | Severity |
|---------|-----------|--------|---------------|----------|
| TC-SECURITY-001 | Reviewer Access Admin | [ ] Pass [ ] Fail | | |
| TC-SECURITY-002 | Reviewer See Audit Logs | [ ] Pass [ ] Fail | | |
| TC-SECURITY-003 | Token Tampering | [ ] Pass [ ] Fail | | |
| TC-SECURITY-004 | SQL Injection | [ ] Pass [ ] Fail | | |
| TC-SECURITY-005 | PRIVATE Access Control | [ ] Pass [ ] Fail | | |

### Failed Tests Details

| Test ID | Issue | Root Cause | Fix Applied | Status |
|---------|-------|-----------|-------------|--------|
| | | | | |

### Error Messages Encountered

1. **Error Type**: ___________
   - Test ID: ___________
   - Message: ___________
   - Action Taken: ___________

2. **Error Type**: ___________
   - Test ID: ___________
   - Message: ___________
   - Action Taken: ___________

### Performance Metrics

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Dashboard Load Time | < 3s | ___ | [ ] Pass [ ] Fail |
| Review Queue Load Time | < 1s | ___ | [ ] Pass [ ] Fail |
| Batch OCR (1000 docs) | 15-20 min | ___ | [ ] Pass [ ] Fail |
| Avg API Response Time | < 500ms | ___ | [ ] Pass [ ] Fail |

### Security Assessment

- [ ] All permission checks working
- [ ] No data leakage between roles
- [ ] PRIVATE documents protected
- [ ] Audit trail complete
- [ ] Error messages safe (no info leak)
- [ ] Tokens properly validated
- [ ] XSS prevention active
- [ ] CSRF protection active

### Recommendations

1. ___________
2. ___________
3. ___________

### Sign-off

**Tester**: _________________
**Date**: _________________
**Manager Approval**: _________________
**Date**: _________________

---

**End of Test Cases Document**

