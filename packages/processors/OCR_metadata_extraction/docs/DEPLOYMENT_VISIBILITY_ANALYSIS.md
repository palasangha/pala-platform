# Deployment Visibility Analysis & Troubleshooting Guide

**Date**: December 30, 2024
**Issue**: Deployments not showing in Supervisor Window
**Status**: Diagnosed & Ready for Testing

---

## Executive Summary

The supervisor dashboard retrieves deployments through a **user-filtered query** that requires deployments to have the logged-in user's ID. This is working as designed, but deployments may not appear if:

1. **User ID Mismatch** ← MOST LIKELY
2. **No Deployments Exist**
3. **Deployments in Error State**
4. **API Response Parsing Issue**

---

## How Deployment Visibility Works

### Flow Diagram

```
Browser (SupervisorDashboard.tsx)
    ↓ GET /api/supervisor/deployments
API Route (supervisor.py:69-92)
    ↓ WorkerDeployment.find_by_user(mongo, current_user_id)
MongoDB Query
    Filter: {'user_id': ObjectId(current_user_id)}
    Sort: {'created_at': -1}
    Limit: 50 records
    ↓ Return results
Response (to_dict format)
    ↓ Frontend displays
Browser Table
```

### Key Code Locations

| Component | File | Function |
|-----------|------|----------|
| **Frontend Query** | `frontend/src/pages/SupervisorDashboard.tsx:68` | `loadDeployments()` → calls `supervisorAPI.getDeployments()` |
| **API Client** | `frontend/src/services/supervisorService.ts:26-28` | `getDeployments()` → sends `GET /api/supervisor/deployments` |
| **Backend Route** | `backend/app/routes/supervisor.py:69-92` | `get_deployments(current_user_id)` |
| **Database Query** | `backend/app/models/worker_deployment.py:128-143` | `find_by_user(mongo, user_id, skip, limit)` |
| **Data Format** | `backend/app/models/worker_deployment.py:333-383` | `to_dict(deployment)` - converts MongoDB doc to JSON |

---

## Root Cause Analysis

### 🔴 Primary Issue: User ID Filter

```python
# From worker_deployment.py:128-143
@staticmethod
def find_by_user(mongo, user_id, skip=0, limit=50):
    return list(mongo.db.worker_deployments.find(
        {'user_id': ObjectId(user_id)}  # ← CRITICAL FILTER
    ).sort('created_at', -1).skip(skip).limit(limit))
```

**This means:**
- ✅ Deployments owned by **current user** WILL show
- ❌ Deployments owned by **different user** WILL NOT show
- ❌ Deployments with **missing user_id** WILL NOT show

### When Deployments Disappear

Deployments show initially but disappear when:

1. **User logs out then in with different account**
   - Each user only sees their own deployments

2. **Deployment creation failed silently**
   - Background async deployment task failed
   - Database save failed
   - Check status field (should be 'running', not stuck in 'deploying')

3. **API response parsing fails**
   - Frontend expects `response.deployments` array
   - If response format wrong, nothing displays

---

## Diagnostic Checklist

### ✅ Step 1: Verify Deployments Exist

Check if the API actually returns deployments:

**Command:**
```bash
# From your machine with curl
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5000/api/supervisor/deployments | python3 -m json.tool
```

**Expected Response:**
```json
{
  "success": true,
  "deployments": [
    {
      "id": "...",
      "worker_name": "...",
      "host": "...",
      "status": "running"
    }
  ],
  "count": 1
}
```

### ✅ Step 2: Check Browser DevTools

1. Open Chrome/Firefox DevTools (F12)
2. Go to **Network** tab
3. Refresh supervisor dashboard
4. Look for request to `/api/supervisor/deployments`
5. Click it and check **Response** tab

**Good Response:**
- Status: 200
- Body contains `"deployments": [...]` array

**Bad Response:**
- Status: 500 → Backend error
- Status: 401 → Authentication failed
- Status: 200 but empty array → User has no deployments

### ✅ Step 3: Check Backend Logs

```bash
# View Flask logs
docker-compose logs backend | grep -i deployment | tail -20

# Look for these patterns:
# "Created deployment record:"          # Creation succeeded
# "Started background deployment"        # Background task started
# "Deployment successful"                # Should see status=running
# "Deployment failed:"                   # Error occurred
# "Error fetching deployments:"          # API error
```

### ✅ Step 4: Check MongoDB Directly

```bash
# Connect to MongoDB container
docker-compose exec -T mongodb mongosh gvpocr -u gvpocr_admin -p

# List all deployments (no filter)
db.worker_deployments.find().pretty()

# Count deployments by user
db.worker_deployments.aggregate([
  {$group: {_id: "$user_id", count: {$sum: 1}}}
])

# See your current user ID
db.users.findOne({email: "YOUR_EMAIL"})

# Check if deployments have that user_id
db.worker_deployments.find({"user_id": ObjectId("YOUR_USER_ID")}).pretty()
```

### ✅ Step 5: Check Deployment Creation

When you create a new deployment, check the flow:

1. **Frontend**: Shows confirmation message
2. **Backend**: Starts async thread with `_deploy_worker_async()`
3. **Database**: Records created with status='deploying'
4. **Status Update**: Should change to 'running' after ~30 seconds
5. **Refresh**: Dashboard auto-refreshes every 5 seconds (line 119)

---

## Common Issues & Solutions

### Issue 1: Empty Deployments List (0 deployments)

