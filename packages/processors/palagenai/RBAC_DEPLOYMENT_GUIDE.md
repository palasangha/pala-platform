# RBAC System Deployment Guide

**Complete Integration and Deployment Instructions for the RBAC System**

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Backend Integration Steps](#backend-integration-steps)
3. [Database Migration](#database-migration)
4. [Frontend Integration Steps](#frontend-integration-steps)
5. [Configuration Updates](#configuration-updates)
6. [Testing & Verification](#testing--verification)
7. [Troubleshooting](#troubleshooting)
8. [Post-Deployment](#post-deployment)

---

## Pre-Deployment Checklist

- [ ] MongoDB running and accessible
- [ ] Backend Flask server configured
- [ ] Frontend build environment set up
- [ ] All dependencies installed
- [ ] Backup of existing database created
- [ ] Git repository backed up
- [ ] Python 3.8+ installed on backend
- [ ] Node.js 14+ installed on frontend

---

## Backend Integration Steps

### Step 1: Copy New Model Files

```bash
# Navigate to backend directory
cd packages/processors/OCR_metadata_extraction/backend/app/models

# Verify new files are in place
ls -la *.py | grep -E "(role|audit_log)"
```

**New files should be present**:
- `role.py`
- `audit_log.py`

### Step 2: Verify Model Extensions

```bash
# Check that user.py and image.py have been modified
grep -n "roles" app/models/user.py        # Should show roles field
grep -n "classification" app/models/image.py  # Should show classification field
```

### Step 3: Update Routes

```bash
# Navigate to routes directory
cd ../routes

# Verify new route files
ls -la *.py | grep -E "(rbac|dashboard)"
```

**New files should be present**:
- `rbac.py`
- `dashboard.py`

### Step 4: Verify Route Registration

```bash
# Check __init__.py for blueprint registration
grep -n "rbac_bp\|dashboard_bp" __init__.py
```

**Expected output**: Should show imports and registration for both blueprints.

### Step 5: Update Decorators

```bash
# Verify decorators.py has RBAC decorators
grep -n "@require_role\|@require_permission\|@require_admin" utils/decorators.py
```

**Expected output**: Should find all three decorators defined.

### Step 6: Install/Update Dependencies

```bash
cd backend

# Make sure requirements are up to date
pip install -r requirements.txt

# Key packages should include:
# - flask
# - flask-pymongo
# - pyjwt
# - werkzeug
```

### Step 7: Test Backend Import

```bash
# Test that all models import correctly
python3 << 'EOF'
from app.models import User, Role, AuditLog
from app.models.image import Image
from app.utils.decorators import require_role, require_permission, require_admin

print("✓ All models imported successfully")
print("✓ All decorators imported successfully")
EOF
```

---

## Database Migration

### Step 1: Prepare for Migration

```bash
# Create backup of existing database
mongodump --uri "mongodb://localhost:27017/ocr_db" --out ./mongo_backup

# Verify backup was created
ls -lah ./mongo_backup
```

### Step 2: Run Migration

```bash
cd backend/migrations

# Run the migration
python3 -c "
from pymongo import MongoClient
import sys
sys.path.insert(0, '..')

# Import migration
from migrations.001_add_rbac_fields import upgrade
from app.models import mongo
from app import create_app

# Create app context
app = create_app()
with app.app_context():
    from app.models import mongo
    upgrade(mongo)
    print('✓ Migration completed successfully')
"
```

### Step 3: Verify Migration

```bash
# Connect to MongoDB and verify collections
mongosh << 'EOF'
use ocr_db

// Check roles collection
print("Roles collection:")
db.roles.find().forEach(doc => {
  print("  - " + doc.name + ": " + doc.permissions.length + " permissions")
})

// Check user fields
print("\nUsers with roles:")
db.users.find({roles: {$exists: true}}).limit(3).forEach(doc => {
  print("  - " + doc.email + ": " + doc.roles.join(", "))
})

// Check image fields
print("\nImages with RBAC fields:")
print("  Sample: " + db.images.findOne({classification: {$exists: true}}).original_filename)

// Check audit logs collection
print("\nAudit logs collection:")
print("  Status: " + (db.audit_logs.exists() ? "EXISTS" : "MISSING"))

print("\n✓ Migration verified")
EOF
```

---

## Frontend Integration Steps

### Step 1: Copy Frontend Components

```bash
cd frontend/src/components

# Create RBAC components directory if needed
mkdir -p RBAC

# Copy new component files
ls -la RBAC/
# Should contain:
# - ReviewQueue.tsx
# - DocumentClassification.tsx
# - AdminDashboard.tsx
# - AuditLogViewer.tsx
```

### Step 2: Update Auth Store

```bash
# Verify authStore is present
cat stores/authStore.ts | grep -i "roles\|user"

# Should have user type with roles field
```

### Step 3: Update API Service

```bash
# Verify API base URL is configured
grep -n "REACT_APP_API_URL" services/api.ts

# Or check .env file
cat .env | grep API_URL
```

**Expected format**:
```
REACT_APP_API_URL=http://localhost:5000/api
```

### Step 4: Create Routes (if needed)

```bash
# Check if routing setup includes RBAC pages
grep -n "ReviewQueue\|AdminDashboard" pages/*.tsx

# If not found, add to main routing configuration
```

### Step 5: Install Dependencies

```bash
npm install

# Verify key packages
npm list @chakra-ui/react axios react-router-dom zustand
```

### Step 6: Build Frontend

```bash
# Test build
npm run build

# Should complete without errors
```

---

## Configuration Updates

### Backend Configuration

```python
# Ensure config.py has necessary settings:

# JWT Configuration
JWT_SECRET_KEY = 'your-secret-key'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# MongoDB Configuration
MONGO_URI = 'mongodb://localhost:27017/ocr_db'

# CORS Configuration (allow frontend)
CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
```

### Frontend Configuration

```typescript
// .env file
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_APP_NAME=OCR System
REACT_APP_ENV=development
```

### Docker Configuration (if applicable)

```yaml
# docker-compose.yml - Add/Update services
services:
  backend:
    environment:
      FLASK_ENV: production
      MONGO_URI: mongodb://mongodb:27017/ocr_db
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}

  mongodb:
    image: mongo:5.0
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"

  frontend:
    build: ./frontend
    environment:
      REACT_APP_API_URL: http://backend:5000/api
    ports:
      - "3000:3000"
```

---

## Testing & Verification

### Test 1: Backend Route Access

```bash
# Start backend server
cd backend
python run.py

# In another terminal, test RBAC endpoints
curl -X GET http://localhost:5000/api/rbac/review-queue \
  -H "Authorization: Bearer <token>"
```

### Test 2: Create Test Data

```python
# Create test admin user
python3 << 'EOF'
from app import create_app
from app.models.user import User
from app.models.role import Role
from app.models import mongo
from datetime import datetime

app = create_app()
with app.app_context():
    # Initialize roles
    Role.initialize_default_roles(mongo)
    print("✓ Default roles initialized")

    # Create test admin
    admin = User.create(
        mongo,
        email='admin@test.com',
        password='admin123',
        name='Test Admin',
        roles=['admin']
    )
    print(f"✓ Admin user created: {admin['_id']}")

    # Create test reviewer
    reviewer = User.create(
        mongo,
        email='reviewer@test.com',
        password='reviewer123',
        name='Test Reviewer',
        roles=['reviewer']
    )
    print(f"✓ Reviewer user created: {reviewer['_id']}")

    # Create test teacher
    teacher = User.create(
        mongo,
        email='teacher@test.com',
        password='teacher123',
        name='Test Teacher',
        roles=['teacher']
    )
    print(f"✓ Teacher user created: {teacher['_id']}")
EOF
```

### Test 3: Test Authentication

```bash
# Login as admin
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }'

# Should return tokens
```

### Test 4: Test RBAC Enforcement

```bash
# Get token from login response above

# Try to classify document (Admin only)
curl -X POST http://localhost:5000/api/rbac/documents/<doc_id>/classify \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "classification": "PUBLIC",
    "reason": "Test classification"
  }'

# Should succeed for admin

# Try with reviewer token
# Should return 403 Forbidden
```

### Test 5: Test Review Queue Filtering

```bash
# Login as reviewer
# Get review queue
curl -X GET http://localhost:5000/api/rbac/review-queue \
  -H "Authorization: Bearer <reviewer_token>"

# Should return only PUBLIC documents

# Login as teacher
# Should return both PUBLIC and PRIVATE documents
```

### Test 6: Frontend Component Testing

```bash
# Start frontend dev server
cd frontend
npm start

# Navigate to http://localhost:3000

# Test each component:
# 1. Review Queue (/review-queue)
# 2. Admin Dashboard (/admin/dashboard)
# 3. Audit Logs (/admin/audit-logs)
# 4. Document Classification (within document view)
```

---

## Troubleshooting

### Issue: Migration fails with "Collection already exists"

```bash
# Solution: Drop existing collection and re-run
mongosh << 'EOF'
use ocr_db
db.audit_logs.drop()
EOF

# Then re-run migration
```

### Issue: Import errors after adding new models

```bash
# Solution: Clear Python cache
find backend -type d -name __pycache__ -exec rm -rf {} +
pip cache purge

# Reinstall
pip install -r requirements.txt
```

### Issue: CORS errors in frontend

```bash
# Solution: Update CORS configuration in backend
# In config.py, ensure frontend URL is in CORS_ORIGINS

CORS_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'https://yourdomain.com'  # for production
]
```

### Issue: JWT token issues

```bash
# Solution: Verify JWT secret is consistent
# Check backend config
echo $JWT_SECRET_KEY

# Should be set in environment
export JWT_SECRET_KEY='your-secret-key'
```

### Issue: MongoDB connection errors

```bash
# Solution: Verify MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# Should return { ok: 1 }
```

---

## Post-Deployment

### Step 1: Run Integration Tests

```bash
# Full test suite
cd backend
pytest tests/ -v

# Key test files to verify:
# - tests/test_rbac.py
# - tests/test_authorization.py
# - tests/test_audit_logs.py
```

### Step 2: Monitor Logs

```bash
# Frontend logs
npm run build  # Check for build warnings

# Backend logs
python run.py 2>&1 | tee backend.log

# MongoDB logs
mongosh --eval "db.currentOp()"
```

### Step 3: Verify Audit Logging

```bash
# Check audit logs are being recorded
mongosh << 'EOF'
use ocr_db
db.audit_logs.find().sort({created_at: -1}).limit(5).pretty()
EOF
```

### Step 4: Performance Baseline

```bash
# Document response times
# Classification endpoint should respond < 200ms
# Review queue should respond < 500ms
# Dashboard should respond < 1000ms

# Monitor with
ab -n 100 -c 10 http://localhost:5000/api/dashboard/overview
```

### Step 5: Security Audit

- [ ] All sensitive endpoints require authentication
- [ ] Role checks are enforced
- [ ] Unauthorized access is logged
- [ ] Data isolation works correctly
- [ ] Audit trail is immutable

### Step 6: Documentation Updates

```bash
# Update project README with:
# - RBAC system overview
# - User roles and permissions
# - API endpoint documentation
# - Setup instructions
```

---

## Deployment to Production

### Pre-Production Checklist

- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance baseline established
- [ ] Disaster recovery plan in place
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] SSL/TLS certificates configured

### Production Environment Setup

```bash
# 1. Set environment variables
export FLASK_ENV=production
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/ocr_db
export CORS_ORIGINS="https://yourdomain.com"

# 2. Build frontend
cd frontend
npm run build

# 3. Start with production server (gunicorn)
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# 4. Serve frontend (nginx/apache)
# Configure reverse proxy to backend
```

### Monitoring Setup

```yaml
# prometheus.yml - Add RBAC metrics
scrape_configs:
  - job_name: 'ocr_api'
    static_configs:
      - targets: ['localhost:5000']

# Alert on:
# - Authorization failures > 10/min
# - Database errors
# - API response time > 1000ms
# - Audit log growth anomalies
```

### Rollback Plan

```bash
# If issues occur:

# 1. Restore from backup
mongorestore --uri "mongodb://localhost:27017" ./mongo_backup

# 2. Rollback code
git revert <commit-hash>

# 3. Restart services
docker-compose restart

# 4. Verify system health
curl http://localhost:5000/health
```

---

## Verification Checklist

After deployment, verify:

- [ ] Admin can classify documents
- [ ] Reviewers see only PUBLIC documents
- [ ] Teachers see PUBLIC and PRIVATE documents
- [ ] Review queue filters work correctly
- [ ] Document approval/rejection workflow functions
- [ ] Audit logs record all actions
- [ ] Dashboard shows correct metrics
- [ ] Authorization decorators enforce access
- [ ] Unauthorized access is denied and logged
- [ ] Performance is acceptable (< 1s for most operations)
- [ ] No database errors in logs
- [ ] All components load without errors

---

## Success Indicators

RBAC system is successfully deployed when:

✓ Users can log in with roles
✓ Role-based permissions are enforced
✓ Documents are correctly classified
✓ Review workflow functions end-to-end
✓ Audit trail captures all actions
✓ Dashboard shows real-time metrics
✓ All API endpoints respond correctly
✓ Zero security vulnerabilities detected
✓ Performance meets requirements
✓ All tests passing

---

## Support & Documentation

For detailed information see:
- `RBAC_INTEGRATION_SUMMARY.md` - System architecture
- `API_QUICK_REFERENCE.md` - Complete API documentation
- Backend route files: `app/routes/rbac.py`, `app/routes/dashboard.py`
- Frontend components: `frontend/src/components/RBAC/`

---

## Summary

The RBAC system deployment is complete when:

1. ✓ All new models and routes integrated
2. ✓ Database migration applied
3. ✓ Frontend components deployed
4. ✓ All tests passing
5. ✓ Monitoring active
6. ✓ Documentation complete

**Estimated deployment time**: 2-4 hours (depending on environment complexity)

**Support contacts**:
- Backend issues: See `backend/` directory
- Frontend issues: See `frontend/` directory
- Database issues: MongoDB documentation

---

Last Updated: 2026-01-22
Version: 1.0.0
Status: Ready for Deployment
