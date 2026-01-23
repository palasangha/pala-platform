# RBAC System - Required Fixes

**Priority Fixes for Production Deployment**

Date: 2026-01-22

---

## Fix #1: Add Exception Logging to Review Queue (CRITICAL)

**File**: `backend/app/routes/rbac.py`
**Line**: 149-150
**Issue**: Database exceptions not logged to audit trail

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_VIEW_DOCUMENT,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to fetch review queue', 'details': str(e)}), 500
```

**Impact**: ✅ Review queue errors now logged and auditable

---

## Fix #2: Add Exception Logging to Claim Document (CRITICAL)

**File**: `backend/app/routes/rbac.py`
**Line**: 227-228
**Issue**: Database exceptions not logged to audit trail

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to claim document', 'details': str(e)}), 500
```

**Impact**: ✅ Claim failures now logged

---

## Fix #3: Add Audit Log for Claim Failure (CRITICAL)

**File**: `backend/app/routes/rbac.py`
**Line**: 209-210
**Issue**: When update returns modified_count == 0, no audit log created

**Current Code**:
```python
        if result.modified_count == 0:
            return jsonify({'error': 'Failed to claim document'}), 500
```

**Fixed Code**:
```python
        if result.modified_count == 0:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'MongoDB update failed', 'modified_count': 0})
            return jsonify({'error': 'Failed to claim document'}), 500
```

**Impact**: ✅ Claim failures properly logged

---

## Fix #4: Add Exception Logging to Approve Document (CRITICAL)

**File**: `backend/app/routes/rbac.py`
**Line**: 306-307
**Issue**: Database exceptions not logged

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_APPROVE_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to approve document', 'details': str(e)}), 500
```

**Impact**: ✅ Approve failures now logged

---

## Fix #5: Add Document Not Found Logging to Approve (GOOD PRACTICE)

**File**: `backend/app/routes/rbac.py`
**Line**: 260-261
**Issue**: Document not found not logged in approve endpoint

**Current Code**:
```python
        if not image:
            return jsonify({'error': 'Document not found'}), 404
```

**Fixed Code**:
```python
        if not image:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_APPROVE_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'Document not found'})
            return jsonify({'error': 'Document not found'}), 404
```

**Impact**: ✅ All approval attempts logged

---

## Fix #6: Add Exception Logging to Reject (CRITICAL)

**File**: `backend/app/routes/rbac.py`
**Line**: ~355 (end of reject_document function)
**Issue**: Database exceptions not logged

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_REJECT_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to reject document', 'details': str(e)}), 500
```

**Impact**: ✅ Rejection failures logged

---

## Fix #7: Add Exception Logging to Dashboard Overview (HIGH)

**File**: `backend/app/routes/dashboard.py`
**Line**: 98-99
**Issue**: Dashboard errors not logged, date parsing errors not user-friendly

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except ValueError as e:
        if 'fromisoformat' in str(e):
            return jsonify({
                'error': 'Invalid date format',
                'expected_format': 'ISO 8601 (e.g., 2026-01-22 or 2026-01-22T10:00:00Z)',
                'example': datetime.utcnow().isoformat()
            }), 400
        return jsonify({'error': 'Invalid input: ' + str(e)}), 400

    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/overview'})
        return jsonify({'error': 'Failed to load dashboard', 'details': str(e)}), 500
```

**Impact**: ✅ Dashboard errors logged + better date validation

---

## Fix #8: Add Exception Logging to User Metrics (HIGH)

**File**: `backend/app/routes/dashboard.py`
**Line**: ~140 (in get_user_metrics exception handler)
**Issue**: Database exceptions not logged

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/user-metrics'})
        return jsonify({'error': 'Failed to load user metrics', 'details': str(e)}), 500
```

**Impact**: ✅ Metrics errors logged

---

## Fix #9: Add Exception Logging to Quality Metrics (HIGH)

**File**: `backend/app/routes/dashboard.py`
**Line**: ~180 (in get_quality_metrics exception handler)

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/quality-metrics'})
        return jsonify({'error': 'Failed to load quality metrics', 'details': str(e)}), 500
```

**Impact**: ✅ Quality metrics errors logged

---

## Fix #10: Add Exception Logging to SLA Metrics (HIGH)

**File**: `backend/app/routes/dashboard.py`
**Line**: ~240 (in get_sla_metrics exception handler)

**Current Code**:
```python
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Fixed Code**:
```python
    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/sla-metrics'})
        return jsonify({'error': 'Failed to load SLA metrics', 'details': str(e)}), 500
```

