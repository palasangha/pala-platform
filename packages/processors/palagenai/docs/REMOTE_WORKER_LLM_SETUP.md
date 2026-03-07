# Remote Worker LLM Setup Guide

This guide explains how to set up and run Ollama and LlamaCPP services on remote worker machines.

## Overview

The `docker-compose.worker.yml` includes optional Ollama and LlamaCPP services that can be deployed on remote machines alongside the OCR workers. These services enable local LLM-based OCR capabilities without relying on the main server's resources.

## Services Available

### 1. **Ollama Service**
- **Image**: `ollama/ollama:latest`
- **Port**: 11434
- **Models**: Configurable via `OLLAMA_MODEL`
- **Default Model**: `llama3.2-vision`
- **Status**: Disabled by default (`OLLAMA_ENABLED=false`)

### 2. **LlamaCPP Service**
- **Model**: Phi-3.5 Vision Instruct (GGUF format)
- **Port**: 8000 (mapped to 8007 on host)
- **Memory**: Requires GPU or CPU (resource-intensive)
- **Status**: Disabled by default (`LLAMACPP_ENABLED=false`)

### 3. **OCR Workers**
- Multiple workers (scalable with `--scale worker=N`)
- Connect to NSQ broker on main server
- Use local or main server LLM services

## Setup Instructions

### Step 1: Configure Environment Variables

Edit or create `.env.worker` in the gvpocr directory:

```bash
cp .env.worker.example .env.worker
```

Edit `.env.worker`:

```env
# Main Server IP Address
MAIN_SERVER_IP=172.12.0.132

# MongoDB Credentials
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=gvp%40123

# Enable local LLM services
OLLAMA_ENABLED=true          # Set to true to enable Ollama
LLAMACPP_ENABLED=true        # Set to true to enable LlamaCPP

# Model selections
OLLAMA_MODEL=llama3.2-vision
LLAMACPP_MODEL=gemma3-vision

# HuggingFace token (required for LlamaCPP model downloads)
HUGGING_FACE_HUB_TOKEN=your_token_here
```

### Step 2: Start Workers with LLM Services

#### Option A: Start only OCR workers (without LLM)
```bash
docker compose --env-file .env.worker -f docker-compose.worker.yml up -d --scale worker=4
```

#### Option B: Start workers with Ollama
```bash
# Enable Ollama in .env.worker
sed -i 's/OLLAMA_ENABLED=false/OLLAMA_ENABLED=true/' .env.worker

# Start with llm profile
docker compose --env-file .env.worker --profile llm -f docker-compose.worker.yml up -d --scale worker=4
```

#### Option C: Start workers with LlamaCPP
```bash
# Enable LlamaCPP in .env.worker
sed -i 's/LLAMACPP_ENABLED=false/LLAMACPP_ENABLED=true/' .env.worker

# Start with llm profile
docker compose --env-file .env.worker --profile llm -f docker-compose.worker.yml up -d --scale worker=4
```

#### Option D: Start workers with both Ollama and LlamaCPP
```bash
# Enable both in .env.worker
sed -i 's/OLLAMA_ENABLED=false/OLLAMA_ENABLED=true/' .env.worker
sed -i 's/LLAMACPP_ENABLED=false/LLAMACPP_ENABLED=true/' .env.worker

# Start with llm profile
docker compose --env-file .env.worker --profile llm -f docker-compose.worker.yml up -d --scale worker=4
```

### Step 3: Verify Services

#### Check all running services
```bash
docker compose --env-file .env.worker -f docker-compose.worker.yml ps
```

#### Check Ollama status
```bash
curl http://localhost:11434/api/tags
```

#### Check LlamaCPP status
```bash
curl http://localhost:8007/health
```

#### View worker logs
```bash
docker compose --env-file .env.worker -f docker-compose.worker.yml logs -f worker
```

#### View Ollama logs
```bash
docker compose --env-file .env.worker --profile llm -f docker-compose.worker.yml logs -f ollama
```

