# LM Studio GPU Acceleration Setup

## Overview
This document describes the setup of LM Studio with NVIDIA GPU acceleration in Docker for fast local LLM inference.

## Hardware Requirements
- NVIDIA GPU (tested with RTX 4090 with 24GB VRAM)
- NVIDIA drivers installed on host
- Docker with NVIDIA Container Runtime

## Installation & Configuration

### 1. Check NVIDIA Setup
```bash
nvidia-smi  # Verify GPU is detected
```

### 2. Start LM Studio with Docker
```bash
cd /mnt/sda1/mango1_home/gvpocr
docker-compose up -d lmstudio
```

### 3. GPU Backend Configuration
The LM Studio service automatically uses the NVIDIA CUDA backend:
- Backend: `llama.cpp-linux-x86_64-nvidia-cuda-avx2`
- Configuration: `~/.lmstudio/.internal/backend-preferences-v1.json`
- X11 Display: Mounts host display for GUI access

### 4. Verify GPU Usage
```bash
# Check if model is loaded
docker exec gvpocr-lmstudio /root/.lmstudio/bin/lms ls

# Test API
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "google/gemma-3-12b", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 5}'

# Monitor GPU usage
nvidia-smi -l 1  # Updates every second
```

## Configuration Files

### docker-compose.yml
- Service name: `lmstudio`
- Port: 1234
- GPU reservation: NVIDIA (1 GPU)
- Volumes:
  - AppImage mount: `/mnt/sda1/mango1_home/gvpocr/LM-Studio-0.3.31-7-x64.AppImage`
  - LM Studio config: `~/.lmstudio`
  - Models cache: `~/.cache`
  - X11 display: `/tmp/.X11-unix/X1`

### lmstudio.Dockerfile
- Base: `nvidia/cuda:12.6.1-runtime-ubuntu22.04`
- Includes:
  - CUDA runtime libraries
  - X11/GTK libraries for GUI
  - FUSE support for AppImage
  - Health checks

### Backend Preferences
File: `~/.lmstudio/.internal/backend-preferences-v1.json`
```json
[{"model_format":"gguf","name":"llama.cpp-linux-x86_64-nvidia-cuda-avx2","version":"1.56.0"}]
```

## Performance Metrics

### Tested Configuration
- Model: google/gemma-3-12b (12B parameters)
- GPU: NVIDIA RTX 4090 (24GB VRAM)
- GPU Memory Used: ~10.4GB
- Inference Speed: ~12.5 seconds per image for OCR processing

### API Response Times
```
Test Query: "What is 2+2?"
Response: ~1-2 seconds
Output: "2 + 2 = 4"
```

## Backend Integration

### For OCR Workers
Workers are configured to connect to LM Studio at `http://lmstudio:1234`:
- Environment: `LMSTUDIO_HOST=http://lmstudio:1234`
- Model: `LMSTUDIO_MODEL=google/gemma-3-12b`
- Timeout: 600s for inference
- Max tokens: 4096

### API Endpoints
- List models: `GET /v1/models`
- Chat completion: `POST /v1/chat/completions`
- Health check: `GET /v1/models` (Docker healthcheck)

## Troubleshooting

### GPU Not Being Used
Check if CPU backend is selected instead:
```bash
docker logs gvpocr-lmstudio | grep "Surveying"
```

**Fix:** Update backend preferences:
```bash
cat > ~/.lmstudio/.internal/backend-preferences-v1.json << 'EOF'
[{"model_format":"gguf","name":"llama.cpp-linux-x86_64-nvidia-cuda-avx2","version":"1.56.0"}]
EOF
docker-compose restart lmstudio
```

### API Timeouts
- Ensure GPU has enough VRAM for loaded model
- Check inference logs: `docker logs gvpocr-lmstudio`
- Verify network connectivity: `docker exec gvpocr-backend curl http://lmstudio:1234/v1/models`

### Model Loading Issues
The container needs X11 display access:
```bash
xhost +local:  # Allow local connections
```

## References
- [LM Studio Documentation](https://lmstudio.ai/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [llama.cpp CUDA Support](https://github.com/ggerganov/llama.cpp)
