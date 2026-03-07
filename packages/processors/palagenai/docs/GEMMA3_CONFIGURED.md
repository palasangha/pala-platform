# Gemma3 Configuration for llama.cpp

This guide explains how to configure and use Google's Gemma3 Vision model with llama.cpp in GVPOCR.

## Quick Setup

### Step 1: Download Gemma3 Model

```bash
cd models/
chmod +x DOWNLOAD_GEMMA3.sh
./DOWNLOAD_GEMMA3.sh
```

You'll be prompted for your HuggingFace token. To get one:
1. Visit https://huggingface.co/settings/tokens
2. Create a new token (read access is sufficient)
3. Copy and paste when prompted

### Step 2: Start llama.cpp Service

```bash
cd ..
docker-compose up -d llamacpp
```

### Step 3: Verify Service

```bash
# Check health
curl http://localhost:8007/health

# View logs
docker-compose logs llamacpp
```

### Step 4: Use in GVPOCR

1. Go to OCR Review or Bulk Processing
2. Select "llama.cpp (Local LLM)" from provider dropdown
3. Process images!

## Configuration Details

### Current Setup

- **Model File**: `gemma3-vision-q4_k_m.gguf`
- **Model ID**: google/gemma-3-vision-7b-it-GGUF
- **Quantization**: Q4_K_M (4-bit, ~7GB)
- **Port**: 8007 (external) → 8000 (internal)
- **Docker Compose Command**:
  ```yaml
  command: ["-m", "/models/gemma3-vision-q4_k_m.gguf", "--host", "0.0.0.0", "--port", "8000"]
  ```

### Model Information

**Gemma3 Vision 7B**
- Size: ~7GB (Q4_K_M quantization)
- Vision Capability: ✅ Yes (multimodal)
- OCR Support: ✅ Yes
- Language Support: Multiple (English, Hindi, etc.)
- Performance: Good balance of speed and quality
- VRAM Required: 6-8GB for optimal performance

## Alternative Quantizations

If you want different size/quality tradeoffs:

### Q3_K_M (Smaller, Faster)
```bash
# Download
huggingface-cli download google/gemma-3-vision-7b-it-GGUF \
  gemma-3-vision-7b-it-Q3_K_M.gguf --local-dir .

# Update docker-compose.yml command to:
command: ["-m", "/models/gemma-3-vision-7b-it-Q3_K_M.gguf", "--host", "0.0.0.0", "--port", "8000"]

# Restart
docker-compose restart llamacpp
```

### Q5_K_M (Larger, Better Quality)
```bash
# Download
huggingface-cli download google/gemma-3-vision-7b-it-GGUF \
  gemma-3-vision-7b-it-Q5_K_M.gguf --local-dir .

# Update docker-compose.yml and restart
```

### F16 (Highest Quality, Very Large)
```bash
# Only recommended with 16GB+ VRAM
huggingface-cli download google/gemma-3-vision-7b-it-GGUF \
  gemma-3-vision-7b-it-f16.gguf --local-dir .
```

## Model Comparison

| Quantization | Size | Speed | Quality | VRAM | Recommended |
|--------------|------|-------|---------|------|-------------|
| Q3_K_M | 5GB | ⚡⚡⚡⚡ | ⭐⭐ | 4GB | Small systems |
| **Q4_K_M** | **7GB** | **⚡⚡⚡** | **⭐⭐⭐⭐** | **6GB** | **✅ Default** |
| Q5_K_M | 9GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 8GB | High quality |
| F16 | 14GB | ⚡ | ⭐⭐⭐⭐⭐ | 16GB | Best quality |

## Performance Expectations

### With GPU (CUDA 12+)
- First inference: 30-60 seconds (model load)
- Subsequent: 15-25 seconds per image
- Throughput: ~3-4 images per minute

### With CPU Only
- First inference: 60-120 seconds (model load)
- Subsequent: 30-60 seconds per image
- Throughput: ~1-2 images per minute

## Troubleshooting

### "Model not found" Error

