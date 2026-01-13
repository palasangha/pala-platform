# llama.cpp OCR Support Setup Guide

This guide explains how to set up and use llama.cpp as an OCR provider in GVPOCR.

## What is llama.cpp?

**llama.cpp** is a lightweight C++ implementation of LLaMA that allows you to run large language models locally on your machine without needing GPU acceleration (though it benefits from it). It supports various models including multimodal models that can process images for OCR tasks.

## Installation & Setup

### 1. Install llama.cpp

#### On Ubuntu/Debian:
```bash
# Clone the repository
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build from source
make

# Or use pre-built binaries
wget https://github.com/ggerganov/llama.cpp/releases/download/b1/llama-b1-linux-x64.zip
unzip llama-b1-linux-x64.zip
```

#### On macOS:
```bash
# Using Homebrew
brew install llama.cpp

# Or build from source
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
```

#### On Windows:
```bash
# Using WSL2 is recommended
# Or download pre-built binaries from:
# https://github.com/ggerganov/llama.cpp/releases
```

### 2. Download a Multimodal Model

For OCR tasks, you'll need a model that supports vision/image input. Recommended models:

- **LLaVA** - Good for document and image understanding
- **GPT-4V-like models** - If available in GGUF format
- **Llava-1.5** - Optimized for vision tasks

```bash
# Download LLaVA model (example)
cd llama.cpp/models
wget https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k.gguf
wget https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/mmproj-model-f16.gguf
```

### 3. Start llama.cpp Server

```bash
# Basic usage with single model
./server -m models/ggml-model-q4_k.gguf \
  --mmproj models/mmproj-model-f16.gguf \
  -ngl 33 \
  -p "Extract text from this image:" \
  --host 0.0.0.0 \
  --port 8000

# Options:
# -ngl 33     : GPU layers (adjust based on your GPU)
# --host      : Server hostname
# --port      : Server port
# -p          : Default prompt
# -t          : Number of threads (default: all available)
# -c          : Context size (default: 512)
```

### 4. Configure GVPOCR

Add these environment variables to your `.env` file:

```bash
# Enable llama.cpp provider
LLAMACPP_ENABLED=true

# llama.cpp server connection
LLAMACPP_HOST=http://localhost:8000

# Optional: Model name (for reference, llama.cpp uses loaded model)
LLAMACPP_MODEL=llava-v1.5

# Optional: Set as default OCR provider
DEFAULT_OCR_PROVIDER=llamacpp
```

Or in `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - LLAMACPP_ENABLED=true
      - LLAMACPP_HOST=http://llamacpp:8000
      - LLAMACPP_MODEL=llava-v1.5
      - DEFAULT_OCR_PROVIDER=llamacpp
```

### 5. Using Docker with llama.cpp

Create a `docker-compose.llamacpp.yml`:

```yaml
version: '3.8'

services:
  llamacpp:
    image: ghcr.io/ggerganov/llama.cpp:latest
    ports:
      - "8000:8000"
    volumes:
      - ./models:/models
    command: >
      /app/server -m /models/ggml-model-q4_k.gguf
      --mmproj /models/mmproj-model-f16.gguf
      -ngl 33
      --host 0.0.0.0
      --port 8000
    environment:
      - THREADS=8

  backend:
    environment:
      - LLAMACPP_ENABLED=true
      - LLAMACPP_HOST=http://llamacpp:8000
```

Run it:
```bash
docker-compose -f docker-compose.yml -f docker-compose.llamacpp.yml up
```

## Usage

### Via API

Select llama.cpp as the OCR provider when processing an image:

```bash
curl -X POST http://localhost:5000/api/ocr/process/{image_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "llamacpp",
    "languages": ["en", "hi"],
    "handwriting": false,
    "custom_prompt": "Extract all text from this document"
  }'
```

### Via Web UI

1. Navigate to an image in a project
2. In the OCR Review panel, select **"llama.cpp (Local LLM)"** from the Provider dropdown
3. Set language preferences
4. Click "Process OCR"

## Supported Models

### Vision-Capable Models (Recommended)

| Model | Size | Speed | Quality | Notes |
|-------|------|-------|---------|-------|
| LLaVA-1.5 (7B) | 4.5GB | Fast | Good | Best for OCR |
| LLaVA-1.5 (13B) | 8GB | Medium | Better | Higher accuracy |
| Llava-Mistral (7B) | 4.5GB | Fast | Good | Faster inference |
| Llama-2-Vision | 7-13GB | Medium | Good | Larger models |

### Quantization Formats

- **Q4_K_M** - Recommended, good balance of size and quality
- **Q5_K_M** - Better quality, larger size
- **Q8** - Highest quality, largest size
- **F16** - Highest quality, largest file

## Performance Optimization

### For CPU-only systems:
```bash
./server -m models/ggml-model-q4_k.gguf \
  -t 8 \
  -c 512 \
  --mmproj models/mmproj-model-f16.gguf
```

### For GPU systems (CUDA):
```bash
./server -m models/ggml-model-q4_k.gguf \
  -ngl 33 \
  -t 4 \
  --mmproj models/mmproj-model-f16.gguf
```

### For GPU systems (Metal - macOS):
```bash
./server -m models/ggml-model-q4_k.gguf \
  -ngl 1 \
  --mmproj models/mmproj-model-f16.gguf
```

## Troubleshooting

### llama.cpp server not responding
```bash
# Check if server is running
curl http://localhost:8000/health

# Check logs for errors
tail -f /var/log/llamacpp.log

# Restart with verbose output
./server -m models/ggml-model-q4_k.gguf -v
```

### Model not found
```bash
# Verify model files exist
ls -lah models/

# Check model path is correct in command
```

### Out of memory errors
```bash
# Use smaller quantization
# Change from q8 to q4_k_m

# Or reduce context size
./server -m models/ggml-model-q4_k.gguf -c 512
```

### Slow performance
```bash
# Increase GPU layers (-ngl)
./server -m models/ggml-model-q4_k.gguf -ngl 33

# Reduce context size
./server -m models/ggml-model-q4_k.gguf -c 256

# Reduce max tokens in GVPOCR config
```

## Advanced Configuration

### Custom Prompts

You can provide custom OCR prompts when processing images:

```bash
curl -X POST http://localhost:5000/api/ocr/process/{image_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "llamacpp",
    "custom_prompt": "Extract all text from this medical document. Format as structured data."
  }'
```

### Batch Processing with llama.cpp

The llama.cpp provider fully supports batch processing through the bulk OCR interface.

## Resources

- **llama.cpp GitHub**: https://github.com/ggerganov/llama.cpp
- **LLaVA Models**: https://huggingface.co/liuhaotian/llava-v1.5-7b-gguf
- **Model Quantization**: https://huggingface.co/TheBloke/
- **llama.cpp API Docs**: https://github.com/ggerganov/llama.cpp/tree/master/examples/server

## Limitations

- Image input must be base64-encoded (automatic in GVPOCR)
- Performance depends on model size and hardware
- Accuracy varies with model selection
- No GPU required but GPU acceleration is beneficial
