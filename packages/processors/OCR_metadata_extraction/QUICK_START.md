# RBAC System Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide gets you up and running with the RBAC workflow simulation immediately.

---

## Prerequisites

```bash
# Ensure you're in the backend directory
cd /mnt/sda1/mango1_home/pala-platform/packages/processors/OCR_metadata_extraction/backend

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

---

## Option 1: Simple Test Data (Recommended for Quick Testing)

Use the basic seed script for quick validation:

```bash
python3 seed_rbac_data.py
```

**What you get:**
- 4 test users (1 admin, 2 reviewers, 1 teacher)
- 53 documents across all statuses
- 40+ audit logs
- Simple, focused test data

**Use when:**
- Quick testing of dashboard
- Validating fixes
- Checking basic RBAC functionality

---

## Option 2: Full Workflow Simulation (Recommended for Demo)

Use the comprehensive workflow script for realistic demo:

```bash
python3 seed_workflow_simulation.py
```

**What you get:**
- 8 users (1 admin, 5 reviewers, 2 teachers)
- 35 documents with complete workflow
- Queue transitions and reassignments
- 150+ audit logs with full history
- Realistic document flow simulation

**Use when:**
- Demonstrating RBAC to stakeholders
- Testing complete workflows
- Validating queue management
- Testing reassignment logic

---

## Test Credentials

### Option 1 (seed_rbac_data.py)

```
Admin:     test.admin@docgen.ai       / admin123
Reviewer:  test.reviewer1@docgen.ai   / reviewer123
Reviewer:  test.reviewer2@docgen.ai   / reviewer123
Teacher:   test.teacher@docgen.ai     / teacher123
```

### Option 2 (seed_workflow_simulation.py)

```
Admin:      admin@docgen.ai       / password123
Reviewer 1: reviewer1@docgen.ai  / password123
Reviewer 2: reviewer2@docgen.ai  / password123
Reviewer 3: reviewer3@docgen.ai  / password123
Reviewer 4: reviewer4@docgen.ai  / password123
Reviewer 5: reviewer5@docgen.ai  / password123
Teacher 1:  teacher1@docgen.ai   / password123
Teacher 2:  teacher2@docgen.ai   / password123
```

---

## Quick Test Checklist

### ✅ Step 1: Run Seed Script

```bash
cd backend
python3 seed_workflow_simulation.py  # or seed_rbac_data.py
```

Wait for success message.

### ✅ Step 2: Test Admin Dashboard

1. Login: `admin@docgen.ai` / `password123`
2. Navigate to: `/rbac/admin-dashboard`
3. **Verify:**
   - Total Documents shows a number > 0
   - In Review shows count
   - Approved shows count
   - Rejected shows count
   - Pending shows count
   - Average Review Time shows value (not 0)

**Expected (workflow simulation):**
- Total Documents: **35**
- Various counts for different statuses
- Progress bar visible
- Bottleneck alert may appear

### ✅ Step 3: Test Review Queue

1. Login: `reviewer1@docgen.ai` / `password123`
2. Navigate to: `/rbac/review-queue`
3. **Verify:**
   - **File names visible** in table (e.g., "annual_report_2025.pdf")
   - Classification badges show (PUBLIC/PRIVATE)
   - Status badges show
   - See only documents assigned to reviewer1
   - Claim/Approve/Reject buttons work

**Expected (workflow simulation):**
- Shows **7 documents** assigned to reviewer1
- All with original filenames visible

### ✅ Step 4: Test Audit Logs

1. Login: `admin@docgen.ai` / `password123`
2. Navigate to: `/rbac/audit-logs`
3. **Verify:**
   - Audit logs display without errors
   - Action types show correctly:
     - USER_LOGIN
     - CLASSIFY_DOCUMENT
     - CLAIM_DOCUMENT
     - APPROVE_DOCUMENT
     - REJECT_DOCUMENT
     - DOCUMENT_ASSIGNED
     - ROLES_UPDATED
   - Filter by action type works
   - Filter by user works
   - Pagination works

**Expected (workflow simulation):**
- Total audit logs: **150+**
- All action types present
- No "undefined" or error messages

### ✅ Step 5: Test RBAC Restrictions

**Test as Reviewer:**
1. Login: `reviewer1@docgen.ai` / `password123`
2. Try to access: `/rbac/admin-dashboard`
3. **Expected:** Should get permission denied or redirect

**Test as Teacher:**
1. Login: `teacher1@docgen.ai` / `password123`
2. Navigate to: `/rbac/review-queue`
3. **Expected:**
   - Can see BOTH PUBLIC and PRIVATE documents
   - Shows 5 documents assigned to teacher1
   - More access than reviewers

---

## Common Issues & Fixes

### Issue 1: "No module named 'pymongo'"

**Problem:** Dependencies not installed

**Fix:**
```bash
cd backend
pip install -r requirements.txt
```

### Issue 2: "Connection refused" or MongoDB errors

**Problem:** MongoDB not running

**Fix:**
```bash
# Check if MongoDB is running
# Start MongoDB service (method depends on your setup)
# Update .env file with correct MONGO_URI
```

### Issue 3: Dashboard shows all zeros

**Problem:** Seed script didn't run successfully

**Fix:**
```bash
# Re-run seed script
cd backend
python3 seed_workflow_simulation.py

