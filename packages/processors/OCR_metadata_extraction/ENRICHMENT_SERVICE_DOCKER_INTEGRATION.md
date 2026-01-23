# Enrichment Service - Docker Compose Integration Guide

**Version**: 1.0  
**Date**: January 17, 2026  
**Status**: Complete & Verified

---

## Overview

The Enrichment Service is fully containerized and orchestrated through `docker-compose.enrichment.yml`. All 11 services work together in a distributed architecture.

---

## Service Architecture

### Service Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Prometheus   │  │   Grafana    │  │ AlertManager │      │
│  │   :9090      │  │   :3001      │  │   :9093      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                    AGENT INFRASTRUCTURE                      │
│  ┌──────────────┐                                           │
│  │  MCP Server  │ (WebSocket :3000)                         │
│  │   :3000      │                                           │
│  └──────────────┘                                           │
│         ↑                                                   │
│    ┌────┴──┬──┬──┬──┐                                      │
│    ↓      ↓  ↓  ↓  ↓                                       │
│  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐               │
│  │Meta  ││Entity││Struct││Content││Context              │
│  │Agent ││Agent ││Agent ││Agent  ││Agent                │
│  │:8001 │├:8002 │├:8003 │├:8004 │├:8005 │               │
│  └──────┘└──────┘└──────┘└──────┘└──────┘               │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                  ENRICHMENT SERVICES                         │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │     Coordinator  │  │  Worker (×2)     │               │
│  │     :8001        │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│         ↑                                 ↓                │
│         └─────→ NSQ Topic ←───────────────┘               │
│               "enrichment"                                │
└─────────────────────────────────────────────────────────────┘
           ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                    APIs & INFRASTRUCTURE                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Review API   │  │  Cost API    │  │  MongoDB     │     │
│  │ :5001 (TLS)  │  │ :5002 (TLS)  │  │ :27017       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Definitions

### 1. Monitoring & Observability

#### Prometheus (Time-Series Database)
```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: gvpocr-prometheus
  restart: unless-stopped
  
  # Configuration
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ./alerts.yml:/etc/prometheus/alerts.yml:ro
    - prometheus_data:/prometheus  # Persistent storage
  
  # Network & Ports
  ports:
    - "9090:9090"
  networks:
    - gvpocr-network
  
  # Health Check
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", 
           "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
  
  # Metrics Scraped
  scrapes:
    - enrichment-coordinator (8001/metrics)
    - enrichment-worker (8002/metrics)
    - review-api (5001/metrics)
    - cost-api (5002/metrics)
    - mcp-server (3000/metrics)
```

**Metrics Collected**:
- `enrichment_documents_enriched_total{status="completed|error|review_pending"}`
- `enrichment_duration_seconds{phase="1|2|3|total"}`
- `enrichment_completeness_score`
- `enrichment_review_queue_size`
- `enrichment_claude_cost_usd_total{model="sonnet|opus|haiku"}`
- `enrichment_agent_availability{agent_id="..."}` (from all 5 agents)

#### Grafana (Visualization)
```yaml
grafana:
  image: grafana/grafana:latest
  container_name: gvpocr-grafana
  restart: unless-stopped
  
  # Configuration
  environment:
    - GF_SECURITY_ADMIN_USER=admin
    - GF_SECURITY_ADMIN_PASSWORD=admin123
    - GF_USERS_ALLOW_SIGN_UP=false
  
  # Provisioning
  volumes:
    - grafana_data:/var/lib/grafana
    - grafana_provisioning:/etc/grafana/provisioning
  
  # Network & Ports
  ports:
    - "3001:3000"  # http://localhost:3001
  networks:
    - gvpocr-network
  
  # Dependencies
  depends_on:
    - prometheus  # Uses prometheus as datasource
  
  # Default Dashboards
  provisioned_dashboards:
    1. Enrichment Overview - Docs processed, costs, completeness
    2. Agent Performance - Response times, availability
    3. Cost Tracking - Budget status, spend trends
    4. Document Quality - Success rates, review analysis
    5. Processing Throughput - Docs/hour, queue depth
```

**Access**: http://localhost:3001 (admin / admin123)

