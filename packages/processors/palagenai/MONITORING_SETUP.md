# Monitoring Setup Guide - Phase 1 Error Handling

**Purpose**: Track error handling improvements and system performance
**Date**: January 21, 2026
**Target Metrics**: Completeness, Processing Time, Error Distribution

---

## Monitoring Architecture

### Metrics to Track

```
Application Metrics:
├─ Completeness Score (%)
│  ├─ Current: 27.8%
│  ├─ Target: 60%+
│  └─ Measurement: avg(quality_metrics.completeness_score)
│
├─ Processing Time (seconds)
│  ├─ Current: 180+ (with wasted retries)
│  ├─ Target: 120-240 (normalized)
│  └─ Measurement: total_processing_time_ms
│
├─ Error Distribution
│  ├─ Error Types: timeout, connection, invalid_data, auth, overloaded, event_loop
│  ├─ Current: No classification
│  ├─ Target: Clear classification
│  └─ Measurement: Error logs with type field
│
├─ Fallback Rate (%)
│  ├─ Current: 72% (high, bad)
│  ├─ Target: <30% (low, good)
│  └─ Measurement: sum(_source=="fallback") / total
│
├─ Timeout Frequency
│  ├─ Current: High (60s fixed timeout hits many)
│  ├─ Target: Low (adaptive timeouts prevent most)
│  └─ Measurement: count(failed with timeout)
│
└─ Retry Success Rate
   ├─ Current: Low (retries after timeout usually fail)
   ├─ Target: High (fewer unnecessary retries)
   └─ Measurement: success_retries / total_retries
```

---

## Quick Start: Simple Monitoring

### Option 1: MongoDB Queries (No Setup)

```bash
# Check completeness improvement
mongosh mongodb://gvpocr_admin:PASSWORD@localhost:27017/gvpocr --eval "
use gvpocr
db.enriched_documents.aggregate([
  {\$match: {created_at: {\$gte: new Date(new Date().getTime() - 3600000)}}},
  {\$group: {
    _id: null,
    avg_completeness: {\$avg: '\$quality_metrics.completeness_score'},
    count: {\$sum: 1}
  }}
])
"

# Check error types
docker logs gvpocr-enrichment-worker | grep "failed with" | \
  sed 's/.*failed with \([a-z_]*\).*/\1/' | \
  sort | uniq -c | sort -rn

# Check processing time
docker logs gvpocr-enrichment-worker | grep "total_processing_time" | \
  awk '{print $NF}' | awk '{print $1/1000}' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'
```

### Option 2: Bash Monitoring Script

```bash
#!/bin/bash
# File: /usr/local/bin/monitor-enrichment.sh
# Run: monitor-enrichment.sh or add to crontab

MONGO_URI="mongodb://gvpocr_admin:PASSWORD@localhost:27017/gvpocr"

echo "=== OCR Enrichment Monitoring ==="
echo "Timestamp: $(date)"
echo ""

# Completeness
echo "1. Completeness Score (Target: 60%+)"
COMPLETENESS=$(mongosh "$MONGO_URI" --quiet --eval "
use gvpocr
db.enriched_documents.aggregate([
  {\$match: {created_at: {\$gte: new Date(new Date().getTime() - 3600000)}}},
  {\$group: {_id: null, avg: {\$avg: '\$quality_metrics.completeness_score'}}}
]).toArray()[0]?.avg || 0
" | tail -1)
echo "   Current: ${COMPLETENESS}%"

# Error types
echo ""
echo "2. Error Distribution"
docker logs gvpocr-enrichment-worker --since 1h | grep "failed with" | \
  sed 's/.*failed with \([a-z_]*\).*/\1/' | sort | uniq -c | sort -rn | \
  head -10

# Processing time
echo ""
echo "3. Processing Time (Target: 120-240s)"
AVG_TIME=$(docker logs gvpocr-enrichment-worker --since 1h | \
  grep "total_processing_time_ms:" | \
  awk -F: '{sum+=$NF; count++} END {if (count>0) print int(sum/count/1000); else print 0}')
echo "   Average: ${AVG_TIME}s"

# Fallback rate
echo ""
echo "4. Fallback Rate (Target: <30%)"
FALLBACK=$(mongosh "$MONGO_URI" --quiet --eval "
use gvpocr
let result = db.enriched_documents.aggregate([
  {\$match: {created_at: {\$gte: new Date(new Date().getTime() - 3600000)}}},
  {\$group: {
    _id: null,
    fallback: {\$sum: {\$cond: [{'\$eq': ['\$enriched_data._source', 'fallback']}, 1, 0]}},
    total: {\$sum: 1}
  }},
  {\$project: {_id: 0, rate: {\$multiply: [{'\$divide': ['\$fallback', '\$total']}, 100]}}}
]).toArray()[0];
print(result?.rate?.toFixed(1) || 0)
" | tail -1)
echo "   Fallback: ${FALLBACK}%"

echo ""
echo "=== End Report ==="
```

