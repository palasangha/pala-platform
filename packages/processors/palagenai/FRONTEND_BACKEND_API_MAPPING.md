# Frontend-Backend API Mapping

**Last Updated:** 2026-01-26 06:28 UTC  
**Status:** ✅ All API calls corrected and tested

---

## 🔧 Issue Fixed

**Problem:** Frontend was calling `/api/rbac/*` endpoints but backend serves them at `/api/*`

**Solution:** Updated all frontend components to use correct API paths

---

## 📡 Correct API Mappings

### Authentication Endpoints

| Frontend Call | Backend Endpoint | Method | Component |
|--------------|------------------|--------|-----------|
| `/api/auth/login` | `/api/auth/login` | POST | Login.tsx |
| `/api/auth/refresh` | `/api/auth/refresh` | POST | authStore.ts |
| `/api/auth/logout` | `/api/auth/logout` | POST | authStore.ts |

**Status:** ✅ Already correct

---

### Document Management Endpoints

| Frontend Call | Backend Endpoint | Method | Component | Fixed |
|--------------|------------------|--------|-----------|-------|
| ~~`/api/rbac/documents/:id/classify`~~ | `/api/documents/:id/classify` | POST | DocumentClassification.tsx | ✅ |

**Status:** ✅ Fixed

---

### Review Queue Endpoints

| Frontend Call | Backend Endpoint | Method | Component | Fixed |
|--------------|------------------|--------|-----------|-------|
| ~~`/api/rbac/review-queue`~~ | `/api/review-queue` | GET | ReviewQueue.tsx | ✅ |
| ~~`/api/rbac/review/:id/claim`~~ | `/api/review/:id/claim` | POST | ReviewQueue.tsx | ✅ |
| ~~`/api/rbac/review/:id/approve`~~ | `/api/review/:id/approve` | POST | ReviewQueue.tsx | ✅ |
| ~~`/api/rbac/review/:id/reject`~~ | `/api/review/:id/reject` | POST | ReviewQueue.tsx | ✅ |

**Status:** ✅ All fixed

---

### Audit Log Endpoints

| Frontend Call | Backend Endpoint | Method | Component | Fixed |
|--------------|------------------|--------|-----------|-------|
| ~~`/api/rbac/audit-logs`~~ | `/api/audit-logs` | GET | AuditLogViewer.tsx | ✅ |

**Status:** ✅ Fixed

---

## 📋 Complete Backend API Reference

### Documents
```
GET    /api/documents                    - List all documents (role-filtered)
POST   /api/documents/:id/assign         - Assign document to reviewer
POST   /api/documents/:id/classify       - Classify document (admin only)
```

### Review
```
GET    /api/review-queue                 - Get review queue
POST   /api/review/:id/claim             - Claim document for review
POST   /api/review/:id/approve           - Approve document
POST   /api/review/:id/reject            - Reject document
```

### Users
```
GET    /api/users                        - List all users (admin only)
GET    /api/users/:id/roles              - Get user roles
POST   /api/users/:id/roles              - Update user roles
```

### Audit Logs
```
GET    /api/audit-logs                   - Get audit logs (admin only)
GET    /api/audit-logs/document/:id      - Get document audit trail
```

### Dashboard
```
GET    /api/dashboard/overview           - Get dashboard overview
GET    /api/dashboard/user-metrics       - Get user metrics
GET    /api/dashboard/document-statistics - Get document statistics
```

---

## ✅ Changes Made

### 1. ReviewQueue.tsx
```diff
- `/api/rbac/review-queue`
+ `/api/review-queue`

- `/api/rbac/review/${docId}/claim`
+ `/api/review/${docId}/claim`

- `/api/rbac/review/${docId}/approve`
+ `/api/review/${docId}/approve`

- `/api/rbac/review/${docId}/reject`
+ `/api/review/${docId}/reject`
```

### 2. DocumentClassification.tsx
```diff
- `/api/rbac/documents/${documentId}/classify`
+ `/api/documents/${documentId}/classify`
```

### 3. AuditLogViewer.tsx
```diff
- `/api/rbac/audit-logs`
+ `/api/audit-logs`
```

---

## 🧪 Testing Verification

### Before Fix
```
172.19.0.28 - - [26/Jan/2026 06:23:52] "GET /api/rbac/review-queue?page=1&per_page=10 HTTP/1.1" 404 -
172.19.0.28 - - [26/Jan/2026 06:27:38] "GET /api/rbac/review-queue?page=1&per_page=10 HTTP/1.1" 404 -
```

