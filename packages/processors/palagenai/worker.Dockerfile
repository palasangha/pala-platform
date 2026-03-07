# OCR Worker Dockerfile - Optimized for distributed processing
# This Dockerfile is specifically designed for OCR worker processes
#
# BUILD INSTRUCTIONS:
# For development with proper cache invalidation, use BuildKit:
#   DOCKER_BUILDKIT=1 docker-compose build ocr-worker
#
# If code changes aren't reflected, force rebuild:
#   DOCKER_BUILDKIT=1 docker-compose build --no-cache ocr-worker
#
# Key Design Decisions:
# 1. Separate from backend.Dockerfile to avoid layer caching issues
# 2. COPY backend/requirements.txt early for cache optimization
# 3. COPY backend /app as dedicated layer to detect code changes
# 4. Health check validates worker initialization
# 5. BuildKit cache mount speeds up pip installs
# 6. Uses explicit file copy for better cache invalidation

# Enable BuildKit for better caching
# syntax=docker/dockerfile:1.4

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OCR processing
# - gcc/g++: Compilation of native extensions
# - tesseract: OCR engine and language packs
# - poppler-utils: PDF text extraction
# - libgl1: OpenGL support for image processing
# - chromium/chromium-driver: Chrome Lens provider
# - Network tools: curl, wget, smbclient, openssh-client
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-spa \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    smbclient \
    openssh-client

# Copy requirements first for better layer caching
# This layer only rebuilds if requirements.txt changes
COPY backend/requirements.txt .

# Install Python dependencies with BuildKit cache mount
# Caches pip packages between builds for faster subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code - CRITICAL for cache invalidation
# Docker will detect file changes and rebuild this layer when:
# - Any Python file in backend/app/ changes
# - Worker runner script changes
# This is the key to detecting code changes properly
COPY backend/app ./app
COPY backend/run_worker.py .
COPY backend/run.py .

# Create uploads directory for processing results
RUN mkdir -p uploads && chmod 755 uploads

# Environment configuration
ENV PYTHONUNBUFFERED=1

# Health check - verify worker can import OCR modules
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from app.workers.ocr_worker import OCRWorker; print('worker_ok')" || exit 1

# Default command - overridden by docker-compose
# Each worker instance will be started with its own worker ID via HOSTNAME
CMD ["python", "run_worker.py", "--worker-id", "${HOSTNAME}", "--nsqlookupd", "nsqlookupd:4161"]
