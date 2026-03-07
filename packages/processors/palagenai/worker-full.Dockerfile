# Worker Dockerfile - Full image with updated backend code
# This Dockerfile creates a complete worker image with the latest ocr_worker.py

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
    unzip \
    smbclient \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy backend code
COPY backend ./

# Set working directory
WORKDIR /app

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "run_worker.py"]
