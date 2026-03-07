# Enrichment Service - MCP Agent-Based Pipeline

Transforms raw OCR data from historical documents into fully enriched metadata matching the historical letters JSON schema with 100% completeness requirement.

## Overview

The enrichment service uses a distributed architecture with 5 specialized MCP agents coordinated through a 3-phase pipeline:

- **Phase 1 (Parallel)**: Metadata, entity extraction, and structure parsing using local Ollama
- **Phase 2 (Sequential)**: Content generation using Claude Sonnet 
- **Phase 3 (Sequential)**: Historical context and significance using Claude Opus

## Architecture

```
OCR Job Complete (MongoDB)
        ↓
EnrichmentCoordinator (monitors & publishes to NSQ)
        ↓
NSQ Topic "enrichment"
        ↓
EnrichmentWorker (NSQ consumer)
        ↓
AgentOrchestrator
├── Phase 1 (Parallel)
│   ├── metadata-agent (Ollama)
│   ├── entity-agent (Ollama + Claude)
│   └── structure-agent (Ollama)
├── Phase 2 (Sequential)
│   └── content-agent (Claude Sonnet)
└── Phase 3 (Sequential)
    └── context-agent (Claude Opus)
        ↓
SchemaValidator (95%+ completeness check)
        ↓
     ┌──┴──┐
     ↓     ↓
 SAVE  REVIEW QUEUE
     ↓
DataMapper (merge with OCR)
     ↓
Archipelago Commons
```

## Components

### Core Services

#### 1. EnrichmentCoordinator
- Monitors MongoDB for completed OCR jobs
- Creates enrichment tasks in NSQ queue
- Tracks enrichment job progress
- **File**: `coordinator/enrichment_coordinator.py`
- **Command**: `python -m enrichment_service.coordinator.enrichment_coordinator`

#### 2. EnrichmentWorker
- Consumes tasks from NSQ topic "enrichment"
- Orchestrates full 3-phase MCP agent pipeline
- Validates schema completeness
- Routes incomplete documents to review queue
- Supports concurrent processing with configurable batch size
- **File**: `workers/enrichment_worker.py`
- **Command**: `python -m enrichment_service.workers.enrichment_worker`
- **Scalability**: Deploy multiple workers for throughput (default: 2 replicas)

#### 3. AgentOrchestrator
- **CRITICAL**: Manages 3-phase pipeline execution
- Handles agent communication via MCP client
- Result merging and schema validation
- Budget-aware Phase 3 optional processing
- **File**: `workers/agent_orchestrator.py`
- **Methods**:
  - `async run_phase1(ocr_data)` - Parallel agent execution
  - `async run_phase2(phase1_results, ocr_data)` - Content generation
  - `async run_phase3(phase1_results, phase2_results, ocr_data)` - Historical context
  - `async enrich_document(document_id, ocr_data)` - Full pipeline

#### 4. MCP Client
- WebSocket JSON-RPC 2.0 client for agent communication
- Connection pooling and auto-reconnection
- Retry logic with exponential backoff
- **File**: `mcp_client/client.py`
- **Key Method**: `async invoke_tool(agent_id, tool_name, arguments, timeout=60)`

#### 5. Schema Validator
- Recursive required field extraction from JSON schema
- Completeness score calculation (target: ≥0.95)
- Missing field identification
- **File**: `schema/validator.py`
- **Key Method**: `calculate_completeness(enriched_data) -> dict`

#### 6. Review Queue Manager
- Manages human review workflow for incomplete documents
- Tracks reviewers and approval status
- Stores reviewer notes and corrections
- **File**: `review/review_queue.py`
- **Methods**: create_task, assign_task, approve_task, reject_task

#### 7. APIs

**Review API** (port 5001)
- `GET /api/review/queue` - Get pending review tasks (paginated)
- `GET /api/review/{review_id}` - Get specific task with context
- `POST /api/review/{review_id}/assign` - Assign to reviewer
- `POST /api/review/{review_id}/approve` - Approve with corrections
- `POST /api/review/{review_id}/reject` - Reject and re-queue
- `GET /api/review/stats` - Queue statistics

**Cost API** (port 5002)
- `GET /api/cost/budget/daily` - Daily budget status
- `GET /api/cost/budget/monthly` - Monthly budget status
- `POST /api/cost/estimate/task` - Estimate single task cost
- `POST /api/cost/estimate/document` - Estimate document cost
- `POST /api/cost/estimate/collection` - Estimate collection cost
- `GET /api/cost/job/{job_id}` - Job cost analysis
- `GET /api/cost/report/models` - Model usage breakdown
- `GET /api/cost/config` - Current cost configuration

### 5 Specialized MCP Agents

**Located**: `packages/agents/{agent-name}/`