**Run manually**:
```bash
chmod +x /usr/local/bin/monitor-enrichment.sh
monitor-enrichment.sh
```

**Add to crontab** (run every 30 minutes):
```bash
crontab -e

# Add line:
*/30 * * * * /usr/local/bin/monitor-enrichment.sh >> /var/log/enrichment-monitor.log 2>&1
```

---

## Key Metrics Reference

### Completeness Score
```
Definition: % of required fields extracted (actual data vs fallback)
Formula: Extracted fields / Total required fields × 100

Current (before Phase 1): 27.8%
Target (after Phase 1): 60%+
Excellent: 80-95%

What it means:
- 27.8% = Only 5 of 18 fields extracted
- 60%+ = At least 11 of 18 fields extracted
- 95%+ = Nearly all fields extracted

Alert if: < 50% (indicating something wrong)
```

### Processing Time
```
Definition: Total seconds to enrich one document

Current (before Phase 1): 180+ seconds wasted on timeouts
Target (after Phase 1): 120-240 seconds normalized
Good: < 200 seconds
Alert if: > 300 seconds

Breakdown:
- Phase 1: 30-180s (extraction)
- Phase 2: 90-150s (analysis)
- Phase 3: 0-240s (context, if enabled)
```

### Fallback Rate
```
Definition: % of results that are fallback (empty/default) vs actual

Current (before Phase 1): 72% fallback (bad)
Target (after Phase 1): <30% fallback (good)
Excellent: <10% fallback

What it means:
- 72% = 13 of 18 fields are empty/default values
- 30% = 5 of 18 fields are fallback, 13 are actual
- 10% = 16 of 18 fields are actual data

Alert if: > 40% (too much fallback)
```

### Error Type Distribution
```
Expected types after Phase 1:
- TIMEOUT: Lower than before (adaptive timeouts prevent)
- CONNECTION: Stable (network-related)
- INVALID_DATA: Low (should validate before use)
- AUTHENTICATION: Low (should not happen often)
- OVERLOADED: Low (service overload)
- EVENT_LOOP: Very low (1-2 in entire system)
- UNKNOWN: Low (should be classified)

Alert if: Any single type > 20% of all errors
```

---

## Dashboard Setup (Choose One)

### Option A: No Dashboard (Just Logs)
```bash
# Monitor in real-time
docker logs -f gvpocr-enrichment-worker | grep -E "timeout:|failed with|_source:"
```

### Option B: Simple Web Dashboard (Python Flask)

```python
# File: /app/enrichment_monitoring.py
from flask import Flask, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
db = MongoClient(os.getenv('MONGO_URI'))['gvpocr']

@app.route('/metrics')
def get_metrics():
    """Get current metrics"""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Completeness
    comp = list(db.enriched_documents.aggregate([
        {$match: {created_at: {$gte: one_hour_ago}}},
        {$group: {_id: None, avg: {$avg: '$quality_metrics.completeness_score'}}}
    ])) or [{'avg': 0}]

    # Processing time
    proc = list(db.enriched_documents.aggregate([
        {$match: {created_at: {$gte: one_hour_ago}}},
        {$group: {_id: None, avg: {$avg: '$enrichment_metadata.total_processing_time_ms'}}}
    ])) or [{'avg': 0}]

    return jsonify({
        'completeness': round(comp[0]['avg'] * 100, 1),
        'processing_time_seconds': round(proc[0]['avg'] / 1000, 1),
        'timestamp': datetime.utcnow().isoformat(),
        'target_completeness': 60,
        'target_processing_time': 200
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
```

**Run**:
```bash
MONGO_URI="mongodb://gvpocr_admin:PASSWORD@localhost:27017/gvpocr" python3 /app/enrichment_monitoring.py

# Access at: http://localhost:5555/metrics
```

### Option C: Grafana Dashboard

