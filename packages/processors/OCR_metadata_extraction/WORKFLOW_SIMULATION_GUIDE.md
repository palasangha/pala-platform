# RBAC Workflow Simulation Guide

## Overview

This guide documents the comprehensive RBAC workflow simulation system that creates realistic test data demonstrating document flow, role-based access control, queue management, and audit tracking.

---

## What Gets Created

### Users (8 Total)

| Role | Count | Usernames | Default Password |
|------|-------|-----------|------------------|
| **Admin** | 1 | `admin@docgen.ai` | `password123` |
| **Reviewers** | 5 | `reviewer1-5@docgen.ai` | `password123` |
| **Teachers** | 2 | `teacher1-2@docgen.ai` | `password123` |

#### User Details

**Admin:**
- Name: System Admin
- Email: admin@docgen.ai
- Permissions: Full system access

**Reviewers:**
1. Alice Johnson - reviewer1@docgen.ai
2. Bob Smith - reviewer2@docgen.ai
3. Carol Williams - reviewer3@docgen.ai
4. David Brown - reviewer4@docgen.ai
5. Emma Davis - reviewer5@docgen.ai

**Teachers:**
1. Prof. Michael Chen - teacher1@docgen.ai
2. Prof. Sarah Martinez - teacher2@docgen.ai

---

### Documents (35 Total)

Documents are created with realistic metadata simulating various business documents:

**Document Types:**
- Letters
- Newsletters
- Publications
- Reports
- Memos
- Invoices
- Contracts
- Forms
- Certificates
- Notices

**Source Types:**
- Scanned Document
- Email Attachment
- Web Upload
- Mobile Capture
- Bulk Import

**Document Fields:**
```json
{
  "document_id": "ObjectId",
  "title": "Annual Report 2025",
  "original_filename": "annual_report_2025.pdf",
  "source_type": "Scanned Document",
  "classification": "PUBLIC | PRIVATE",
  "document_status": "UPLOADED | CLASSIFIED | OCR_PROCESSED | IN_REVIEW | REVIEWED_APPROVED",
  "current_queue": "upload | classification_complete | ocr_complete | reviewer_queue | in_review | ...",
  "queue_history": ["upload", "classification_complete", "ocr_complete", ...],
  "assignment_history": [
    {
      "assigned_to": "reviewer_id",
      "assigned_by": "admin_id",
      "assigned_at": "timestamp",
      "role": "reviewer"
    }
  ],
  "assigned_to": "user_id",
  "claimed_by": "user_id",
  "reviewed_by": "user_id",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

## Workflow Simulation Phases

### Phase 1: Document Upload
- 35 documents created in `UPLOADED` status
- All documents assigned to `upload` queue
- Created by admin user
- Spread over last 30 days

### Phase 2: Classification
- Admin classifies all 35 documents
- Distribution:
  - **PUBLIC:** ~25 documents (70%)
  - **PRIVATE:** ~10 documents (30%)
- Status changes: `UPLOADED` → `CLASSIFIED`
- Queue changes: `upload` → `classification_complete`
- Audit logs created for each classification

### Phase 3: OCR Processing
- All 35 documents processed through OCR
- Sample OCR text generated
- Status changes: `CLASSIFIED` → `OCR_PROCESSED`
- Queue changes: `classification_complete` → `ocr_complete`
- Processing time: 2-24 hours after classification

### Phase 4: Reviewer Assignment
- **Distribution:** 7 documents per reviewer
- Round-robin assignment across 5 reviewers
- Queue changes: `ocr_complete` → `reviewer_queue`
- Audit logs created for each assignment

**Assignment Breakdown:**
```
Reviewer 1 (Alice Johnson):     7 documents
Reviewer 2 (Bob Smith):          7 documents
Reviewer 3 (Carol Williams):     7 documents
Reviewer 4 (David Brown):        7 documents
Reviewer 5 (Emma Davis):         7 documents
TOTAL:                          35 documents
```

### Phase 5: Reviewer Work
- Reviewers claim their assigned documents
- Status changes: `OCR_PROCESSED` → `IN_REVIEW`
- Queue changes: `reviewer_queue` → `in_review`
- Reviewers approve documents after review
- 30% of documents receive manual edits
- Review time: 2-48 hours after claim
- Status changes: `IN_REVIEW` → `REVIEWED_APPROVED`
- Queue changes: `in_review` → `reviewer_approved`

### Phase 6: Teacher Assignment
- **Distribution:** 10 documents total
  - Teacher 1: 5 documents
  - Teacher 2: 5 documents
- Only previously approved documents assigned
- Queue changes: `reviewer_approved` → `teacher_queue`
- Audit logs track assignment to teachers

### Phase 7: Reassignments
- **5 documents** reassigned between reviewers
- Simulates workload balancing
- Documents moved back to `reviewer_queue`
- Audit logs track:
  - Previous owner
  - New owner
  - Reassignment reason
  - Timestamp

### Phase 8: Rejections & Corrections
- **3 documents** rejected
- Rejection reasons:
  - "OCR quality too low - needs reprocessing"
  - "Missing critical information"
  - "Document classification incorrect"
  - "Requires manual data entry"
  - "Image quality insufficient"
- Status changes: `REVIEWED_APPROVED` → `REJECTED`
- Queue changes: `reviewer_approved` → `rejected`
- Documents unclaimed for re-processing

---

## Queue States

Documents flow through these queues:

| Queue Name | Description | Typical Status |
|------------|-------------|----------------|
| `upload` | Initial upload state | UPLOADED |
| `classification_complete` | After classification | CLASSIFIED |
| `ocr_complete` | After OCR processing | OCR_PROCESSED |
| `reviewer_queue` | Assigned to reviewer | OCR_PROCESSED |
| `in_review` | Currently being reviewed | IN_REVIEW |
| `reviewer_approved` | Approved by reviewer | REVIEWED_APPROVED |
| `teacher_queue` | Assigned to teacher | REVIEWED_APPROVED |
| `rejected` | Rejected for reprocessing | IN_REVIEW |
| `reviewer_queue_reassigned` | Reassigned to different reviewer | OCR_PROCESSED |

---

## Assignment Rules

### Reviewer Assignment Logic
```python
# Round-robin assignment
for i, doc in enumerate(documents):
    reviewer_index = i % 5
    assign_document(doc, reviewers[reviewer_index])
