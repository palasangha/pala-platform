# Enrichment Services Docker Integration Analysis

## Executive Summary

The enrichment services (API, Coordinator, Worker) **CAN be successfully integrated** into the existing `docker-compose.yml` without major restructuring. However, there are critical issues to address:

1. **Port Conflict with AlertManager**: Port `9094` is already in use by the `antigravity` service on the host
2. **Service Already Configured**: Enrichment services are already defined in the current docker-compose.yml
3. **Dockerfile Migration**: Services currently use individual Dockerfiles that can be properly consolidated

---

## Current Status: Enrichment Services in docker-compose.yml

### ✅ Services Already Included

| Service | Container Name | Port Mapping | Status |
|---------|---|---|---|
| **enrichment-coordinator** | gvpocr-enrichment-coordinator | 8011:8001 | ✅ Defined |
| **enrichment-worker** | gvpocr-enrichment-worker | N/A | ✅ Defined (2 replicas) |
| **review-api** | gvpocr-review-api | 5001:5001 | ✅ Defined |
| **cost-api** | gvpocr-cost-api | 5002:5002 | ✅ Defined |

**Conclusion**: Enrichment services are **already in the docker-compose.yml** and don't need migration!

---

## Critical Issues Found

### 🔴 Issue 1: AlertManager Port 9094 Conflict

**Problem**:
- Docker attempting to bind port `9094` (host) to `9093` (container)
- Host port `9094` already in use by `antigravity` service (PID: 2020511)

**Current Configuration**:
```yaml
alertmanager:
  ports:
    - 9094:9093  # ← Conflict here
```

**Error Message**:
```
failed to set up container networking: driver failed programming external connectivity
on endpoint gvpocr-alertmanager: failed to bind host port 0.0.0.0:9094/tcp: address already in use
```

**Solutions**:

#### Option A: Use Different Port (RECOMMENDED)
Change port mapping to an available port:
```yaml
alertmanager:
  ports:
    - 9095:9093  # Use 9095 instead of 9094
```

#### Option B: No Host Port Binding
If AlertManager only needs internal access:
```yaml
alertmanager:
  # Remove ports section - keep internal communication only
```

#### Option C: Disable AlertManager
Remove or comment out the alertmanager service if not needed for development.

---

### 🟡 Issue 2: Service Dependencies Not Explicitly Defined

**Current Problem**:
- Enrichment-coordinator depends on MCP server (WebSocket connection)
- Enrichment-worker depends on MCP server
- These dependencies exist but aren't formally declared in `depends_on`

**Current Configuration**:
```yaml
enrichment-coordinator:
  depends_on:
    - mcp-server
    - mongodb
    - nsqd
```

**Status**: ✅ Already properly configured!

---

## Dockerfile Analysis & Migration Strategy

### Current Dockerfile Structure

**Three separate Dockerfiles** for enrichment services:

| Dockerfile | Purpose | Base Image | Key Differences |
|---|---|---|---|
| `Dockerfile.api` | Review & Cost APIs | python:3.11-slim | Exposes port 5000 (generic) |
| `Dockerfile.coordinator` | Monitors OCR jobs | python:3.11-slim | Runs coordinator module |
| `Dockerfile.worker` | Processes enrichment tasks | python:3.11-slim | No exposed ports |

### Build Contexts Issue

**Current docker-compose.yml**:
```yaml
review-api:
  build:
    context: ./backend          # ← Wrong context!
    dockerfile: Dockerfile      # ← Generic backend Dockerfile
  command: python run_review_api.py

cost-api:
  build:
    context: ./backend          # ← Wrong context!
    dockerfile: Dockerfile      # ← Generic backend Dockerfile
  command: python run_cost_api.py
```

**Problem**: Review-api and cost-api are using the **backend Dockerfile** instead of the enrichment service Dockerfile!

**Should be**:
```yaml
review-api:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.api
  environment:
    - PORT=5001
    - FLASK_MODULE=enrichment_service.review.review_api

cost-api:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.api
  environment:
    - PORT=5002
    - FLASK_MODULE=enrichment_service.cost.cost_api
```

---

## Recommended Changes to docker-compose.yml

### 1. Fix AlertManager Port

**Location**: Lines ~885-900 (estimated)

**Change**:
```diff
  alertmanager:
    image: prom/alertmanager:latest
    container_name: gvpocr-alertmanager
    restart: unless-stopped
    ports:
-     - 9094:9093
+     - 9095:9093
    environment:
      - ALERTMANAGER_CONFIG=/etc/alertmanager/config.yml
```

### 2. Fix review-api Build Configuration

**Location**: review-api service

**Current**:
```yaml
review-api:
  build:
    context: ./backend
    dockerfile: Dockerfile
  command: python run_review_api.py
  ports:
    - 5001:5001
  environment:
    - PORT=5001
```

**Recommended**:
```yaml
review-api:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.api
  container_name: gvpocr-review-api
  command: python -u -m enrichment_service.review.review_api
  restart: unless-stopped
  ports:
    - 5001:5001
  environment:
    - FLASK_ENV=production
    - PORT=5001
    - PYTHONUNBUFFERED=1
    - PYTHONPATH=/app
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
  networks:
    - gvpocr-network
  depends_on:
    - mongodb
  healthcheck:
    test:
      - CMD
      - curl
      - -f
      - http://localhost:5001/health
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

### 3. Fix cost-api Build Configuration

**Similar to review-api**:
```yaml
cost-api:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.api
  container_name: gvpocr-cost-api
  command: python -u -m enrichment_service.cost.cost_api
  restart: unless-stopped
  ports:
    - 5002:5002
  environment:
    - FLASK_ENV=production
    - PORT=5002
    - PYTHONUNBUFFERED=1
    - PYTHONPATH=/app
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
  networks:
    - gvpocr-network
  depends_on:
    - mongodb
  healthcheck:
    test:
      - CMD
      - curl
      - -f
      - http://localhost:5002/health
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

