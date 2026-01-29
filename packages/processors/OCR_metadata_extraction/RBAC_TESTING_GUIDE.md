# RBAC Testing Guide - Sample Data & Test Scenarios

## Overview
Complete test environment created with 10 sample documents, multiple users with different roles, and various document statuses to test the entire RBAC workflow.

---

## 📊 Sample Data Created

### Users (10 Total)

#### Admins (1)
- **admin@example.com** / admin123

#### Reviewers (4)
- **reviewer1@example.com** / reviewer123 (Alice Johnson)
- **reviewer2@example.com** / reviewer123 (Bob Smith)  
- **reviewer3@example.com** / reviewer123 (Carol Davis)
- **reviewer@example.com** / reviewer123 (Reviewer User)

#### Teachers (4)
- **teacher1@example.com** / teacher123 (David Brown)
- **teacher2@example.com** / teacher123 (Emma Wilson)
- **teacher3@example.com** / teacher123 (Frank Miller)
- **teacher@example.com** / teacher123 (Teacher User)

#### Your Account (1)
- **bhushan0508@gmail.com** (reviewer role)

---

### Documents (10 Total)

| # | Document Name | Status | Classification | Assigned To |
|---|---------------|--------|----------------|-------------|
| 1 | Letter_Gandhi_to_Nehru_1947.pdf | **Pending** | Private | Not assigned |
| 2 | Discourse_Vipassana_Course_1970.pdf | **In Review** | Public | Assigned to reviewer |
| 3 | Letter_Student_Request_1965.pdf | **Approved** | Public | Reviewed & approved |
| 4 | Workshop_Buddhism_Hinduism_1994.pdf | **Rejected** | Public | Reviewed & rejected |
| 5 | Personal_Letter_Family_1968.pdf | **Pending** | Private | Not assigned |
| 6 | Course_Schedule_Mumbai_1971.pdf | **In Review** | Public | Assigned to reviewer |
| 7 | Teacher_Instructions_Private_1969.pdf | **Approved** | Private | Reviewed & approved |
| 8 | Thank_You_Letter_Student_1972.pdf | **Pending** | Public | Not assigned |
| 9 | Land_Donation_Agreement_1976.pdf | **In Review** | Private | Assigned to reviewer |
| 10 | Dhamma_Newsletter_1975.pdf | **Approved** | Public | Reviewed & approved |

#### Status Distribution
- **Pending**: 3 documents (ready for assignment)
- **In Review**: 3 documents (assigned to reviewers)
- **Approved**: 3 documents (completed reviews)
- **Rejected**: 1 document (rejected with notes)

---

## 🧪 Test Scenarios

### Scenario 1: Teacher Assigns Document to Reviewer

**Login as:** teacher1@example.com / teacher123

**Steps:**
1. Navigate to document queue/dashboard
2. View pending documents (should see 3 pending)
3. Select "Letter_Gandhi_to_Nehru_1947.pdf"
4. Click "Assign to Reviewer"
5. Choose reviewer1@example.com from dropdown
6. Confirm assignment

**Expected Result:**
- Document status changes to "In Review"
- Document appears in reviewer1's queue
- Audit log entry created
- Teacher can view private documents (Gandhi letter is private)

---

### Scenario 2: Reviewer Claims and Reviews Document

**Login as:** reviewer1@example.com / reviewer123

**Steps:**
1. View "My Assigned Documents" queue
2. Should see assigned documents
3. Open "Discourse_Vipassana_Course_1970.pdf"
4. Review the OCR text and metadata
5. Click "Approve" button
6. Add review notes: "Text quality excellent, metadata complete"
7. Submit review

**Expected Result:**
- Document status changes to "Approved"
- Document removed from reviewer's active queue
- Review timestamp and notes recorded
- Audit log entry created

---

### Scenario 3: Reviewer Rejects Document

**Login as:** reviewer2@example.com / reviewer123

**Steps:**
1. View assigned documents
2. Open "Course_Schedule_Mumbai_1971.pdf"
3. Click "Reject" button
4. Select reason: "Poor OCR Quality"
5. Add notes: "Multiple words unreadable, needs re-processing"
6. Submit rejection

**Expected Result:**
- Document status changes to "Rejected"
- Rejection reason and notes saved
- Document available for reassignment/reprocessing
- Audit log entry created

---

### Scenario 4: Teacher Views Private Documents

**Login as:** teacher2@example.com / teacher123

**Steps:**
1. Navigate to document queue
2. Filter by classification: "Private"
3. Should see private documents:
   - Letter_Gandhi_to_Nehru_1947.pdf
   - Personal_Letter_Family_1968.pdf
   - Teacher_Instructions_Private_1969.pdf
   - Land_Donation_Agreement_1976.pdf

**Expected Result:**
- Teacher can view all 4 private documents
- Can assign private documents to reviewers

---

### Scenario 5: Reviewer Cannot See Unassigned Private Docs

**Login as:** reviewer3@example.com / reviewer123

**Steps:**
1. Navigate to document queue
2. Filter by classification: "Private"
3. View available documents

**Expected Result:**
- Reviewer should NOT see unassigned private documents
- Can only see private documents explicitly assigned to them
- "Land_Donation_Agreement_1976.pdf" visible if assigned to reviewer3

---