#### Agent 1: metadata-agent
- **Tools**: extract_document_type, extract_storage_info, extract_digitization_metadata, determine_access_level
- **Model**: Ollama llama3.2 (free, local)
- **Output**: Complete metadata section
- **Processing**: <5s per document

#### Agent 2: entity-agent
- **Tools**: extract_people, extract_organizations, extract_locations, extract_events, generate_relationships
- **Model**: Hybrid (Ollama + optional Claude for disambiguation)
- **Output**: people[], organizations[], locations[], events[], relationships[]
- **Processing**: 5-15s per document

#### Agent 3: structure-agent
- **Tools**: extract_salutation, parse_letter_body, extract_closing, extract_signature, identify_attachments, parse_correspondence
- **Model**: Ollama mixtral (free, local)
- **Output**: content structure + document.correspondence
- **Processing**: 5-10s per document

#### Agent 4: content-agent
- **Tools**: generate_summary, extract_keywords, classify_subjects, extract_dates, detect_language_features
- **Model**: Claude Sonnet 4 (cloud, paid ~$0.045/doc)
- **Output**: content.summary, analysis.keywords[], subjects[]
- **Processing**: 10-20s per document

#### Agent 5: context-agent
- **Tools**: research_historical_context, assess_significance, generate_biographies, link_related_documents
- **Model**: Claude Opus 4.5 (cloud, paid ~$0.15/doc - OPTIONAL)
- **Output**: historical_context, significance, biographies
- **Processing**: 20-30s per document
- **Budget Control**: Disabled when >25% daily budget spent

## Data Models

### MongoDB Collections

**enrichment_jobs**
```json
{
  "job_id": "enrich_abc123",
  "ocr_job_id": "ocr_xyz789",
  "collection_id": "goenka_letters",
  "status": "processing|completed|error|review_pending",
  "total_documents": 100,
  "processed_count": 45,
  "review_pending_count": 3,
  "error_count": 2,
  "cost_summary": {
    "total_cost_usd": 12.45,
    "ollama_cost": 0.0,
    "claude_sonnet_cost": 4.50,
    "claude_opus_cost": 7.95
  },
  "created_at": "2025-01-17T12:00:00Z",
  "completed_at": "2025-01-17T14:30:00Z"
}
```

**enriched_documents**
```json
{
  "document_id": "doc_456",
  "enrichment_job_id": "enrich_abc123",
  "ocr_data": {...},
  "enriched_data": {
    "metadata": {...},
    "document": {...},
    "content": {...},
    "analysis": {...}
  },
  "quality_metrics": {
    "completeness_score": 0.98,
    "confidence_scores": {...},
    "missing_fields": [],
    "low_confidence_fields": []
  },
  "review_status": "approved|pending|not_required",
  "created_at": "2025-01-17T12:10:00Z"
}
```

**review_queue**
```json
{
  "review_id": "review_789",
  "document_id": "doc_456",
  "enrichment_job_id": "enrich_abc123",
  "reason": "completeness_below_threshold|low_confidence",
  "flagged_fields": [
    {
      "field_path": "analysis.historical_context",
      "issue": "empty",
      "confidence": 0.0
    }
  ],
  "status": "pending|in_progress|approved|rejected",
  "assigned_to": "reviewer_001",
  "created_at": "2025-01-17T12:10:00Z",
  "assigned_at": "2025-01-17T12:15:00Z",
  "approved_at": "2025-01-17T12:25:00Z",
  "reviewer_notes": "Added historical context from archival research",
  "corrections": {...}
}
```

**cost_records**
```json
{
  "record_id": "cost_rec_123",
  "enrichment_job_id": "enrich_abc123",
  "document_id": "doc_456",
  "model": "claude-opus-4-5|claude-sonnet-4|ollama",
  "task_name": "research_historical_context",
  "input_tokens": 2500,
  "output_tokens": 1500,
  "cost_usd": 0.140,
  "created_at": "2025-01-17T12:12:30Z"
}
```

## Configuration

See `.env.example` for all available configuration variables. Key settings:

```bash
# Database
MONGO_URI=mongodb://user:pass@mongodb:27017/gvpocr

# Message Queue
NSQD_HOST=nsqd
NSQD_PORT=4150

# MCP Agents
MCP_SERVER_URL=ws://mcp-server:3000
MCP_JWT_SECRET=secret_key

# AI Models
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://ollama:11434

# Quality Control
ENRICHMENT_REVIEW_THRESHOLD=0.95

# Cost Controls
MAX_COST_PER_DOC=0.50
DAILY_BUDGET_USD=100.00
ENABLE_PHASE3_CONTEXT=true
```

## Installation

### Local Development

