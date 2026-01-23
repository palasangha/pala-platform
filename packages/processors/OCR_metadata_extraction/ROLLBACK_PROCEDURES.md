# Rollback Procedures - Phase 1 Error Handling

**Purpose**: Quick recovery if Phase 1 deployment has issues
**Time to Execute**: 5-10 minutes
**Confidence**: High (changes are isolated to agent orchestrator)

---

## When to Rollback

### Immediate Rollback (Do Now)
```
1. Import errors / Module not found
2. Worker won't start (crashes on startup)
3. Completeness drops below 20% after 30 minutes
4. Processing time increases beyond 400+ seconds
5. All documents failing with same error
6. Cannot even run one test document successfully
```

### Wait Before Rollback (Monitor First)
```
1. Completeness below 50% but increasing
   → Wait 1-2 hours for stabilization
2. Some errors appearing
   → Monitor error types, check if expected
3. Processing time slightly higher
   → May be normal during ramp-up
4. Mixed success/failures
   → Expected during transition
```

---

## Quick Rollback (5 min)

### Option 1: File-Based Rollback

```bash
#!/bin/bash
# File: /usr/local/bin/rollback-phase1.sh

set -e

echo "🔄 Starting Phase 1 Rollback..."

# 1. Stop worker
echo "1. Stopping enrichment worker..."
docker stop gvpocr-enrichment-worker || true
sleep 5

# 2. Check backup exists
if [ ! -f enrichment_service/workers/agent_orchestrator.py.backup.* ]; then
    echo "❌ ERROR: No backup file found!"
    echo "   Checked: enrichment_service/workers/agent_orchestrator.py.backup.*"
    exit 1
fi

# 3. Restore backup
echo "2. Restoring backup..."
BACKUP_FILE=$(ls -t enrichment_service/workers/agent_orchestrator.py.backup.* | head -1)
cp "$BACKUP_FILE" enrichment_service/workers/agent_orchestrator.py
echo "   Restored from: $BACKUP_FILE"

# 4. Remove new files
echo "3. Removing new error handling modules..."
rm -rf enrichment_service/errors/
rm -f enrichment_service/config/timeouts.py
echo "   ✓ Removed enrichment_service/errors/"
echo "   ✓ Removed enrichment_service/config/timeouts.py"

# 5. Rebuild image
echo "4. Rebuilding Docker image..."
docker-compose build enrichment-worker
echo "   ✓ Build complete"

# 6. Start worker
echo "5. Starting enrichment worker..."
docker-compose up -d enrichment-worker
sleep 10

# 7. Verify
echo "6. Verifying rollback..."
if docker ps | grep -q gvpocr-enrichment-worker; then
    echo "   ✓ Worker started"
else
    echo "   ❌ Worker failed to start"
    exit 1
fi

# 8. Check logs
echo "7. Checking logs for errors..."
ERRORS=$(docker logs gvpocr-enrichment-worker 2>&1 | grep -i "error\|traceback" | head -5)
if [ -z "$ERRORS" ]; then
    echo "   ✓ No errors in startup logs"
else
    echo "   ⚠️ Errors detected:"
    echo "$ERRORS"
fi

echo ""
echo "✅ Rollback Complete!"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: docker logs -f gvpocr-enrichment-worker"
echo "  2. Test processing: Send a test document"
echo "  3. Check completeness: Should be back to ~27.8%"
echo "  4. Investigate: Why Phase 1 failed"
```

**Execute**:
```bash
chmod +x /usr/local/bin/rollback-phase1.sh
/usr/local/bin/rollback-phase1.sh
```

### Option 2: Manual Rollback (Step-by-Step)

```bash
# 1. Stop the worker
docker stop gvpocr-enrichment-worker
echo "✓ Worker stopped"

# 2. Verify backup exists
ls -la enrichment_service/workers/agent_orchestrator.py.backup.*
# Should see: agent_orchestrator.py.backup.20260121_HHMMSS

# 3. Restore the original file
cp enrichment_service/workers/agent_orchestrator.py.backup.20260121_HHMMSS \
   enrichment_service/workers/agent_orchestrator.py
echo "✓ Agent orchestrator restored"

# 4. Remove new modules
rm -rf enrichment_service/errors/
rm enrichment_service/config/timeouts.py
echo "✓ New modules removed"

# 5. Rebuild Docker image
cd /mnt/sda1/mango1_home/pala-platform/packages/processors/OCR_metadata_extraction
docker-compose build enrichment-worker
echo "✓ Docker image rebuilt"

# 6. Start worker
docker-compose up -d enrichment-worker
echo "✓ Worker started"

# 7. Wait and verify
sleep 10
docker ps | grep enrichment-worker
echo "✓ Verification complete"
```

---

## Verify Rollback Successful