### Scenario 6: Admin Views All Documents and Audit Logs

**Login as:** admin@example.com / admin123

**Steps:**
1. Navigate to admin dashboard
2. View all documents (public + private, all statuses)
3. Navigate to audit logs
4. Filter by action type: "document_assigned"
5. Filter by user: reviewer1@example.com
6. View detailed audit trail

**Expected Result:**
- Admin sees all 10 documents regardless of status/classification
- Audit logs show all assignment and review actions
- Can see who assigned, who reviewed, timestamps
- Can export audit logs

---

### Scenario 7: Bulk Assignment by Teacher

**Login as:** teacher3@example.com / teacher123

**Steps:**
1. Navigate to pending documents
2. Select multiple documents:
   - Thank_You_Letter_Student_1972.pdf
   - Personal_Letter_Family_1968.pdf
3. Click "Bulk Assign"
4. Choose reviewer3@example.com
5. Confirm assignment

**Expected Result:**
- Both documents assigned to reviewer3
- Status changes to "In Review" for both
- 2 audit log entries created
- reviewer3 sees both in their queue

---

### Scenario 8: Reviewer Views Own Statistics

**Login as:** reviewer1@example.com / reviewer123

**Steps:**
1. Navigate to "My Statistics" or dashboard
2. View metrics:
   - Total documents assigned
   - Documents approved
   - Documents rejected
   - Average review time
   - Pending reviews

**Expected Result:**
- See personal review statistics
- Charts/graphs showing review activity
- Cannot see other reviewers' stats

---

### Scenario 9: Admin Manages User Roles

**Login as:** admin@example.com / admin123

**Steps:**
1. Navigate to "User Management"
2. Find user: reviewer1@example.com
3. Click "Edit Roles"
4. Add "teacher" role (reviewer can now have both roles)
5. Save changes
6. Logout and login as reviewer1@example.com
7. Check permissions

**Expected Result:**
- reviewer1 now has both reviewer and teacher permissions
- Can view private documents
- Can assign documents to other reviewers
- Audit log shows role change by admin

---

### Scenario 10: Cross-Role Permission Validation

**Test as different users:**

**Teacher tries to approve document:**
- Login as teacher1@example.com
- Try to access approve/reject buttons on assigned documents
- **Expected:** Buttons not visible or action blocked

**Reviewer tries to assign document:**
- Login as reviewer2@example.com
- Try to assign pending document to another reviewer
- **Expected:** Assignment option not available

**Admin performs any action:**
- Login as admin@example.com
- Can assign, review, approve, reject, manage users
- **Expected:** All actions permitted

---

## 📋 Verification Checklist

### Document Status Workflow
- [ ] Pending → In Review (via assignment)
- [ ] In Review → Approved (via review)
- [ ] In Review → Rejected (via review)
- [ ] Rejected → Pending (via reassignment)

### Role Permissions
- [ ] Admin can see all documents
- [ ] Teacher can see all documents (public + private)
- [ ] Teacher can assign documents
- [ ] Reviewer can only see assigned documents
- [ ] Reviewer can approve/reject assigned documents
- [ ] Reviewer cannot see unassigned private documents

### Audit Logging
- [ ] Document assignment logged
- [ ] Document approval logged
- [ ] Document rejection logged
- [ ] User role changes logged
- [ ] All logs include user ID, timestamp, IP address

### UI/UX Elements
- [ ] Status badges display correctly
- [ ] Assignment dropdowns populated with reviewers
- [ ] Review notes textarea functional
- [ ] Rejection reason dropdown available
- [ ] Private documents marked with lock icon
- [ ] Notifications sent on assignment

---

## 🔍 Query Samples for Verification

### Check Document Status Distribution
```javascript
db.ocr_results.aggregate([
  { $group: { _id: "$review_status", count: { $sum: 1 } } }
])
```

### View Audit Logs
```javascript
db.audit_logs.find({}).sort({ timestamp: -1 }).limit(10)
```

### Check User Roles
```javascript
db.users.find({}, { email: 1, name: 1, roles: 1 })
```

### Find Documents Assigned to Specific Reviewer
```javascript
db.ocr_results.find({ 
  assigned_to: "<reviewer_user_id>",
  review_status: "in_review"
})
```

### Get Reviewer Statistics
```javascript
db.ocr_results.aggregate([
  { $match: { reviewed_by: "<reviewer_user_id>" } },
  { $group: { 
      _id: "$review_status", 
      count: { $sum: 1 } 
  }}
])
```

---

## 🐛 Known Issues to Test

1. **Private Document Visibility**
   - Ensure reviewers cannot query/access unassigned private docs via API

2. **Concurrent Assignments**
   - Test if two teachers can assign same document simultaneously

3. **Role Changes Mid-Review**
   - Test what happens if reviewer's role removed while document assigned

4. **Bulk Actions**
   - Test bulk assignment/approval performance

---

## 📝 Test Results Template

| Scenario | User | Expected | Actual | Pass/Fail | Notes |
|----------|------|----------|--------|-----------|-------|
| 1 | teacher1 | Document assigned | | | |
| 2 | reviewer1 | Document approved | | | |
| 3 | reviewer2 | Document rejected | | | |
| ... | | | | | |

---

**Created:** 2026-01-26
**Last Updated:** 2026-01-26
**Version:** 1.0