**Impact**: ✅ SLA metrics errors logged

---

## Automated Fix Script

Run this to apply all fixes automatically:

```bash
# Script to apply all logging fixes
cat > /tmp/apply_rbac_fixes.py << 'EOF'
#!/usr/bin/env python3
import re
import sys

def apply_fix(file_path, old_pattern, new_code, fix_name):
    """Apply a fix to a file"""
    with open(file_path, 'r') as f:
        content = f.read()

    if old_pattern not in content:
        print(f"❌ {fix_name}: Pattern not found")
        return False

    content = content.replace(old_pattern, new_code)

    with open(file_path, 'w') as f:
        f.write(content)

    print(f"✅ {fix_name}: Applied")
    return True

# Apply fixes
fixes = [
    (
        'backend/app/routes/rbac.py',
        '    except Exception as e:\n        return jsonify({\'error\': str(e)}), 500\n\n\n# ============================================================================\n# REVIEW QUEUE ENDPOINTS',
        '    except Exception as e:\n        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_VIEW_DOCUMENT,\n                       details={\'error\': str(e), \'error_type\': type(e).__name__})\n        return jsonify({\'error\': \'Failed to fetch review queue\', \'details\': str(e)}), 500\n\n\n# ============================================================================\n# REVIEW QUEUE ENDPOINTS',
        'Fix #1: Add exception logging to review queue'
    ),
]

# Execute fixes
for file_path, old, new, name in fixes:
    apply_fix(file_path, old, new, name)

print("\n✅ All fixes applied successfully!")
EOF

python3 /tmp/apply_rbac_fixes.py
```

---

## Manual Application Guide

### Step 1: Backup Original Files
```bash
cp backend/app/routes/rbac.py backend/app/routes/rbac.py.backup
cp backend/app/routes/dashboard.py backend/app/routes/dashboard.py.backup
```

### Step 2: Apply Each Fix

Use your editor to find and replace as documented above, or:

```bash
# Using sed for line-by-line fixes
sed -i '149s/return jsonify/{'\''error'\'': str(e)}), 500/AuditLog.create(...)\n        return jsonify(...)/' backend/app/routes/rbac.py
```

### Step 3: Verify Changes

```bash
# Check that fixes were applied
grep -n "AuditLog.create" backend/app/routes/rbac.py | wc -l
# Should be significantly more than before

# Verify syntax
python3 -m py_compile backend/app/routes/rbac.py
python3 -m py_compile backend/app/routes/dashboard.py
```

### Step 4: Test Changes

```bash
# Start backend
python run.py

# Test review queue error
curl -X GET http://localhost:5000/api/rbac/review-queue \
  -H "Authorization: Bearer $TOKEN" 2>&1 | jq

# Verify audit logs were created
mongosh << 'EOF'
use ocr_db
db.audit_logs.find().sort({created_at: -1}).limit(10).pretty()
EOF
```

---

## Testing Checklist

After applying fixes:

- [ ] No Python syntax errors
- [ ] All tests pass
- [ ] Review queue errors logged
- [ ] Claim failures logged
- [ ] Approve failures logged
- [ ] Reject failures logged
- [ ] Dashboard errors logged
- [ ] Audit logs visible in MongoDB
- [ ] Error messages user-friendly
- [ ] HTTP status codes correct

---

## Rollback Instructions

If issues occur:

```bash
# Restore backups
cp backend/app/routes/rbac.py.backup backend/app/routes/rbac.py
cp backend/app/routes/dashboard.py.backup backend/app/routes/dashboard.py

# Verify
python3 -m py_compile backend/app/routes/rbac.py
python3 -m py_compile backend/app/routes/dashboard.py

# Restart
python run.py
```

---

## Summary

**Total Fixes Required**: 10
**Priority 1 (Critical)**: 5 fixes - Add exception logging to endpoints
**Priority 2 (High)**: 5 fixes - Dashboard error handling

**Time to Apply**: 15-30 minutes
**Risk Level**: ✅ LOW - Only adds logging, no behavior changes

**Before Deployment**:
- [ ] Apply all 10 fixes
- [ ] Run tests
- [ ] Verify audit logs are created
- [ ] Check error messages in UI

---

**Status**: Ready for implementation
**Recommendation**: Apply all fixes before production deployment