### Check 1: No New Error Handling
```bash
# Old behavior: Should see fixed timeout
docker logs gvpocr-enrichment-worker | grep -i "timeout" | head -1
# Expected: "timeout=60" or similar (fixed value)

# Should NOT see adaptive timeout
docker logs gvpocr-enrichment-worker | grep "timeout:" | grep -v "60" || echo "✓ No adaptive timeouts found"

# Should NOT see error classification
docker logs gvpocr-enrichment-worker | grep "failed with" | head -1 || echo "✓ No error classification found"
```

### Check 2: Worker Is Running
```bash
# Verify container running
docker ps | grep gvpocr-enrichment-worker
# Should see the container listed

# Verify no startup errors
docker logs gvpocr-enrichment-worker | grep -i "error" | head -5 || echo "✓ No startup errors"
```

### Check 3: Processing Works
```bash
# Process a test document
# Monitor logs
docker logs -f gvpocr-enrichment-worker | grep "Starting enrichment" &

# Send test through API or queue
# Check for success

# Stop log monitoring
pkill -f "docker logs -f"
```

### Check 4: Completeness Back to Normal
```bash
# Query recent documents
mongosh mongodb://gvpocr_admin:PASSWORD@localhost:27017/gvpocr --eval "
use gvpocr
db.enriched_documents.aggregate([
  {\$match: {created_at: {\$gte: new Date(new Date().getTime() - 600000)}}},
  {\$group: {_id: null, avg: {\$avg: '\$quality_metrics.completeness_score'}}}
])
"

# Expected: ~27.8% (back to original)
# If still 60%+: Something didn't rollback properly
```

---

## Partial Rollback (Only Update Code)

If you want to keep the new code but revert the agent orchestrator:

```bash
# 1. Just restore the orchestrator
cp enrichment_service/workers/agent_orchestrator.py.backup.* \
   enrichment_service/workers/agent_orchestrator.py

# 2. Keep new modules (for potential use later)
# Don't delete enrichment_service/errors/
# Don't delete enrichment_service/config/timeouts.py

# 3. Rebuild and restart
docker-compose build enrichment-worker
docker-compose up -d enrichment-worker

# Result: Back to old behavior, but new code available for retry
```

---

## Full Rollback (Remove Everything)

If you want to completely remove Phase 1 changes:

```bash
# 1. Restore agent orchestrator
cp enrichment_service/workers/agent_orchestrator.py.backup.* \
   enrichment_service/workers/agent_orchestrator.py

# 2. Remove all new files
rm -rf enrichment_service/errors/
rm -f enrichment_service/config/timeouts.py
rm -f tests/test_error_handling.py

# 3. Remove documentation (optional)
rm -f PHASE1_IMPLEMENTATION.md
rm -f QUICK_REFERENCE.md
rm -f BEFORE_AFTER_COMPARISON.md
rm -f DEPLOYMENT_GUIDE.md
rm -f MONITORING_SETUP.md
rm -f ROLLBACK_PROCEDURES.md

# 4. Rebuild and restart
docker-compose build enrichment-worker
docker-compose up -d enrichment-worker

# Result: Complete rollback to pre-Phase1 state
```

---

## Rollback in Production (Safe Procedure)

### Step 1: Notify Team
```
Subject: ⚠️ Rolling back Phase 1 error handling
Impact: Enrichment service will pause for ~10 minutes
Reason: [Brief description of issue]
ETA: [Time to complete]
```

### Step 2: Prepare
```bash
# 1. Verify backup
ls -la enrichment_service/workers/agent_orchestrator.py.backup.*

# 2. Have rollback script ready
ls -la /usr/local/bin/rollback-phase1.sh

# 3. Have access to MongoDB (for verification)
# Test connection: mongosh mongodb://localhost:27017/gvpocr
```

### Step 3: Execute
```bash
# 1. Execute rollback script
/usr/local/bin/rollback-phase1.sh

# 2. Monitor logs
docker logs -f gvpocr-enrichment-worker &

# 3. Wait for stabilization (5 minutes)
sleep 300

# 4. Verify metrics
mongosh mongodb://localhost:27017/gvpocr --eval "
use gvpocr
db.enriched_documents.aggregate([
  {\$match: {created_at: {\$gte: new Date(new Date().getTime() - 600000)}}},
  {\$group: {_id: null, avg: {\$avg: '\$quality_metrics.completeness_score'}}}
])
"
```

### Step 4: Verify
```bash
# 1. Logs clean
docker logs gvpocr-enrichment-worker | grep -i error | wc -l
# Should be 0 or very low

# 2. Worker healthy
docker ps | grep gvpocr-enrichment-worker
# Should be running

# 3. Documents processing
mongosh mongodb://localhost:27017/gvpocr --eval "
use gvpocr
db.enriched_documents.countDocuments({created_at: {\$gte: new Date(new Date().getTime() - 300000)}})
"
# Should be > 0 (documents created in last 5 min)

# 4. Completeness back to normal
# Run check from verification section
```

