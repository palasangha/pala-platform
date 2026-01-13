# Phi-3.5 Vision Model Setup for llamacpp

## ✅ Configuration Complete

The llamacpp service has been configured to use the **Phi-3.5 Vision** model from HuggingFace cache.

### Model Information
- **Repository:** `abetlen/Phi-3.5-vision-instruct-gguf`
- **Main Model:** Phi-3.5-3.8B-vision-instruct-Q8_0.gguf (~7.5GB)
- **Projection Model:** Phi-3.5-3.8B-vision-instruct-mmproj-F16.gguf (~596MB)
- **Cache Location:** `~/.cache/huggingface/hub/models--abetlen--Phi-3.5-vision-instruct-gguf/`
- **Total Size:** ~12GB
- **Quantization:** Q8_0 (High quality, good for OCR)

### Updated docker-compose.yml

The following configuration has been applied:

```yaml
llamacpp:
  build:
    context: .
    dockerfile: llama.cpp.Dockerfile
  container_name: gvpocr-llamacpp
  restart: unless-stopped
  ports:
    - "8007:8000"
  volumes:
    - ./models:/models
    - ~/.cache/huggingface/hub:/root/.cache/huggingface/hub:ro
  command: [
    "-m", "/root/.cache/huggingface/hub/models--abetlen--Phi-3.5-vision-instruct-gguf/snapshots/39c8650873918d40fa529518eadc3680268a4e1b/Phi-3.5-3.8B-vision-instruct-Q8_0.gguf",
    "--mmproj", "/root/.cache/huggingface/hub/models--abetlen--Phi-3.5-vision-instruct-gguf/snapshots/39c8650873918d40fa529518eadc3680268a4e1b/Phi-3.5-3.8B-vision-instruct-mmproj-F16.gguf",
    "--host", "0.0.0.0",
    "--port", "8000"
  ]
  networks:
    - gvpocr-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

## Starting the Service

### Option 1: Linux/Mac with Docker

```bash
# Build the image
docker-compose build llamacpp

# Start the service
docker-compose up -d llamacpp

# Check status
docker-compose ps llamacpp

# View logs
docker-compose logs -f llamacpp
```

### Option 2: On Mac with GPU Acceleration

The Dockerfile includes Metal GPU support for Apple Silicon Macs. Just run:

```bash
./setup_llamacpp_mac.sh
```

## Testing the Service

```bash
# Check health
curl http://localhost:8007/health

# Should return:
# {"status": "ok"}
```

## Using in OCR Pipeline

Add to your `.env` file:

```bash
# Enable llamacpp
LLAMACPP_ENABLED=true

# Model name (for logging/tracking)
LLAMACPP_MODEL=phi-3.5-vision

# Service endpoint
LLAMACPP_HOST=http://localhost:8007
```

## Performance Notes

- **First startup:** 1-2 minutes (model loads into memory)
- **Inference speed:** ~2-5 seconds per image
- **GPU acceleration:** Enabled for Apple Silicon (Metal), CPU for Intel
- **Memory usage:** ~8GB (Q8_0 quantization)

## Model Files Location

```
~/.cache/huggingface/hub/
└── models--abetlen--Phi-3.5-vision-instruct-gguf/
    └── snapshots/
        └── 39c8650873918d40fa529518eadc3680268a4e1b/
            ├── Phi-3.5-3.8B-vision-instruct-Q8_0.gguf
            └── Phi-3.5-3.8B-vision-instruct-mmproj-F16.gguf
```

## Troubleshooting

### Service won't start
```bash
# Check Docker logs
docker-compose logs llamacpp

# Ensure HuggingFace cache is readable
ls -l ~/.cache/huggingface/hub/models--abetlen--Phi-3.5-vision-instruct-gguf/
```

### Out of memory
- The model requires ~8GB RAM minimum
- GPU memory is also needed for acceleration
- Check available memory: `free -h` (Linux) or Activity Monitor (Mac)

### Model file not found
```bash
# Verify files exist
ls -lh ~/.cache/huggingface/hub/models--abetlen--Phi-3.5-vision-instruct-gguf/snapshots/39c8650873918d40fa529518eadc3680268a4e1b/

# Should show both .gguf files
```

## Alternative Models

To use a different model, edit `docker-compose.yml` and update the `-m` path in the command section.

Popular alternatives:
- `abetlen/Phi-3.5-vision-instruct-gguf:Phi-3.5-3.8B-vision-instruct-F16.gguf` (Higher quality, ~14GB)
- `bartowski/Llava-1.6-Mistral-7B-GGUF` (if available)
- `xtuner/llava-phi-3.5-vision-32k-GGUF` (if available)

## More Information

- [llama.cpp Vision Support](https://github.com/ggerganov/llama.cpp#multimodal-models)
- [Phi-3.5 Model Card](https://huggingface.co/abetlen/Phi-3.5-vision-instruct-gguf)
- [HuggingFace Hub](https://huggingface.co)

