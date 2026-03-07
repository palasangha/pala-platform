# 🐳 Samma AI Docker - Quick Start Guide

## What Was Created

✅ **docker-compose.yml** - Complete Docker orchestration with all services
✅ **backend/Dockerfile** - Multi-stage Flask backend container
✅ **frontend/Dockerfile** - Flutter web + Nginx frontend container
✅ **frontend/nginx.conf** - Nginx configuration with API proxy
✅ **docker-manage.sh** - Helper script for easy service management
✅ **.env.docker** - Example environment variables
✅ **DOCKER_SETUP.md** - Comprehensive Docker documentation
✅ **.dockerignore files** - Optimized Docker build context

---

## Custom Port Configuration

| Service | Port | Reason |
|---------|------|--------|
| **Backend** | 5001 | Flask API |
| **Frontend** | 8080 | Nginx (Flutter Web) |
| **MongoDB** | 27018 | Custom (avoid conflicts with local MongoDB on 27017) |
| **Qdrant** | 6334 | Custom (avoid conflicts with local Qdrant on 6333) |

Internal Docker communication uses standard ports:
- MongoDB: 27017 (internal)
- Qdrant: 6333 (internal)

---

## 5-Minute Setup

### Step 1: Prepare Environment

```bash
cd /mnt/sda1/mango1_home/pala-platform/samma_ai

# Copy example environment
cp .env.docker .env

# Edit with your API keys
nano .env
```

**Required in .env:**
- `ANTHROPIC_API_KEY` - Your Claude API key

**Optional:**
- `OLLAMA_BASE_URL` - For local Ollama integration
- `OPENAI_API_KEY` - For OpenAI support
- `COPILOT_API_KEY` - For GitHub Copilot support

### Step 2: Build Services

```bash
./docker-manage.sh build
```

This will:
- Build the Flask backend image (~500MB)
- Build the Flutter web + Nginx frontend image (~100MB)

### Step 3: Start Services

```bash
./docker-manage.sh up
```

This will:
- Start MongoDB (port 27018)
- Start Qdrant (port 6334)
- Start Backend (port 5001)
- Start Frontend (port 8080)
- Automatically check health

### Step 4: Verify Everything Works

```bash
./docker-manage.sh status
```

You should see:
```
✓ Backend: http://localhost:5001/api/health
✓ Frontend: http://localhost:8080
✓ MongoDB: mongodb://localhost:27018/samma_ai
✓ Qdrant: http://localhost:6334/health
```

### Step 5: Open in Browser

```
http://localhost:8080
```

---

## Docker Management Commands

### Quick Reference

```bash
# Start services
./docker-manage.sh up

# View logs
./docker-manage.sh logs

# Check status
./docker-manage.sh status

# Stop services
./docker-manage.sh down

# Restart services
./docker-manage.sh restart

# Open backend shell
./docker-manage.sh shell

# Connect to MongoDB
./docker-manage.sh mongo

# Test endpoints
./docker-manage.sh test

# Clean everything
./docker-manage.sh clean
```

### Using docker-compose Directly

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
docker-compose logs -f qdrant

# Check status
docker-compose ps

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Execute command in container
docker-compose exec backend python --version
docker-compose exec mongodb mongosh samma_ai
```

---

## Service Details

### Backend Service

**Docker Image**: Python 3.13 slim + Flask dependencies
**Port**: 5001
**Health Check**: `curl http://localhost:5001/api/health`

Environment variables:
- `MONGO_URI`: `mongodb://mongodb:27017/samma_ai` (internal Docker)
- `QDRANT_HOST`: `qdrant` (internal Docker)
- `QDRANT_PORT`: `6333` (internal Docker)

### Frontend Service

**Docker Image**: Flutter + Nginx Alpine
**Port**: 8080
**Health Check**: `curl http://localhost:8080`

Features:
- Auto-builds Flutter web app
- Serves static files via Nginx
- Proxies `/api/*` calls to backend
- CORS enabled

### MongoDB Service

**Docker Image**: MongoDB 7.0 Alpine
**External Port**: 27018
**Internal Port**: 27017
**Data Volume**: `mongodb_data`

Connect from host:
```bash
mongosh mongodb://localhost:27018/samma_ai
```

### Qdrant Service

**Docker Image**: Qdrant latest
**External Port**: 6334
**Internal Port**: 6333
**Data Volume**: `qdrant_data`

Check health:
```bash
curl http://localhost:6334/health
```

---

## Common Workflows

### Development: Modify Backend Code

1. Edit files in `backend/app/`
2. Changes are reflected automatically (volume mount)
3. View logs: `docker-compose logs -f backend`