```bash
# Install Python 3.11+
python --version  # Should be 3.11+

# Install dependencies
pip install -r enrichment_service/requirements.txt

# Set up MongoDB
# Option 1: Use existing MongoDB instance
export MONGO_URI=mongodb://localhost:27017/gvpocr

# Option 2: Use Docker
docker run -d \
  -e MONGO_INITDB_ROOT_USERNAME=user \
  -e MONGO_INITDB_ROOT_PASSWORD=pass \
  -p 27017:27017 \
  mongo:7.0

# Set up NSQ
# Option 1: Use Docker
docker run -d -p 4160:4160 -p 4161:4161 nsqio/nsq:latest /nsqlookupd
docker run -d -p 4150:4150 -p 4151:4151 nsqio/nsq:latest \
  /nsqd --lookupd-tcp-address=nsqlookupd:4160

# Start enrichment services
python -m enrichment_service.coordinator.enrichment_coordinator &
python -m enrichment_service.workers.enrichment_worker &
python -m enrichment_service.review.review_api &
python -m enrichment_service.utils.cost_api &
```

### Docker Deployment

```bash
# See DOCKER_DEPLOYMENT.md for complete instructions

# Quick start
cd ..  # Go to OCR_metadata_extraction directory
./start-enrichment.sh

# Or manually
docker-compose -f docker-compose.enrichment.yml up -d
```

## Testing

```bash
# Run all tests
pytest enrichment_service/tests/

# Run specific test file
pytest enrichment_service/tests/test_integration.py

# Run with coverage
pytest --cov=enrichment_service enrichment_service/tests/

# Run unit tests only (fast)
pytest -m unit enrichment_service/tests/

# Run with verbose output
pytest -v enrichment_service/tests/
```

## Monitoring

### Metrics

Prometheus metrics exposed on port 8000/metrics:

- `enrichment_documents_enriched_total{status}` - Documents processed
- `enrichment_duration_seconds` - Processing time by phase
- `enrichment_completeness_score` - Completeness distribution
- `enrichment_review_queue_size` - Pending reviews
- `enrichment_claude_cost_usd_total{model}` - Claude API costs
- `enrichment_agent_availability{agent_id}` - Agent health

### Dashboards

Grafana dashboards (http://localhost:3000):
1. **Enrichment Overview** - Documents, costs, completeness
2. **Agent Performance** - Response times, availability
3. **Cost Tracking** - Budget status, spend trends
4. **Document Quality** - Success rates, review analysis
5. **Processing Throughput** - Docs/hour, queue depth

### Alerts

30+ Prometheus alerts configured for:
- Low completeness rate (<85%)
- High review queue (>100 documents)
- Budget exceeded
- Agent unavailable
- Slow processing (<30 docs/hour)

See `enrichment_service/utils/prometheus_alerts.yaml`

## Performance Benchmarks

Typical performance on 8GB RAM system:

| Metric | Value |
|--------|-------|
| Documents/hour | 50-100 |
| Cost per document | $0.10-$0.50 |
| Completeness score | >95% |
| Phase 1 duration | 5-15s |
| Phase 2 duration | 10-20s |
| Phase 3 duration | 20-30s |
| Human review rate | <5% |
| API response time | <1s |

## Troubleshooting

### Worker Not Processing Documents

```bash
# Check NSQ queue
curl http://localhost:4161/api/stats

# Check worker logs
docker logs enrichment_worker_1 -f

# Verify MCP server connectivity
curl http://localhost:3000/health

# Check database
mongo gvpocr --eval "db.enrichment_jobs.count()"
```

### High Memory Usage

Reduce Ollama concurrency in docker-compose.yml:
```yaml
ollama:
  environment:
    OLLAMA_NUM_PARALLEL: 1
    OLLAMA_NUM_THREAD: 2
```

### Slow Processing

- Check agent response times in Grafana
- Restart slow agents: `docker restart enrichment_content_agent`
- Increase workers: `docker-compose up -d --scale enrichment-worker=4`
- Check Claude API rate limits

### Low Completeness Scores

- Review agent prompts (in agent implementations)
- Increase confidence thresholds in ENRICHMENT_CONFIDENCE_THRESHOLD
- Check OCR quality (low OCR confidence leads to incomplete enrichment)
- Add documents to review queue for manual completion

## Contributing

1. Fork and create feature branch
2. Add tests for new functionality
3. Run `pytest` to verify all tests pass
4. Submit pull request with description

## License

Part of the Pala Platform OCR system.

## Support

For issues and questions:
1. Check troubleshooting section above
2. Review logs: `docker-compose logs -f`
3. Check Grafana dashboards: http://localhost:3000
4. Review cost API for budget status: http://localhost:5002/api/cost/budget/daily