### Step 5: Communicate
```
Subject: ✓ Phase 1 rollback complete
Status: SUCCESS
Duration: 10 minutes
Impact: None (service restored)

Next steps:
1. Investigate root cause
2. Fix issues
3. Re-deploy when ready

Completeness: Back to ~27.8% (expected)
All systems: Operational
```

---

## Troubleshooting Rollback

### Issue: Backup file not found
```bash
# Solution: Use git to restore
git checkout enrichment_service/workers/agent_orchestrator.py

# If git not available:
# Manually restore from Docker image (advanced)
```

### Issue: Worker still won't start
```bash
# 1. Check error
docker logs gvpocr-enrichment-worker

# 2. Clear Docker cache
docker-compose down
docker system prune -a

# 3. Rebuild and restart
docker-compose build --no-cache enrichment-worker
docker-compose up -d enrichment-worker
```

### Issue: Still seeing new error handling after rollback
```bash
# Problem: Docker image not rebuilt
# Solution:
docker-compose build --no-cache enrichment-worker

# Or pull image fresh:
docker image rm ocr_metadata_extraction-enrichment-worker
docker-compose build enrichment-worker
```

### Issue: Completeness still shows 60%?
```bash
# This is OK - data doesn't rollback, just the code
# New documents processed with old code will be ~27.8%
# Documents from Phase 1 testing will show 60%

# To verify rollback worked:
# 1. Check logs show fixed timeout (60s)
# 2. Check no error classification
# 3. Process new test document
# 4. Check it shows ~27.8% completeness
```

---

## Decision Tree: Should You Rollback?

```
Issue detected?
│
├─ Import/Syntax Error?
│  ├─ Yes → ROLLBACK immediately
│  │         (Fix: Check code deployment)
│  └─ No → Continue
│
├─ Worker crashes on startup?
│  ├─ Yes → ROLLBACK immediately
│  │         (Fix: Check Python syntax)
│  └─ No → Continue
│
├─ Completeness < 20% after 30 min?
│  ├─ Yes → ROLLBACK
│  │         (Fix: Check adaptive timeouts)
│  └─ No → Continue
│
├─ Processing time > 400s consistently?
│  ├─ Yes → Check MCP server first
│  │   ├─ MCP OK → ROLLBACK
│  │   └─ MCP slow → Fix MCP, don't rollback
│  └─ No → Continue
│
├─ Error spike (50+ errors/hour)?
│  ├─ Yes → Investigate error types
│  │   ├─ Expected errors → Monitor
│  │   └─ Unexpected errors → ROLLBACK
│  └─ No → Continue
│
├─ Completeness increasing to 50%+?
│  ├─ Yes → DO NOT ROLLBACK, keep monitoring
│  └─ No → May rollback if above trends met
│
└─ All metrics looking good?
   └─ Keep Phase 1! ✓
```

---

## Post-Rollback Actions

### Immediate (Same Day)
1. [ ] Notify team of rollback
2. [ ] Document issue/error
3. [ ] Create GitHub issue or ticket
4. [ ] Start investigation

### Short-term (1-2 Days)
1. [ ] Root cause analysis
2. [ ] Fix identified issue
3. [ ] Plan re-deployment
4. [ ] Additional testing

### Before Re-deployment
1. [ ] Verify fix in dev environment
2. [ ] Test with sample documents
3. [ ] Review all changes again
4. [ ] Get approval to re-deploy

---

## Quick Reference

### Files to Check
```
Original code backup:
  enrichment_service/workers/agent_orchestrator.py.backup.*

Code to restore:
  enrichment_service/workers/agent_orchestrator.py

Files to remove:
  enrichment_service/errors/
  enrichment_service/config/timeouts.py
  tests/test_error_handling.py

Containers to restart:
  gvpocr-enrichment-worker
  gvpocr-enrichment-coordinator (depends on worker)
```

### Quick Commands
```bash
# View backup location
ls -la enrichment_service/workers/agent_orchestrator.py.backup.*

# Quick rollback
cp enrichment_service/workers/agent_orchestrator.py.backup.* \
   enrichment_service/workers/agent_orchestrator.py && \
rm -rf enrichment_service/errors/ && \
docker-compose build enrichment-worker && \
docker-compose up -d enrichment-worker

# Check status after rollback
docker ps | grep enrichment-worker && \
docker logs gvpocr-enrichment-worker | tail -10
```

---

**Rollback Procedures Version**: 1.0
**Last Updated**: January 21, 2026
**Status**: Ready for Production
**Time to Execute**: 5-10 minutes
