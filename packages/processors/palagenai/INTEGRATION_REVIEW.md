# Docker Compose Integration Review

**Date**: January 19, 2026
**Status**: ✅ INTEGRATION COMPLETE with ISSUES IDENTIFIED
**Reviewed**: docker-compose.yml (merged from enrichment)

---

## Executive Summary

All services from `docker-compose.enrichment.yml` have been successfully integrated into `docker-compose.yml`. The consolidated compose file now contains **31 services** across 6 categories. However, **5 configuration issues** were identified that should be addressed for production deployment.

---

## 1. Integration Status ✅

### Services Successfully Merged

**From docker-compose.enrichment.yml:**
- ✅ Monitoring: prometheus, grafana, alertmanager
- ✅ Enrichment: enrichment-coordinator, enrichment-worker
- ✅ Agents: metadata-agent, entity-agent, structure-agent, content-agent, context-agent
- ✅ APIs: review-api, cost-api
- ✅ MCP Server: mcp-server

**Original Services (Preserved):**
- ✅ Infrastructure: mongodb, nsqlookupd, nsqd, nsqadmin
- ✅ Core: backend, frontend, caddy
- ✅ Models: ollama, llamacpp, vllm, lmstudio, open-webui
- ✅ Workers: ocr-worker, result-aggregator
- ✅ File Services: samba, ssh-server, file-server
- ✅ Registry: registry

**Total: 31 Services**

---

## 2. Port Analysis ✅

### All Ports Allocated (No Conflicts)

| Port | Service | Status |
|------|---------|--------|
| 80, 443 | caddy (Web) | ✓ |
| 3000 | caddy (HTTPS Alt) | ⚠️ See Issue #7 |
| 3001 | grafana | ✓ |
| 3003 | mcp-server | ✓ |
| 5000 | backend | ✓ |
| 5001 | review-api | ✓ |
| 5002 | cost-api | ✓ |
| 5678 | backend (Debug) | ✓ |
| 5009 | registry | ✓ |
| 5010 | caddy (Alt) | ✓ |
| 8001 | enrichment-coordinator | ✓ |
| 8007 | llamacpp | ✓ |
| 8010 | file-server | ✓ |
| 8000 | vllm | ⚠️ See Issue #5 |
| 8080 | open-webui | ✓ |
| 9090 | prometheus | ✓ |
| 9093 | alertmanager | ✓ |
| 11434 | ollama | ✓ |
| 27017 | mongodb | ✓ |
| 4150-4161 | NSQ services | ✓ |
| 4171 | nsqadmin | ✓ |
| 1234 | lmstudio | ✓ |
| 2222 | ssh-server | ✓ |
| 13137-13445 | samba | ✓ |

**Conclusion**: No port conflicts. All ports are unique.

---

## 3. Service Dependencies ✅

### Dependency Tree (All Valid)

```
mongodb
├── backend
│   ├── frontend
│   │   └── caddy
│   └── caddy
├── cost-api
├── enrichment-coordinator
│   └── mcp-server
│       ├── metadata-agent
│       ├── entity-agent
│       ├── structure-agent
│       ├── content-agent
│       └── context-agent
├── enrichment-worker
│   └── mcp-server
├── ocr-worker
│   ├── nsqd
│   │   └── nsqlookupd
│   └── ollama
├── result-aggregator
│   └── nsqd
└── review-api

prometheus
└── grafana

ollama
└── open-webui
```

**Status**: ✅ All dependencies exist. No circular dependencies.

---

## 4. Issues Found & Recommendations

### 🔴 CRITICAL ISSUES (Must Fix)

#### Issue #1: Grafana Healthcheck Points to Wrong Port
**Location**: docker-compose.yml:588
**Problem**: Grafana healthcheck checks `http://localhost:9090` (Prometheus port)
**Should be**: `http://localhost:3000` (Grafana port)

**Fix Required**:
```yaml
grafana:
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000"]
```

**Impact**: Grafana healthcheck will always fail until fixed

---

#### Issue #2: Critical Services Missing Healthcheck
**Location**: Multiple services

**Services Affected**:
- `backend` (port 5000) - Main API
- `mongodb` (port 27017) - Database
- `nsqd` (port 4150) - Message queue

**Why It Matters**:
- Docker can't properly detect service failures
- Orchestration tools can't auto-restart failed services
- No visibility into service readiness

