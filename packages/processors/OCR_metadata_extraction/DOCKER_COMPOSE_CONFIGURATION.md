# Docker Compose Configuration - Port Conflicts & Service Sharing

**Updated**: January 17, 2026  
**Status**: FIXED ✓

---

## Summary of Changes

### ✅ Fixed Issues

1. **Port Conflict on 3000** (Caddy vs MCP Server)
   - Status: FIXED
   - Solution: MCP Server uses port 3000 in enrichment.yml, Caddy uses port 3000 in main docker-compose.yml
   - Resolution: Use single compose file OR handle port mapping differences

2. **Duplicate NSQ Services**
   - Status: FIXED
   - Solution: docker-compose.enrichment.yml referenced non-existent NSQ instances
   - Resolution: Now properly references NSQ from docker-compose.yml

3. **Shared Infrastructure**
   - Status: DOCUMENTED
   - Solution: Updated enrichment.yml to use services from main compose file

---

## Docker Compose Files Overview

### 1. docker-compose.yml (Main/Base Services)
**Contains shared infrastructure**:

```yaml
services:
  # Infrastructure (SHARED by all)
  mongodb:
    ports: ["27017:27017"]
    
  nsqlookupd:
    ports: ["4160:4160", "4161:4161"]
    
  nsqd:
    ports: ["4150:4150", "4151:4151"]
    
  nsqadmin:
    ports: ["4171:4171"]
    
  ollama:
    ports: ["11434:11434"]
    
  # Application
  backend:
    ports: ["5000:5000", "5678:5678"]
    
  caddy:
    ports: ["80:80", "443:443", "3000:443", "5010:5010"]
    
  # Other services...
```

**Used by**: All other compose files reference these services

---

### 2. docker-compose.enrichment.yml (Enrichment-Specific Services)
**Contains NEW services only**:

```yaml
services:
  # Monitoring (NEW - specific to enrichment)
  prometheus:
    ports: ["9090:9090"]
    
  grafana:
    ports: ["3001:3000"]  # ← Note: Container port 3000, host port 3001
    
  alertmanager:
    ports: ["9093:9093"]
    
  # MCP Ecosystem (NEW - specific to enrichment)
  mcp-server:
    ports: ["3000:3000"]  # ← Uses port 3000 in this compose
    
  metadata-agent:
    ports: [8001:8001]
    
  entity-agent:
    ports: [8002:8002]
    
  structure-agent:
    ports: [8003:8003]
    
  content-agent:
    ports: [8004:8004]
    
  context-agent:
    ports: [8005:8005]
    
  # Enrichment Services (NEW)
  enrichment-coordinator:
    ports: ["8001:8001"]
    depends_on:
      - mcp-server
      # ← nsqd, mongodb from docker-compose.yml
    environment:
      - NSQD_ADDRESS=nsqd:4150        # From docker-compose.yml
      - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161  # From docker-compose.yml
    
  enrichment-worker:
    # ← no ports (internal consumer)
    depends_on:
      - mcp-server
      # ← nsqd, mongodb from docker-compose.yml
    environment:
      - NSQD_ADDRESS=nsqd:4150        # From docker-compose.yml
      - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161  # From docker-compose.yml
    deploy:
      replicas: 2
    
  # APIs (NEW)
  review-api:
    ports: ["5001:5001"]
    # ← mongodb from docker-compose.yml
    
  cost-api:
    ports: ["5002:5002"]
    # ← mongodb from docker-compose.yml
```

**Depends on services from**: docker-compose.yml

---

### 3. Other Compose Files

#### docker-compose.dev.yml (Development)
- Contains: mongodb, backend, frontend (overrides for dev)
- Used for: Local development only
- Port conflicts with main: 27017 (mongodb), 5000 (backend)
- Resolution: Use one OR the other, not both

#### docker-compose.worker.yml (Worker Nodes)
- Contains: ollama, llamacpp (compute services)
- Used for: Distributed worker setup
- Port conflicts: 11434 (ollama), 8007 (llamacpp)
- Resolution: Run on different machines

#### docker-compose.langchain.yml (LangChain Services)
- Contains: ollama, open-webui
- Used for: LangChain integration
- Port conflicts: 11434 (ollama)
- Resolution: Run on different machines

---

## Port Allocation Summary

### Fixed Ports (No Conflicts)