```

Result: Each of 5 reviewers gets exactly 7 documents

### Teacher Assignment Logic
```python
# First 10 approved documents
approved_docs = get_approved_documents()[:10]

# Split evenly
teacher1_docs = approved_docs[:5]   # First 5
teacher2_docs = approved_docs[5:10] # Next 5
```

Result: Each of 2 teachers gets exactly 5 documents

### Reassignment Logic
```python
# Select 5 random approved documents
docs_to_reassign = random.sample(approved_docs, 5)

# Assign to different reviewer
for doc in docs_to_reassign:
    old_reviewer = doc.assigned_to
    new_reviewer = select_different_reviewer(old_reviewer)
    reassign(doc, old_reviewer, new_reviewer)
```

Result: 5 documents reassigned with full audit trail

---

## Audit Log Tracking

### Action Types Logged

| Action Type | When Triggered | Details Captured |
|-------------|----------------|------------------|
| `DOCUMENT_UPLOADED` | Document created | title, filename, source_type |
| `CLASSIFY_DOCUMENT` | Admin classifies | classification, previous/new status |
| `DOCUMENT_ASSIGNED` | Assignment to user | assigned_to, role, previous owner (if reassigned) |
| `CLAIM_DOCUMENT` | User claims document | claimed_by, claimed_at |
| `APPROVE_DOCUMENT` | User approves | manual_edits count, notes |
| `REJECT_DOCUMENT` | User rejects | rejection reason |
| `USER_CREATED` | User account created | email, role |

### Audit Log Structure
```json
{
  "user_id": "ObjectId",
  "action_type": "DOCUMENT_ASSIGNED",
  "resource_type": "document",
  "resource_id": "ObjectId",
  "previous_state": {
    "assigned_to": "old_user_id"
  },
  "new_state": {
    "assigned_to": "new_user_id"
  },
  "details": {
    "reassignment": true,
    "from": "Alice Johnson",
    "to": "Bob Smith",
    "reason": "Workload balancing"
  },
  "created_at": "2026-02-02T10:30:00Z"
}
```

---

## Expected Final State

### Document Distribution by Queue

```
upload:                      0 documents (all processed)
classification_complete:     0 documents (all processed)
ocr_complete:                0 documents (all assigned)
reviewer_queue:              5 documents (reassigned)
in_review:                   0 documents (all reviewed)
reviewer_approved:          22 documents (waiting or approved)
teacher_queue:              10 documents (with teachers)
rejected:                    3 documents (needs reprocessing)
```

### Document Distribution by Classification

```
PUBLIC:   ~25 documents (70%)
PRIVATE:  ~10 documents (30%)
```

### Reviewer Workload

Each reviewer has 7 documents assigned (some may be reassigned)

### Teacher Workload

- Teacher 1: 5 documents
- Teacher 2: 5 documents

### Audit Log Count

Expected: **150+ audit log entries**
- Document uploads: 35
- Classifications: 35
- Assignments: 35
- Claims: 35
- Approvals: 32
- Teacher assignments: 10
- Reassignments: 5
- Rejections: 3
- User creations: 8

---

## Running the Simulation

### Prerequisites

```bash
cd backend
pip install -r requirements.txt
```

### Execute Script

```bash
cd backend
python3 seed_workflow_simulation.py
```

### Expected Output

```
================================================================================
🚀 COMPREHENSIVE RBAC WORKFLOW SIMULATION
================================================================================