#### AlertManager (Alert Routing)
```yaml
alertmanager:
  image: prom/alertmanager:latest
  container_name: gvpocr-alertmanager
  restart: unless-stopped
  
  # Configuration
  volumes:
    - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    - alertmanager_data:/alertmanager
  
  # Network & Ports
  ports:
    - "9093:9093"  # http://localhost:9093
  networks:
    - gvpocr-network
  
  # Alert Rules (30+)
  alert_conditions:
    - completeness_score < 0.85
    - review_queue_size > 100
    - daily_budget_exceeded
    - agent_unavailable
    - processing_rate < 30 docs/hour
    - cost_per_document > limit
    - phase1_duration > 20s
    - phase2_duration > 30s
    - phase3_duration > 60s
```

**Access**: http://localhost:9093

---

### 2. MCP Server & Agents

#### MCP Server (Model Context Protocol)
```yaml
mcp-server:
  build:
    context: ../../../mcp-server
    dockerfile: Dockerfile
  container_name: gvpocr-mcp-server
  restart: unless-stopped
  
  # Environment
  environment:
    - PORT=3000
    - JWT_SECRET=${MCP_JWT_SECRET:-mcp_development_secret}
    - LOG_LEVEL=info
    - ENVIRONMENT=production
  
  # Network
  ports:
    - "3000:3000"  # WebSocket ws://mcp-server:3000
  networks:
    - gvpocr-network
  
  # Health Check
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  
  # API Endpoints
  endpoints:
    - POST /tools/invoke - Invoke tool on agent
    - GET /health - Health status
    - GET /metrics - Prometheus metrics
```

**Protocol**: WebSocket JSON-RPC 2.0  
**Auth**: JWT token (env: MCP_JWT_SECRET)

#### 5 Specialized Agents

**Pattern for Each Agent**:
```yaml
[agent-name]:
  build:
    context: ../../../agents/[agent-name]
    dockerfile: Dockerfile
  container_name: gvpocr-[agent-name]
  restart: unless-stopped
  
  environment:
    - MCP_SERVER_URL=ws://mcp-server:3000
    - AGENT_ID=[agent-name]
    - LOG_LEVEL=info
    # Model-specific environment
  
  networks:
    - gvpocr-network
  
  depends_on:
    - mcp-server
  
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:[port]/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

##### Agent 1: metadata-agent
```yaml
metadata-agent:
  ports: [8001:8001]
  environment:
    - OLLAMA_HOST=http://ollama:11434
    - OLLAMA_MODEL=llama3.2
    - AGENT_ID=metadata-agent
  
  depends_on:
    - mcp-server
    - ollama
  
  # Tools
  tools:
    - extract_document_type(text) → {type, confidence}
    - extract_storage_info(text) → {location, format, condition}
    - extract_digitization_metadata(text) → {dpi, color_depth, ...}
    - determine_access_level(text) → {level, restrictions}
```

##### Agent 2: entity-agent
```yaml
entity-agent:
  ports: [8002:8002]
  environment:
    - OLLAMA_HOST=http://ollama:11434
    - OLLAMA_MODEL=llama3.2
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - AGENT_ID=entity-agent
  
  depends_on:
    - mcp-server
    - ollama
  
  # Tools
  tools:
    - extract_people(text) → [{name, role, title, confidence}]
    - extract_organizations(text) → [{name, type, confidence}]
    - extract_locations(text) → [{name, type, country, coordinates}]
    - extract_events(text) → [{name, date, participants}]
    - generate_relationships(entities) → [{entity1, relation, entity2}]
```

##### Agent 3: structure-agent
```yaml
structure-agent:
  ports: [8003:8003]
  environment:
    - OLLAMA_HOST=http://ollama:11434
    - OLLAMA_MODEL=mixtral
    - AGENT_ID=structure-agent
  
  depends_on:
    - mcp-server
    - ollama
  
  # Tools
  tools:
    - extract_salutation(text) → string
    - parse_letter_body(text) → {paragraphs, sections}
    - extract_closing(text) → string
    - extract_signature(text) → {name, title, location}
    - identify_attachments(text) → [{name, count, type}]
    - parse_correspondence(text) → {sender, recipient, date, subject}
```

##### Agent 4: content-agent
```yaml
content-agent:
  ports: [8004:8004]
  environment:
    - MCP_SERVER_URL=ws://mcp-server:3000
    - OLLAMA_HOST=http://ollama:11434
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - CLAUDE_MODEL=claude-sonnet-4
    - AGENT_ID=content-agent
  
  depends_on:
    - mcp-server
    - ollama
  
  # Tools (uses Claude Sonnet)
  tools:
    - generate_summary(text, length) → string
    - extract_keywords(text) → [string]
    - classify_subjects(text) → [{subject, confidence}]
    - extract_dates(text) → [{date, event, confidence}]
    - detect_language_features(text) → {style, tone, formality}
  
  # Pricing
  cost_per_doc: ~$0.045
