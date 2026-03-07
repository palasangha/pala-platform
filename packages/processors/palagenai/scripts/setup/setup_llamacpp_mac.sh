#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      llamacpp GPU Setup for macOS (Apple Silicon/Intel)       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Detect Mac architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "✅ Detected: Apple Silicon (M1/M2/M3/M4)"
    GPU_TYPE="metal"
else
    echo "✅ Detected: Intel Mac"
    GPU_TYPE="auto"
fi
echo ""

# Check Docker Desktop
if ! command -v docker &> /dev/null; then
    echo "❌ Docker Desktop not installed"
    echo "   Install from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker installed"
DOCKER_VERSION=$(docker --version)
echo "   $DOCKER_VERSION"
echo ""

# Check for models
if [ ! -f "./models/ggml-model-q4_k_m.gguf" ]; then
    echo "❌ Vision model not found!"
    echo ""
    echo "📥 Downloading OCR model..."
    cd models
    python3 download_ocr_model.py
    if [ $? -ne 0 ]; then
        echo "❌ Download failed"
        exit 1
    fi
    cd ..
fi

MODEL_SIZE=$(du -h ./models/ggml-model-q4_k_m.gguf | cut -f1)
echo "✅ Vision model found (${MODEL_SIZE})"
echo "   File: ./models/ggml-model-q4_k_m.gguf"
echo ""

# Check projection model
if [ -f "./models/mmproj-model-f16.gguf" ]; then
    echo "✅ Vision projection model found"
    PROJ_SIZE=$(du -h ./models/mmproj-model-f16.gguf | cut -f1)
    echo "   File: ./models/mmproj-model-f16.gguf (${PROJ_SIZE})"
else
    echo "⚠️  Vision projection model not found (optional for some models)"
fi
echo ""

echo "═════════════════════════════════════════════════════════════════"
echo "🚀 Starting llamacpp with GPU acceleration..."
echo "═════════════════════════════════════════════════════════════════"
echo ""

# Build Dockerfile with Metal support if Apple Silicon
if [ "$ARCH" = "arm64" ]; then
    echo "📝 Building llamacpp Docker image with Metal GPU support..."
    docker build \
        -t gvpocr-llamacpp:latest \
        -f llama.cpp.Dockerfile \
        --build-arg CUDA_VISIBLE_DEVICES="" \
        .
else
    echo "📝 Building llamacpp Docker image..."
    docker build -t gvpocr-llamacpp:latest -f llama.cpp.Dockerfile .
fi

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo ""
echo "✅ Image built successfully"
echo ""
echo "🐳 Starting Docker container..."
docker-compose up -d llamacpp

if [ $? -ne 0 ]; then
    echo "❌ Failed to start container"
    docker-compose logs llamacpp
    exit 1
fi

echo ""
echo "⏳ Waiting for service to be ready..."
sleep 10

# Check health
for i in {1..30}; do
    if curl -s http://localhost:8007/health > /dev/null 2>&1; then
        echo ""
        echo "✅ Service is healthy!"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo ""
echo "═════════════════════════════════════════════════════════════════"
echo "🎉 Setup Complete!"
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Service Status:"
docker-compose ps llamacpp
echo ""
echo "🧪 Test the service:"
echo "   curl http://localhost:8007/health"
echo ""
echo "📖 View logs:"
echo "   docker-compose logs -f llamacpp"
echo ""
echo "💡 To use in your OCR pipeline:"
echo "   - Set LLAMACPP_ENABLED=true in .env"
echo "   - Set LLAMACPP_HOST=http://localhost:8007"
echo ""
