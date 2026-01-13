# Setting Up llama.cpp Service with Gemma3

This guide explains how to start the llama.cpp service that's now included in docker-compose.yml.

## Quick Start

### 1. Download the Model

The llama.cpp service requires a multimodal model (LLaVA is recommended for OCR):

```bash
# Make the script executable
chmod +x download_gemma3_model.sh

# Download the model
./download_gemma3_model.sh
```

This downloads LLaVA-1.5 (7B) which is optimized for OCR and document understanding.

### 2. Start the Service

The llama.cpp service is already configured in docker-compose.yml. To start all services including llama.cpp:

```bash
docker-compose up -d
```

Or to start only llama.cpp:

```bash
docker-compose up -d llamacpp
```

### 3. Verify It's Running

Check if the service is healthy:

```bash
# Check container status
docker-compose ps llamacpp

# Check health endpoint
curl http://localhost:8001/health

# View logs
docker-compose logs -f llamacpp
```

## Configuration

The llama.cpp service is configured with:

**Port:** `8001` (mapped to container port `8000`)
**Host:** `http://llamacpp:8000` (internal Docker network)
**Threads:** `8`
**Context Size:** `2048 tokens`
**GPU Acceleration:** `33 layers` (adjust based on your GPU memory)

### Environment Variables

In `docker-compose.yml`:
```yaml
LLAMACPP_ENABLED=true
LLAMACPP_HOST=http://llamacpp:8000
LLAMACPP_MODEL=gemma3-vision
```

These are already set in the docker-compose file.

## Supported Models

The service can run various GGUF-format models. Here are recommended options:

### For OCR (Recommended)
- **LLaVA-1.5 (7B)** - Best for document/image understanding ✅ Default
- **LLaVA-1.5 (13B)** - Better accuracy, requires more memory
- **LLaVA-NeXT** - Latest version with improvements

### For General Vision Tasks
- **Gemma3-Vision** - Newer alternative
- **Llama3-Vision** - Meta's model
- **Llava-Mistral** - Faster inference

### Model Sizes & Quantization
- **Q4_K_M** - 4-bit, ~4-5GB, recommended ✅
- **Q5_K_M** - 5-bit, ~6-7GB, better quality
- **F16** - Full precision, ~14GB, highest quality

## Using Different Models

To use a different model:

1. Download the model files to `./models/` directory
2. Update `docker-compose.yml` in the `llamacpp` service section
3. Change the model filename in the `command` section:

```yaml
command: >
  /app/server
  -m /models/your-model-q4_k_m.gguf
  --mmproj /models/your-mmproj-model-f16.gguf
  --host 0.0.0.0
  --port 8000
  -ngl 33
  -t 8
```

4. Restart the service:
```bash
docker-compose restart llamacpp
```

## Performance Tuning

### For GPUs with Limited Memory (< 6GB)
```yaml
-ngl 20        # Reduce GPU layers
-c 1024        # Reduce context size
```

### For High-Performance GPUs (12GB+)
```yaml
-ngl 33        # Use more GPU layers
-c 4096        # Increase context size
```

### For CPU-only Systems
```yaml
-ngl 0         # No GPU layers
-t 16          # Increase threads
-c 512         # Reduce context for speed
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs llamacpp

# Common issues:
# - Model files not found: Ensure ./models/ directory has GGUF files
# - GPU out of memory: Reduce -ngl value or use smaller model
# - Port already in use: Change port mapping in docker-compose.yml
```

### Slow response times
```bash
# Check system resources
docker stats llamacpp

# Solutions:
# 1. Increase GPU layers (-ngl)
# 2. Reduce context size (-c)
# 3. Use faster quantization (Q4 instead of Q5)
# 4. Reduce threads if CPU-bound
```

### Out of memory errors
```bash
# Reduce context size in docker-compose.yml
-c 1024        # Was 2048

# Or use smaller model
# LLaVA-7B instead of LLaVA-13B
```

### Model not found error
```bash
# Verify model files exist
ls -lh ./models/

# Expected files:
# - ggml-model-q4_k_m.gguf (main model, ~5GB)
# - mmproj-model-f16.gguf (vision projection, ~500MB)

# Re-download if needed
./download_gemma3_model.sh
```

## Docker Compose Commands

```bash
# Start all services including llama.cpp
docker-compose up -d

# Start only llama.cpp
docker-compose up -d llamacpp

# View logs in real-time
docker-compose logs -f llamacpp

# Stop the service
docker-compose stop llamacpp

# Restart the service
docker-compose restart llamacpp

# Remove the container
docker-compose down

# View resource usage
docker stats llamacpp

# Execute command in container
docker-compose exec llamacpp /bin/bash
```

## Integration with GVPOCR

Once the llama.cpp service is running:

1. **Via Web UI:**
   - Go to OCR Review or Bulk Processing
   - Select "llama.cpp (Local LLM)" from the OCR Provider dropdown
   - Process images normally

2. **Via API:**
   ```bash
   curl -X POST http://localhost:5000/api/ocr/process/{image_id} \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "provider": "llamacpp",
       "languages": ["en", "hi"],
       "custom_prompt": "Extract all text from this image"
     }'
   ```

3. **Via Bulk Processing:**
   - Start bulk processing jobs
   - Select llama.cpp as the provider
   - Process folders of documents

## Network Access

### Internal (within Docker)
- Container name: `llamacpp`
- Address: `http://llamacpp:8000`

### External (from host machine)
- Address: `http://localhost:8001`

This is useful for testing outside Docker or running other applications.

## Advanced Configuration

### Multi-Model Setup (Optional)

To run multiple llama.cpp services with different models:

```yaml
llamacpp-llava:
  image: ghcr.io/ggerganov/llama.cpp:latest
  ports:
    - "8001:8000"
  volumes:
    - ./models:/models
  command: >
    /app/server
    -m /models/llava-model-q4_k_m.gguf
    --mmproj /models/llava-mmproj-f16.gguf
    --port 8000

llamacpp-gemma3:
  image: ghcr.io/ggerganov/llama.cpp:latest
  ports:
    - "8002:8000"
  volumes:
    - ./models:/models
  command: >
    /app/server
    -m /models/gemma3-model-q4_k_m.gguf
    --mmproj /models/gemma3-mmproj-f16.gguf
    --port 8000
```

Then update LLAMACPP_HOST in backend for the one you want to use.

## Storage Management

The models are stored in `./models/` directory on your host machine. This allows:

- **Persistence:** Models survive container restarts
- **Sharing:** Multiple services can use the same models
- **Easy updates:** Simply replace model files

To see total storage used:
```bash
du -sh ./models/
```

## References

- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **LLaVA Models:** https://huggingface.co/liuhaotian/llava-v1.5-7b-gguf
- **Model Optimization:** https://huggingface.co/TheBloke/
- **GVPOCR Docs:** See LLAMACPP_SETUP.md in the project root

## Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs llamacpp`
2. Verify model files: `ls -lh ./models/`
3. Test the endpoint: `curl http://localhost:8001/health`
4. Check Docker resources: `docker stats llamacpp`
5. Refer to LLAMACPP_SETUP.md for more details
