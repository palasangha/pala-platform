# Docker Testing Guide - LangChain with Web UI

## Overview

This guide shows how to test your LangChain integration using Docker with a web UI for easy interaction.

## Prerequisites

- Docker 29.1.3+ (✅ Already installed)
- Docker Compose (included with Docker)
- ~4GB RAM for Ollama
- Optional: GPU for faster inference

## Option 1: Quick Start with Docker Compose (Recommended)

### Step 1: Start All Services

```bash
cd /mnt/sda1/mango1_home/gvpocr

# Start Ollama + Open WebUI + LangFlow
docker-compose -f docker-compose.langchain.yml up -d
```

### Step 2: Pull Models (One-time)

```bash
# Enter Ollama container
docker exec -it langchain-ollama ollama pull mistral
docker exec -it langchain-ollama ollama pull nomic-embed-text
```

Or use the web UI to pull models.

### Step 3: Access the Web UI

- **Open WebUI** (Chat interface): http://localhost:8080
- **LangFlow** (Visual builder): http://localhost:7860
- **Ollama API**: http://localhost:11434/api

### Step 4: Test LangChain Integration

From your Flask app:
```python
from app.services.langchain_service import get_langchain_service

service = get_langchain_service(
    ollama_host='http://ollama:11434'  # Docker network
)
response = service.invoke("What is AI?")
```

### Step 5: Monitor Containers

```bash
# View logs
docker-compose -f docker-compose.langchain.yml logs -f

# View running containers
docker-compose -f docker-compose.langchain.yml ps

# Stop all services
docker-compose -f docker-compose.langchain.yml down
```

## Option 2: Manual Docker Commands

### Start Ollama

```bash
docker run -d \
  --name langchain-ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama:latest
```

### Start Open WebUI

```bash
docker run -d \
  --name langchain-webui \
  -p 8080:8080 \
  -e OLLAMA_API_BASE_URL=http://localhost:11434/api \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:latest
```

### Start LangFlow (Optional)

```bash
docker run -d \
  --name langchain-langflow \
  -p 7860:7860 \
  aiolabs/langflow:latest
```

### Pull Models

```bash
docker exec -it langchain-ollama ollama pull mistral
docker exec -it langchain-ollama ollama pull nomic-embed-text
```

## Option 3: Test with Your Flask App in Docker

### Build Your App Image

```bash
# Create Dockerfile for your app
cat > Dockerfile << 'EOF'
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy app
COPY backend/ .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run Flask
ENV FLASK_APP=run.py
ENV OLLAMA_HOST=http://ollama:11434
EXPOSE 5000

CMD ["python", "backend/run.py"]
EOF
```

### Build and Run

```bash
# Build image
docker build -t gvpocr-langchain .

# Start all services
docker-compose -f docker-compose.langchain.yml up -d

# Start your app
docker run -d \
  --name gvpocr-app \
  --network gvpocr_langchain-net \
  -e OLLAMA_HOST=http://ollama:11434 \
  -p 5000:5000 \
  gvpocr-langchain
```

## Accessing the Services

### Open WebUI (Recommended for Testing)

1. Open http://localhost:8080
2. Create account (default: admin/admin)
3. You'll see connected Ollama models
4. Start chatting with Mistral
5. Can test your LangChain responses

### API Testing

```bash
# Health check
curl http://localhost:11434/api/tags

# List models
curl http://localhost:11434/api/tags | jq .

# Test Ollama directly
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "prompt": "What is AI?",
    "stream": false
  }' | jq .

# Test your Flask app
curl http://localhost:5000/api/langchain/health
```

### LangFlow (Visual Builder)

1. Open http://localhost:7860
2. Build chains visually
3. Connect to Ollama backend
4. Test prompts
5. Export code for production

## Useful Docker Commands

```bash
# View all running containers
docker ps

# View logs
docker logs langchain-ollama
docker logs langchain-webui
docker logs langchain-langflow

# Stop all services
docker-compose -f docker-compose.langchain.yml down

# Stop and remove volumes
docker-compose -f docker-compose.langchain.yml down -v

# Clean up
docker system prune -a

# Enter container
docker exec -it langchain-ollama bash
docker exec -it langchain-webui bash

# Check container stats
docker stats
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8080
lsof -i :11434
lsof -i :7860

# Kill process
kill -9 <PID>

# Or use different ports in docker-compose.yml
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check logs
docker logs langchain-ollama

# Test connection
docker exec langchain-ollama curl http://localhost:11434/api/tags
```

### WebUI Won't Load

```bash
# Restart container
docker restart langchain-webui

# Check logs
docker logs langchain-webui

# Rebuild
docker-compose -f docker-compose.langchain.yml down
docker-compose -f docker-compose.langchain.yml up -d
```

### Models Not Showing in WebUI

```bash
# Pull models manually
docker exec -it langchain-ollama ollama pull mistral
docker exec -it langchain-ollama ollama pull nomic-embed-text

# Check installed models
docker exec langchain-ollama ollama list
```

## Performance Optimization

### Use GPU (if available)

```bash
# Update docker-compose.yml:
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Limit Memory

```bash
# In docker-compose.yml:
ollama:
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 2G
```

## Integration with Your Flask App

Update your Flask app to use Docker Ollama:

```python
# .env
OLLAMA_HOST=http://ollama:11434  # Inside Docker network
OLLAMA_MODEL=mistral
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

Or set when running:

```bash
docker run -e OLLAMA_HOST=http://ollama:11434 your-app
```

## Complete Testing Workflow

1. **Start Docker Stack**
   ```bash
   docker-compose -f docker-compose.langchain.yml up -d
   ```

2. **Pull Models**
   ```bash
   docker exec -it langchain-ollama ollama pull mistral nomic-embed-text
   ```

3. **Test Ollama**
   ```bash
   curl http://localhost:11434/api/tags
   ```

4. **Test Open WebUI**
   - Visit http://localhost:8080
   - Chat with Mistral
   - Verify responses

5. **Test Your Flask App**
   ```bash
   curl http://localhost:5000/api/langchain/health
   ```

6. **View Logs**
   ```bash
   docker-compose -f docker-compose.langchain.yml logs -f
   ```

## File Locations

- **Docker Compose**: `/mnt/sda1/mango1_home/gvpocr/docker-compose.langchain.yml`
- **Flask App**: `/mnt/sda1/mango1_home/gvpocr/backend/`
- **LangChain Service**: `backend/app/services/langchain_service.py`
- **API Routes**: `backend/app/routes/langchain_routes.py`

## Next Steps

1. ✅ Start Docker services
2. ✅ Pull Ollama models
3. ✅ Test via Web UI (http://8080)
4. ✅ Test API endpoints
5. ✅ Integrate with your Flask routes
6. ✅ Deploy to production

## Support

- Open WebUI Docs: https://github.com/open-webui/open-webui
- LangFlow Docs: https://github.com/logspace-ai/langflow
- Ollama Docs: https://github.com/ollama/ollama

---

**Quick Reference:**
- WebUI: `http://localhost:8080`
- LangFlow: `http://localhost:7860`
- Ollama API: `http://localhost:11434`
- Your App: `http://localhost:5000`