### 4. Verify enrichment-coordinator Configuration

**Current** (Already correct):
```yaml
enrichment-coordinator:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.coordinator
  container_name: gvpocr-enrichment-coordinator
  command: python -u -m enrichment_service.coordinator.enrichment_coordinator
  restart: unless-stopped
  ports:
    - 8011:8001
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
    - MCP_SERVER_URL=ws://mcp-server:3003
  networks:
    - gvpocr-network
  depends_on:
    - mcp-server
    - mongodb
    - nsqd
  healthcheck:
    test:
      - CMD
      - python
      - -c
      - "import requests; requests.get('http://localhost:8001/health')"
    interval: 30s
    timeout: 10s
    retries: 3
```

✅ **Status**: Already correctly configured

### 5. Verify enrichment-worker Configuration

**Current** (Already correct):
```yaml
enrichment-worker:
  build:
    context: .
    dockerfile: enrichment_service/Dockerfile.worker
  command: python -u -m enrichment_service.workers.enrichment_worker
  restart: unless-stopped
  environment:
    - FLASK_ENV=production
    - MONGO_URI=mongodb://mongodb:27017/gvpocr
    - MONGO_USERNAME=${MONGO_ROOT_USERNAME:-gvpocr_admin}
    - MONGO_PASSWORD=${MONGO_ROOT_PASSWORD}
    - NSQD_ADDRESS=nsqd:4150
    - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
    - MCP_SERVER_URL=ws://mcp-server:3003
    - ENRICHMENT_ENABLED=true
    - MAX_CLAUDE_TOKENS_PER_DOC=50000
    - COST_ALERT_THRESHOLD_USD=100.00
  networks:
    - gvpocr-network
  depends_on:
    - mcp-server
    - mongodb
    - nsqd
  deploy:
    replicas: 2
```

✅ **Status**: Already correctly configured

---

## Port Usage Summary

### Current Ports in Use

| Port | Service | Status |
|------|---------|--------|
| 27017 | MongoDB | ✅ Available |
| 5000 | Backend API | ✅ Available |
| 5001 | Review API | ✅ Available |
| 5002 | Cost API | ✅ Available |
| 5678 | Python Debugger | ✅ Available |
| 3000 | Frontend (via Caddy) | ✅ Available |
| 3001 | Grafana | ✅ Available |
| 3003 | MCP Server | ✅ Available |
| 8001 | Enrichment Coordinator | ✅ Available (exposed as 8011) |
| 8010 | File Server | ✅ Available |
| 8011 | Enrichment Coordinator (host) | ✅ Available |
| 8080 | Open-WebUI | ✅ Available |
| 9090 | Prometheus | ✅ Available |
| **9094** | **AlertManager (host)** | ❌ **IN USE - CONFLICT** |
| 9093 | AlertManager (container) | ✅ Available |
| 11434 | Ollama | ✅ Available |

---

## Action Items

### Immediate Actions (Required)

1. **Fix AlertManager Port**
   - Change host port from `9094` to `9095` (or any available port)
   - Update Prometheus alert routing if it references port 9094

2. **Fix review-api Build**
   - Change `context: ./backend` to `context: .`
   - Change `dockerfile: Dockerfile` to `dockerfile: enrichment_service/Dockerfile.api`
   - Update command to use enrichment service module path
   - Verify port 5001 binding works correctly

3. **Fix cost-api Build**
   - Same changes as review-api
   - Verify port 5002 binding works correctly

### Verification Steps

```bash
# 1. Validate docker-compose syntax
docker-compose config > /dev/null && echo "✅ Valid"

# 2. Check for port conflicts
docker-compose port

# 3. Dry-run service startup
docker-compose ps

# 4. Start services individually for testing
docker-compose up -d mongodb nsqd nsqlookupd
docker-compose up -d mcp-server
docker-compose up -d enrichment-coordinator enrichment-worker
docker-compose up -d review-api cost-api

# 5. Check service health
docker-compose ps
docker logs gvpocr-enrichment-coordinator
docker logs gvpocr-review-api
docker logs gvpocr-cost-api
```

---

## Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Services in docker-compose | ✅ Already defined | No migration needed |
| Enrichment Coordinator config | ✅ Correct | No changes needed |
| Enrichment Worker config | ✅ Correct | No changes needed |
| Review API config | ❌ Incorrect build context | Needs fix |
| Cost API config | ❌ Incorrect build context | Needs fix |
| AlertManager port conflict | ❌ Port 9094 in use | Needs port change |
| Overall integration | ✅ Feasible | All issues are solvable |

---

## Conclusion

**The enrichment services DO NOT need to be migrated** — they are already in the docker-compose.yml. The main issues are:

1. **AlertManager port conflict** (9094 already in use)
2. **Incorrect build contexts** for review-api and cost-api
3. **Minor configuration inconsistencies**

Once these issues are fixed, the enrichment services will work seamlessly within the existing docker-compose setup.
