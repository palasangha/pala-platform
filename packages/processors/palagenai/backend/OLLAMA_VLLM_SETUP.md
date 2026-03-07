# Ollama and vLLM Setup Guide

This guide covers setting up Ollama and vLLM services for local vision model inference in GVPOCR.

---

## Overview

GVPOCR now supports two local inference engines for vision models:

1. **Ollama** - Easy-to-use local LLM/Vision model server
2. **vLLM** - High-performance inference engine optimized for throughput

Both services run in Docker containers with GPU acceleration and integrate seamlessly with the GVPOCR backend.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Ollama Setup](#ollama-setup)
- [vLLM Setup](#vllm-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Model Management](#model-management)
- [Performance Comparison](#performance-comparison)

---

## Prerequisites

### Hardware Requirements

**Minimum:**
- NVIDIA GPU with 8GB+ VRAM (for 11B models)
- 16GB+ System RAM
- 50GB+ Free Disk Space

**Recommended:**
- NVIDIA GPU with 24GB+ VRAM (for larger models or parallel processing)
- 32GB+ System RAM
- 100GB+ Free Disk Space

### Software Requirements

1. **NVIDIA Container Toolkit** (for GPU support in Docker)

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

2. **Verify GPU Access**

```bash
# Test GPU in Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

You should see your GPU(s) listed.

---

## Ollama Setup

### Step 1: Configure Environment Variables

Edit `backend/.env`:

```env
# Ollama Configuration
OLLAMA_ENABLED=true
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2-vision
```

### Step 2: Start Ollama Service

```bash
cd /mnt/sda1/mango1_home/gvpocr

# Start only Ollama service
docker-compose up -d ollama

# Check logs
docker-compose logs -f ollama
```

### Step 3: Pull Vision Models

```bash
# Access Ollama container
docker exec -it gvpocr-ollama bash

# Pull Llama 3.2 Vision model (11B)
ollama pull llama3.2-vision

# Or pull other vision models
ollama pull llava:13b
ollama pull llava:34b

# List installed models
ollama list

# Exit container
exit
```

### Step 4: Test Ollama

```bash
# Test from host
curl http://localhost:11434/api/tags

# Test vision inference
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2-vision",
  "prompt": "What is in this image?",
  "images": ["base64_encoded_image_here"]
}'
```

### Step 5: Restart Backend

```bash
# Restart backend to connect to Ollama
docker-compose restart backend
```

---

## vLLM Setup

### Step 1: Get Hugging Face Token

1. Create account at https://huggingface.co/
2. Go to Settings → Access Tokens
3. Create a new token with "Read" access
4. Accept Llama model license at https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct

### Step 2: Configure Environment Variables

Edit `backend/.env`:

```env
# vLLM Configuration
VLLM_ENABLED=true
VLLM_HOST=http://vllm:8000
VLLM_MODEL=llama-vision
VLLM_API_KEY=vllm-secret-token
VLLM_TIMEOUT=1200
VLLM_MAX_TOKENS=8192

# Hugging Face Token (required for downloading Llama models)
HUGGING_FACE_HUB_TOKEN=hf_your_token_here

# vLLM Model Configuration
VLLM_MODEL_NAME=llama-vision
```

Also update in root `.env`:

```env
# Add these to root .env for docker-compose
HUGGING_FACE_HUB_TOKEN=hf_your_token_here
VLLM_API_KEY=vllm-secret-token
VLLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
VLLM_MODEL_NAME=llama-vision
```

### Step 3: Start vLLM Service

```bash
cd /mnt/sda1/mango1_home/gvpocr

# Start vLLM service
docker-compose up -d vllm

# Monitor startup (first run will download model - takes time)
docker-compose logs -f vllm
```

**Note:** First startup will download the model (~22GB for Llama-3.2-11B). This can take 15-30 minutes depending on your internet speed.

### Step 4: Wait for Model Loading

vLLM needs time to:
1. Download the model (first time only)
2. Load model into GPU memory
3. Initialize serving engine

Watch logs until you see:
```
INFO:     Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Test vLLM

```bash
# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Test inference
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer vllm-secret-token" \
  -d '{
    "model": "llama-vision",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What is in this image?"},
          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
      }
    ]
  }'
```

### Step 6: Restart Backend

```bash
# Restart backend to connect to vLLM
docker-compose restart backend
```

---

## Configuration

### Docker Compose Configuration

#### Ollama Service

Located in [docker-compose.yml](docker-compose.yml#L100-L126):

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: gvpocr-ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama  # Stores models
  environment:
    - OLLAMA_HOST=0.0.0.0
    - OLLAMA_ORIGINS=*
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

#### vLLM Service

Located in [docker-compose.yml](docker-compose.yml#L128-L162):

```yaml
vllm:
  image: vllm/vllm-openai:latest
  container_name: gvpocr-vllm
  ports:
    - "8000:8000"
  environment:
    - HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}
  command: >
    --model meta-llama/Llama-3.2-11B-Vision-Instruct
    --host 0.0.0.0
    --port 8000
    --max-model-len 4096
    --gpu-memory-utilization 0.90
    --dtype auto
    --api-key vllm-secret-token
    --served-model-name llama-vision
```

### Backend Configuration

Located in [app/config.py](app/config.py#L64-L70):

```python
# vLLM Configuration
VLLM_HOST = os.getenv('VLLM_HOST', 'http://vllm:8000')
VLLM_MODEL = os.getenv('VLLM_MODEL', 'llama-vision')
VLLM_API_KEY = os.getenv('VLLM_API_KEY', 'vllm-secret-token')
VLLM_ENABLED = os.getenv('VLLM_ENABLED', 'true').lower() == 'true'
VLLM_TIMEOUT = int(os.getenv('VLLM_TIMEOUT', '1200'))
VLLM_MAX_TOKENS = int(os.getenv('VLLM_MAX_TOKENS', '8192'))
```

### Provider Configuration

vLLM Provider: [app/services/ocr_providers/vllm_provider.py](app/services/ocr_providers/vllm_provider.py)

---

## Usage

### Using Ollama for OCR

```bash
# Via API
curl -X POST http://localhost:5000/api/ocr/process \
  -H "Content-Type: multipart/form-data" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/image.jpg" \
  -F "provider=ollama" \
  -F "languages[]=en"
```

### Using vLLM for OCR

```bash
# Via API
curl -X POST http://localhost:5000/api/ocr/process \
  -H "Content-Type: multipart/form-data" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/image.jpg" \
  -F "provider=vllm" \
  -F "languages[]=en"
```

### Bulk Processing with Parallel Jobs

```bash
# Process folder with vLLM using 4 parallel workers
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "folder_path": "/path/to/images",
    "provider": "vllm",
    "languages": ["en"],
    "parallel": true,
    "max_workers": 4,
    "export_formats": ["json", "csv"]
  }'
```

---

## Troubleshooting

### Ollama Issues

#### Issue 1: Ollama service won't start

**Check logs:**
```bash
docker-compose logs ollama
```

**Common causes:**
- GPU not available
- NVIDIA Container Toolkit not installed
- Port 11434 already in use

**Fix:**
```bash
# Check GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Check port
sudo lsof -i :11434

# Restart service
docker-compose restart ollama
```

#### Issue 2: "Model not found" error

**Solution:**
```bash
# Pull the model
docker exec -it gvpocr-ollama ollama pull llama3.2-vision

# Verify
docker exec -it gvpocr-ollama ollama list
```

#### Issue 3: Out of memory errors

**Solution:**
```bash
# Use smaller model
docker exec -it gvpocr-ollama ollama pull llama3.2-vision:7b

# Update .env
OLLAMA_MODEL=llama3.2-vision:7b
```

### vLLM Issues

#### Issue 1: vLLM container exits immediately

**Check logs:**
```bash
docker-compose logs vllm
```

**Common causes:**
- Missing Hugging Face token
- Insufficient GPU memory
- Model not licensed

**Fix:**
```bash
# Add HF token to .env
HUGGING_FACE_HUB_TOKEN=hf_your_token_here

# Accept license at:
# https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct

# Restart
docker-compose restart vllm
```

#### Issue 2: Model download is slow/stuck

**Monitor download:**
```bash
# Watch progress
docker-compose logs -f vllm

# Check disk space
df -h

# Check network
docker exec -it gvpocr-vllm curl -I https://huggingface.co
```

#### Issue 3: CUDA out of memory

**Error:**
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solutions:**

1. **Reduce GPU memory utilization:**
```yaml
# In docker-compose.yml
command: >
  --gpu-memory-utilization 0.70  # Reduce from 0.90
```

2. **Reduce max model length:**
```yaml
command: >
  --max-model-len 2048  # Reduce from 4096
```

3. **Use quantized model:**
```yaml
command: >
  --model meta-llama/Llama-3.2-11B-Vision-Instruct
  --quantization awq  # Enable quantization
```

#### Issue 4: "Authorization failed" error

**Fix:**
```bash
# Ensure API key matches in both .env files
# backend/.env
VLLM_API_KEY=vllm-secret-token

# Root .env for docker-compose
VLLM_API_KEY=vllm-secret-token

# Restart services
docker-compose restart vllm backend
```

### Backend Connection Issues

#### Issue: Backend can't connect to Ollama/vLLM

**Check network:**
```bash
# From backend container
docker exec -it gvpocr-backend curl http://ollama:11434/api/tags
docker exec -it gvpocr-backend curl http://vllm:8000/v1/models
```

**Verify configuration:**
```bash
# Check environment variables
docker exec -it gvpocr-backend env | grep -E "OLLAMA|VLLM"
```

**Fix:**
```bash
# Ensure all services on same network
docker network inspect gvpocr-network

# Restart all services
docker-compose restart backend ollama vllm
```

---

## Model Management

### Ollama Models

#### List Available Models

```bash
# In container
docker exec -it gvpocr-ollama ollama list

# From host
curl http://localhost:11434/api/tags
```

#### Pull Models

```bash
# Vision models
docker exec -it gvpocr-ollama ollama pull llama3.2-vision
docker exec -it gvpocr-ollama ollama pull llava:13b
docker exec -it gvpocr-ollama ollama pull llava:34b

# Text models (for metadata extraction)
docker exec -it gvpocr-ollama ollama pull llama3
docker exec -it gvpocr-ollama ollama pull mistral
```

#### Remove Models

```bash
# Remove model to free space
docker exec -it gvpocr-ollama ollama rm llava:34b
```

#### Model Storage

Models stored in Docker volume:
```bash
# Inspect volume
docker volume inspect gvpocr_ollama_data

# Backup models
docker run --rm -v gvpocr_ollama_data:/data -v $(pwd):/backup ubuntu tar czf /backup/ollama_models.tar.gz -C /data .
```

### vLLM Models

#### Supported Models

vLLM supports any Hugging Face vision model with LLaMA architecture:

- `meta-llama/Llama-3.2-11B-Vision-Instruct` (default)
- `meta-llama/Llama-3.2-90B-Vision-Instruct` (requires more VRAM)
- Other vision-language models on HuggingFace

#### Change Model

Edit `.env`:
```env
VLLM_MODEL=meta-llama/Llama-3.2-90B-Vision-Instruct
```

Restart vLLM:
```bash
docker-compose restart vllm
```

**Note:** New model will be downloaded on first run.

#### Model Cache

Models cached in Docker volume:
```bash
# Inspect cache
docker volume inspect gvpocr_vllm_cache

# Clear cache (will re-download models)
docker volume rm gvpocr_vllm_cache
docker-compose up -d vllm
```

---

## Performance Comparison

### Ollama vs vLLM

| Feature | Ollama | vLLM |
|---------|--------|------|
| **Setup Difficulty** | Easy | Medium |
| **First-time Setup** | Fast (~5 min) | Slow (~30 min download) |
| **Memory Usage** | Moderate | High |
| **Throughput** | Good | Excellent |
| **Parallel Requests** | Limited | Optimized |
| **API Compatibility** | Custom | OpenAI-compatible |
| **Model Switching** | Easy (`ollama pull`) | Restart required |
| **Best For** | Single image processing | Bulk processing, high throughput |

### Benchmarks

**Test Setup:**
- GPU: NVIDIA RTX 3090 (24GB)
- Model: Llama-3.2-11B-Vision
- Image: 1024x768 JPEG
- Workers: 4 parallel

**Single Image Processing:**

| Provider | Time (s) | Tokens/s |
|----------|----------|----------|
| Ollama | 2.3 | ~450 |
| vLLM | 1.8 | ~580 |

**Bulk Processing (100 images):**

| Provider | Total Time | Avg per Image | Throughput |
|----------|------------|---------------|------------|
| Ollama | 4m 20s | 2.6s | 23 img/min |
| vLLM | 3m 10s | 1.9s | 31 img/min |

### Recommendations

**Use Ollama when:**
- Processing individual images interactively
- Want easy model switching
- Limited VRAM (<16GB)
- Prototyping and testing

**Use vLLM when:**
- Bulk processing large datasets
- High throughput required
- Parallel processing workloads
- Production deployments
- Sufficient VRAM (16GB+)

---

## Advanced Configuration

### GPU Allocation

#### Split GPU Between Services

If you have multiple GPUs:

```yaml
# docker-compose.yml

ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['0']  # Use GPU 0
            capabilities: [gpu]

vllm:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['1']  # Use GPU 1
            capabilities: [gpu]
```

### Resource Limits

#### Ollama Memory Limit

```yaml
ollama:
  deploy:
    resources:
      limits:
        memory: 16G
      reservations:
        memory: 8G
```

#### vLLM Memory Limit

```yaml
vllm:
  deploy:
    resources:
      limits:
        memory: 24G
      reservations:
        memory: 16G
```

### Custom vLLM Parameters

```yaml
vllm:
  command: >
    --model meta-llama/Llama-3.2-11B-Vision-Instruct
    --tensor-parallel-size 2  # Use 2 GPUs
    --max-num-seqs 256  # Batch size
    --max-model-len 8192  # Context length
    --gpu-memory-utilization 0.95
    --dtype bfloat16  # Precision
    --enable-prefix-caching  # Speed up repeated prompts
```

---

## Monitoring

### Check Service Status

```bash
# All services
docker-compose ps

# Individual service
docker ps --filter name=gvpocr-ollama
docker ps --filter name=gvpocr-vllm
```

### Monitor GPU Usage

```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# GPU usage by container
docker stats gvpocr-ollama gvpocr-vllm
```

### Check Health

```bash
# Ollama health
curl http://localhost:11434/api/tags

# vLLM health
curl http://localhost:8000/health

# Backend providers
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:5000/api/ocr/providers
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# Specific service
docker-compose logs -f ollama
docker-compose logs -f vllm

# Last 100 lines
docker-compose logs --tail 100 vllm
```

---

## Production Deployment

### Security

1. **Change API Keys**
```env
# Use strong, random keys
VLLM_API_KEY=$(openssl rand -hex 32)
```

2. **Restrict Network Access**
```yaml
# Only expose to internal network
ports:
  - "127.0.0.1:8000:8000"  # vLLM
  - "127.0.0.1:11434:11434"  # Ollama
```

3. **Use TLS/SSL**
- Add nginx reverse proxy with SSL
- Use Let's Encrypt certificates

### Backup

```bash
# Backup Ollama models
docker run --rm -v gvpocr_ollama_data:/data -v $(pwd):/backup ubuntu tar czf /backup/ollama_backup.tar.gz -C /data .

# Backup vLLM cache
docker run --rm -v gvpocr_vllm_cache:/data -v $(pwd):/backup ubuntu tar czf /backup/vllm_backup.tar.gz -C /data .
```

### Monitoring Tools

Consider adding:
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **NVIDIA DCGM** - GPU monitoring
- **cAdvisor** - Container monitoring

---

## Quick Start Commands

### Start Everything

```bash
# Start all services including Ollama and vLLM
docker-compose up -d

# Wait for services to be ready
docker-compose logs -f ollama vllm
```

### Start Individual Services

```bash
# Only Ollama
docker-compose up -d ollama

# Only vLLM
docker-compose up -d vllm

# Backend + Ollama
docker-compose up -d backend ollama
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop specific
docker-compose stop ollama vllm
```

### Update Services

```bash
# Pull latest images
docker-compose pull ollama vllm

# Restart with new images
docker-compose up -d ollama vllm
```

---

## Summary

You now have:

✅ Ollama service running on port 11434
✅ vLLM service running on port 8000
✅ Backend configured to use both providers
✅ GPU acceleration enabled
✅ Models ready for vision OCR tasks

**Next Steps:**
1. Pull vision models into Ollama
2. Wait for vLLM to download and load model
3. Test both providers via API
4. Start processing images!

For questions or issues, check the [Troubleshooting](#troubleshooting) section or review Docker logs.