1. **Add MongoDB data source**:
   - URL: mongodb://localhost:27017/gvpocr
   - Database: gvpocr

2. **Create panels**:
   - **Completeness**: `db.enriched_documents.aggregate([{$group: {_id: null, avg: {$avg: '$quality_metrics.completeness_score'}}}])`
   - **Error Count**: `db.enriched_documents.find({}).count()`
   - **Processing Time**: `db.enriched_documents.aggregate([{$group: {_id: null, avg: {$avg: '$enrichment_metadata.total_processing_time_ms'}}}])`

---

## What to Monitor During First 24 Hours

### Every Hour
- [ ] Check completeness is improving (should see 50%+ by hour 2-3)
- [ ] Verify error types are being classified
- [ ] Check no new error patterns appearing

### Every 4 Hours
- [ ] Verify adaptive timeouts in logs (see different timeout values)
- [ ] Check fallback rate is decreasing
- [ ] Review error distribution

### Every 12 Hours
- [ ] Overall completeness trend (should be 60%+)
- [ ] Processing time normalized to 120-240s
- [ ] No significant regressions

### Daily
- [ ] Average completeness for the day (target: 60%+)
- [ ] Error summary by type
- [ ] Processing time statistics (min/avg/max)
- [ ] Comparison with pre-deployment baseline

---

## Alert Conditions

### Critical (Page On-Call)
```
1. Completeness < 40% for 10 minutes
2. Processing time > 400 seconds for 15 minutes
3. More than 50% of results are fallback for 20 minutes
4. Any import/module error in logs
```

### Warning (Alert but Don't Page)
```
1. Completeness < 60% for 30 minutes
2. Processing time > 300 seconds for 20 minutes
3. More than 30% of results are fallback for 30 minutes
4. Single error type > 30% of all errors
```

### Info (Log but Don't Alert)
```
1. Completeness > 50% (good!)
2. Processing time normalized (120-240s)
3. Clear error type distribution (all classified)
4. Fallback rate < 30% (good!)
```

---

## Monitoring Checklist: Pre vs Post Deployment

### Before Phase 1 Deployment
```
Metric                  Current Value
Completeness            27.8% ✗
Processing Time         180+ seconds ✗
Error Classification    None ✗
Fallback Rate           72% ✗
Adaptive Timeouts       No ✗
Data Source Tracking    No ✗
```

### After Phase 1 Deployment (Expected)
```
Metric                  Target Value     Status
Completeness            60%+             Check daily
Processing Time         120-240 sec      Should improve
Error Classification    7 types          Verify in logs
Fallback Rate           <30%             Should decrease
Adaptive Timeouts       30-240s          Check logs
Data Source Tracking    _source field    Verify in DB
```

---

## Troubleshooting Monitoring Issues

### No data showing in queries?
```bash
# 1. Verify MongoDB connection
mongosh mongodb://localhost:27017/gvpocr

# 2. Check if documents exist
use gvpocr
db.enriched_documents.countDocuments()

# 3. Check if new docs being created
db.enriched_documents.find().sort({created_at: -1}).limit(1)
```

### Logs not showing adaptive timeouts?
```bash
# Check if updated code deployed
grep "get_tool_timeout" enrichment_service/workers/agent_orchestrator.py

# If missing: Redeploy
docker-compose build enrichment-worker
docker-compose up -d enrichment-worker
```

### Completeness still 27.8%?
```bash
# 1. Check error logs
docker logs gvpocr-enrichment-worker | grep -i error | head -20

# 2. Verify agent_orchestrator.py has new code
grep "from enrichment_service.errors" enrichment_service/workers/agent_orchestrator.py

# 3. Check if MCP server is responding
curl http://mcp-server:3003/status

# 4. If issues: Consider rollback
```

---

## Next Steps After Monitoring Confirms Success

### Day 1-2 (After 60%+ completeness confirmed)
- [ ] Update team on improvements
- [ ] Document baseline metrics
- [ ] Plan Phase 2 (circuit breaker, logging)

### Week 1 (Stable operations)
- [ ] Review full week of data
- [ ] Calculate actual savings vs estimate
- [ ] Decide on Phase 3 (local models)

### Month 1 (Ongoing)
- [ ] Continue baseline monitoring
- [ ] Plan improvements
- [ ] Update SLOs based on actual data

---

**Monitoring Setup Version**: 1.0
**Last Updated**: January 21, 2026
**Status**: Ready to Deploy
