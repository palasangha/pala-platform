# Dashboard Quick Start Guide

## ✅ Deployment Complete

**Date:** 2026-01-26  
**Status:** Frontend rebuilt and deployed with API fixes

---

## 🚀 Quick Start

### 1. Clear Browser Cache
**IMPORTANT:** Hard refresh to load new code
- **Mac:** `Cmd + Shift + R`
- **Windows/Linux:** `Ctrl + Shift + R`
- **Alternative:** Use incognito/private window

### 2. Login
URL: https://localhost:3000

### 3. Test Accounts

| Role | Email | Password | Access Level |
|------|-------|----------|--------------|
| Admin | admin@example.com | admin123 | Full access, all 50 docs |
| Teacher | teacher1@example.com | teacher123 | All docs, can assign |
| Reviewer | reviewer1@example.com | reviewer123 | Assigned docs only |

---

## 📱 Available Pages

### Admin Dashboard (`/rbac/admin-dashboard`)
**Purpose:** View statistics overview

**Shows:**
- Total documents: 50
- In review: 13
- Approved: 9
- Rejected: 1
- Pending: 27
- Average review time

**Note:** This is a **STATS page**, not a document list!

---

### Review Queue (`/rbac/review-queue`)
**Purpose:** Work with documents

**Shows:**
- Documents list (assigned or all, based on role)
- Claim button (for reviewers)
- Approve/Reject buttons
- Document details

**This is where you see the actual documents!**

---

### Audit Logs (`/rbac/audit-logs`)
**Access:** Admin only

**Shows:**
- All system actions
- User assignments
- Approval/rejection history
- Role changes

---

### User Management (`/rbac/user-roles`)
**Access:** Admin only

**Features:**
- List all users
- Change user roles
- View user activity

---

## 🔧 What Was Fixed

### API Endpoint Corrections
```diff
Before (404 errors):
- /api/rbac/review-queue
- /api/rbac/review/:id/claim
- /api/rbac/review/:id/approve
- /api/rbac/review/:id/reject
- /api/rbac/documents/:id/classify
- /api/rbac/audit-logs

After (working):
+ /api/review-queue
+ /api/review/:id/claim
+ /api/review/:id/approve
+ /api/review/:id/reject
+ /api/documents/:id/classify
+ /api/audit-logs
```

### Files Updated
1. `ReviewQueue.tsx` - 4 endpoints fixed
2. `DocumentClassification.tsx` - 1 endpoint fixed
3. `AuditLogViewer.tsx` - 1 endpoint fixed

### Deployment
1. Frontend code updated ✅
2. Docker image rebuilt ✅
3. Container restarted ✅
4. New bundle hash: `index-C--aNazw.js` ✅

---

## 🧪 How to Verify It's Working

### Check Browser Console (F12)
1. Open developer tools
2. Go to Network tab
3. Refresh page
4. Look for API calls

**Should see:**
```
✅ GET /api/review-queue → 200 OK
✅ GET /api/dashboard/overview → 200 OK
```

**Should NOT see:**
```
❌ GET /api/rbac/review-queue → 404 Not Found
```

### Check JavaScript Bundle
Look in Network tab for JavaScript file being loaded:

**Correct (new):**
```
✅ index-C--aNazw.js
```

**Old (needs cache clear):**
```
❌ index-D4BRdVNv.js
```

If loading old bundle → Hard refresh browser!

---

## 🐛 Troubleshooting

### "No documents visible in dashboard"

**Issue:** You're on Admin Dashboard page  
**Solution:** Go to "Review Queue" page instead

The Admin Dashboard shows **statistics**, not document list.  
The Review Queue shows **actual documents**.

---

### "Getting 404 errors"

**Issue:** Browser cache loading old code  
**Solution:**
1. Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Win)
2. Or clear browser cache completely
3. Or use incognito/private window

---

### "Review queue shows 0 documents"

**Possible reasons:**
1. **You're a reviewer** → Only shows docs assigned to you
   - Login as admin/teacher to see all docs
2. **No docs in review** → Try assigning some docs first
3. **Filter applied** → Check if there's a status filter active

**Current database:**
- 13 documents in "in_review" status
- 27 documents in "pending" status  
- 9 documents in "approved" status
- 1 document in "rejected" status

---

### "Still seeing errors after cache clear"

**Steps:**
1. Check browser console for exact error message
2. Copy the error or take screenshot
3. Check which API endpoint is being called
4. Verify Docker containers are running:
   ```bash
   docker ps | grep gvpocr
   ```

---

## 📊 Database Current State

```
Total Documents: 50
├── Pending: 27 (ready to be assigned)
├── In Review: 13 (assigned to reviewers)
├── Approved: 9 (completed)
└── Rejected: 1 (needs reprocessing)

Total Users: 10
├── Admin: 1
├── Teachers: 4
└── Reviewers: 5

Classifications:
├── Public: 30
└── Private: 20
```

---

## 🎯 Typical Workflow

### As Admin/Teacher:
1. Login → `/rbac/admin-dashboard`
2. View stats overview
3. Go to Review Queue → `/rbac/review-queue`
4. See all 13 in-review documents
5. Assign pending docs to reviewers
6. Monitor progress

### As Reviewer:
1. Login → `/rbac/review-queue`
2. See documents assigned to you
3. Click "Claim" to start review
4. Review document content
5. Approve or Reject with notes
6. Document moves to next status

---

## 📖 API Reference

See: `FRONTEND_BACKEND_API_MAPPING.md`

Quick reference:
- Documents: `GET /api/documents`
- Review Queue: `GET /api/review-queue`
- Approve: `POST /api/review/:id/approve`
- Reject: `POST /api/review/:id/reject`
- Dashboard: `GET /api/dashboard/overview`
- Audit Logs: `GET /api/audit-logs`

All endpoints tested and working ✅

---

## ✅ Checklist

Before testing:
- [ ] Docker containers running
- [ ] Frontend container rebuilt
- [ ] Browser cache cleared
- [ ] Using correct URL (https://localhost:3000)
- [ ] Correct login credentials

If errors appear:
- [ ] Check browser console (F12)
- [ ] Verify API endpoint (should be /api/*, not /api/rbac/*)
- [ ] Confirm JavaScript bundle is new (index-C--aNazw.js)
- [ ] Try incognito/private window

---

## 🎉 Ready to Use!

Everything is deployed and working. Just:
1. **Hard refresh browser** (most important!)
2. Login with any test account
3. Navigate to **Review Queue** to see documents
4. Admin Dashboard shows stats, Review Queue shows docs

**Questions?** Check the error in browser console and share the screenshot.

---

**Last Updated:** 2026-01-26 06:38 UTC  
**Status:** ✅ Production Ready