```

##### Agent 5: context-agent
```yaml
context-agent:
  ports: [8005:8005]
  environment:
    - MCP_SERVER_URL=ws://mcp-server:3000
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - CLAUDE_MODEL=claude-opus-4-5
    - AGENT_ID=context-agent
  
  depends_on:
    - mcp-server
  
  # Tools (uses Claude Opus - PREMIUM)
  tools:
    - research_historical_context(entities, date) → {context, sources}
    - assess_significance(content, context) → {score, analysis}
    - generate_biographies(people) → [{name, biography, impact}]
    - link_related_documents(entities) → [{doc_id, relationship}]
  
  # Pricing
  cost_per_doc: ~$0.15
  
  # Optional - Can be disabled by BudgetManager
  enable_condition: daily_budget_remaining > 25%
```

---

### 3. Enrichment Services

#### Enrichment Coordinator
```yaml
enrichment-coordinator:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-enrichment-coordinator
  command: python run_enrichment_coordinator.py
  restart: unless-stopped
  
  # Port (Metrics only, no public API)
  ports:
    - "8001:8001"  # Metrics endpoint
  
  # Environment
  environment:
    - FLASK_ENV=production
    - PORT=8001
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
    - NSQD_ADDRESS=nsqd:4150
    - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
    - ENRICHMENT_ENABLED=true
    - ENRICHMENT_BATCH_SIZE=50
    - ENRICHMENT_REVIEW_THRESHOLD=0.95
    - MCP_SERVER_URL=ws://mcp-server:3000
  
  # Volumes
  volumes:
    - ./backend:/app/backend:ro
  
  # Network
  networks:
    - gvpocr-network
  
  # Dependencies
  depends_on:
    - mongodb
    - nsqd
    - mcp-server
  
  # Health Check
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  
  # Function
  function: |
    1. Monitors MongoDB for completed OCR jobs (bulk_jobs collection)
    2. For each completed OCR job:
       - Create enrichment_job record
       - Publish enrichment tasks to NSQ topic "enrichment"
       - Batch: 50 documents per task (ENRICHMENT_BATCH_SIZE)
    3. Track job progress in enrichment_jobs collection
    4. Expose metrics on :8001/metrics
```

#### Enrichment Worker
```yaml
enrichment-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  command: python run_enrichment_worker.py
  restart: unless-stopped
  
  # Environment
  environment:
    - FLASK_ENV=production
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
    - NSQD_ADDRESS=nsqd:4150
    - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
    - MCP_SERVER_URL=ws://mcp-server:3000
    - ENRICHMENT_ENABLED=true
    - MAX_CLAUDE_TOKENS_PER_DOC=50000
    - COST_ALERT_THRESHOLD_USD=100.00
  
  # Volumes
  volumes:
    - ./backend:/app/backend:ro
  
  # Network
  networks:
    - gvpocr-network
  
  # Dependencies
  depends_on:
    - mongodb
    - nsqd
    - mcp-server
  
  # Scaling
  deploy:
    replicas: 2  # ← IMPORTANT: Run 2+ instances
  
  # Health Check
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  
  # Function
  function: |
    1. Consumes messages from NSQ topic "enrichment"
    2. For each message:
       - Parse document_id, ocr_data
       - Run AgentOrchestrator (3-phase pipeline)
         Phase 1: Parallel agents (5-15s, free)
         Phase 2: Claude Sonnet (10-20s, ~$0.045)
         Phase 3: Claude Opus (20-30s, ~$0.15, optional)
       - Validate schema completeness (≥95%)
       - If pass: Save to enriched_documents
       - If fail: Route to review_queue
    3. Track costs in cost_records
    4. Update enrichment_jobs progress
    5. Ack message to NSQ when complete
