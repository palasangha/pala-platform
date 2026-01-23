# End-to-End Testing Guide

Complete guide for testing the MCP agent-based enrichment pipeline with sample historical letters.

## Overview

This guide walks through testing the entire enrichment pipeline:

1. **Deploy services** with Docker Compose
2. **Insert sample OCR data** into MongoDB
3. **Monitor pipeline** in real-time
4. **Analyze results** for completeness and costs

## Prerequisites

- Docker & Docker Compose installed
- 8GB+ RAM available
- 20GB disk space
- Anthropic API key (for Claude models)

## Step-by-Step Testing

### Phase 1: Deploy the Stack

#### 1a. Configure Environment

```bash
# From OCR_metadata_extraction directory
cp .env.example .env

# Edit .env with your configuration
nano .env

# Critical variables to set:
# ANTHROPIC_API_KEY=sk-ant-your-key
# MCP_JWT_SECRET=your-secret
# MONGO_PASSWORD=secure-password
```

#### 1b. Start Services

```bash
# Make startup script executable
chmod +x start-enrichment.sh

# Start the entire stack (this takes 5-10 minutes)
./start-enrichment.sh

# Output shows:
# ✓ All services started
# ✓ Ollama models downloaded (llama3.2, mixtral)
# ✓ Access points displayed
```

#### 1c. Verify Services

```bash
# Check all services are running and healthy
chmod +x health-check.sh
./health-check.sh

# Expected output:
# ✓ MongoDB (port 27017)
# ✓ NSQ (port 4161)
# ✓ Ollama (port 11434)
# ✓ Prometheus (port 9090)
# ✓ Grafana (port 3000)
# ✓ Review API (port 5001)
# ✓ Cost API (port 5002)
```

**Troubleshooting**: If services aren't healthy after 2 minutes:

```bash
# Check logs
docker-compose -f docker-compose.enrichment.yml logs -f enrichment_mongodb

# Restart a service
docker-compose -f docker-compose.enrichment.yml restart enrichment_worker_1

# Full restart
docker-compose -f docker-compose.enrichment.yml down -v
docker-compose -f docker-compose.enrichment.yml up -d
```

### Phase 2: Insert Test Data

#### 2a. Prepare Test Data

The test data is pre-created in `test-data/sample-letters.json` with 5 sample historical letters:

- **Letter 001**: Invitation letter (1978) - high OCR confidence (0.94)
- **Letter 002**: Personal letter (1990) - medium confidence (0.91)
- **Letter 003**: Business letter (1985) - high confidence (0.93)
- **Letter 004**: Multilingual letter (1992) - lower confidence (0.87)
- **Letter 005**: Ceremonial letter (1980) - highest confidence (0.96)

#### 2b. Insert Data into MongoDB

```bash
# Make test data script executable
chmod +x test-data/insert-test-data.sh

# Insert test data
./test-data/insert-test-data.sh

# Expected output:
# ✓ MongoDB connection successful
# ✓ Inserted test_letter_001 (confidence: 0.94)
# ✓ Inserted test_letter_002 (confidence: 0.91)
# ✓ Inserted test_letter_003 (confidence: 0.93)
# ✓ Inserted test_letter_004 (confidence: 0.87)
# ✓ Inserted test_letter_005 (confidence: 0.96)
# ✓ OCR job created with ID: ocr_test_1705425600
```

#### 2c. Verify Data in MongoDB

```bash
# Connect to MongoDB
mongosh \
    --username enrichment_user \
    --password changeMe123 \
    --host localhost:27017

# In MongoDB shell:
> use gvpocr
> db.ocr_jobs.find({status: "completed"})
> db.ocr_results.count()  # Should show 5
> db.ocr_results.findOne()
```

### Phase 3: Monitor Enrichment Processing

#### 3a. Start Real-Time Monitor

The enrichment pipeline should automatically start processing the OCR job within 10-30 seconds.

```bash
# Start monitoring enrichment progress in a new terminal
chmod +x monitor-enrichment.sh
./monitor-enrichment.sh

# Real-time dashboard shows:
# - Enrichment jobs status
# - Documents processed (approved/review/errors)
# - Review queue status
# - Completeness metrics
# - Cost tracking
# - NSQ queue depth
# - Agent health
```

**What to watch for**:

1. **Enrichment Jobs**: Should see "Processing" increase to "Completed"
2. **Documents Processed**: Count should increase from 0 to 5
3. **Completeness**: Should show average completeness (target: >0.95)
4. **Review Queue**: Documents <95% complete should appear here
5. **Costs**: Shows Claude API usage and costs
6. **Agent Health**: All agents should show ✓ (running)

**Expected Timeline**:

- t=0s: OCR job inserted
- t=10-15s: EnrichmentCoordinator picks it up
- t=20-40s: Phase 1 agents run (parallel, ~5-15s)
- t=50-70s: Phase 2 content-agent runs (~10-20s)
- t=80-110s: Phase 3 context-agent runs (~20-30s)
- t=120s+: Schema validation, storage to MongoDB
- **Total**: ~2 minutes for 5 documents