**Recommended Action**: Add healthchecks
```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s

mongodb:
  healthcheck:
    test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s

nsqd:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:4151/stats"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

---

### 🟠 WARNING ISSUES (Should Fix)

#### Issue #3: Backend OLLAMA_HOST Uses localhost
**Location**: docker-compose.yml:62
**Current**: `OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}`
**Problem**: Default uses `localhost` instead of container name

**Fix Required**:
```yaml
- OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
```

**Impact**: If OLLAMA_HOST env var not set, backend won't find Ollama service

---

#### Issue #4: NSQ Broadcast Address Hardcoded
**Location**: docker-compose.yml:287
**Current**: `/nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=172.12.0.132`
**Problem**: IP `172.12.0.132` is specific to your environment

**Fix Required**:
Make it configurable:
```yaml
nsqd:
  command: /nsqd --lookupd-tcp-address=nsqlookupd:4160 --broadcast-address=${NSQ_BROADCAST_ADDRESS:-172.12.0.132}
```

Add to `.env`:
```
NSQ_BROADCAST_ADDRESS=172.12.0.132
```

**Impact**: Deployment to different networks will fail

---

### 🟡 MINOR ISSUES (Nice to Have)

#### Issue #5: Two Services Missing container_name
**Services**:
- `enrichment-worker`
- `ocr-worker`

**Current**: Auto-generated names (e.g., `gvpocr_enrichment-worker_1`, `gvpocr_enrichment-worker_2`)

**Why It Matters**:
- Makes container references harder
- Difficult to target specific replicas
- Inconsistent with other services (29 have explicit names)

**Fix Required**:
```yaml
enrichment-worker:
  container_name: gvpocr-enrichment-worker
  # Note: If you need replicas, use deploy.replicas instead

ocr-worker:
  container_name: gvpocr-ocr-worker
```

**Note**: If services use replicas (deploy), you can't use fixed container_name for multiple instances.

---

#### Issue #6: vllm and llamacpp Port Conflict
**Status**: ✅ Actually OK

Both use port 8000 internally but different host ports:
- `llamacpp`: 8007:8000 ✓
- `vllm`: 8000:8000 ✓

Both can run simultaneously. No action needed.

---

#### Issue #7: Caddy Port Mapping is Unconventional
**Ports**: `3000:443` (maps HTTP port 3000 to HTTPS 443)

**Why It's Odd**:
- Port 3000 typically serves HTTP
- This serves HTTPS instead
- Should document this clearly

**Recommendation**: Add comment to docker-compose.yml:
```yaml
caddy:
  ports:
    - 80:80      # HTTP
    - 443:443    # HTTPS
    - 3000:443   # HTTPS alternate (for development)
    - 5010:5010  # Metrics/admin
```

---

## 5. Configuration Summary

### Environment Variables

**Services using MongoDB**: 7 services
- backend, cost-api, enrichment-coordinator, enrichment-worker, ocr-worker, result-aggregator, review-api

**Services using NSQ**: 5 services
- backend, enrichment-coordinator, enrichment-worker, ocr-worker, result-aggregator

**Services using MCP Server**: 6 services
- enrichment-coordinator, enrichment-worker, metadata-agent, entity-agent, structure-agent, content-agent, context-agent

### Restart Policies

✅ All 31 services: `restart: unless-stopped`

### Health Checks

- **WITH healthcheck**: 19 services ✅
- **WITHOUT healthcheck**: 12 services ⚠️
  - Critical: backend, mongodb, nsqd (should have healthcheck)
  - Non-critical: frontend, caddy, registry, samba, ssh-server, etc. (OK)

### Container Building

- **Pre-built images**: 15 services (ollama, prometheus, mysql, etc.)
- **Build locally**: 16 services (backend, frontend, agents, etc.)

---

## 6. Data Persistence

### Volumes Defined

All volumes properly defined:
- mongodb_data, mongodb_config (Database)
- prometheus_data, grafana_data, grafana_provisioning, alertmanager_data (Monitoring)
- registry_data (Container Registry)
- ollama_data, vllm_cache (ML Models)
- caddy_data, caddy_config, caddy_logs (Web Server)
- open_webui_data (WebUI)
- bhushanji_shared (Bind mount to ${GVPOCR_PATH})

**Status**: ✅ All volumes properly configured for data persistence

---

## 7. Network Configuration

### Networks

```yaml
networks:
  gvpocr-network:
    driver: bridge           # Internal communication
  archipelago-network:
    external: true          # External integration
    name: archipelago-deployment_esmero-net