## Configuration Details

### Worker Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAIN_SERVER_IP` | 172.12.0.132 | Main server IP address |
| `MONGO_USERNAME` | gvpocr_admin | MongoDB username |
| `MONGO_PASSWORD` | gvp%40123 | MongoDB password (URL-encoded) |
| `OLLAMA_ENABLED` | false | Enable local Ollama service |
| `LLAMACPP_ENABLED` | false | Enable local LlamaCPP service |
| `OLLAMA_HOST` | http://ollama:11434 | Ollama service host |
| `LLAMACPP_HOST` | http://llamacpp:8000 | LlamaCPP service host |
| `OLLAMA_MODEL` | llama3.2-vision | Ollama model to use |
| `LLAMACPP_MODEL` | gemma3-vision | LlamaCPP model to use |

### Resource Requirements

#### Ollama (with llama3.2-vision)
- **VRAM**: 8-12 GB (for vision model)
- **CPU**: 4+ cores recommended
- **Storage**: 10-20 GB for model cache

#### LlamaCPP (with Phi-3.5-vision)
- **VRAM**: 6-8 GB (Q8_0 quantized)
- **CPU**: 4+ cores recommended
- **Storage**: 20-30 GB for model + cache

#### OCR Workers
- **CPU**: 1-2 cores per worker
- **RAM**: 2-4 GB per worker

## Usage Examples

### Example 1: 4 Workers + Ollama Only
```bash
# Update .env.worker
OLLAMA_ENABLED=true
LLAMACPP_ENABLED=false

# Start services
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml up -d --scale worker=4
```

### Example 2: 6 Workers + LlamaCPP Only
```bash
# Update .env.worker
OLLAMA_ENABLED=false
LLAMACPP_ENABLED=true

# Start services
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml up -d --scale worker=6
```

### Example 3: Scale Up/Down
```bash
# Scale to 8 workers
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml up -d --scale worker=8

# Scale down to 2 workers
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml up -d --scale worker=2
```

## Troubleshooting

### LlamaCPP fails to build
**Issue**: Docker build fails for llama.cpp.Dockerfile

**Solution**:
1. Ensure the llama.cpp.Dockerfile exists in the gvpocr directory
2. Check available disk space (at least 30 GB)
3. Check GPU drivers (if using GPU acceleration)

### Ollama model download fails
**Issue**: Model downloads timeout or fail

**Solution**:
1. Check internet connectivity
2. Increase download timeout in environment
3. Pre-download models manually:
   ```bash
   docker exec gvpocr-remote-ollama ollama pull llama3.2-vision
   ```

### Models not responding
**Issue**: Workers can't connect to Ollama/LlamaCPP

**Solution**:
1. Verify service is running: `docker ps | grep ollama`
2. Check ports are open: `netstat -tulpn | grep -E '11434|8007'`
3. Verify environment variables match service names in docker-compose
4. Check service logs: `docker logs gvpocr-remote-ollama`

## Performance Tips

1. **GPU Acceleration**: 
   - Add GPU support in docker-compose if available
   - Uncomment GPU configuration in service definitions

2. **Model Caching**:
   - Models are cached in Docker volumes
   - First run will download models (takes 10-30 minutes)
   - Subsequent runs use cached models

3. **Worker Scaling**:
   - Test with 2-4 workers initially
   - Monitor resource usage before scaling up
   - Keep LLM service resources separate from worker resources

## Monitoring

### Check service health
```bash
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml ps
```

### Monitor resource usage
```bash
docker stats gvpocr-worker-1 gvpocr-worker-2 gvpocr-remote-ollama
```

### View real-time logs
```bash
docker compose --env-file .env.worker --profile llm \
  -f docker-compose.worker.yml logs -f
```

## Next Steps

1. Configure and test Ollama or LlamaCPP on your remote machine
2. Monitor model download progress
3. Run sample OCR jobs to verify LLM integration
4. Scale workers based on available resources
5. Monitor performance and adjust settings as needed
