# Setting Up Gemma3 Model for llama.cpp

This guide explains how to download and configure Gemma3 or alternative vision models for use with llama.cpp in GVPOCR.

## Quick Setup

### Option 1: Interactive Download Script (Recommended)

```bash
cd models/
chmod +x download_model.sh
./download_model.sh
```

This will prompt you to choose from:
1. **LLaVA 1.5 (7B)** - Best for OCR documents
2. **Llama 3 Vision (8B)** - Better understanding
3. **Gemma 3 Vision (7B)** - Latest Google model

### Option 2: Manual Download from HuggingFace

#### For LLaVA 1.5 (Recommended):
```bash
cd models/
huggingface-cli download TheBloke/llava-1.5-7b-GGUF llava-1.5-7b-Q4_K_M.gguf --local-dir . --local-dir-use-symlinks False
mv llava-1.5-7b-Q4_K_M.gguf ggml-model-q4_k_m.gguf
```

#### For Gemma 3 Vision:
```bash
cd models/
huggingface-cli download google/gemma-3-vision-7b-it-GGUF gemma-3-vision-7b-it-Q4_K_M.gguf --local-dir . --local-dir-use-symlinks False
mv gemma-3-vision-7b-it-Q4_K_M.gguf ggml-model-q4_k_m.gguf
```

#### For Llama 3 Vision:
```bash
cd models/
huggingface-cli download TheBloke/Llama-3-Vision-GGUF Llama-3-Vision-Q4_K_M.gguf --local-dir . --local-dir-use-symlinks False
mv Llama-3-Vision-Q4_K_M.gguf ggml-model-q4_k_m.gguf
```

## Installation Requirements

### Install HuggingFace CLI
```bash
pip install huggingface_hub
```

### For Large Models (>5GB)
You may need to:
1. Create a HuggingFace account: https://huggingface.co/
2. Get your access token: https://huggingface.co/settings/tokens
3. Login before downloading:
```bash
huggingface-cli login
# Paste your token when prompted
```

## Model Options & Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **LLaVA 1.5 (7B)** | 4.5GB | ⚡⚡⚡ | ⭐⭐⭐ | **Documents & OCR** |
| Llama 3 Vision (8B) | 7GB | ⚡⚡ | ⭐⭐⭐⭐ | General vision |
| Gemma 3 Vision (7B) | 7GB | ⚡⚡ | ⭐⭐⭐⭐ | General vision |
| LLaVA 1.6 (34B) | 20GB | ⚡ | ⭐⭐⭐⭐⭐ | Best accuracy |

**Recommendation**: Use **LLaVA 1.5** for best balance of speed and accuracy for OCR.

## Starting the Service

Once you have a model file named `ggml-model-q4_k_m.gguf` in the `models/` directory:

```bash
# Start the service
docker-compose up -d llamacpp

# Verify it's running
curl http://localhost:8007/health

# View logs
docker-compose logs -f llamacpp
```

## Configuration

The docker-compose.yml is already configured to use:
- Model path: `/models/ggml-model-q4_k_m.gguf`
- Port: 8007 (external) → 8000 (internal)
- Backend access: `http://llamacpp:8000`

## Using Different Model Files

If you want to use a model with a different filename:

1. Edit `docker-compose.yml`:
```yaml
llamacpp:
  command: ["-m", "/models/your-model-name.gguf", ...]
```

2. Restart the service:
```bash
docker-compose restart llamacpp
```

## Testing the Service

### Health Check
```bash
curl http://localhost:8007/health
# Should return: {"status": "ok"}
```

### In GVPOCR
1. Go to **OCR Review** or **Bulk Processing**
2. Select **"llama.cpp (Local LLM)"** from provider dropdown
3. Process an image
4. Check `docker-compose logs llamacpp` for processing details

## Troubleshooting

### "Model not found" error
```bash
# Verify file exists
ls -lh models/ggml-model-q4_k_m.gguf

# Check docker container can see it
docker-compose exec llamacpp ls -lh /models/
```

### "Out of memory" error
- Use a smaller quantization (Q4_K_M instead of F16)
- Use a smaller model (7B instead of 13B)
- Reduce context size in server configuration

### Download timeout
- Use a download manager like Aria2c
- Try downloading during off-peak hours
- Split into smaller chunks if available

### HuggingFace authentication needed
```bash
# Set token as environment variable
export HF_TOKEN="your_token_here"

# Or login via CLI
huggingface-cli login
```

## Additional Resources

- **HuggingFace Models**: https://huggingface.co/models?pipeline_tag=image-text-to-text
- **TheBloke GGUF Models**: https://huggingface.co/TheBloke
- **llama.cpp Docs**: https://github.com/ggerganov/llama.cpp/tree/master/examples/server
- **LLaVA**: https://github.com/haotian-liu/LLaVA
- **Gemma**: https://huggingface.co/google

## FAQ

**Q: Which model should I use?**
A: Start with LLaVA 1.5 (7B). It's optimized for documents and fastest.

**Q: Can I use multiple models?**
A: Yes! Run multiple llamacpp services on different ports, then configure backend to use specific one.

**Q: Does it require GPU?**
A: No, but GPU acceleration (CUDA) significantly speeds it up. CPU inference works but slower.

**Q: How much disk space do I need?**
A: ~10GB for model + ~5GB for other services.

**Q: Can I run this on old hardware?**
A: Models will work on CPU, but responses will be slower (~30-60 seconds per image).
