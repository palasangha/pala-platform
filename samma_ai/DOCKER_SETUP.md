# 🐳 Samma AI - Docker Setup Guide

## Overview

This guide covers containerizing the Samma AI project with Docker and Docker Compose. The setup includes:

- **Backend**: Flask REST API (port 5001)
- **Frontend**: Flutter Web served via Nginx (port 8080)
- **MongoDB**: App database (custom port 27018)
- **Qdrant**: Vector database (custom port 6334)

---

## Prerequisites

- Docker >= 20.10
- Docker Compose >= 2.0
- 4GB+ RAM available
- Tipitaka database file: `database/tipitaka_ultimate.db`

### Check Installation

```bash
docker --version
docker-compose --version
```

---

## Quick Start

### 1. Prepare Environment

```bash
# Copy Docker configuration
cp .env.docker .env

# Edit .env with your API keys
nano .env
```

### 2. Build Services

```bash
# Build all services
docker-compose build

# Or build specific service
docker-compose build backend
docker-compose build frontend
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
docker-compose logs -f qdrant
```

### 4. Check Health

```bash
# Check all services
docker-compose ps

# Check backend health
curl http://localhost:5001/api/health

# Check frontend
curl http://localhost:8080

# Check MongoDB
mongosh mongodb://localhost:27018/samma_ai

# Check Qdrant
curl http://localhost:6334/health
```

### 5. Stop Services

```bash
# Stop all services (keep data)
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

---

## Port Configuration

| Service | Internal Port | External Port | Usage |
|---------|---------------|---------------|-------|
| Backend | 5001 | 5001 | Flask API |
| Frontend | 80 | 8080 | Nginx (Flutter Web) |
| MongoDB | 27017 | 27018 | App database |
| Qdrant | 6333 | 6334 | Vector database |

### Why Custom Ports?

- **MongoDB 27018**: Avoid conflicts with local MongoDB instances
- **Qdrant 6334**: Avoid conflicts with local Qdrant instances
- This allows running both Docker containers and local services simultaneously

---

## Environment Configuration

### Required Variables

Edit `.env` before starting:

```bash
# API Keys (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# Optional: Local Model
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Optional: OpenAI or Copilot
OPENAI_API_KEY=
COPILOT_API_KEY=
```

### Key Points

- `OLLAMA_BASE_URL=http://host.docker.internal:11434` allows Docker containers to access host's Ollama
- All database URLs inside containers use Docker service names (e.g., `mongodb:27017`)
- CORS is configured to allow frontend → backend communication

---

## Docker Compose Services

### Backend Service

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "5001:5001"
    depends_on:
      - mongodb
      - qdrant
    environment:
      MONGO_URI: mongodb://mongodb:27017/samma_ai
      QDRANT_HOST: qdrant
      QDRANT_PORT: 6333
```

**Features**:
- Multi-stage build (reduces image size)
- Health checks enabled
- Volume mounts for development
- Depends on MongoDB and Qdrant being healthy

### Frontend Service

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
```

**Features**:
- Builds Flutter web app to static files
- Serves via Nginx with API proxy
- Automatically proxies `/api/*` to backend
- Configurable CORS

### MongoDB Service

```yaml
services:
  mongodb:
    image: mongo:7.0-alpine
    ports:
      - "27018:27017"  # Custom external port
```

**Features**:
- Alpine Linux image (small footprint)
- Data persisted in `mongodb_data` volume
- Health checks enabled
- No authentication by default (development)

### Qdrant Service

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"  # Custom external port
```

**Features**:
- Latest Qdrant image
- Data persisted in `qdrant_data` volume
- Health checks enabled
- API key support

---

## Development Workflow

### Running with Live Code Updates

The backend service has volume mounts for development:

```yaml
volumes:
  - ./backend/app:/app/app       # Source code
  - ./backend/config:/app/config # Configuration
  - ./database:/app/database:ro  # Read-only database
```

**Changes to Python files** are reflected immediately in development mode.

### Rebuild Backend After Dependency Changes

```bash
# Update requirements.txt
nano backend/requirements.txt

# Rebuild backend image
docker-compose build backend

# Restart backend service
docker-compose up -d backend
```

### Access MongoDB During Development

```bash
# From host machine
mongosh mongodb://localhost:27018/samma_ai

# Check collections
db.getCollectionNames()

# View conversations
db.conversations.find().pretty()
```

### Access Qdrant During Development

```bash
# Check collections
curl http://localhost:6334/collections

# Check specific collection
curl http://localhost:6334/collections/tipitaka_mula

# Check collection points (embeddings count)
curl http://localhost:6334/collections/tipitaka_mula/points/count
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs -f <service-name>

# Example: Backend logs
docker-compose logs -f backend

# Check specific error
docker-compose logs backend | grep -i error
```

### Port Already in Use

```bash
# Check which process is using port
lsof -i :5001    # Backend
lsof -i :8080    # Frontend
lsof -i :27018   # MongoDB
lsof -i :6334    # Qdrant