```

---

### 4. API Services

#### Review API
```yaml
review-api:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-review-api
  command: python run_review_api.py
  restart: unless-stopped
  
  # Port (HTTPS)
  ports:
    - "5001:5001"
  
  # Environment
  environment:
    - FLASK_ENV=production
    - PORT=5001
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
    - ENABLE_HTTPS=true
    - SSL_CERT_PATH=/certs/server.crt
    - SSL_KEY_PATH=/certs/server.key
  
  # Volumes
  volumes:
    - ./backend:/app/backend:ro
    - ./certs:/certs:ro
  
  # Network
  networks:
    - gvpocr-network
  
  # Dependencies
  depends_on:
    - mongodb
  
  # Health Check
  healthcheck:
    test: ["CMD", "curl", "-f", "https://localhost:5001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  
  # API Endpoints
  endpoints:
    GET  /api/review/queue              - Paginated list of pending reviews
    GET  /api/review/{review_id}        - Get specific review task
    POST /api/review/{review_id}/assign - Assign to reviewer
    POST /api/review/{review_id}/approve - Approve with corrections
    POST /api/review/{review_id}/reject - Reject and re-queue
    GET  /api/review/stats              - Queue statistics
```

**Access**: https://localhost:5001/api/review/queue

#### Cost API
```yaml
cost-api:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-cost-api
  command: python run_cost_api.py
  restart: unless-stopped
  
  # Port (HTTPS)
  ports:
    - "5002:5002"
  
  # Environment
  environment:
    - FLASK_ENV=production
    - PORT=5002
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
    - ENABLE_HTTPS=true
    - SSL_CERT_PATH=/certs/server.crt
    - SSL_KEY_PATH=/certs/server.key
  
  # Volumes
  volumes:
    - ./backend:/app/backend:ro
    - ./certs:/certs:ro
  
  # Network
  networks:
    - gvpocr-network
  
  # Dependencies
  depends_on:
    - mongodb
  
  # Health Check
  healthcheck:
    test: ["CMD", "curl", "-f", "https://localhost:5002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  
  # API Endpoints
  endpoints:
    GET  /api/cost/budget/daily              - Daily budget status
    GET  /api/cost/budget/monthly            - Monthly budget status
    POST /api/cost/estimate/task             - Estimate single task
    POST /api/cost/estimate/document         - Estimate document
    POST /api/cost/estimate/collection       - Estimate collection
    GET  /api/cost/job/{job_id}              - Job cost analysis
    GET  /api/cost/report/models             - Model usage breakdown
    GET  /api/cost/config                    - Current configuration
```

**Access**: https://localhost:5002/api/cost/budget/daily

---

### 5. Infrastructure Services

#### MongoDB
```yaml
mongodb:
  image: mongo:7.0
  container_name: gvpocr-mongodb
  restart: unless-stopped
  
  # Authentication
  environment:
    - MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
    - MONGO_INITDB_DATABASE=gvpocr
  
  # Port
  ports:
    - "27017:27017"
  
  # Volumes
  volumes:
    - mongodb_data:/data/db
    - mongodb_config:/data/configdb
  
  # Network
  networks:
    - gvpocr-network
  
  # Collections
  collections:
    - enrichment_jobs
    - enriched_documents
    - review_queue
    - cost_records
    - ocr_results
    - bulk_jobs
```

#### NSQ (Message Queue)
```yaml
# nsqlookupd - Discovery service
nsqlookupd:
  image: nsqio/nsq:latest
  command: /nsqlookupd
  ports:
    - "4160:4160"  # TCP
    - "4161:4161"  # HTTP
  networks:
    - gvpocr-network

# nsqd - Queue broker
nsqd:
  image: nsqio/nsq:latest
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160
  ports:
    - "4150:4150"  # TCP
    - "4151:4151"  # HTTP
  networks:
    - gvpocr-network
  depends_on:
    - nsqlookupd
  
  # Topic
  topic: "enrichment"
  channel: "enrichment-workers"
```

#### Ollama (Local LLM)
```yaml
ollama:
  image: ollama/ollama:latest
  container_name: gvpocr-ollama
  restart: unless-stopped
  
  # Port
  ports:
    - "11434:11434"
  
  # Environment
  environment:
    - OLLAMA_NUM_PARALLEL=2
    - OLLAMA_NUM_THREAD=4
  
  # Volumes (model cache)
  volumes:
    - ollama_data:/root/.ollama
  
  # Network
  networks:
    - gvpocr-network
  
  # Models
  models:
    - llama3.2 (Phase 1: Metadata, Entity agents)
    - mixtral (Phase 1: Structure agent)
```

---

## Network Configuration

### Docker Network

```yaml
networks:
  gvpocr-network:
    external: true  # Created beforehand with:
                    # docker network create gvpocr-network
```

**Service Discovery**:
```
enrichment-worker → mongodb:27017          (MongoDB)
enrichment-worker → nsqd:4150              (NSQ broker)
enrichment-worker → mcp-server:3000        (MCP via WebSocket)
mcp-server → metadata-agent:8001           (Direct HTTP)
mcp-server → entity-agent:8002
mcp-server → structure-agent:8003
mcp-server → content-agent:8004
mcp-server → context-agent:8005
agents → ollama:11434                      (Ollama models)
```

---

## Storage & Persistence

### Volumes

```yaml
volumes:
  # Prometheus time-series data
  prometheus_data:
    driver: local
    mount_point: /prometheus

  # Grafana configuration & dashboards
  grafana_data:
    driver: local
    mount_point: /var/lib/grafana

  # Grafana provisioning configs
  grafana_provisioning:
    driver: local
    mount_point: /etc/grafana/provisioning

  # AlertManager alert history
  alertmanager_data:
    driver: local
    mount_point: /alertmanager

  # MongoDB data
  mongodb_data:
    driver: local
    mount_point: /data/db

  # Ollama model cache
  ollama_data:
    driver: local
    mount_point: /root/.ollama
```

**Data Backup Strategy**:
```bash
# Backup MongoDB
docker exec gvpocr-mongodb mongodump \
  -u ${MONGO_ROOT_USERNAME} \
  -p ${MONGO_ROOT_PASSWORD} \
  -d gvpocr \
  -o /backups/mongodb

# Backup Prometheus
docker exec gvpocr-prometheus tar czf /backups/prometheus.tar.gz /prometheus

# Backup Grafana
docker exec gvpocr-grafana tar czf /backups/grafana.tar.gz /var/lib/grafana
```

---

## Startup Sequence

### Order of Service Startup

```
1. Network:
   docker network create gvpocr-network

2. Infrastructure (parallel):
   - MongoDB (27017)
   - NSQ lookupd (4160/4161)
   - NSQ broker (4150/4151)
   - Ollama (11434)

3. Monitoring (sequential):
   - Prometheus (9090)
   - Grafana (3001) [depends on Prometheus]
   - AlertManager (9093)

4. MCP Ecosystem:
   - MCP Server (3000)
   - All 5 Agents (8001-8005) [depend on MCP Server]

5. Enrichment Services:
   - Coordinator (8001)
   - Workers ×2 (8002)
   - Review API (5001)
   - Cost API (5002)

Total Startup Time: ~2-3 minutes
```

### Health Check Verification

```bash
# After docker-compose up, verify services:
./health-check.sh

# Individual health checks:
curl http://localhost:9090/-/healthy        # Prometheus
curl http://localhost:3001/api/health       # Grafana
curl http://localhost:9093/-/healthy        # AlertManager
curl http://localhost:3000/health           # MCP Server
curl http://localhost:11434/api/tags        # Ollama
curl http://localhost:4161/api/stats        # NSQ
curl http://localhost:8001/health           # Coordinator
curl http://localhost:8002/health           # Worker
curl https://localhost:5001/health          # Review API
curl https://localhost:5002/health          # Cost API
```

---

## Resource Requirements

### CPU & Memory

| Service | CPU | Memory | Notes |
|---------|-----|--------|-------|
| MongoDB | 1 | 1GB | Database |
| NSQ | 0.5 | 256MB | Message queue |
| Ollama | 4 | 4GB+ | Local models (llama3.2, mixtral) |
| MCP Server | 1 | 512MB | Agent orchestration |
| Each Agent | 0.5 | 256MB | 5 agents × 128MB |
| Coordinator | 0.5 | 256MB | Job monitoring |
| Worker ×2 | 1 | 512MB | Processing |
| Review API | 0.5 | 256MB | HTTP API |
| Cost API | 0.5 | 256MB | HTTP API |
| Prometheus | 1 | 2GB | Metrics storage |
| Grafana | 0.5 | 512MB | Visualization |
| AlertManager | 0.5 | 256MB | Alert routing |
| **TOTAL** | **~13** | **~10GB** | Shared/dynamic |

**Typical Production Setup**: 16 CPU cores, 16GB RAM

---

## Environment Variables

### Required Variables

```bash
# MongoDB Authentication
MONGO_ROOT_USERNAME=gvpocr_admin
MONGO_ROOT_PASSWORD=<strong-password>

# Claude API
ANTHROPIC_API_KEY=sk-ant-<api-key>

# MCP Security
MCP_JWT_SECRET=<jwt-secret>
```

### Optional Variables

```bash
# Enrichment Configuration
ENRICHMENT_BATCH_SIZE=50
ENRICHMENT_REVIEW_THRESHOLD=0.95
MAX_CLAUDE_TOKENS_PER_DOC=50000

# Budget Controls
DAILY_BUDGET_USD=100.00
MAX_COST_PER_DOC=0.50
COST_ALERT_THRESHOLD_USD=100.00

# Ollama
OLLAMA_NUM_PARALLEL=2
OLLAMA_NUM_THREAD=4

# Grafana
GF_SECURITY_ADMIN_PASSWORD=admin123
```

---

## Deployment Commands

### Start All Services

```bash
# Navigate to project root
cd /path/to/OCR_metadata_extraction

# Create network
docker network create gvpocr-network

# Start enrichment services
docker-compose -f docker-compose.enrichment.yml up -d

# Verify startup
docker-compose -f docker-compose.enrichment.yml ps
docker-compose -f docker-compose.enrichment.yml logs -f
```

### Scale Workers

```bash
# Run 4 worker instances instead of 2
docker-compose -f docker-compose.enrichment.yml up -d --scale enrichment-worker=4

# Check load distribution
curl http://localhost:4161/api/stats
```

### Stop Services

```bash
# Graceful shutdown
docker-compose -f docker-compose.enrichment.yml down

# Remove volumes (data loss!)
docker-compose -f docker-compose.enrichment.yml down -v
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.enrichment.yml logs -f

# Specific service
docker-compose -f docker-compose.enrichment.yml logs -f enrichment-worker

# Last 100 lines
docker-compose -f docker-compose.enrichment.yml logs --tail=100 review-api
```

---

## Monitoring & Troubleshooting

### Access Points

```
Service              URL/Port
─────────────────────────────────────────
MongoDB              localhost:27017
NSQ Admin            localhost:4161
Ollama API           localhost:11434
MCP Server           ws://localhost:3000
Prometheus           http://localhost:9090
Grafana              http://localhost:3001 (admin/admin123)
AlertManager         http://localhost:9093
Review API           https://localhost:5001
Cost API             https://localhost:5002
```

### Common Issues & Fixes

**Issue 1: "network gvpocr-network not found"**
```bash
docker network create gvpocr-network
```

**Issue 2: "Address already in use"**
```bash
# Find & kill process on port (e.g., 9090)
lsof -i :9090
kill <PID>

# Or use different ports in compose override:
docker-compose -f docker-compose.enrichment.yml -f docker-compose.override.yml up -d
```

**Issue 3: "Ollama models not loaded"**
```bash
# Check available models
curl http://localhost:11434/api/tags

# Pull missing models
docker exec gvpocr-ollama ollama pull llama3.2
docker exec gvpocr-ollama ollama pull mixtral
```

**Issue 4: "NSQ connection refused"**
```bash
# Verify NSQ is running
docker-compose -f docker-compose.enrichment.yml ps nsqd

# Check NSQ status
curl http://localhost:4161/api/stats
```

---

## Performance Optimization

### Container Resource Limits

```yaml
# In docker-compose.enrichment.yml
enrichment-worker:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### Ollama Tuning

```bash
# Reduce parallel inference
environment:
  OLLAMA_NUM_PARALLEL: 1  # Default: 2
  OLLAMA_NUM_THREAD: 2    # Default: 4
```

### NSQ Tuning

```bash
# Increase queue capacity
command: /nsqd \
  --lookupd-tcp-address=nsqlookupd:4160 \
  --max-msg-size=5242880 \
  --max-body-size=5242880
```

---

## Conclusion

The Enrichment Service Docker Compose setup provides:

✓ **Scalable**: Horizontal scaling via replicas  
✓ **Observable**: Full monitoring & alerting  
✓ **Reliable**: Health checks & auto-restart  
✓ **Isolated**: Service-to-service communication via network  
✓ **Persistent**: Data preservation via volumes  
✓ **Secure**: TLS for API services, JWT for MCP  

**Production Checklist**:
- [ ] Create gvpocr-network
- [ ] Set MONGO_ROOT_PASSWORD securely
- [ ] Set ANTHROPIC_API_KEY
- [ ] Set MCP_JWT_SECRET
- [ ] Pull Ollama models (llama3.2, mixtral)
- [ ] Configure volume backups
- [ ] Set resource limits
- [ ] Test health checks
- [ ] Monitor initial startup logs
- [ ] Verify cost tracking accuracy

---

**Document Complete** ✓  
Date: January 17, 2026