#### 3b. Monitor via Grafana Dashboards

While the monitor script runs, also check Grafana for visual metrics:

```bash
# Open in browser
http://localhost:3000

# Login: admin / admin123

# Navigate to dashboards:
1. Enrichment Overview - See document flow
2. Agent Performance - Monitor agent response times
3. Cost Tracking - Track API costs in real-time
4. Document Quality - Completeness distribution
5. Processing Throughput - Documents/hour metric
```

#### 3c. Monitor via Prometheus

Check raw metrics in Prometheus:

```bash
# Open in browser
http://localhost:9090

# Try queries:
# - enrichment_documents_enriched_total{status="success"}
# - rate(enrichment_duration_seconds_bucket[1m])
# - enrichment_completeness_score
# - enrichment_claude_cost_usd_total
```

### Phase 4: Analyze Results

#### 4a. Run Comprehensive Analysis

Once processing completes (monitor should show all documents processed):

```bash
# Analyze results
chmod +x analyze-results.sh
./analyze-results.sh

# Output shows:
# - Document Processing Summary
# - Completeness Analysis
# - Cost Analysis (by model, by task)
# - Quality Issues (low confidence fields)
# - Performance Metrics
```

**Key Metrics to Check**:

| Metric | Target | What to Do If Below |
|--------|--------|-------------------|
| Average Completeness | >0.95 | Refine agent prompts |
| Auto-Approval Rate | >90% | Adjust review threshold |
| Cost per Document | <$0.50 | Optimize model routing |
| Median Completeness | >0.95 | Check missing fields |

#### 4b. Manually Review Results

```bash
# Connect to MongoDB to view enriched documents
mongosh \
    --username enrichment_user \
    --password changeMe123 \
    --host localhost:27017

# In MongoDB shell:
> use gvpocr

# View first enriched document
> db.enriched_documents.findOne()

# Check completeness scores
> db.enriched_documents.find({}, {document_id: 1, "quality_metrics.completeness_score": 1})

# Check review queue (documents that need human review)
> db.review_queue.find({status: "pending"}, {document_id: 1, reason: 1, flagged_fields: 1})

# View cost breakdown
> db.cost_records.find({}, {model: 1, task_name: 1, cost_usd: 1})
```

#### 4c. Check Review Queue via API

```bash
# Get pending review tasks
curl http://localhost:5001/api/review/queue

# Get review statistics
curl http://localhost:5001/api/review/stats

# Get specific review task
REVIEW_ID=$(curl -s http://localhost:5001/api/review/queue | jq -r '.tasks[0].review_id')
curl http://localhost:5001/api/review/$REVIEW_ID
```

#### 4d. Check Costs via API

```bash
# Get budget status
curl http://localhost:5002/api/cost/budget/daily

# Get document cost breakdown
curl -X POST http://localhost:5002/api/cost/estimate/document \
  -H "Content-Type: application/json" \
  -d '{"doc_length_chars": 2000}'

# Get cost report by models
curl http://localhost:5002/api/cost/report/models
```

### Phase 5: Interpret Results

#### Expected Outcomes (5-Document Test)

**Processing Completion**:
```
Expected:
- All 5 documents processed in ~2 minutes
- 4-5 documents auto-approved (>95% completeness)
- 0-1 documents in review queue (<95% completeness)
```

**Completeness Distribution**:
```
Expected:
- 80-100%: Perfect completeness (100%)
- 90-95%: High completeness (95-99%)
- 10-20%: Medium completeness (85-94%)
- 0-10%: Low completeness (<85%)
```

**Costs** (with US pricing):
```
Phase 1 (Ollama):
- 3 agents × 5 documents = 15 calls = $0 (free)

Phase 2 (Claude Sonnet):
- content-agent: 5 calls × ~$0.009/call = $0.045

Phase 3 (Claude Opus):
- context-agent: 5 calls × ~$0.035/call = $0.175 (if enabled)

Expected Total: $0.22-0.25 for 5 documents ($0.04-0.05/doc)
```

**Agent Performance**:
```
Expected response times:
- metadata-agent: 5-10 seconds
- entity-agent: 8-15 seconds
- structure-agent: 5-10 seconds
- content-agent: 10-20 seconds
- context-agent: 20-30 seconds
```

#### Quality Checks

**Missing Fields Analysis**:

Review the top missing fields identified in analyze-results.sh:

- If `analysis.historical_context` is missing → context-agent may have failed or been disabled (check budget)
- If `content.summary` is missing → content-agent may need prompt refinement
- If `analysis.people` is missing → entity-agent prompt needs improvement

**Low Confidence Fields**:

Check which fields have confidence scores <0.70:

- Update agent prompts if same field appears in multiple documents
- Consider increasing confidence threshold if only occasional issues

### Phase 6: Troubleshooting

#### Scenario 1: No Documents Appear in enriched_documents

**Possible causes**:
1. Coordinator not running → check logs: `docker logs enrichment_coordinator -f`
2. Worker not running → check logs: `docker logs enrichment_worker_1 -f`
3. NSQ connectivity issue → check NSQ health: `curl http://localhost:4161/api/stats`