# Check for errors in output
# Verify success message appears
```

### Issue 4: File names not showing

**Problem:** This should be fixed now, but if still occurs:

**Fix:**
- Verify backend queries `images` collection (not `ocr_results`)
- Check frontend uses `doc.original_filename`
- Re-run seed script to create proper data

### Issue 5: Audit logs show errors

**Problem:** Action type constants not defined (should be fixed)

**Fix:**
- Verify `audit_log.py` has all action type constants
- Verify routes use `AuditLog.ACTION_*` constants
- Re-run seed script

---

## File Locations

### Scripts
```
backend/seed_rbac_data.py           - Simple test data
backend/seed_workflow_simulation.py - Full workflow simulation
```

### Documentation
```
RBAC_FIX_SUMMARY.md           - Complete fix documentation
WORKFLOW_SIMULATION_GUIDE.md  - Workflow simulation details
QUICK_START.md                - This file
```

### Modified Backend Files
```
backend/app/models/audit_log.py    - Added action type constants
backend/app/routes/rbac.py         - Fixed collection references, audit logs
backend/app/routes/dashboard.py    - Added metrics, fixed audit logs
```

### Modified Frontend Files
```
frontend/src/components/RBAC/AdminDashboard.tsx - Fixed data access
```

---

## API Testing (Optional)

### Test Dashboard API

```bash
# Get access token first (login via UI or API)
# Then test dashboard endpoint

curl -X GET http://localhost:5000/api/dashboard/overview \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected Response:**
```json
{
  "status": "success",
  "total_documents": 35,
  "in_review": 6,
  "approved": 12,
  "rejected": 3,
  "pending": 8,
  "average_review_time": 45.5,
  "overview": { ... },
  "status_breakdown": { ... },
  "bottleneck": { ... }
}
```

### Test Review Queue API

```bash
curl -X GET http://localhost:5000/api/review-queue \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Expected Response:**
```json
{
  "status": "success",
  "queue": [
    {
      "id": "...",
      "original_filename": "annual_report_2025.pdf",
      "title": "Annual Report 2025",
      "classification": "PUBLIC",
      "document_status": "IN_REVIEW",
      ...
    }
  ],
  "pagination": { ... }
}
```

---

## Next Steps

After validating the system works:

1. **Customize Test Data:**
   - Modify seed scripts to match your needs
   - Adjust document counts
   - Change user roles

2. **Test Workflows:**
   - Upload new documents
   - Classify documents
   - Assign to reviewers
   - Claim and review
   - Approve/reject
   - Verify audit trail

3. **Test Edge Cases:**
   - Try reassigning documents
   - Test rejection workflow
   - Verify permission boundaries
   - Check private document access

4. **Deploy to Production:**
   - Once validated, deploy fixes
   - Run migration if needed
   - Test with real users
   - Monitor audit logs

---

## Support

### Check Logs

**Backend Logs:**
```bash
# Run Flask app in debug mode
cd backend
python3 run.py

# Check console output for errors
```

**Frontend Logs:**
```bash
# Open browser DevTools (F12)
# Check Console tab for errors
# Check Network tab for API responses
```

### Database Inspection

**MongoDB:**
```bash
# Connect to MongoDB
mongo

# Use your database
use your_database_name

# Count documents
db.images.count()
db.users.count()
db.audit_logs.count()

# Check a sample document
db.images.findOne()

# Check review queue documents
db.images.find({ review_status: 'in_review' }).count()
```

### Common Checks

```bash
# Check if documents exist
db.images.count({ original_filename: { $exists: true } })

# Check if audit logs have valid action types
db.audit_logs.distinct('action_type')

# Check user roles
db.users.find({}, { email: 1, roles: 1 })
```

---

## Summary

**Quick Start:**
1. `cd backend`
2. `python3 seed_workflow_simulation.py`
3. Login as `admin@docgen.ai` / `password123`
4. Test dashboard, review queue, audit logs
5. Verify file names, metrics, RBAC

**All Fixed:**
- ✅ Dashboard data rendering
- ✅ Review queue file names
- ✅ Audit log action types
- ✅ RBAC permissions
- ✅ Complete test data

**Ready for:**
- Demo to stakeholders
- Production deployment
- Real workflow testing
- User acceptance testing

---

**Need Help?**
- Check `RBAC_FIX_SUMMARY.md` for detailed fixes
- Check `WORKFLOW_SIMULATION_GUIDE.md` for workflow details
- Review seed script output for errors
- Inspect browser console and network tab

---

**Version:** 1.0
**Last Updated:** February 2, 2026
