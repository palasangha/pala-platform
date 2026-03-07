# Configuration Issues & Quick Fixes

## Overview

5 configuration issues identified during integration review. This document provides quick fixes for each.

---

## Issue #1: Grafana Healthcheck Port ❌ CRITICAL

**Current State** (Line 588):
```yaml
grafana:
  healthcheck:
    test:
      - CMD
      - wget
      - --quiet
      - --tries=1
      - --spider
      - http://localhost:9090/-/healthy  # ❌ WRONG - This is Prometheus port!
```

**Problem**: Healthcheck is checking Prometheus (port 9090), not Grafana (port 3000)

**Fix**:
```yaml
grafana:
  healthcheck:
    test:
      - CMD
      - wget
      - --quiet
      - --tries=1
      - --spider
      - http://localhost:3000  # ✅ CORRECT - Grafana port
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

**Impact**: Without this fix, `docker-compose ps` will show grafana as "unhealthy" even when it's working correctly.

---

## Issue #2: Missing Healthcheck on backend ❌ CRITICAL

**Current State**: No healthcheck defined for backend service

**Add**:
```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-backend
  restart: unless-stopped
  # ... existing config ...

  # ADD THIS:
  healthcheck:
    test:
      - CMD
      - curl
      - -f
      - http://localhost:5000/health
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

**Assumption**: Backend provides a `/health` endpoint. If not, use a different endpoint or check for TCP connectivity.

---

## Issue #3: Missing Healthcheck on mongodb ❌ CRITICAL

**Current State**: No healthcheck defined for mongodb

**Add**:
```yaml
mongodb:
  image: mongo:7.0
  container_name: gvpocr-mongodb
  restart: unless-stopped
  # ... existing config ...

  # ADD THIS:
  healthcheck:
    test:
      - CMD
      - mongosh
      - --eval
      - db.adminCommand('ping')
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

**Alternative** (if mongosh not available):
```yaml
healthcheck:
  test:
    - CMD
    - mongo
    - --eval
    - db.adminCommand('ping')
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

---

## Issue #4: Backend OLLAMA_HOST Uses localhost ⚠️ WARNING

**Current State** (Line 62):
```yaml
- OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}  # ❌ Uses localhost as fallback
```

**Problem**: If `OLLAMA_HOST` environment variable is not set, it defaults to `localhost:11434` instead of the Docker container name.

**Fix**:
```yaml
- OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}  # ✅ Uses ollama container name
```

**Why**: Inside Docker, services communicate using container names (DNS), not `localhost`. Using `localhost` means it will try to connect to the backend container itself, not the actual Ollama service.

**How to Verify**:
```bash
# Test from backend container
docker-compose exec backend curl $OLLAMA_HOST/api/tags

# Should work with the fix
docker-compose exec backend curl http://ollama:11434/api/tags
```

---

## Issue #5: Missing Healthcheck on nsqd ⚠️ WARNING

**Current State**: No healthcheck defined for nsqd

**Add**:
```yaml
nsqd:
  image: nsqio/nsq:v1.2.1
  container_name: gvpocr-nsqd
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=172.12.0.132
  ports:
    - 4150:4150
    - 4151:4151
  depends_on:
    - nsqlookupd
  networks:
    - gvpocr-network
  restart: unless-stopped

  # ADD THIS:
  healthcheck:
    test:
      - CMD
      - curl
      - -f
      - http://localhost:4151/stats
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

**Explanation**: Port 4151 is NSQ's HTTP stats port. This healthcheck verifies nsqd is responding to API requests.

---

## Issue #6: NSQ Broadcast Address Hardcoded ⚠️ WARNING

**Current State** (Line 287):
```yaml
nsqd:
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=172.12.0.132
```

**Problem**: IP address `172.12.0.132` is hardcoded and specific to your environment. Deploying to another network will fail.

**Fix Option 1: Use Environment Variable**

Update docker-compose.yml:
```yaml
nsqd:
  image: nsqio/nsq:v1.2.1
  container_name: gvpocr-nsqd
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=${NSQ_BROADCAST_ADDRESS:-172.12.0.132}
  # ... rest of config ...