**Solution**:
```bash
# Restart coordinator and workers
docker-compose -f docker-compose.enrichment.yml restart enrichment_coordinator
docker-compose -f docker-compose.enrichment.yml restart enrichment_worker_1
docker-compose -f docker-compose.enrichment.yml restart enrichment_worker_2

# Wait 30 seconds and check monitor
./monitor-enrichment.sh
```

#### Scenario 2: Low Completeness Scores

**Possible causes**:
1. Agent prompts not optimized for letter format
2. OCR quality too low (confidence <0.85)
3. Schema too strict or missing required fields

**Solution**:
```bash
# Identify missing fields
./analyze-results.sh | grep "Missing Fields Analysis" -A 20

# Review agent prompts for common missing fields
# Edit: packages/agents/{agent-name}/tools/prompts.py

# Re-run test after prompt improvements
./test-data/insert-test-data.sh
./monitor-enrichment.sh
```

#### Scenario 3: High Costs

**Possible causes**:
1. Phase 3 (context-agent) processing all documents (very expensive)
2. Token estimates incorrect (using more tokens than estimated)
3. Claude API pricing increase

**Solution**:
```bash
# Check cost breakdown
./analyze-results.sh | grep "Cost by Task" -A 20

# If context-agent is expensive, disable in .env:
ENABLE_PHASE3_CONTEXT=false

# Or set budget limit:
MAX_COST_PER_DOC=0.30
DAILY_BUDGET_USD=50.00

# Re-run test
```

#### Scenario 4: NSQ Queue Backing Up

**Possible causes**:
1. Agents too slow or timing out
2. Worker crashed

**Solution**:
```bash
# Check NSQ queue depth
curl http://localhost:4161/api/stats | jq '.topics[] | select(.name=="enrichment")'

# Restart worker to clear queue
docker-compose -f docker-compose.enrichment.yml restart enrichment_worker_1

# Or scale workers
docker-compose -f docker-compose.enrichment.yml up -d --scale enrichment-worker=4
```

### Phase 7: Next Steps

#### If Test Passes (Completeness >90%, Costs <$0.50/doc)

1. **Scale to larger batch**
   ```bash
   # Create 50-100 test documents
   # Run end-to-end pipeline
   # Verify completeness maintained at scale
   ```

2. **Optimize prompts**
   - Identify top 5 missing fields
   - Refine agent prompts
   - Re-test with same documents
   - Verify improvement

3. **Prepare for production**
   - Backup MongoDB
   - Configure SSL/TLS
   - Set up log aggregation
   - Deploy monitoring alerts

#### If Test Fails (Completeness <80%, High Costs)

1. **Analyze failures**
   ```bash
   ./analyze-results.sh
   # Focus on "Missing Fields Analysis" and "Top Low Confidence Fields"
   ```

2. **Refine agents**
   - Review agent prompts
   - Test individual agents
   - Check OCR quality (OCR confidence <0.85 problematic)

3. **Adjust configuration**
   - Increase ENRICHMENT_REVIEW_THRESHOLD if auto-approving too aggressively
   - Disable expensive agents if over budget
   - Optimize model routing

### Performance Benchmarks

**Expected Results on 8GB RAM System**:

```
5 Documents Test:
- Processing time: 2-3 minutes
- Auto-approval rate: 80-100%
- Average completeness: 0.92-0.98
- Total cost: $0.20-0.40
- Cost per document: $0.04-0.08

50 Documents Test:
- Processing time: 20-30 minutes
- Auto-approval rate: 85-95%
- Average completeness: 0.93-0.97
- Total cost: $2.00-4.00
- Cost per document: $0.04-0.08

100 Documents Test:
- Processing time: 40-60 minutes
- Auto-approval rate: 85-95%
- Average completeness: 0.93-0.97
- Total cost: $4.00-8.00
- Cost per document: $0.04-0.08
```

### Cleanup

**After testing is complete**:

```bash
# Stop and remove all containers/volumes
docker-compose -f docker-compose.enrichment.yml down -v

# Remove test data
rm -rf test-data/sample-letters.json

# Clean up generated files
docker volume prune -f
```

## Success Criteria

The enrichment pipeline is ready for production when:

✅ **Completeness**: ≥95% of documents achieve ≥95% schema completeness
✅ **Auto-Approval**: ≥90% of documents auto-approve without human review
✅ **Costs**: Cost per document ≤$0.50 (budget acceptable)
✅ **Throughput**: Processes ≥50 documents/hour
✅ **Reliability**: All agents healthy and responsive
✅ **Monitoring**: Grafana dashboards show all metrics
✅ **APIs**: Review and cost APIs responding correctly

## Support

For issues during testing:

1. Check **health-check.sh** output
2. Review logs in docker-compose dashboard
3. Check **monitor-enrichment.sh** for real-time status
4. Run **analyze-results.sh** to identify issues
5. Review troubleshooting section above

Good luck! 🚀