This script will create:
  - 1 Admin user
  - 5 Reviewer users
  - 2 Teacher users
  - 35 Documents with complete workflow
  - Queue transitions and reassignments
  - Complete audit trail

================================================================================
🗑️  CLEARING EXISTING WORKFLOW DATA
================================================================================
   ✅ Deleted 8 users
   ✅ Deleted 35 documents
   ✅ Deleted 1 projects
   ✅ Cleared workflow data

================================================================================
👥 CREATING USERS
================================================================================
   ✅ System Admin (admin@docgen.ai) - Role: admin
   ✅ Alice Johnson (reviewer1@docgen.ai) - Role: reviewer
   ...

[Full workflow execution output]

================================================================================
✅ WORKFLOW SIMULATION COMPLETE
================================================================================

You can now test the RBAC system with realistic workflow data!
All users use password: password123
```

### JSON Output

The script generates `workflow_simulation_output.json`:

```json
{
  "summary": {
    "total_users": 8,
    "total_documents": 35,
    "total_audit_logs": 150
  },
  "users": {
    "admins": [{"name": "System Admin", "email": "admin@docgen.ai"}],
    "reviewers": [...],
    "teachers": [...]
  },
  "documents": {
    "total": 35,
    "by_classification": {"PUBLIC": 25, "PRIVATE": 10},
    "by_queue": {...}
  },
  "assignments": {
    "reviewers": {
      "Alice Johnson": 7,
      "Bob Smith": 7,
      ...
    },
    "teachers": {
      "Prof. Michael Chen": 5,
      "Prof. Sarah Martinez": 5
    }
  }
}
```

---

## Testing RBAC Behavior

### Test 1: Admin Access

**Login:** admin@docgen.ai / password123

**Expected Behavior:**
- ✅ Can view admin dashboard (`/rbac/admin-dashboard`)
- ✅ Sees all 35 documents
- ✅ Can view all user roles (`/rbac/user-roles`)
- ✅ Can view complete audit logs (`/rbac/audit-logs`)
- ✅ Can classify documents
- ✅ Can assign documents to users
- ✅ Dashboard shows:
  - Total Documents: 35
  - Various queue states
  - Document counts by status

### Test 2: Reviewer Access (Restricted)

**Login:** reviewer1@docgen.ai / password123

**Expected Behavior:**
- ✅ Can view review queue (`/rbac/review-queue`)
- ✅ Sees ONLY 7 documents assigned to them
- ❌ Cannot see documents assigned to other reviewers
- ❌ Cannot access admin dashboard
- ❌ Cannot access user role management
- ❌ Cannot view complete audit logs
- ✅ Can claim documents assigned to them
- ✅ Can approve/reject claimed documents
- ✅ Can only see PUBLIC documents (not PRIVATE unless assigned)

**File Names Visible:**
- All documents show `original_filename` in table
- Example: "annual_report_2025.pdf"

### Test 3: Teacher Access (Enhanced)

**Login:** teacher1@docgen.ai / password123

**Expected Behavior:**
- ✅ Can view review queue
- ✅ Sees documents in teacher queue (5 documents)
- ✅ Can see BOTH PUBLIC and PRIVATE documents
- ✅ Can claim and review teacher-assigned documents
- ❌ Cannot access admin dashboard
- ❌ Cannot access user role management
- ✅ More permissions than reviewers

### Test 4: Queue Filtering

**As Reviewer 1:**
```
GET /api/review-queue
```

**Expected Response:**
```json
{
  "status": "success",
  "queue": [
    {
      "id": "...",
      "original_filename": "document_001.pdf",
      "title": "Annual Report 2025",
      "classification": "PUBLIC",
      "document_status": "IN_REVIEW",
      "assigned_to": "reviewer1_id",
      "claimed_by": "reviewer1_id",
      "current_queue": "in_review"
    }
  ],
  "pagination": {...}
}
```

Only shows documents where `assigned_to == current_user_id`

### Test 5: Audit Log Verification

**As Admin:**

View audit logs at `/rbac/audit-logs`

**Filter by Action Type:**
- DOCUMENT_ASSIGNED: Shows all assignments and reassignments
- CLASSIFY_DOCUMENT: Shows classification actions
- APPROVE_DOCUMENT: Shows approvals
- REJECT_DOCUMENT: Shows rejections

**Filter by User:**
- Select "reviewer1@docgen.ai"
- Should show only actions performed by Reviewer 1

**Verify Reassignment Trail:**
1. Find a reassigned document
2. Check audit logs for that document
3. Should see:
   - Initial assignment
   - Approval by first reviewer
   - Reassignment to second reviewer
   - Complete history with timestamps

### Test 6: Document Workflow

**Complete Workflow Test:**

1. **As Admin:**
   - Upload new document
   - Classify as PUBLIC
   - Verify audit log entry

2. **As Admin:**
   - Assign document to Reviewer 1
   - Verify document appears in Reviewer 1's queue
   - Verify NOT visible to Reviewer 2

3. **As Reviewer 1:**
   - Claim document
   - Verify status changes to IN_REVIEW
   - Approve document
   - Verify status changes to REVIEWED_APPROVED

4. **As Admin:**
   - Reassign to Reviewer 2
   - Verify document moves to Reviewer 2's queue
   - Verify audit log shows reassignment

5. **Verify Audit Trail:**
   - All actions logged
   - Timestamps correct
   - Previous/new states captured

---

## Dashboard Metrics Validation

### Expected Admin Dashboard Metrics

After running simulation:

| Metric | Expected Value | Calculation |
|--------|---------------|-------------|
| **Total Documents** | 35 | All documents |
| **Classification Pending** | 0 | All classified |
| **Classified** | 35 | All documents classified |
| **OCR Processed** | 35 | All processed |
| **In Review** | Varies | Documents currently being reviewed |
| **Approved** | ~27 | Approved minus reassigned/rejected |
| **Rejected** | 3 | Documents sent back |
| **Pending** | 0 | All moved past upload stage |
| **Average Review Time** | Calculated | Time from claim to review |

---

## RBAC Permission Matrix

| Feature | Admin | Teacher | Reviewer |
|---------|-------|---------|----------|
| View Dashboard | ✅ | ❌ | ❌ |
| View All Documents | ✅ | ❌ | ❌ |
| View Assigned Documents | ✅ | ✅ | ✅ |
| Classify Documents | ✅ | ❌ | ❌ |
| Assign Documents | ✅ | ❌ | ❌ |
| Claim Documents | ✅ | ✅ | ✅ |
| Approve Documents | ✅ | ✅ | ✅ |
| Reject Documents | ✅ | ✅ | ✅ |
| View PUBLIC Documents | ✅ | ✅ | ✅ (only assigned) |
| View PRIVATE Documents | ✅ | ✅ | ❌ (unless assigned) |
| Manage Users | ✅ | ❌ | ❌ |
| View Complete Audit Logs | ✅ | ❌ | ❌ |
| View Own Audit Logs | ✅ | ✅ | ✅ |

---

## Troubleshooting

### No Documents Showing

**Problem:** Review queue is empty

**Solutions:**
1. Check user is logged in correctly
2. Verify documents are assigned to user
3. Run simulation script again
4. Check MongoDB connection

### File Names Not Showing

**Problem:** Filename column blank in review queue

**Solutions:**
1. Verify documents have `original_filename` field
2. Check frontend is using correct field name
3. Ensure backend queries `images` collection (not `ocr_results`)

### Permission Denied Errors

**Problem:** User gets 403 Forbidden

**Solutions:**
1. Check user has correct role assigned
2. Verify JWT token is valid
3. Check role permissions in database
4. Ensure decorators are applied correctly on backend routes

### Audit Logs Not Recording

**Problem:** Audit log viewer is empty

**Solutions:**
1. Check all action types use constants (e.g., `AuditLog.ACTION_*`)
2. Verify MongoDB `audit_logs` collection exists
3. Check audit log creation doesn't have errors
4. Ensure audit log entries have correct structure

---

## Advanced Scenarios

### Scenario 1: Workload Balancing

**Objective:** Demonstrate reassignment for workload balancing

**Steps:**
1. Login as Admin
2. View current reviewer assignments
3. Identify reviewer with most documents
4. Reassign 2-3 documents to reviewer with fewer documents
5. Verify audit logs show reassignment details
6. Verify documents move to new reviewer's queue

### Scenario 2: Quality Control

**Objective:** Demonstrate rejection and correction workflow

**Steps:**
1. Login as Reviewer 1
2. Review a document
3. Identify quality issues
4. Reject document with reason
5. Verify document status changes to REJECTED
6. Verify document is unclaimed
7. Admin can then reassign or reprocess

### Scenario 3: Private Document Handling

**Objective:** Verify PRIVATE document access restrictions

**Steps:**
1. Login as Reviewer 1
2. Try to view PRIVATE documents not assigned to them
3. Should get permission denied or not see them
4. Login as Teacher 1
5. Should be able to see PRIVATE documents in teacher queue
6. Verify access control working correctly

---

## Data Cleanup

### Remove Simulation Data

```python
# In MongoDB shell or Python
from app.models import mongo

