# Docker Deployment Guide - Enrichment Pipeline

## Overview

This Docker Compose configuration deploys the complete MCP agent-based enrichment pipeline for processing OCR data and transforming it into fully enriched historical letter metadata.

## Architecture

```
OCR Pipeline (external)
    ↓
EnrichmentCoordinator (monitors MongoDB)
    ↓
NSQ Topic "enrichment"
    ↓
EnrichmentWorker(s) (NSQ consumers)
    ↓
AgentOrchestrator (3-phase MCP orchestration)
    ↓
MongoDB enriched_documents collection
```

## Prerequisites

1. **Docker & Docker Compose**: Latest versions installed
2. **System Resources**: 
   - Minimum 8GB RAM available
   - 20GB disk space for MongoDB + Ollama models
   - GPU optional (for Ollama acceleration)
3. **API Keys**:
   - Anthropic API key (for Claude models)
   - MCP JWT secret (for agent authentication)

## Quick Start

### 1. Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your actual values
nano .env
```

**Critical variables to set:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
MCP_JWT_SECRET=your-secret-key-here
MONGO_PASSWORD=secure-password-here
GRAFANA_ADMIN_PASSWORD=secure-password-here
```

### 2. Start the Stack

```bash
# Pull latest images
docker-compose -f docker-compose.enrichment.yml pull

# Start all services (will pull and build images)
docker-compose -f docker-compose.enrichment.yml up -d

# Verify services are running
docker-compose -f docker-compose.enrichment.yml ps
```

Expected output:
```
NAME                           STATUS           PORTS
enrichment_mongodb             Up (healthy)     27017
enrichment_nsqlookupd          Up (healthy)     4160-4161
enrichment_nsqd                Up (healthy)     4150-4151
enrichment_ollama              Up (healthy)     11434
enrichment_prometheus          Up (healthy)     9090
enrichment_grafana             Up (healthy)     3000
enrichment_mcp_server          Up (healthy)     3000
enrichment_metadata_agent      Up              
enrichment_entity_agent        Up              
enrichment_structure_agent     Up              
enrichment_content_agent       Up              
enrichment_context_agent       Up              
enrichment_coordinator         Up              
enrichment_worker_1            Up              
enrichment_worker_2            Up              
enrichment_review_api          Up (healthy)     5001
enrichment_cost_api            Up (healthy)     5002
```

### 3. Download Ollama Models

After Ollama container starts, pull the required models:

```bash
# Pull llama3.2 (used by Phase 1 agents)
docker exec enrichment_ollama ollama pull llama3.2

# Pull mixtral (used by structure-agent)
docker exec enrichment_ollama ollama pull mixtral

# List available models
docker exec enrichment_ollama ollama list
```

This takes 10-30 minutes depending on internet speed. Models are cached in the `ollama_data` volume.

### 4. Verify Services

#### MongoDB Connection
```bash
# Connect to MongoDB
docker exec enrichment_mongodb mongosh \
  --username enrichment_user \
  --password changeMe123 \
  --authenticationDatabase admin

# In MongoDB shell:
> use gvpocr
> show collections
```

#### NSQ Management
```bash
# View NSQ admin interface
# Open browser to: http://localhost:4161/
```

#### Prometheus Metrics
```bash
# Open browser to: http://localhost:9090/

# Try some queries:
# - enrichment_documents_enriched_total{status="success"}
# - rate(enrichment_duration_seconds_bucket[5m])
# - enrichment_completeness_score
```

#### Grafana Dashboards
```bash
# Open browser to: http://localhost:3000/

# Default credentials:
# Username: admin
# Password: admin123 (or from GRAFANA_ADMIN_PASSWORD in .env)

# Dashboards should auto-import:
# - Enrichment Overview
# - Agent Performance
# - Cost Tracking
# - Document Quality
# - Processing Throughput
```

#### Review Queue API
```bash
# Get pending review tasks
curl http://localhost:5001/api/review/queue

# Get review queue statistics
curl http://localhost:5001/api/review/stats
```

#### Cost Tracking API
```bash
# Get daily budget status
curl http://localhost:5002/api/cost/budget/daily

# Get cost estimates for a document
curl -X POST http://localhost:5002/api/cost/estimate/document \
  -H "Content-Type: application/json" \
  -d '{"doc_length_chars": 2000}'
```