```

**Status**: ✅ Properly configured for internal and external communication

---

## 8. Recommended Actions (Priority Order)

### Priority 1: CRITICAL (Fix Before Deployment)

1. ✏️ **Fix Grafana healthcheck port** (Issue #1)
   - Change line 588 from `9090` to `3000`
   - Time: 2 minutes

2. ✏️ **Add healthcheck to backend** (Issue #2)
   - Time: 5 minutes

3. ✏️ **Add healthcheck to mongodb** (Issue #2)
   - Time: 5 minutes

4. ✏️ **Fix backend OLLAMA_HOST default** (Issue #3)
   - Change line 62 from `localhost` to `ollama`
   - Time: 2 minutes

### Priority 2: HIGH (Should Fix Before Production)

5. ✏️ **Add healthcheck to nsqd** (Issue #2)
   - Time: 5 minutes

6. ✏️ **Make NSQ broadcast address configurable** (Issue #4)
   - Time: 10 minutes
   - Add environment variable

### Priority 3: MEDIUM (Nice to Have)

7. 📝 **Add container_name to enrichment-worker and ocr-worker** (Issue #5)
   - Consider if replicas are needed first
   - Time: 5 minutes

8. 📝 **Document Caddy port 3000 mapping** (Issue #7)
   - Time: 2 minutes

---

## 9. Testing Checklist

After fixing issues, verify:

- [ ] All containers start: `docker-compose up -d`
- [ ] All healthchecks pass: `docker-compose ps` (all showing "healthy")
- [ ] Services communicate:
  ```bash
  docker-compose exec backend curl http://ollama:11434/api/tags
  docker-compose exec backend curl http://mongodb:27017
  docker-compose exec enrichment-worker curl http://mcp-server:3003/health
  ```
- [ ] Monitoring stack accessible:
  - [ ] Prometheus: http://localhost:9090
  - [ ] Grafana: http://localhost:3001
  - [ ] AlertManager: http://localhost:9093
- [ ] APIs accessible:
  - [ ] Backend: http://localhost:5000
  - [ ] Review API: https://localhost:5001
  - [ ] Cost API: https://localhost:5002

---

## 10. Deployment Notes

### Single-File Deployment

✅ **Simplified Deployment**

Old way (with separate enrichment.yml):
```bash
docker-compose -f docker-compose.yml -f docker-compose.enrichment.yml up -d
```

New way (unified):
```bash
docker-compose up -d
```

### Resource Requirements

- **Total Services**: 31
- **Core Services**: 15
- **ML/AI Services**: 6 (ollama, llamacpp, vllm, lmstudio, open-webui, mcp-server)
- **Monitoring**: 3 (prometheus, grafana, alertmanager)
- **Enrichment**: 2 (enrichment-coordinator, enrichment-worker with 2 replicas)
- **Agents**: 5 (metadata, entity, structure, content, context)

**Estimated Resource Usage**:
- CPU: 8-16 cores (depending on load)
- Memory: 32-64GB (ML models consume most)
- Disk: 200GB+ (for model caches and data)

---

## 11. Summary

| Aspect | Status | Details |
|--------|--------|---------|
| Integration | ✅ Complete | All services merged successfully |
| Port Mapping | ✅ Good | No conflicts, all unique |
| Dependencies | ✅ Valid | All dependencies exist, no circular deps |
| Health Checks | ⚠️ Partial | 19/31 have checks, 3 critical missing |
| Configuration | ⚠️ Issues | 5 configuration issues identified |
| Data Persistence | ✅ Complete | All volumes properly configured |
| Network Setup | ✅ Good | Proper isolation and external connectivity |
| Documentation | ✅ Complete | This review document |

**Overall Assessment**: ✅ **INTEGRATION SUCCESSFUL** with **5 identified issues to fix** before production use.

---

## 12. Files Modified

- ✅ `/docker-compose.yml` - Merged all enrichment services
- ✅ Deleted `/docker-compose.enrichment.yml` - No longer needed
- ✅ Created this review document for reference

---

**Next Step**: Address the 5 issues listed in Section 8, then verify with the testing checklist in Section 9.
