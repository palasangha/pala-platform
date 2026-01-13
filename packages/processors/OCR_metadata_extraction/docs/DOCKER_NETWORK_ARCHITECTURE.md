# Docker Internal Network Architecture - GVPOCR

## 🎯 Overview

The system now uses Docker internal networking with proxy services to maintain service isolation while allowing cross-machine worker communication.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN SERVER (172.12.0.132)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Docker Bridge Network: gvpocr_gvpocr-network (172.23.0.0/16)
│  ├─ gvpocr-mongodb      (27017)                             │
│  ├─ gvpocr-nsqd        (4150/4151)                          │
│  ├─ gvpocr-nsqlookupd  (4160/4161)                          │
│  ├─ gvpocr-backend     (5000)                               │
│  ├─ gvpocr-frontend    (80/443)                             │
│  └─ gvpocr-samba       (13445)                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
              ↑
              │ Network Bridge (socat proxies)
              │
┌─────────────────────────────────────────────────────────────┐
│  REMOTE WORKERS (172.12.0.83 - Mac)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Docker Bridge Network: worker-network                       │
│  ├─ Proxy Services:                                         │
│  │  ├─ gvpocr-mongodb-proxy      (127.0.0.1:27017)        │
│  │  ├─ gvpocr-nsqd-proxy         (127.0.0.1:4150)         │
│  │  └─ gvpocr-nsqlookupd-proxy   (127.0.0.1:4161)         │
│  │                                                           │
│  └─ Worker Services:                                        │
│     ├─ gvpocr-worker-worker1-1   (OCR Worker 1)            │
│     ├─ gvpocr-worker-worker2-1   (OCR Worker 2)            │
│     └─ gvpocr-worker-worker3-1   (OCR Worker 3)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📡 Communication Flow

### Worker → Services

1. **Worker initiates connection**
   ```
   Worker Container → Docker Network Interface
   ```

2. **Service Discovery**
   ```
   Worker connects to: mongodb-proxy:27017
   (instead of: 172.12.0.132:27017)
   ```

3. **Proxy forwarding**
   ```
   socat container forwards traffic:
   mongodb-proxy:27017 → TCP4:172.12.0.132:27017
   ```

4. **Main Server Response**
   ```
   MongoDB returns response → Proxy → Worker
   ```

### Architecture Benefits

| Aspect | Benefit |
|--------|---------|
| **Isolation** | Services isolated in separate Docker networks |
| **Discovery** | Container names used for service lookup |
| **Flexibility** | Easy to add/remove workers or scale services |
| **Security** | Services not directly exposed to external IPs |
| **Maintenance** | Changes in main server don't affect worker configs |

## 🔧 Configuration

### Main Server (docker-compose.yml)

**Network Definition:**
```yaml
networks:
  gvpocr-network:
    driver: bridge
    # Services automatically assigned to this network
```

**Services on Network:**
- `mongodb`: Container DNS resolves to gvpocr-mongodb
- `nsqd`: Container DNS resolves to gvpocr-nsqd
- `nsqlookupd`: Container DNS resolves to gvpocr-nsqlookupd
- All other services connected via this network

### Remote Workers (docker-compose.worker.yml)

**Proxy Services:**
```yaml
mongodb-proxy:
  image: alpine:latest
  command: socat TCP4-LISTEN:27017,reuseaddr,fork TCP4:172.12.0.132:27017
  networks:
    - worker-network

nsqd-proxy:
  image: alpine:latest
  command: socat TCP4-LISTEN:4150,reuseaddr,fork TCP4:172.12.0.132:4150
  networks:
    - worker-network

nsqlookupd-proxy:
  image: alpine:latest
  command: socat TCP4-LISTEN:4161,reuseaddr,fork TCP4:172.12.0.132:4161
  networks:
    - worker-network
```

**Worker Services:**
```yaml
worker1:
  environment:
    # Internal network addresses (via proxies)
    - MONGO_URI=mongodb://gvpocr_admin:gvp%40123@mongodb-proxy:27017/gvpocr
    - NSQD_ADDRESS=nsqd-proxy:4150
    - NSQLOOKUPD_ADDRESSES=nsqlookupd-proxy:4161
  networks:
    - worker-network
```

## 🚀 Service Startup

### Main Server
```bash
cd /mnt/sda1/mango1_home/gvpocr
docker-compose up -d
```

Services start on internal network with DNS names:
- gvpocr-mongodb
- gvpocr-nsqd
- gvpocr-nsqlookupd

### Remote Workers
```bash
cd ~/gvpocr-worker
docker-compose -f docker-compose.worker.yml up -d
```

Proxy services start first, then workers connect via internal network.

## 🔍 Monitoring

### Check Main Server Services
```bash
docker network inspect gvpocr_gvpocr-network
```

Output shows all connected services and their internal IPs.

### Check Worker Proxies
```bash
ssh tod@172.12.0.83 "cd ~/gvpocr-worker && docker-compose -f docker-compose.worker.yml logs mongodb-proxy"
```

### Check Worker Connections
```bash
ssh tod@172.12.0.83 "cd ~/gvpocr-worker && docker-compose -f docker-compose.worker.yml logs worker1"
```

Look for:
```
connection successful
```

## 🛠️ Troubleshooting

### Workers can't connect to services

1. **Check proxy services running**
   ```bash
   docker-compose -f docker-compose.worker.yml ps | grep proxy
   ```

2. **Check proxy logs**
   ```bash
   docker-compose -f docker-compose.worker.yml logs mongodb-proxy
   ```

3. **Check worker connectivity to proxy**
   ```bash
   docker-compose -f docker-compose.worker.yml exec worker1 nc -zv mongodb-proxy 27017
   ```

### Network latency issues

- Proxies use socat (lightweight Unix forwarding)
- Typical overhead: <1ms per connection
- Multiple connections may add latency

### Services not discovered

- Ensure services are on `gvpocr-network` on main server
- Ensure proxies are on `worker-network` on remote machine
- Container names must match in environment variables

## 📊 Network Ports

### Main Server Exposed Ports
| Port | Service | Purpose |
|------|---------|---------|
| 27017 | MongoDB | Database |
| 4150 | NSQ Daemon | Task queue |
| 4161 | NSQ Lookupd | Service discovery |
| 5000 | Backend API | REST API |
| 80/443 | Frontend | Web UI |
| 13445 | Samba | File sharing |

### Remote Worker Exposed Ports
| Port | Service | Purpose |
|------|---------|---------|
| 27017 | MongoDB Proxy | Database access |
| 4150 | NSQ Daemon Proxy | Task queue access |
| 4161 | NSQ Lookupd Proxy | Service discovery |

## 🔐 Security Considerations

1. **Network Isolation**: Services on internal Docker network, not exposed on host
2. **Proxy Forwarding**: All traffic tunneled through socat proxies
3. **Authentication**: MongoDB requires credentials even on internal network
4. **Firewall**: Only proxy ports exposed on remote machine

## 🚀 Future Improvements

1. **Docker Overlay Networks**: Use overlay networks for better performance
2. **Service Mesh**: Consider Istio or Linkerd for advanced routing
3. **DNS External Service**: Create DNS entry for internal service discovery
4. **Load Balancing**: Add load balancer service in front of workers

---

**Status**: ✅ **OPERATIONAL**

All workers connected via Docker internal network architecture with proxy services.
