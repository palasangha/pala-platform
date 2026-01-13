#!/bin/bash

# Script to download LLaVA Vision model for llama.cpp
# This script downloads the quantized GGUF models required for llama.cpp to run

set -e

echo "🚀 Downloading LLaVA Vision Model for llama.cpp..."
echo ""
echo "This will download LLaVA-1.5 model files (~5-6GB total)"
echo "Models will be saved to: ./models/"
echo ""

# Create models directory if it doesn't exist
mkdir -p ./models

echo "⏳ Downloading LLaVA-1.5 model (q4_k_m quantization)..."
cd ./models

echo "📥 Downloading LLaVA-1.5 (7B) - Recommended for OCR"
echo "   This is optimized for document understanding..."
echo ""

# LLaVA model (recommended for OCR)
if [ ! -f "ggml-model-q4_k_m.gguf" ]; then
    echo "📥 Downloading main LLaVA model (~4.5GB)..."
    echo "   Source: HuggingFace (mys/ggml_llava-v1.5-7b)"
    curl -L -o ggml-model-q4_k_m.gguf \
        "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k_m.gguf" || \
    echo "⚠️  Download failed. Try downloading manually from:"
    echo "    https://huggingface.co/mys/ggml_llava-v1.5-7b"
else
    echo "✓ ggml-model-q4_k_m.gguf already exists"
fi

if [ ! -f "mmproj-model-f16.gguf" ]; then
    echo ""
    echo "📥 Downloading vision projection model (~520MB)..."
    curl -L -o mmproj-model-f16.gguf \
        "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/mmproj-model-f16.gguf" || \
    echo "⚠️  Download failed. Try downloading manually from:"
    echo "    https://huggingface.co/mys/ggml_llava-v1.5-7b"
else
    echo "✓ mmproj-model-f16.gguf already exists"
fi

echo ""
echo "✅ Model download complete!"
echo ""
echo "📊 Models ready at:"
ls -lh *.gguf 2>/dev/null || echo "⚠️  No models found - check your downloads"

echo ""
echo "📝 Next steps:"
echo "1. Build the llama.cpp Docker image: docker-compose build llamacpp"
echo "2. Start the services: docker-compose up -d"
echo "3. Verify it's running: docker-compose logs llamacpp"
echo "4. Test the service: curl http://localhost:8001/health"
echo ""
echo "The llama.cpp service will be available at:"
echo "  - External: http://localhost:8001"
echo "  - Internal (Docker): http://llamacpp:8000"
echo ""
echo "⚠️  Model Download Alternatives:"
echo ""
echo "If HuggingFace download is slow, try these alternatives:"
echo ""
echo "  LLaVA-1.5 (13B) - Better accuracy (8GB):"
echo "    https://huggingface.co/TheBloke/llava-1.5-13b-GGUF"
echo ""
echo "  Llama3-Vision:"
echo "    https://huggingface.co/TheBloke/Llama-3-Vision-GGUF"
echo ""
echo "  After downloading, rename files to match docker-compose.yml:"
echo "    - Main model -> ggml-model-q4_k_m.gguf"
echo "    - Projection -> mmproj-model-f16.gguf"
echo ""