## Testing the Pipeline

### 1. Create a Test OCR Document

```bash
# Connect to MongoDB
docker exec -it enrichment_mongodb mongosh \
  --username enrichment_user \
  --password changeMe123 \
  --authenticationDatabase admin

# In MongoDB shell:
> use gvpocr
> db.ocr_jobs.insertOne({
  job_id: "test_ocr_001",
  collection_id: "test_collection",
  status: "completed",
  documents: [
    {
      document_id: "test_doc_001",
      text: "Dear Friend, I am pleased to invite you to the meditation center opening...",
      confidence: 0.92,
      detected_language: "en"
    }
  ],
  created_at: new Date()
})
```

### 2. Trigger Enrichment

The coordinator monitors for completed OCR jobs. Check logs:

```bash
# View coordinator logs
docker logs enrichment_coordinator -f

# View worker logs
docker logs enrichment_worker_1 -f
```

### 3. Check Results

```bash
# In MongoDB shell:
> db.enriched_documents.findOne({document_id: "test_doc_001"})

# Check review queue if completeness < 95%
> db.review_queue.find({status: "pending"})

# Check costs
> db.cost_records.find({document_id: "test_doc_001"})
```

## Monitoring & Observability

### Key Metrics to Watch

**Dashboard: Enrichment Overview**
- Documents processed (success/review/error)
- Completeness score distribution
- Daily budget status
- Active workers

**Dashboard: Agent Performance**
- Agent availability (target: 99%+)
- Response times (target: <30s)
- Error rates (target: <1%)

**Dashboard: Cost Tracking**
- Daily spend vs budget
- Cost per document (target: $0.10-$0.50)
- Model usage breakdown

**Dashboard: Document Quality**
- Success rate (target: >90%)
- Human review rate (target: <5%)
- Missing fields analysis

### Common Alerts

Alert | Threshold | Action
------|-----------|--------
Low Completeness Rate | <85% | Review agent prompts
High Review Queue | >100 docs | Increase workers or budget
Daily Budget Exceeded | 100%+ spent | Stop processing or increase budget
Agent Unavailable | Down >5min | Restart service
Slow Processing | <30 docs/hour | Check NSQ queue, add workers

### Debugging

```bash
# View all service logs
docker-compose -f docker-compose.enrichment.yml logs -f

# View specific service
docker-compose -f docker-compose.enrichment.yml logs -f enrichment_worker_1

# Get service stats
docker stats enrichment_mongodb enrichment_ollama

# Check network connectivity
docker exec enrichment_worker_1 ping mcp-server

# Test MCP server health
curl http://localhost:3000/health
```

## Scaling

### Add More Workers

```bash
# Edit docker-compose.enrichment.yml
# Change:
# enrichment-worker:
#   deploy:
#     replicas: 2  # <-- increase this

# Restart services
docker-compose -f docker-compose.enrichment.yml up -d
```

### Adjust Concurrency

```bash
# In .env, adjust:
CONCURRENT_WORKERS=4        # Number of concurrent enrichments per worker
ENRICHMENT_BATCH_SIZE=100   # Documents per batch
```

### Optimize Resource Usage

```bash
# View resource usage
docker stats

# Limit container resources in docker-compose.yml:
# resources:
#   limits:
#     cpus: '2'
#     memory: 2G
```

## Maintenance

### Backup MongoDB

```bash
# Create backup
docker exec enrichment_mongodb mongodump \
  --username enrichment_user \
  --password changeMe123 \
  --out /backups/$(date +%Y%m%d)

# Copy from container
docker cp enrichment_mongodb:/backups ./backups
```

### View Container Sizes

```bash
docker system df
```

### Clean Up Old Volumes

```bash
# Remove unused volumes
docker volume prune

# Remove specific volume
docker volume rm OCR_metadata_extraction_mongodb_data
```

### Update Services

```bash
# Pull latest images
docker-compose -f docker-compose.enrichment.yml pull

# Rebuild and restart
docker-compose -f docker-compose.enrichment.yml up -d --build

# Check version
docker exec enrichment_mongodb mongosh --version
```