# Kill process or change port in docker-compose.yml
```

### MongoDB Connection Error

```bash
# Check MongoDB is running
docker-compose ps mongodb

# Check MongoDB logs
docker-compose logs mongodb

# Verify from host
mongosh mongodb://localhost:27018/samma_ai --eval "db.adminCommand('ping')"
```

### Qdrant Connection Error

```bash
# Check Qdrant is running
docker-compose ps qdrant

# Check Qdrant health
curl http://localhost:6334/health

# Check Qdrant logs
docker-compose logs qdrant
```

### Backend Can't Connect to MongoDB

**Issue**: "Connection refused"

**Solution**:
```bash
# Restart MongoDB first
docker-compose restart mongodb

# Wait for health check
docker-compose logs mongodb | grep -i health

# Then restart backend
docker-compose restart backend
```

### Frontend Not Loading

```bash
# Check Nginx logs
docker-compose logs -f frontend

# Check built files exist
docker-compose exec frontend ls -la /usr/share/nginx/html

# Verify backend is accessible from frontend
docker-compose exec frontend curl http://backend:5001/api/health
```

---

## Common Commands

### View Running Services

```bash
docker-compose ps
```

### View Service Logs

```bash
# All services
docker-compose logs

# Last 50 lines of all services
docker-compose logs --tail 50

# Follow specific service
docker-compose logs -f backend

# Follow with timestamps
docker-compose logs -f --timestamps
```

### Execute Commands in Container

```bash
# Interactive bash in backend
docker-compose exec backend bash

# Run Python command in backend
docker-compose exec backend python -c "print('hello')"

# Check Python version
docker-compose exec backend python --version

# View installed packages
docker-compose exec backend pip list
```

### Database Operations

```bash
# MongoDB shell
docker-compose exec mongodb mongosh samma_ai

# Backup MongoDB
docker-compose exec mongodb mongodump --out /backups

# SQLite shell
docker-compose exec backend sqlite3 /app/database/tipitaka_ultimate.db
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend

# Stop and start (full restart)
docker-compose down
docker-compose up -d
```

---

## Performance Optimization

### Reduce Image Sizes

The Dockerfiles use multi-stage builds to minimize image size:

**Backend**: ~500MB (Python 3.13 slim + dependencies)
**Frontend**: ~100MB (Nginx alpine + Flutter web build)

### Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Caching

To speed up rebuilds:

```bash
# Use Docker BuildKit
export DOCKER_BUILDKIT=1
docker-compose build --no-cache backend
```

---

## Production Deployment

### For Production

1. **Use a reverse proxy**: Add Nginx with SSL/TLS
2. **Enable MongoDB authentication**: Set `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`
3. **Use environment-specific configs**: Create `docker-compose.prod.yml`
4. **Set resource limits**: Add CPU and memory constraints
5. **Enable logging drivers**: Use centralized logging (ELK, Splunk, etc.)

### Example Production docker-compose.yml

```yaml
version: '3.8'

services:
  mongodb:
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD}
    deploy:
      resources:
        limits:
          memory: 2G

  backend:
    environment:
      FLASK_ENV: production
      DEBUG: false
    deploy:
      resources:
        limits:
          memory: 1G
```

---

## Monitoring & Logging

### Check Service Health

```bash
# All services at once
docker-compose ps

# Detailed status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### View Metrics

```bash
# CPU and Memory usage
docker stats

# Real-time stats for specific service
docker stats samma-backend
```

### Centralized Logging

Add logging configuration to `docker-compose.yml`:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## File Structure

```
samma_ai/
├── docker-compose.yml         # Main orchestration
├── .env.docker                # Example environment variables
├── DOCKER_SETUP.md            # This guide
│
├── backend/
│   ├── Dockerfile             # Backend container image
│   ├── .dockerignore          # Build context exclusions
│   ├── requirements.txt        # Python dependencies
│   ├── run.py                 # Entry point
│   ├── app/                   # Flask application
│   └── config/                # Configuration files
│
├── frontend/
│   ├── Dockerfile             # Frontend container image
│   ├── .dockerignore          # Build context exclusions
│   ├── nginx.conf             # Nginx configuration
│   ├── pubspec.yaml           # Flutter dependencies
│   └── lib/                   # Flutter source code
│
└── database/
    └── tipitaka_ultimate.db   # Tipitaka database (not in container)
```

---

## Next Steps

1. **Setup Environment**: `cp .env.docker .env && nano .env`
2. **Build Services**: `docker-compose build`
3. **Start Services**: `docker-compose up -d`
4. **Check Health**: `docker-compose ps`
5. **View Logs**: `docker-compose logs -f`
6. **Access Services**:
   - Frontend: http://localhost:8080
   - Backend: http://localhost:5001/api/health
   - MongoDB: mongodb://localhost:27018
   - Qdrant: http://localhost:6334

---

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Check health: `docker-compose ps`
3. Verify network: `docker network inspect samma-network`
4. Review troubleshooting section above