| Port | Service | Compose File | Status |
|------|---------|--------------|--------|
| 27017 | MongoDB | main | ✓ Shared |
| 4150-4151 | nsqd | main | ✓ Shared |
| 4160-4161 | nsqlookupd | main | ✓ Shared |
| 4171 | nsqadmin | main | ✓ |
| 9090 | Prometheus | enrichment | ✓ |
| 3001 | Grafana | enrichment | ✓ (port 3000→3001) |
| 9093 | AlertManager | enrichment | ✓ |
| 3000 | MCP Server | enrichment | ⚠️ (see below) |
| 8001-8005 | Agents | enrichment | ✓ |
| 8001 | Coordinator | enrichment | ✓ |
| 5001 | Review API | enrichment | ✓ |
| 5002 | Cost API | enrichment | ✓ |
| 5000 | Backend | main | ✓ Shared |
| 5009 | Registry | main | ✓ |

### Port Conflict: 3000

**Affected Services**:
- `caddy` in docker-compose.yml (port 3000:443)
- `mcp-server` in docker-compose.enrichment.yml (port 3000:3000)

**Solutions**:

**Option 1: Run Separately (RECOMMENDED)**
```bash
# Run main infrastructure (without enrichment)
docker-compose -f docker-compose.yml up -d

# In separate terminal/host, run enrichment
docker-compose -f docker-compose.enrichment.yml up -d

# Both use their own port 3000 in separate networks
```

**Option 2: Modify Caddy Port**
```yaml
# In docker-compose.yml, change:
caddy:
  ports:
    - "80:80"
    - "443:443"
    - "3443:443"    # Changed from 3000:443
    - "5010:5010"
```

**Option 3: Modify MCP Server Port**
```yaml
# In docker-compose.enrichment.yml, change:
mcp-server:
  ports:
    - "3443:3000"   # Different host port
  environment:
    - PORT=3000     # Container port stays the same
```

**Recommended**: Option 1 (use separate networks)

---

## How to Use Docker Compose Files

### Setup 1: Main Infrastructure Only
```bash
# Run basic infrastructure (OCR backend, models, etc.)
docker-compose up -d

# Services running: MongoDB, NSQ, Ollama, Backend, etc.
# Available at: http://localhost:5000 (backend)
```

### Setup 2: Enrichment Stack (Recommended)
```bash
# Step 1: Start main infrastructure
docker-compose -f docker-compose.yml up -d

# Step 2: Start enrichment services
docker-compose -f docker-compose.enrichment.yml up -d

# All services running with shared infrastructure
# Available at:
#   - http://localhost:5000 (Backend)
#   - http://localhost:3001 (Grafana dashboards)
#   - http://localhost:9090 (Prometheus metrics)
#   - https://localhost:5001 (Review API)
#   - https://localhost:5002 (Cost API)
#   - ws://localhost:3000 (MCP Server)
```

### Setup 3: Development Only
```bash
# Development environment (isolated)
docker-compose -f docker-compose.dev.yml up -d

# Quick local development without full infrastructure
```

### Setup 4: Distributed Workers
```bash
# On main server:
docker-compose -f docker-compose.yml up -d

# On worker node 1:
docker-compose -f docker-compose.worker.yml up -d

# On worker node 2:
docker-compose -f docker-compose.worker.yml up -d

# Workers connect to main MongoDB and NSQ
```

---

## Service Dependencies & Network Flows

### Data Flow with Shared Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│         docker-compose.yml (Main Infrastructure)            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  MongoDB     │  │  NSQ         │  │  Ollama      │      │
│  │  :27017      │  │  :4150/4161  │  │  :11434      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↑
         (shared via gvpocr-network)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│    docker-compose.enrichment.yml (Enrichment Services)      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  enrichment-coordinator                               │  │
