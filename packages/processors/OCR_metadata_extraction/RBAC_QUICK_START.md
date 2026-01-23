# RBAC System - Quick Start Guide

**Fast track to using the RBAC system**

---

## For Backend Developers

### 1. Start Backend with RBAC

```bash
cd backend
pip install -r requirements.txt
python run.py
```

### 2. Run Database Migration

```bash
cd backend/migrations
python -c "
from pymongo import MongoClient
import sys
sys.path.insert(0, '..')

from migrations.001_add_rbac_fields import upgrade
from app.models import mongo
from app import create_app

app = create_app()
with app.app_context():
    from app.models import mongo
    upgrade(mongo)
"
```

### 3. Create Test Users

```bash
python3 << 'EOF'
from app import create_app
from app.models.user import User
from app.models.role import Role
from app.models import mongo

app = create_app()
with app.app_context():
    Role.initialize_default_roles(mongo)

    # Admin user
    admin = User.create(mongo, 'admin@test.com', 'admin123', name='Admin', roles=['admin'])
    print(f"Admin: {admin['_id']}")

    # Reviewer user
    reviewer = User.create(mongo, 'reviewer@test.com', 'reviewer123', name='Reviewer', roles=['reviewer'])
    print(f"Reviewer: {reviewer['_id']}")

    # Teacher user
    teacher = User.create(mongo, 'teacher@test.com', 'teacher123', name='Teacher', roles=['teacher'])
    print(f"Teacher: {teacher['_id']}")
EOF
```

### 4. Test RBAC Endpoints

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}' \
  | jq -r '.access_token')

# Get dashboard
curl http://localhost:5000/api/dashboard/overview \
  -H "Authorization: Bearer $TOKEN" | jq

# Get review queue
curl http://localhost:5000/api/rbac/review-queue \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## For Frontend Developers

### 1. Start Frontend Dev Server

```bash
cd frontend
npm install
npm start
```

### 2. Import Components

```typescript
import { ReviewQueue } from './components/RBAC/ReviewQueue';
import { AdminDashboard } from './components/RBAC/AdminDashboard';
import { DocumentClassification } from './components/RBAC/DocumentClassification';
import { AuditLogViewer } from './components/RBAC/AuditLogViewer';
```

### 3. Add Routes

```typescript
// pages/ReviewPage.tsx
import ReviewQueue from '../components/RBAC/ReviewQueue';

export default function ReviewPage() {
  return <ReviewQueue />;
}

// pages/AdminPage.tsx
import AdminDashboard from '../components/RBAC/AdminDashboard';

export default function AdminPage() {
  return <AdminDashboard />;
}

// pages/AuditPage.tsx
import AuditLogViewer from '../components/RBAC/AuditLogViewer';

export default function AuditPage() {
  return <AuditLogViewer />;
}
```

### 4. Use in Router

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ReviewPage from './pages/ReviewPage';
import AdminPage from './pages/AdminPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/review-queue" element={<ReviewPage />} />
        <Route path="/admin/dashboard" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## API Quick Reference

### Classification (Admin)
```bash
curl -X POST http://localhost:5000/api/rbac/documents/{doc_id}/classify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "classification": "PUBLIC",
    "reason": "Community review"
  }'
```

### Review Queue
```bash
curl http://localhost:5000/api/rbac/review-queue?page=1&per_page=10 \
  -H "Authorization: Bearer $TOKEN"
```

### Claim Document
```bash
curl -X POST http://localhost:5000/api/rbac/review/{doc_id}/claim \
  -H "Authorization: Bearer $TOKEN"
```

### Approve Document
```bash
curl -X POST http://localhost:5000/api/rbac/review/{doc_id}/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "edit_fields": {"author": "John Doe"},
    "notes": "Verified author"
  }'
```

### Dashboard
```bash
curl http://localhost:5000/api/dashboard/overview \
  -H "Authorization: Bearer $TOKEN"
```