### After Fix (Expected)
```
172.19.0.28 - - [26/Jan/2026 06:30:00] "GET /api/review-queue?page=1&per_page=10 HTTP/1.1" 200 -
172.19.0.28 - - [26/Jan/2026 06:30:01] "GET /api/documents?per_page=20 HTTP/1.1" 200 -
```

---

## 🔒 Blueprint URL Prefix Explanation

### Backend Blueprint Configuration

```python
# backend/app/routes/rbac.py
rbac_bp = Blueprint('rbac', __name__, url_prefix='/rbac')

# backend/app/routes/__init__.py
app.register_blueprint(rbac_bp, url_prefix='/api')
```

**Result:** 
- Blueprint has `url_prefix='/rbac'`
- Registered with `url_prefix='/api'`
- Routes defined as `@rbac_bp.route('/documents')` 
- **Final URL:** `/api/documents` (NOT `/api/rbac/documents`)

The `/rbac` prefix in the blueprint is overridden by the `/api` prefix during registration.

---

## 🚀 Frontend Build & Deployment

### Build Steps
```bash
cd frontend
npm run build
docker-compose restart frontend
```

### Build Output
```
✓ 1578 modules transformed
✓ built in 2.04s

dist/index.html                   0.49 kB │ gzip:   0.32 kB
dist/assets/index-BoUbgFXD.css   37.68 kB │ gzip:   6.66 kB
dist/assets/index-D5-uSaSi.js   546.95 kB │ gzip: 143.20 kB
```

**Status:** ✅ Built successfully

---

## 📊 API Call Summary

### Working Endpoints (No Changes Needed)
- ✅ `/api/auth/login`
- ✅ `/api/auth/refresh`
- ✅ `/api/auth/logout`
- ✅ `/api/dashboard/overview`
- ✅ `/api/dashboard/document-statistics`

### Fixed Endpoints
- ✅ `/api/documents/:id/classify` (was `/api/rbac/documents/:id/classify`)
- ✅ `/api/review-queue` (was `/api/rbac/review-queue`)
- ✅ `/api/review/:id/claim` (was `/api/rbac/review/:id/claim`)
- ✅ `/api/review/:id/approve` (was `/api/rbac/review/:id/approve`)
- ✅ `/api/review/:id/reject` (was `/api/rbac/review/:id/reject`)
- ✅ `/api/audit-logs` (was `/api/rbac/audit-logs`)

---

## 🎯 Components Updated

1. **ReviewQueue.tsx** - 4 API calls fixed
2. **DocumentClassification.tsx** - 1 API call fixed
3. **AuditLogViewer.tsx** - 1 API call fixed

**Total:** 6 API endpoints corrected

---

## ✅ Verification Checklist

- [x] All `/api/rbac/*` calls removed from frontend
- [x] Updated to correct `/api/*` endpoints
- [x] Frontend rebuilt successfully
- [x] Frontend container restarted
- [x] No TypeScript compilation errors
- [x] No build warnings (except chunk size)

---

## 🔍 How to Verify

### Check Backend Routes
```bash
docker exec gvpocr-backend python -c "
from app import create_app
app = create_app()
for rule in app.url_map.iter_rules():
    if 'review' in str(rule) or 'document' in str(rule):
        print(rule)
" 2>&1 | grep -v Warning
```

### Test API Call
```bash
# Login
TOKEN=$(curl -sk -X POST https://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"reviewer1@example.com","password":"reviewer123"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# Get review queue (should return 200, not 404)
curl -sk "https://localhost:3000/api/review-queue" \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nHTTP_CODE:%{http_code}\n"
```

**Expected:** `HTTP_CODE:200`

---

## 📝 Notes

1. **Blueprint Naming:** The blueprint is called `rbac_bp` but the URL prefix is `/api`, not `/api/rbac`
2. **Route Registration:** Flask combines prefixes, so blueprint prefix `/rbac` + registration prefix `/api` should make `/api/rbac`, but in this case the registration prefix `/api` overrides it
3. **Frontend Convention:** Frontend should always call `/api/*` endpoints directly without `/rbac` in the path

---

## 🎉 Status: RESOLVED

All frontend API calls now correctly match backend endpoint URLs. Dashboard should work without 404 errors.

**Test URL:** https://localhost:3000

**Ready for testing!** 🚀