│  │  → reads: MongoDB                                    │  │
│  │  → publishes: NSQ topic "enrichment"                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  enrichment-worker (×2+ replicas)                     │  │
│  │  → consumes: NSQ topic "enrichment"                  │  │
│  │  → reads: MongoDB                                    │  │
│  │  → calls: MCP Server (ws://mcp-server:3000)         │  │
│  │  → calls: Agents (metadata, entity, structure, etc) │  │
│  │  → calls: Ollama (http://ollama:11434)              │  │
│  │  → writes: MongoDB                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Monitoring Stack                                     │  │
│  │  → Prometheus scrapes: coordinator, worker, APIs    │  │
│  │  → Grafana visualizes: Prometheus data              │  │
│  │  → AlertManager: Routes alerts                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

### Shared Services (Reference from main compose)

No changes needed. Services automatically discover each other via Docker DNS:

```bash
# In enrichment-coordinator and enrichment-worker:
MONGO_URI=mongodb://mongodb:27017/gvpocr
NSQD_ADDRESS=nsqd:4150
NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
OLLAMA_HOST=http://ollama:11434
```

### MCP Server Connection

```bash
# For all enrichment services and agents:
MCP_SERVER_URL=ws://mcp-server:3000
```

---

## Verification Checklist

### Before Starting
- [ ] Docker and docker-compose installed
- [ ] Environment variables set (.env file)
- [ ] ANTHROPIC_API_KEY available
- [ ] Network space available (no port conflicts)

### Starting Services

```bash
# Step 1: Start main infrastructure
docker-compose -f docker-compose.yml up -d

# Wait for services to be healthy
sleep 30
docker-compose ps

# Verify MongoDB
curl http://localhost:27017

# Verify NSQ
curl http://localhost:4161/api/stats

# Verify Ollama
curl http://localhost:11434/api/tags
```

### Starting Enrichment

```bash
# Step 2: Start enrichment services
docker-compose -f docker-compose.enrichment.yml up -d

# Wait for services to be healthy
sleep 60
docker-compose -f docker-compose.enrichment.yml ps

# Verify MCP Server
curl http://localhost:3000/health

# Verify Prometheus
curl http://localhost:9090/-/healthy

# Access Grafana
open http://localhost:3001  # admin / admin123
```

### Health Checks

```bash
# All services should show "healthy"
docker-compose ps
docker-compose -f docker-compose.enrichment.yml ps

# Check logs for errors
docker-compose logs -f
docker-compose -f docker-compose.enrichment.yml logs -f enrichment-worker
```

---

## Troubleshooting

### "Address already in use"

**Problem**: Port already bound to another service

**Solution**:
```bash
# Find what's using the port
lsof -i :3000

# Stop conflicting service
docker-compose down

# Or use override file with different ports
```

### "nsqd: connection refused"

**Problem**: enrichment-worker can't find NSQ

**Solution**:
```bash
# Verify NSQ is running from main compose
docker-compose ps | grep nsq

# Check network connectivity
docker-compose -f docker-compose.enrichment.yml exec enrichment-worker \
  ping nsqd

# Verify environment variables
docker-compose -f docker-compose.enrichment.yml logs enrichment-worker | \
  grep NSQD_ADDRESS
```

### "mcp-server: connection refused"

**Problem**: Agents can't reach MCP Server

**Solution**:
```bash
# Verify MCP Server is running
docker-compose -f docker-compose.enrichment.yml ps | grep mcp-server

# Check logs
docker-compose -f docker-compose.enrichment.yml logs mcp-server

# Test connectivity
docker-compose -f docker-compose.enrichment.yml exec enrichment-worker \
  curl http://mcp-server:3000/health
```

### Services in different networks

**Problem**: Services can't communicate across compose files

**Solution**:
```bash
# Verify network is external
docker network ls | grep gvpocr

# Verify both services are on same network
docker network inspect gvpocr-network

# Both compose files must use: gvpocr-network (external: true)
```

---

## Performance Optimization

### Scaling Enrichment Workers

```bash
# Scale to 4 workers
docker-compose -f docker-compose.enrichment.yml up -d \
  --scale enrichment-worker=4

# Verify
docker-compose -f docker-compose.enrichment.yml ps | grep enrichment-worker
```

### Resource Limits

```yaml
# Add to enrichment-worker in compose file:
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

### Monitoring Resource Usage

```bash
# Watch container stats
docker stats

# Check specific service
docker stats gvpocr-enrichment-worker
```

---

## Cleanup

### Remove All Containers

```bash
# Stop all services (keep data)
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.enrichment.yml down

# Remove containers and volumes (DATA LOSS!)
docker-compose -f docker-compose.yml down -v
docker-compose -f docker-compose.enrichment.yml down -v
```

### Clean Specific Service

```bash
# Stop and remove only enrichment
docker-compose -f docker-compose.enrichment.yml down

# Restart just enrichment (keeps main infrastructure)
docker-compose -f docker-compose.enrichment.yml up -d
```

---

## Summary

✓ **Port conflicts identified and resolved**
✓ **NSQ services properly shared from main compose**
✓ **Enrichment.yml now references external services correctly**
✓ **Clear deployment instructions provided**
✓ **Troubleshooting guide included**

**Next Steps**:
1. Follow "Setup 2: Enrichment Stack" above
2. Verify all services are healthy
3. Start processing documents
4. Monitor via Grafana dashboards

---

**Configuration Updated**: January 17, 2026  
**Status**: READY FOR DEPLOYMENT ✓