## Production Deployment

### Pre-Production Checklist

- [ ] Anthropic API key configured and tested
- [ ] MCP JWT secret changed from default
- [ ] MongoDB password changed from default
- [ ] SSL/TLS certificates generated for APIs
- [ ] Backup strategy configured
- [ ] Alert recipients configured in AlertManager
- [ ] Load testing completed (target: 100 docs/hour)
- [ ] Cost estimates validated with small batch
- [ ] Health checks verified on all services

### Production Configuration

```bash
# .env for production
ENVIRONMENT=production
LOG_LEVEL=INFO
ENRICHMENT_BATCH_SIZE=100
CONCURRENT_WORKERS=4
DAILY_BUDGET_USD=500.00
ENRICHMENT_REVIEW_THRESHOLD=0.95
ENABLE_PHASE3_CONTEXT=true  # Full Claude processing
```

### Monitoring in Production

- Set up log aggregation (ELK, DataDog, etc.)
- Configure uptime monitoring (New Relic, Datadog)
- Set up cost alerts via AWS/GCP billing
- Enable persistent volumes on managed storage (EBS, GCS)
- Configure automated backups

### Health Checks

```bash
# Create health check script
cat > health_check.sh << 'HEALTHEOF'
#!/bin/bash

echo "=== Enrichment Pipeline Health Check ==="
echo "MongoDB: $(curl -s http://localhost:27017 && echo 'OK' || echo 'FAILED')"
echo "NSQ: $(curl -s http://localhost:4161/api/nodes && echo 'OK' || echo 'FAILED')"
echo "Ollama: $(curl -s http://localhost:11434/api/tags && echo 'OK' || echo 'FAILED')"
echo "Prometheus: $(curl -s http://localhost:9090/-/healthy && echo 'OK' || echo 'FAILED')"
echo "Review API: $(curl -s http://localhost:5001/health && echo 'OK' || echo 'FAILED')"
echo "Cost API: $(curl -s http://localhost:5002/health && echo 'OK' || echo 'FAILED')"
HEALTHEOF

chmod +x health_check.sh
./health_check.sh
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs enrichment_mongodb

# Common issues:
# 1. Port already in use - change port in docker-compose.yml
# 2. Volume permissions - run: docker-compose down -v
# 3. Out of disk space - free up space and restart
```

### High Memory Usage

```bash
# Check memory usage by service
docker stats

# Reduce Ollama memory
# Edit docker-compose.yml:
# environment:
#   OLLAMA_NUM_PARALLEL: 1
#   OLLAMA_NUM_THREAD: 2
```

### Slow Processing

```bash
# Check worker queue
curl http://localhost:4161/api/nodes

# Check agent response times in Grafana
# If slow, restart agents:
docker-compose -f docker-compose.enrichment.yml restart enrichment_content_agent

# Increase batch size in .env
ENRICHMENT_BATCH_SIZE=100
```

### MongoDB Connection Errors

```bash
# Test connection
docker exec enrichment_mongodb mongosh \
  --username enrichment_user \
  --password <password> \
  --host mongodb

# Check MongoDB logs
docker logs enrichment_mongodb
```

## Shutdown

```bash
# Graceful shutdown (services finish current work)
docker-compose -f docker-compose.enrichment.yml down

# Force shutdown
docker-compose -f docker-compose.enrichment.yml down -v  # Also remove volumes

# Remove everything including data
docker-compose -f docker-compose.enrichment.yml down -v
docker volume prune -f
```

## Performance Benchmarks

Expected performance on standard 8GB RAM system:

| Metric | Value |
|--------|-------|
| Documents/hour | 50-100 |
| Cost per document | $0.10-$0.50 |
| Completeness score | >95% |
| Processing time | 10-30 seconds |
| Human review rate | <5% |
| API response time | <1 second |

## Support & Documentation

- **MCP Framework**: See packages/mcp-server/README.md
- **Agent Development**: See packages/agents/README.md
- **Enrichment Service**: See enrichment_service/README.md
- **Schema**: See enrichment_service/schema/historical_letters_schema.json
- **API Docs**: See enrichment_service/review/API.md

## License & Attribution

This enrichment pipeline is part of the Pala Platform OCR metadata extraction system.