# Delete workflow users
mongo.db.users.delete_many({
    'email': {'$regex': '(reviewer|teacher|admin)@docgen.ai'}
})

# Delete workflow project and documents
project = mongo.db.projects.find_one({'name': 'Workflow Test Project'})
if project:
    mongo.db.images.delete_many({'project_id': project['_id']})
    mongo.db.projects.delete_one({'_id': project['_id']})

# Clear audit logs
mongo.db.audit_logs.delete_many({})
```

Or simply run the script again - it clears existing data automatically.

---

## API Endpoints Used

### Dashboard
```
GET /api/dashboard/overview
```

### Review Queue
```
GET /api/review-queue?page=1&per_page=10
```

### Document Operations
```
POST /api/review/<doc_id>/claim
POST /api/review/<doc_id>/approve
POST /api/review/<doc_id>/reject
POST /api/documents/<doc_id>/classify
POST /api/documents/<doc_id>/assign
```

### User Management
```
GET /api/users
GET /api/users/<user_id>/roles
POST /api/users/<user_id>/roles
```

### Audit Logs
```
GET /api/audit-logs?page=1&per_page=50
GET /api/audit-logs?action_type=DOCUMENT_ASSIGNED
GET /api/audit-logs?user_id=<user_id>
GET /api/audit-logs/document/<doc_id>
```

---

## Summary

This workflow simulation creates a complete, realistic RBAC system test environment with:

- ✅ 8 users across 3 roles
- ✅ 35 documents with complete metadata
- ✅ Multiple queue transitions
- ✅ Assignment and reassignment workflows
- ✅ Approval and rejection flows
- ✅ 150+ audit log entries
- ✅ Complete role-based access control
- ✅ Realistic timestamps and workflow timing

The simulation demonstrates:
- Role-based document access
- Queue-based workflow management
- Assignment and ownership tracking
- Audit trail completeness
- Permission enforcement
- Multi-stage approval process

Use this data to validate UI components, test RBAC enforcement, and demonstrate system capabilities.

---

**Version:** 1.0
**Last Updated:** February 2, 2026
**Script:** `seed_workflow_simulation.py`