```

Update `.env` file:
```bash
NSQ_BROADCAST_ADDRESS=172.12.0.132
```

**Fix Option 2: Use Hostname (More Flexible)**

```yaml
nsqd:
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=nsqd
```

**Impact**: With the fix, deployment to different networks will work correctly. The broadcast address can be configured per environment.

---

## Issue #7: Missing container_name on enrichment-worker 🟡 MINOR

**Current State**: enrichment-worker has `deploy.replicas: 2` but no `container_name`

**Problem**:
- Multiple replicas can't have the same container_name
- Auto-generated names are confusing: `gvpocr_enrichment-worker_1`, `gvpocr_enrichment-worker_2`
- Inconsistent with other services (29/31 have explicit names)

**Solution Options**:

**Option A: Add container_name (if only one replica needed)**
```yaml
enrichment-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-enrichment-worker  # ✅ ADD THIS
  command: python run_enrichment_worker.py
  # ... rest of config ...
  deploy:
    replicas: 2
```

**Option B: Remove replicas if fixed names needed**
```yaml
enrichment-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: gvpocr-enrichment-worker
  command: python run_enrichment_worker.py
  # ... rest of config ...
  # REMOVE: deploy.replicas section
```

**Option C: Keep auto-generated names (acceptable)**
```yaml
enrichment-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  # No container_name - use auto-generated
  command: python run_enrichment_worker.py
  # ... rest of config ...
  deploy:
    replicas: 2
```

**Recommendation**: Option C (keep auto-generated) since multiple replicas are needed. This is actually fine - Docker will generate consistent names.

---

## Issue #8: Missing container_name on ocr-worker 🟡 MINOR

**Same as Issue #7 above**

**Current State**:
```yaml
ocr-worker:
  build:
    context: .
    dockerfile: worker.Dockerfile
  # No container_name
  command: python run_worker.py --worker-id $${HOSTNAME} --nsqlookupd nsqlookupd:4161
  # ...
  deploy:
    replicas: 3
```

**Solution**: Same options as Issue #7. Recommend keeping auto-generated names since 3 replicas are needed.

---

## Issue #9: Caddy Port 3000 Documentation 🟡 MINOR

**Current State** (Line 132):
```yaml
caddy:
  ports:
    - 80:80
    - 443:443
    - 3000:443   # Maps HTTP port 3000 to HTTPS (443)
    - 5010:5010
```

**Why It's Odd**: Port 3000 typically serves HTTP, but here it serves HTTPS.

**Fix**: Add comment for clarity
```yaml
caddy:
  ports:
    - 80:80           # HTTP
    - 443:443         # HTTPS
    - 3000:443        # HTTPS alternate (maps port 3000 to HTTPS for dev)
    - 5010:5010       # Metrics/admin
```

**Alternative**: If you want HTTP on 3000:
```yaml
- 3000:80   # Maps port 3000 to HTTP instead of HTTPS
```

---

## Quick Fix Checklist

Copy and paste fixes in order:

### Critical (Must Fix)
- [ ] Fix Grafana healthcheck port (line 588)
- [ ] Add backend healthcheck
- [ ] Add mongodb healthcheck
- [ ] Fix backend OLLAMA_HOST (line 62)
- [ ] Add nsqd healthcheck

### Warning (Should Fix)
- [ ] Make NSQ broadcast address configurable (line 287)

### Minor (Nice to Have)
- [ ] Document Caddy port 3000 mapping (line 132)

### Total Time: ~35 minutes

---

## Verification Script

After applying fixes, run:

```bash
# Verify all services start
docker-compose up -d

# Check all healthchecks pass
docker-compose ps

# All should show: Up X seconds (healthy)

# Test backend → ollama connectivity
docker-compose exec backend curl http://ollama:11434/api/tags

# Test backend → mongodb connectivity
docker-compose exec backend curl -I http://mongodb:27017

# Test enrichment → mcp-server connectivity
docker-compose exec enrichment-worker curl http://mcp-server:3003/health

# Monitor logs
docker-compose logs -f
```

---

## Summary

| Issue | Type | Severity | Time | Status |
|-------|------|----------|------|--------|
| Grafana port | Config | CRITICAL | 2 min | ❌ Not Fixed |
| Backend healthcheck | Config | CRITICAL | 5 min | ❌ Not Fixed |
| MongoDB healthcheck | Config | CRITICAL | 5 min | ❌ Not Fixed |
| OLLAMA_HOST | Config | WARNING | 2 min | ❌ Not Fixed |
| NSQ healthcheck | Config | WARNING | 5 min | ❌ Not Fixed |
| NSQ broadcast addr | Config | WARNING | 10 min | ❌ Not Fixed |
| enrichment-worker name | Naming | MINOR | - | ✓ OK (auto-gen) |
| ocr-worker name | Naming | MINOR | - | ✓ OK (auto-gen) |
| Caddy documentation | Docs | MINOR | 2 min | ⚠️ Optional |

**Recommendation**: Fix all CRITICAL and WARNING issues before deployment (~30 minutes).