### Audit Logs
```bash
curl "http://localhost:5000/api/rbac/audit-logs?page=1&action_type=CLASSIFY_DOCUMENT" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Role Permissions Matrix

| Action | Admin | Reviewer | Teacher |
|--------|-------|----------|---------|
| Classify Documents | ✅ | ❌ | ❌ |
| Run OCR | ✅ | ❌ | ❌ |
| View PUBLIC Queue | ✅ | ✅ | ✅ |
| View PRIVATE Queue | ✅ | ❌ | ✅ |
| Claim Document | ✅ | ✅ | ✅ |
| Approve Document | ✅ | ✅ | ✅ |
| Reject Document | ✅ | ✅ | ✅ |
| View Dashboard | ✅ | ❌ | ❌ |
| View Audit Logs | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |

---

## Common Tasks

### Create Admin User
```python
User.create(mongo, 'admin@company.com', 'password', roles=['admin'])
User.add_role(mongo, user_id, 'admin')
```

### Get User Roles
```python
roles = User.get_roles(mongo, user_id)
```

### Check Permission
```python
has_permission = Role.has_permission(mongo, 'admin', 'classify_document')
```

### Classify Document
```python
Image.classify(mongo, doc_id, 'PUBLIC', admin_user_id, 'Reason text')
```

### Query Audit Logs
```python
logs = AuditLog.find_by_action_type(mongo, 'CLASSIFY_DOCUMENT')
trail = AuditLog.find_by_resource(mongo, doc_id)
```

---

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Migration runs successfully
- [ ] Test users created
- [ ] Admin can classify documents
- [ ] Reviewer sees only PUBLIC documents
- [ ] Teacher sees PUBLIC + PRIVATE documents
- [ ] Review queue filters work
- [ ] Dashboard loads
- [ ] Audit logs recorded
- [ ] Frontend components render
- [ ] API calls succeed

---

## Environment Variables

```bash
# Backend
export FLASK_ENV=development
export MONGO_URI=mongodb://localhost:27017/ocr_db
export JWT_SECRET_KEY=your-secret-key
export CORS_ORIGINS=http://localhost:3000

# Frontend
export REACT_APP_API_URL=http://localhost:5000/api
export REACT_APP_ENV=development
```

---

## Troubleshooting

### Migration fails
```bash
# Check MongoDB connection
mongosh --eval "db.adminCommand('ping')"

# Drop existing collection
mongosh << 'EOF'
use ocr_db
db.audit_logs.drop()
EOF
```

### Roles not showing
```python
# Initialize roles
Role.initialize_default_roles(mongo)

# Verify
print(list(mongo.db.roles.find()))
```

### CORS errors
```python
# Update config.py
CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
```

### JWT errors
```bash
# Regenerate secret
export JWT_SECRET_KEY=$(openssl rand -hex 32)
```

---

## Next Steps

1. **Read**: `RBAC_INTEGRATION_SUMMARY.md` - System overview
2. **Deploy**: `RBAC_DEPLOYMENT_GUIDE.md` - Step-by-step deployment
3. **Reference**: `RBAC_FILE_MANIFEST.md` - File locations
4. **Test**: Run test suite and verify all checks pass
5. **Monitor**: Set up logging and monitoring

---

## Key Files

| File | Purpose |
|------|---------|
| `app/models/role.py` | Role system |
| `app/models/audit_log.py` | Audit trail |
| `app/routes/rbac.py` | RBAC endpoints |
| `app/routes/dashboard.py` | Dashboard endpoints |
| `app/utils/decorators.py` | Auth decorators |
| `components/RBAC/*.tsx` | Frontend components |
| `migrations/001_add_rbac_fields.py` | Database migration |

---

## Common Commands

```bash
# Start backend
python run.py

# Run frontend
npm start

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}'

# Check health
curl http://localhost:5000/health

# View database
mongosh ocr_db
```

---

**Ready to start? Follow these 3 easy steps:**

1. **Backend**: `python run.py`
2. **Frontend**: `npm start`
3. **Create users**: Run test user creation script

Then navigate to your frontend URL and login with test credentials!

---

**Questions?** See detailed guides:
- Backend: `RBAC_INTEGRATION_SUMMARY.md`
- Deployment: `RBAC_DEPLOYMENT_GUIDE.md`
- Files: `RBAC_FILE_MANIFEST.md`