**Symptoms:**
- No deployments show in table
- API returns empty array
- Users say "nothing ever appears"

**Diagnosis:**
```bash
# Check total deployments
docker-compose exec -T mongodb mongosh gvpocr -u gvpocr_admin -p
db.worker_deployments.count()  # Should be > 0

# Check deployments for current user
db.worker_deployments.count({"user_id": ObjectId("USER_ID")})
```

**Solutions:**
1. **If count = 0**: No deployments exist at all
   - Create a new deployment through the UI
   - Check backend logs for creation errors

2. **If count > 0 but user count = 0**: User ID mismatch
   - Check which user created the deployments
   - Either log in as that user or re-create deployment

### Issue 2: Deployments Stuck in "Deploying" State

**Symptoms:**
- Deployments appear but status stays "deploying" forever
- Background task failed silently
- Status never changes to "running"

**Diagnosis:**
```bash
# Check logs for deployment errors
docker-compose logs backend | grep -i "deploy" | grep -i "error"

# Check if stuck in deploying
db.worker_deployments.count({"status": "deploying"})

# Check error messages
db.worker_deployments.find(
  {"status": "error"},
  {error_message: 1, worker_name: 1}
).pretty()
```

**Solutions:**
1. Check `error_message` field for reason
2. Delete failed deployment and retry
3. Check SSH keys are accessible
4. Verify remote host is reachable

### Issue 3: API Returns 500 Error

**Symptoms:**
- DevTools shows HTTP 500
- No deployments appear
- Backend error in logs

**Diagnosis:**
```bash
# Check Flask logs for exception
docker-compose logs backend | grep -A 10 "Error fetching deployments"

# Check MongoDB connection
docker-compose logs backend | grep -i "connection"

# Check for JSON serialization errors
docker-compose logs backend | grep -i "json"
```

**Solutions:**
1. Restart backend container
2. Check MongoDB is running: `docker-compose ps mongo`
3. Check JWT token is valid

### Issue 4: User ID Mismatch (Most Common)

**Symptoms:**
- Admin can see all deployments
- Regular user sees none
- Only works for user who created deployment

**Root Cause:**
```python
# This is the culprit:
deployment = WorkerDeployment.create(mongo, user_id, data)
# user_id is saved as the owner, so only that user sees it
```

**Solutions:**
1. **Option A**: Log in as the user who created the deployment
2. **Option B**: Remove user_id filter (not recommended)
3. **Option C**: Update all deployments to have correct user_id
   ```bash
   db.worker_deployments.updateMany(
     {},
     {$set: {user_id: ObjectId("ADMIN_USER_ID")}}
   )
   ```

---

## Frontend Auto-Refresh

The dashboard auto-refreshes every 5 seconds (if enabled):

```typescript
// From SupervisorDashboard.tsx:118-122
useEffect(() => {
  if (autoRefresh) {
    const interval = setInterval(loadDeployments, 5000);  // 5 second refresh
    return () => clearInterval(interval);
  }
}, [autoRefresh]);
```

So after creating a deployment:
1. Status = 'deploying' (immediate)
2. After ~5-30 sec = status changes to 'running'
3. Dashboard refreshes every 5 sec
4. You should see updated status automatically

---

## Testing Checklist

- [ ] Deployments exist in MongoDB
- [ ] Current user owns at least one deployment
- [ ] API endpoint returns HTTP 200
- [ ] Response JSON is valid
- [ ] Response contains `"deployments"` array
- [ ] Array has at least 1 object
- [ ] Each object has required fields (id, worker_name, status)
- [ ] Browser DevTools shows request/response correctly
- [ ] Backend logs show no errors
- [ ] Frontend auto-refresh enabled
- [ ] Try creating a new deployment and watch status change

---

## Quick Fix Script

If you want to manually assign deployments to current user:

```bash
# Get your user ID
USER_EMAIL="your.email@example.com"
USER_ID=$(docker-compose exec -T mongodb mongosh gvpocr -u gvpocr_admin -p --eval "db.users.findOne({email: '$USER_EMAIL'})._id")

# Assign all deployments to your user
docker-compose exec -T mongodb mongosh gvpocr -u gvpocr_admin -p --eval "
db.worker_deployments.updateMany(
  {},
  {\$set: {user_id: ObjectId('$USER_ID')}}
)"

# Verify
docker-compose exec -T mongodb mongosh gvpocr -u gvpocr_admin -p --eval "
db.worker_deployments.count({user_id: ObjectId('$USER_ID')})"
```

---

## Summary Table

| Scenario | Cause | Fix |
|----------|-------|-----|
| **No deployments at all** | None exist in DB | Create new deployment |
| **Deployments exist but don't show** | User ID mismatch | Log in as correct user or reassign |
| **Status stuck on "deploying"** | Async task failed | Check logs, delete and retry |
| **API returns 500** | Backend/MongoDB error | Restart services, check logs |
| **Only some users see deployments** | User isolation working | Each user sees only their deployments |
| **Deployments disappear after refresh** | API parsing issue | Check browser DevTools Network tab |

---

## Next Actions

1. **First**: Use Step 1-3 of Diagnostic Checklist above
2. **If deployments exist**: Check user ID match (Step 4)
3. **If no deployments**: Create one through UI and watch logs
4. **If stuck in "deploying"**: Check backend logs for async errors
5. **Still issues?**: Run the Quick Fix Script to reassign deployments

---

**Created:** December 30, 2024
**For:** GVPOCR Deployment Debugging
**Status:** Ready for User Testing