```bash
# Verify file exists
ls -lh models/gemma3-vision-q4_k_m.gguf

# Check docker can see it
docker-compose exec llamacpp ls -lh /models/

# If missing, re-download
cd models/
./DOWNLOAD_GEMMA3.sh
```

### "Out of memory" Error

**Solution 1**: Use smaller quantization
```bash
# Download Q3_K_M instead
./DOWNLOAD_GEMMA3.sh
# Select smaller quantization when prompted
```

**Solution 2**: Add swap space
```bash
# Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### HuggingFace Authentication Failed

```bash
# Option 1: Use token directly
huggingface-cli login
# Paste your token

# Option 2: Set environment variable
export HF_TOKEN="hf_xxxxxxxxxxxx"
./DOWNLOAD_GEMMA3.sh

# Get token from: https://huggingface.co/settings/tokens
```

### Slow Inference Speed

**Check 1**: GPU is being used
```bash
# Verify GPU is available
nvidia-smi

# Check if llama.cpp is using it
docker-compose logs llamacpp | grep "GPU"
```

**Check 2**: Reduce context size (if applicable)
- Default is fine for most cases
- Contact support if needed for custom configurations

## Advanced Configuration

### Running Multiple Models

To use Gemma3 AND another model simultaneously:

```yaml
llamacpp:
  # Gemma3 on port 8007
  ...
  ports:
    - "8007:8000"

llamacpp-backup:
  # LLaVA on port 8008
  build:
    context: .
    dockerfile: llama.cpp.Dockerfile
  ports:
    - "8008:8000"
  volumes:
    - ./models:/models
  command: ["-m", "/models/llava-model.gguf", "--host", "0.0.0.0", "--port", "8000"]
```

Then update backend to use specific model:
```yaml
LLAMACPP_HOST=http://llamacpp:8000  # For Gemma3
```

### Custom Prompts

Send custom OCR prompts in API requests:

```bash
curl -X POST http://localhost:5000/api/ocr/process/{image_id} \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "llamacpp",
    "custom_prompt": "Extract all text from this document in structured format"
  }'
```

## Monitoring

### Check Service Status
```bash
docker-compose ps llamacpp
```

### View Real-time Logs
```bash
docker-compose logs -f llamacpp
```

### Monitor Resource Usage
```bash
docker stats llamacpp
```

### Check Model Loading
```bash
# Should see "Model loaded successfully!"
docker-compose logs llamacpp | grep -i "loaded\|error"
```

## File Structure

After setup, your directory should look like:

```
gvpocr/
├── models/
│   ├── gemma3-vision-q4_k_m.gguf    (← Your downloaded model ~7GB)
│   ├── DOWNLOAD_GEMMA3.sh            (← Download script)
│   └── README.md
├── docker-compose.yml                (← Updated for Gemma3)
├── llama.cpp.Dockerfile
├── server.py
└── GEMMA3_SETUP.md                   (← This file)
```

## Next Steps

1. **Download**: `cd models && ./DOWNLOAD_GEMMA3.sh`
2. **Start**: `docker-compose up -d llamacpp`
3. **Verify**: `curl http://localhost:8007/health`
4. **Use**: Select "llama.cpp (Local LLM)" in GVPOCR

## Support & Resources

- **Model Card**: https://huggingface.co/google/gemma-3-vision-7b-it-GGUF
- **Google Gemma**: https://ai.google.dev/gemma/
- **llama.cpp**: https://github.com/ggerganov/llama.cpp
- **GVPOCR Docs**: See LLAMACPP_DOCKER_SETUP.md

## FAQ

**Q: Do I need GPU?**
A: No, but it's much faster. CPU inference takes 30-60 seconds per image.

**Q: Can I use a different quantization?**
A: Yes! Download the alternative, update docker-compose.yml, and restart.

**Q: How much disk space do I need?**
A: ~15GB total (7GB model + 3GB Docker + 5GB buffer).

**Q: Is Gemma3 better than LLaVA?**
A: Different strengths. Gemma3 is newer; LLaVA better for OCR. Test both!

**Q: Can I switch models easily?**
A: Yes! Just download another model and update docker-compose.yml command.