### Development: Modify Frontend Code

1. Edit files in `frontend/lib/`
2. Rebuild frontend: `docker-compose build frontend`
3. Restart frontend: `docker-compose up -d frontend`

### Check Database Data

```bash
# MongoDB
docker-compose exec mongodb mongosh samma_ai

# Query conversations
db.conversations.find().pretty()

# SQLite
docker-compose exec backend sqlite3 /app/database/tipitaka_ultimate.db
SELECT COUNT(*) FROM paragraphs WHERE text_layer='mula';
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:5001/api/health | jq .

# Full status
curl http://localhost:5001/api/status | jq .

# Chat request
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is metta?"}' | jq .
```

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 50 lines
docker-compose logs --tail 50

# With timestamps
docker-compose logs -f --timestamps
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs -f

# Check specific service
docker-compose logs backend

# Restart all services
docker-compose restart

# Full restart
docker-compose down
docker-compose up -d
```

### Port Already in Use

```bash
# Check what's using the port
lsof -i :5001    # Backend
lsof -i :8080    # Frontend
lsof -i :27018   # MongoDB
lsof -i :6334    # Qdrant

# Kill the process or change port in docker-compose.yml
```

### Backend Can't Connect to MongoDB

```bash
# Check MongoDB is running
docker-compose ps mongodb

# Check MongoDB logs
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb

# Then restart backend
docker-compose restart backend
```

### Frontend Can't Connect to Backend

```bash
# Check backend is running
docker-compose ps backend

# Test from frontend container
docker-compose exec frontend curl http://backend:5001/api/health

# Check Nginx logs
docker-compose logs frontend

# Check nginx config
docker-compose exec frontend cat /etc/nginx/nginx.conf
```

### Out of Disk Space

```bash
# Clean up Docker system
docker system prune -a -f --volumes

# Specific cleanup
docker-compose down -v
docker image prune -a -f
```

---

## File Structure

```
samma_ai/
├── docker-compose.yml              ← Main orchestration
├── docker-manage.sh                ← Helper script
├── .env.docker                     ← Example env vars
├── DOCKER_QUICK_START.md           ← This file
├── DOCKER_SETUP.md                 ← Detailed guide
│
├── backend/
│   ├── Dockerfile                  ← Backend image
│   ├── .dockerignore               ← Build exclusions
│   ├── requirements.txt
│   ├── run.py
│   ├── app/                        ← Flask code
│   └── config/
│
├── frontend/
│   ├── Dockerfile                  ← Frontend image
│   ├── .dockerignore               ← Build exclusions
│   ├── nginx.conf                  ← Nginx config
│   ├── pubspec.yaml
│   └── lib/                        ← Flutter code
│
└── database/
    └── tipitaka_ultimate.db        ← Tipitaka data (shared)
```

---

## Environment Variables Explained

### Ports & Databases
```
FLASK_ENV=development       # Flask environment
PORT=5001                   # Backend port
MONGO_URI=...              # MongoDB connection (internal)
QDRANT_HOST=qdrant         # Qdrant host (internal)
QDRANT_PORT=6333           # Qdrant port (internal)
```

### API Keys
```
ANTHROPIC_API_KEY=...      # Claude API key (REQUIRED)
OLLAMA_BASE_URL=...        # Local model URL
OPENAI_API_KEY=...         # OpenAI key (optional)
COPILOT_API_KEY=...        # GitHub Copilot key (optional)
```

### Vector Database
```
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_BATCH_SIZE=64    # Batch size for embeddings
VECTOR_SEARCH_TOP_K=5      # Top K results from vector search
```

---

## Next Steps

### Option 1: Quick Start (Recommended)
```bash
./docker-manage.sh up      # Start everything
./docker-manage.sh logs    # Monitor logs
```

### Option 2: Step-by-Step
```bash
cp .env.docker .env
nano .env                  # Edit API keys
./docker-manage.sh build   # Build images
./docker-manage.sh up      # Start services
./docker-manage.sh status  # Check health
```

### Option 3: Manual with Docker Compose
```bash
docker-compose build
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

---

## For More Information

- See **DOCKER_SETUP.md** for comprehensive documentation
- See **docker-manage.sh** for all available commands
- Check logs: `docker-compose logs -f`
- Run tests: `./docker-manage.sh test`

---

## Support

If something doesn't work:

1. **Check logs**: `docker-compose logs -f`
2. **Check health**: `./docker-manage.sh status`
3. **Test endpoints**: `./docker-manage.sh test`
4. **Review DOCKER_SETUP.md** for troubleshooting section

Happy containerizing! 🐳
